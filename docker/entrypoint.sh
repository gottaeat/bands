#!/bin/sh
. /repo/docker/common

# - - sanity checks - - #
if ! mountpoint /data >/dev/null 2>&1; then
    perr "/data is not bind mounted, exiting."
fi

if [ ! -f "/data/config.yml" ]; then
    perr "/data does not contain a config.yml."
fi

# - - hand over - - #
pinfo "setting permissions"
chown -Rh bands:bands /data
evalret

pinfo "starting bands"
exec su bands -c 'bands -c /data/config.yml'
