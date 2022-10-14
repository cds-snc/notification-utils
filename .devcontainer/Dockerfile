FROM mcr.microsoft.com/vscode/devcontainers/python:0-3.9@sha256:9fef24b20e9d57b4afe94ddfe97853ecfb77d8187d25aa07529f5f815f6fa33d

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

COPY scripts/bootstrap.sh /usr/local/bin/
