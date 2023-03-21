# Container image that runs your code
FROM ubuntu:22.04@sha256:2adf22367284330af9f832ffefb717c78239f6251d9d0f58de50b86229ed1427

RUN apt update
RUN apt install -y python3-pip python3 git libmagic-dev

# Copies your code file from your action repository to the filesystem path `/` of the container
RUN mkdir app
COPY . /app
WORKDIR /app

RUN pip install -r requirements.txt

ENTRYPOINT ["sh", "/app/entrypoint.sh"]
