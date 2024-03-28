# Container image that runs your code
FROM ubuntu:22.04@sha256:77906da86b60585ce12215807090eb327e7386c8fafb5402369e421f44eff17e

RUN apt update
RUN apt install -y python3-pip python3 git libmagic-dev

# Copies your code file from your action repository to the filesystem path `/` of the container
RUN mkdir app
COPY . /app
WORKDIR /app

RUN pip install -r requirements.txt

ENTRYPOINT ["sh", "/app/entrypoint.sh"]
