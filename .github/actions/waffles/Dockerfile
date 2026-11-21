# Container image that runs your code
FROM python:3.15.1@sha256:dc005c4de6908d750269a5ee683da95b4cfb5bf419f69b8e95d98d9e44bb2841

RUN apt update
RUN apt install -y python3-pip python3 git libmagic-dev

# Copies your code file from your action repository to the filesystem path `/` of the container
RUN mkdir app
COPY . /app
WORKDIR /app

RUN pip install -r requirements.txt

ENTRYPOINT ["sh", "/app/entrypoint.sh"]
