FROM python:3.5-slim@sha256:2348c9c9fa90808066919c036d59919fbf82c7f9277c2ff8b6b8cc6e72f5b9d7

ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY

ENV PYTHONUNBUFFERED=1 \
	DEBIAN_FRONTEND=noninteractive

RUN \
	echo "Install base packages" \
	&& ([ -z "$HTTP_PROXY" ] || echo "Acquire::http::Proxy \"${HTTP_PROXY}\";" > /etc/apt/apt.conf.d/99HttpProxy) \
	&& apt-get update \
	&& apt-get install -y --no-install-recommends \
		apt-transport-https \
		make \
		curl \
		git \
		build-essential \

	&& echo "Clean up" \
	&& rm -rf /var/lib/apt/lists/* /tmp/*

RUN \
	echo "Install global pip packages" \
	&& pip install \
		virtualenv

WORKDIR /var/project
