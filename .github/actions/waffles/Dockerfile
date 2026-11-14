# Container image that runs your code
FROM python:3.12@sha256:cad37dd20c7cac861af9003af8796d03ea7a998ec1e3a664429740fc9d7d2691

RUN apt update
RUN apt install -y python3-pip python3 git libmagic-dev

# Copies your code file from your action repository to the filesystem path `/` of the container
RUN mkdir app
COPY . /app
WORKDIR /app

RUN pip install -r requirements.txt

ENTRYPOINT ["sh", "/app/entrypoint.sh"]
