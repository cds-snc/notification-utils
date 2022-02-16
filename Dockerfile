#-----------------------------------
#               BASE
#-----------------------------------

#FROM python:3.6-alpine
FROM dockerlocal.artifactory.itp.extra/alpine:3.14.1 as base
 
ENV PYTHONDONTWRITEBYTECODE 1

RUN \
    echo "https://uk.alpinelinux.org/alpine/v3.14/main" > /etc/apk/repositories && \
    echo "https://uk.alpinelinux.org/alpine/v3.14/community" >> /etc/apk/repositories
    
RUN apk update
RUN apk add --no-cache python3 py3-pip python3-dev gcc musl-dev && rm -rf /var/cache/apk/*
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# update pip
RUN pip install --upgrade pip
RUN pip install wheel

WORKDIR /app
# Python dependencies

COPY . /app
RUN pip install -r requirements_for_test.txt

ENTRYPOINT [ "ptw" ]