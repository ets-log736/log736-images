#!/usr/bin/env python3
import argparse
import asyncio
import json
import random
import time

MAX_LINE = 65536

class Router:
    def __init__(self, config, seed):
        self.nodes = config["nodes"]
        self.rules = config.get("rules", [])
        self.started = time.monotonic()
        self.random = random.Random(seed)

    def elapsed_ms(self):
        return int((time.monotonic() - self.started) * 1000)

    def active(self, rule, msg):
        if rule.get("from") not in (None, "*", msg.get("source")):
            return False
        if rule.get("to") not in (None, "*", msg.get("destination")):
            return False
        if rule.get("message_type") not in (None, "*", msg.get("type")):
            return False
        window = rule.get("window")
        if window:
            now = self.elapsed_ms()
            start = int(window.get("start_ms", 0))
            end = start + int(window["duration_ms"])
            if not (start <= now < end):
                return False
        return True

    async def route(self, msg):
        destination = msg.get("destination")
        if destination not in self.nodes:
            return

        delay_ms = 0.0
        for rule in self.rules:
            if not self.active(rule, msg):
                continue
            if rule["type"] == "drop":
                if self.random.random() < float(rule["probability"]):
                    return
            elif rule["type"] == "delay":
                base = float(rule.get("base_ms", 0))
                jitter = float(rule.get("jitter_ms", 0))
                delay_ms += max(0.0, base + self.random.uniform(-jitter, jitter))
            elif rule["type"] == "unavailable":
                return

        if delay_ms:
            await asyncio.sleep(delay_ms / 1000.0)

        endpoint = self.nodes[destination]
        try:
            reader, writer = await asyncio.open_connection(endpoint["host"], endpoint["port"])
            writer.write((json.dumps(msg, separators=(",", ":")) + "\n").encode("utf-8"))
            await writer.drain()
            writer.close()
            await writer.wait_closed()
        except OSError:
            return

async def client(reader, writer, router):
    try:
        while True:
            line = await reader.readline()
            if not line:
                break
            if len(line) > MAX_LINE:
                break
            try:
                msg = json.loads(line.decode("utf-8"))
            except Exception:
                continue
            if not isinstance(msg, dict):
                continue
            if msg.get("version") != 1:
                continue
            if not isinstance(msg.get("source"), str):
                continue
            if not isinstance(msg.get("destination"), str):
                continue
            asyncio.create_task(router.route(msg))
    finally:
        writer.close()
        await writer.wait_closed()

async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=7600)
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        config = json.load(f)

    router = Router(config, args.seed)
    server = await asyncio.start_server(
        lambda r, w: client(r, w, router),
        args.host,
        args.port,
        limit=MAX_LINE + 1,
    )
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())
