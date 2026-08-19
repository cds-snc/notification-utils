# Container image that runs your code
FROM python:3.12@sha256:e5931cdb4a8cec0ad083277c16a39114f14123b8b6c858c8c9689b677789975c

RUN apt update
RUN apt install -y python3-pip python3 git libmagic-dev

# Copies your code file from your action repository to the filesystem path `/` of the container
RUN mkdir app
COPY . /app
WORKDIR /app

RUN pip install -r requirements.txt

ENTRYPOINT ["sh", "/app/entrypoint.sh"]
