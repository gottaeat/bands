FROM alpine:latest AS bands

RUN \
    apk update && \
    apk upgrade && \
    apk --no-cache add py3-pip && \
    adduser bands -D -h /home/bands

USER bands
WORKDIR /repo

ENV PATH="/home/bands/.local/bin:$PATH"
