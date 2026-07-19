FROM python:3.11.15-alpine3.24 AS bands

RUN \
    addgroup -g 1337 bands && \
    adduser -D -H -G bands -u 1337 bands

COPY . /repo

RUN pip install --no-cache-dir /repo

CMD ["/repo/docker/entrypoint.sh"]
