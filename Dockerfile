FROM alpine:3.19.1 AS bands-pyenv

ARG PYTHON_VERSION=3.11.4

RUN \
    apk update && \
    apk upgrade && \
    apk --no-cache add \
        bash build-base bzip2-dev git libffi-dev openssl-dev readline-dev \
        sqlite-dev tk-dev xz-dev zlib-dev && \
    adduser bands -D -h /home/bands -s /bin/bash

USER bands
WORKDIR /home/bands

ENV HOME="/home/bands"
ENV PYENV_ROOT="$HOME/.pyenv"
ENV PATH="$PYENV_ROOT/shims:$PYENV_ROOT/bin:$PATH"

RUN \
    git clone --depth=1 --recursive --shallow-submodules \
        https://github.com/pyenv/pyenv.git .pyenv && \
    cd ~/.pyenv && \
    src/configure && \
    make -C src && \
    git clone --depth=1 --recursive --shallow-submodules \
        https://github.com/pyenv/pyenv-virtualenv.git \
        $(pyenv root)/plugins/pyenv-virtualenv && \
    pyenv install $PYTHON_VERSION && \
    pyenv global $PYTHON_VERSION
