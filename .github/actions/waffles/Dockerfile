# Container image that runs your code
FROM python:3.9@sha256:cfcc9ef77b6cf87f57327aacc6f9b50c7cdb4d7dd93662a36549f05b7403cd47

# Copies your code file from your action repository to the filesystem path `/` of the container
RUN mkdir app
COPY . /app
WORKDIR /app

RUN pip install -r requirements.txt

ENTRYPOINT ["sh", "/app/entrypoint.sh"]
