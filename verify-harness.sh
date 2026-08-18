#!/bin/sh
set -eu

python3 -m py_compile \
    harness/clock_service.py \
    harness/fault_router.py \
    harness/raft_client.py \
    harness/counter_client.py

echo "Harness sources are syntactically valid."
