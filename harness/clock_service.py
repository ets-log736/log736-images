#!/usr/bin/env python3
import argparse
import asyncio
import json
import time
import uuid

MAX_LINE = 65536

class SimulatedClock:
    def __init__(self, offset_ms: int, drift_ppm: float):
        self.offset_ms = offset_ms
        self.drift_ppm = drift_ppm
        self.start_real_ns = time.time_ns()
        self.start_mono_ns = time.monotonic_ns()

    def now_ms(self) -> int:
        elapsed_ms = (time.monotonic_ns() - self.start_mono_ns) / 1_000_000.0
        drift_ms = elapsed_ms * self.drift_ppm / 1_000_000.0
        reference_ms = self.start_real_ns / 1_000_000.0 + elapsed_ms
        return int(round(reference_ms + self.offset_ms + drift_ms))

async def serve(reader, writer, clock):
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
            if msg.get("version") != 1 or msg.get("type") != "local_time_request":
                continue
            request_id = msg.get("message_id")
            if not isinstance(request_id, str) or not request_id:
                continue
            reply = {
                "version": 1,
                "type": "local_time_response",
                "message_id": f"clock-{uuid.uuid4().hex[:12]}",
                "in_reply_to": request_id,
                "local_time_ms": clock.now_ms(),
            }
            writer.write((json.dumps(reply, separators=(",", ":")) + "\n").encode("utf-8"))
            await writer.drain()
    finally:
        writer.close()
        await writer.wait_closed()

async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=7900)
    ap.add_argument("--offset-ms", type=int, required=True)
    ap.add_argument("--drift-ppm", type=float, default=0.0)
    args = ap.parse_args()

    clock = SimulatedClock(args.offset_ms, args.drift_ppm)
    server = await asyncio.start_server(
        lambda r, w: serve(r, w, clock),
        args.host,
        args.port,
        limit=MAX_LINE + 1,
    )
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())
