# Container image that runs your code
FROM python:3.9@sha256:c1613835d7be322f98603f356b9e0c9d40f9589e94dc9f710e714a807a665700

# Copies your code file from your action repository to the filesystem path `/` of the container
RUN mkdir app
COPY . /app
WORKDIR /app

RUN pip install -r requirements.txt

ENTRYPOINT ["sh", "/app/entrypoint.sh"]
