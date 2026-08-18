#!/usr/bin/env python3
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
        self.timeout = int(config.get("request_timeout_ms", 900)) / 1000.0
        self.pending = {}
        self.leader_hint = None
        self.started = time.monotonic()

    async def send(self, message):
        try:
            _, writer = await asyncio.open_connection(self.router_host, self.router_port)
            writer.write((json.dumps(message, separators=(",", ":")) + "\n").encode("utf-8"))
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
                    msg = json.loads(line.decode("utf-8"))
                except Exception:
                    continue
                payload = msg.get("payload", {}) if isinstance(msg, dict) else {}
                reply = payload.get("in_reply_to")
                fut = self.pending.get(reply)
                if fut is not None and not fut.done():
                    fut.set_result(msg)
        finally:
            writer.close()
            await writer.wait_closed()

    async def request(self, destination, message_type, payload):
        mid = f"client-{uuid.uuid4().hex[:12]}"
        fut = asyncio.get_running_loop().create_future()
        self.pending[mid] = fut
        msg = {
            "version": 1,
            "type": message_type,
            "message_id": mid,
            "source": "client",
            "destination": destination,
            "payload": payload,
        }
        if not await self.send(msg):
            self.pending.pop(mid, None)
            return None
        try:
            return await asyncio.wait_for(asyncio.shield(fut), timeout=self.timeout)
        except asyncio.TimeoutError:
            return None
        finally:
            self.pending.pop(mid, None)

    async def command(self, action):
        command = action["command"]
        request_id = action.get("request_id", f"req-{uuid.uuid4().hex[:8]}")
        candidates = []
        if self.leader_hint in self.nodes:
            candidates.append(self.leader_hint)
        target = action.get("target", "auto")
        if target != "auto" and target in self.nodes and target not in candidates:
            candidates.append(target)
        candidates.extend(n for n in self.nodes if n not in candidates)

        for _ in range(2):
            for node in list(candidates):
                response = await self.request(
                    node,
                    "client_command",
                    {"request_id": request_id, "command": command},
                )
                if response is None:
                    continue
                payload = response.get("payload", {})
                emit({"event": "client_observation", "kind": "command", "target": node, "response": response})
                hint = payload.get("leader_id")
                if isinstance(hint, str) and hint in self.nodes:
                    self.leader_hint = hint
                if payload.get("status") == "ok":
                    self.leader_hint = response.get("source")
                    return
            await asyncio.sleep(0.15)
        emit({"event": "client_timeout", "kind": "command", "request_id": request_id})

    async def status(self, action):
        target = action.get("target", "all")
        targets = self.nodes if target == "all" else [target]
        for node in targets:
            response = await self.request(node, "status_request", {})
            if response is None:
                emit({"event": "client_timeout", "kind": "status", "target": node})
            else:
                emit({"event": "client_observation", "kind": "status", "target": node, "response": response})

    async def run_actions(self):
        for action in sorted(self.config.get("actions", []), key=lambda a: int(a.get("at_ms", 0))):
            at = int(action.get("at_ms", 0)) / 1000.0
            delay = at - (time.monotonic() - self.started)
            if delay > 0:
                await asyncio.sleep(delay)
            if action["type"] == "command":
                await self.command(action)
            elif action["type"] == "status":
                await self.status(action)


async def async_main(path):
    config = json.load(open(path, "r", encoding="utf-8"))
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
