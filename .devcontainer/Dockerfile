FROM mcr.microsoft.com/vscode/devcontainers/python:0-3.10@sha256:ef9cc483a593c95e1e83f2cf00b6a0e1ec7df43344416a41ccb3a88aef27beac

ENV POETRY_VERSION="1.3.2"

RUN apt-get update \
    && apt-get -y install --no-install-recommends apt-utils 2>&1 \
    && apt-get -y install \
        curl \
        emacs \
        exa \
        fd-find \
        git \
        iproute2 \
        less \
        libsodium-dev \
        lsb-release \
        man-db \
        manpages \
        net-tools \
        openssh-client \
        procps \
        sudo \
        tldr \
        unzip \
        vim \
    && apt-get autoremove -y \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip

RUN pip install poetry==${POETRY_VERSION} \
  && poetry --version

COPY .devcontainer/scripts/notify-dev-entrypoint.sh /usr/local/bin/
