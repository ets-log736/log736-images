#!/bin/sh
set -eu

IMAGE=${1:-ghcr.io/ets-log736/toolchain:a2026}

podman run --rm "$IMAGE" bash -c '
set -eu

echo "C:"
gcc --version | head -n 1

echo
echo "C++:"
g++ --version | head -n 1

echo
echo "Go:"
go version

echo
echo "Java:"
java -version

echo
echo "Python:"
python3 --version

echo
echo "Node.js:"
node --version

echo
echo "npm:"
npm --version
'
