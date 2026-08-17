# LOG736 Toolchain

Container image used to build and execute LOG736 laboratory submissions.

## Image

```text
ghcr.io/ets-log736/toolchain:a2026
```

The image is based on Ubuntu 24.04 and contains:

- C and C++ (`gcc`, `g++`, `make`)
- Go
- Java 21
- Python 3
- Node.js and npm
- Git and basic Unix tools

## Pull

```sh
podman pull ghcr.io/ets-log736/toolchain:a2026
```

## Build locally

```sh
podman build \
  -f Containerfile \
  -t localhost/log736/toolchain:a2026 \
  .
```

## Verify locally

```sh
./verify-toolchain.sh localhost/log736/toolchain:a2026
```

## Publication

Pushing a change to `Containerfile` or the publishing workflow on `main`
triggers GitHub Actions and publishes:

```text
ghcr.io/ets-log736/toolchain:a2026
```

After the first publication, make the GHCR package public in the package
settings so students can pull it without GitHub authentication.
