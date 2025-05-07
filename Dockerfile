FROM python:3.13-alpine3.20

ENV M365_PROXY_CONFIG_FILE=/config/config.json

WORKDIR /app

# Install build dependencies and required runtime packages
RUN apk add --no-cache --virtual .build-deps \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    python3-dev \
    build-base \
    && apk add --no-cache sqlite-libs=3.45.3-r2 libffi openssl tzdata \
    && python3 -m ensurepip \
    && pip install --no-cache-dir --upgrade "pip>=24.0" "setuptools>=69.5.1" "wheel>=0.42.0" \
    && rm -r /usr/lib/python*/ensurepip

COPY requirements.txt .
RUN pip install --no-cache-dir --no-compile --no-warn-script-location -r requirements.txt \
    && pip cache purge \
    && apk del .build-deps

COPY . .
RUN mkdir -p /app/queue

# Create non-root user and switch to it
RUN adduser -D -u 1000 mproxy
USER mproxy

ENTRYPOINT ["python", "-m", "m365proxy"]
