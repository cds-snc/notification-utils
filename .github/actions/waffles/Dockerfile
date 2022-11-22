# Container image that runs your code
FROM python:3.9@sha256:475fe86ebf1da48ea27009a8f7d7e96231af4142de918a68010d48d0abb9c9c5

# Copies your code file from your action repository to the filesystem path `/` of the container
RUN mkdir app
COPY . /app
WORKDIR /app

RUN pip install -r requirements.txt

ENTRYPOINT ["sh", "/app/entrypoint.sh"]
