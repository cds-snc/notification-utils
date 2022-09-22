FROM mcr.microsoft.com/vscode/devcontainers/python:0-3.9@sha256:b90ac675323f1cd915e157fcd2841455c724ab09effb96cfb22f39c991f373ff

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
