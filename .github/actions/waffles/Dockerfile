# Container image that runs your code
FROM ubuntu:22.04

RUN apt update
RUN apt install -y python3-pip python3

# Copies your code file from your action repository to the filesystem path `/` of the container
RUN mkdir app
COPY . /app
WORKDIR /app

RUN pip3 install -r requirements.txt

ENTRYPOINT ["sh", "/app/entrypoint.sh"]
