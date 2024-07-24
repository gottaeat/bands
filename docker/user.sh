#!/bin/sh
. /repo/docker/common

trap shutdown SIGTERM SIGINT

pinfo "setting envvars"
export HOME="/app"
export PATH="${HOME}/.local/bin:${PATH}"

pinfo "starting bands"
exec bands -c /data/config.yml
