FROM python:3.11-alpine AS bands

RUN \
    addgroup -g 1337 bands && \
    adduser -D -H -G bands -u 1337 bands

COPY . /repo

RUN pip install /repo

CMD ["/repo/docker/entrypoint.sh"]
