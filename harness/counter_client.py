#!/usr/bin/env python3
# Copie publique de référence. Les scénarios exécutent normalement la version
# contenue dans ghcr.io/ets-log736/harness:a2026.
import argparse
import asyncio
import json
import time
import uuid

MAX_LINE = 65536


def emit(obj):
    print(json.dumps(obj, separators=(",", ":")), flush=True)


class Driver:
    def __init__(self, config):
        self.config = config
        self.router_host = config["router"]["host"]
        self.router_port = int(config["router"]["port"])
        self.nodes = list(config["nodes"])
        self.timeout = (
            int(config.get("request_timeout_ms", 900)) / 1000.0
        )
        self.pending = {}
        self.started = time.monotonic()

    async def send(self, message):
        try:
            _, writer = await asyncio.open_connection(
                self.router_host,
                self.router_port,
            )
            writer.write(
                (
                    json.dumps(message, separators=(",", ":"))
                    + "\n"
                ).encode("utf-8")
            )
            await writer.drain()
            writer.close()
            await writer.wait_closed()
            return True
        except OSError:
            return False

    async def handle_conn(self, reader, writer):
        try:
            while True:
                line = await reader.readline()
                if not line or len(line) > MAX_LINE:
                    break
                try:
                    message = json.loads(line.decode("utf-8"))
                except Exception:
                    continue
                payload = (
                    message.get("payload", {})
                    if isinstance(message, dict)
                    else {}
                )
                reply = payload.get("in_reply_to")
                future = self.pending.get(reply)
                if future is not None and not future.done():
                    future.set_result(message)
        finally:
            writer.close()
            await writer.wait_closed()

    async def request(self, destination, message_type, payload):
        message_id = f"client-{uuid.uuid4().hex[:12]}"
        future = asyncio.get_running_loop().create_future()
        self.pending[message_id] = future

        message = {
            "version": 1,
            "type": message_type,
            "message_id": message_id,
            "source": "client",
            "destination": destination,
            "payload": payload,
        }

        if not await self.send(message):
            self.pending.pop(message_id, None)
            return None

        try:
            return await asyncio.wait_for(
                asyncio.shield(future),
                timeout=self.timeout,
            )
        except asyncio.TimeoutError:
            return None
        finally:
            self.pending.pop(message_id, None)

    def target(self, action):
        target = action.get("target", "auto")
        if target == "auto":
            return self.nodes[0]
        if target not in self.nodes:
            raise ValueError(f"unknown target {target}")
        return target

    async def update(self, action):
        node = self.target(action)
        request_id = action.get(
            "request_id",
            f"op-{uuid.uuid4().hex[:8]}",
        )
        response = await self.request(
            node,
            "counter_update",
            {
                "request_id": request_id,
                "delta": int(action["delta"]),
            },
        )
        if response is None:
            emit(
                {
                    "event": "client_timeout",
                    "kind": "update",
                    "target": node,
                    "request_id": request_id,
                }
            )
        else:
            emit(
                {
                    "event": "client_observation",
                    "kind": "update",
                    "target": node,
                    "response": response,
                }
            )

    async def read(self, action):
        node = self.target(action)
        response = await self.request(
            node,
            "counter_read",
            {},
        )
        if response is None:
            emit(
                {
                    "event": "client_timeout",
                    "kind": "read",
                    "target": node,
                }
            )
        else:
            emit(
                {
                    "event": "client_observation",
                    "kind": "read",
                    "target": node,
                    "response": response,
                }
            )

    async def status(self, action):
        target = action.get("target", "all")
        targets = self.nodes if target == "all" else [target]
        for node in targets:
            response = await self.request(
                node,
                "status_request",
                {},
            )
            if response is None:
                emit(
                    {
                        "event": "client_timeout",
                        "kind": "status",
                        "target": node,
                    }
                )
            else:
                emit(
                    {
                        "event": "client_observation",
                        "kind": "status",
                        "target": node,
                        "response": response,
                    }
                )

    async def run_actions(self):
        actions = sorted(
            self.config.get("actions", []),
            key=lambda item: int(item.get("at_ms", 0)),
        )
        for action in actions:
            target_time = int(action.get("at_ms", 0)) / 1000.0
            delay = target_time - (
                time.monotonic() - self.started
            )
            if delay > 0:
                await asyncio.sleep(delay)

            if action["type"] == "update":
                await self.update(action)
            elif action["type"] == "read":
                await self.read(action)
            elif action["type"] == "status":
                await self.status(action)


async def async_main(path):
    with open(path, "r", encoding="utf-8") as handle:
        config = json.load(handle)

    driver = Driver(config)
    server = await asyncio.start_server(
        driver.handle_conn,
        config["listen"]["host"],
        int(config["listen"]["port"]),
        limit=MAX_LINE + 1,
    )
    async with server:
        await driver.run_actions()
        await asyncio.sleep(0.5)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    args = ap.parse_args()
    asyncio.run(async_main(args.config))


if __name__ == "__main__":
    main()
