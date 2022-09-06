FROM python:3.9-alpine

RUN apk add --no-cache bash git build-base && rm -rf /var/cache/apk/*

RUN pip install --upgrade pip

WORKDIR /app

COPY . .

RUN pip install -r requirements_for_test.txt

CMD ls
