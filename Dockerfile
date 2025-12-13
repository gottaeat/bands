FROM python:3.11.14-alpine3.23 AS bands

RUN \
    addgroup -g 1337 bands && \
    adduser -D -H -G bands -u 1337 bands

COPY . /repo

RUN pip install /repo

CMD ["/repo/docker/entrypoint.sh"]
