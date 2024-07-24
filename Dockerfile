FROM alpine:latest AS bands

COPY . /repo

RUN \
    apk update && apk upgrade && \
    apk --no-cache add py3-pip && \
    addgroup -g 1337 bands && \
    adduser -D -h /app -G bands -u 1337 bands

USER bands
RUN \
    pip install --user --break-system-packages /repo

USER root
WORKDIR /data

CMD /repo/docker/entrypoint.sh
