# Container image that runs your code
FROM python:3.11.0@sha256:10fc14aa6ae69f69e4c953cffd9b0964843d8c163950491d2138af891377bc1d

# Copies your code file from your action repository to the filesystem path `/` of the container
RUN mkdir app
COPY . /app
WORKDIR /app

RUN pip install -r requirements.txt

ENTRYPOINT ["sh", "/app/entrypoint.sh"]
