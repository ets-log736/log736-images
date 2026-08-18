# LOG736 Images

Public container images used by the LOG736 laboratory infrastructure.

Both images are based on Ubuntu 24.04.

## Toolchain

```text
ghcr.io/ets-log736/toolchain:a2026
```

Contains:

- C and C++ (`gcc`, `g++`, `make`)
- Go
- Java 21
- Python 3
- Node.js and npm
- Git and basic Unix tools

Pull:

```sh
podman pull ghcr.io/ets-log736/toolchain:a2026
```

Verify:

```sh
./verify-toolchain.sh ghcr.io/ets-log736/toolchain:a2026
```

## Public harness

```text
ghcr.io/ets-log736/harness:a2026
```

Contains the public Lab 1 infrastructure services:

- simulated local clock;
- NDJSON fault router.

Pull:

```sh
podman pull ghcr.io/ets-log736/harness:a2026
```

Verify:

```sh
./verify-harness.sh ghcr.io/ets-log736/harness:a2026
```

## Build locally

```sh
podman build -f Containerfile \
  -t localhost/ets-log736/toolchain:a2026 .

podman build -f Containerfile.harness \
  -t ghcr.io/ets-log736/harness:a2026 .
```

## Publication

Pushing changes to `main` automatically publishes:

```text
ghcr.io/ets-log736/toolchain:a2026
ghcr.io/ets-log736/harness:a2026
```

Both GHCR packages should be configured as public so that students and
laboratory machines can pull them anonymously.

Hidden scenarios, grading logic, and evaluator secrets are not included in
either image.


## Lab 2

The public harness also contains `raft_client.py`, used by the Lab 2 public Raft scenarios.
