FROM python:3.13-alpine

ENV M365_PROXY_CONFIG_FILE=/config/config.json
WORKDIR /app

RUN apk add --no-cache libffi openssl tzdata \
    && pip install --no-cache-dir m365proxy

RUN adduser -D -u 1000 mproxy
USER mproxy

ENTRYPOINT ["python", "-m", "m365proxy"]
CMD ["-log-level WARNING"]