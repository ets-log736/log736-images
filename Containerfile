FROM ubuntu:24.04

LABEL org.opencontainers.image.source="https://github.com/ets-log736/log736-images"
LABEL org.opencontainers.image.description="LOG736 course toolchain"
LABEL org.opencontainers.image.title="LOG736 Toolchain"

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        build-essential \
        ca-certificates \
        git \
        golang-go \
        openjdk-21-jdk-headless \
        nodejs \
        npm \
        python3 \
        python3-pip \
        python3-venv \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /submission
