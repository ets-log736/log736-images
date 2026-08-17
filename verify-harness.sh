#!/bin/sh
set -eu

IMAGE=${1:-ghcr.io/ets-log736/harness:a2026}

podman run --rm "$IMAGE" python3 -c '
import pathlib
for name in ("clock_service.py", "fault_router.py"):
    path = pathlib.Path("/opt/log736") / name
    assert path.is_file(), f"missing {path}"
print("LOG736 harness image OK")
'
