# Container image that runs your code
FROM ubuntu:22.04@sha256:58b87898e82351c6cf9cf5b9f3c20257bb9e2dcf33af051e12ce532d7f94e3fe

RUN apt update
RUN apt install -y python3-pip python3 git libmagic-dev

# Copies your code file from your action repository to the filesystem path `/` of the container
RUN mkdir app
COPY . /app
WORKDIR /app

RUN pip install -r requirements.txt

ENTRYPOINT ["sh", "/app/entrypoint.sh"]
