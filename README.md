# bands
bands is an internet relay chat bot.

## features
- covers all relevant portions of rfc's 1459 and 2812.
- ircv3 caps supported are `chghost` and `multi-prefix`.
- concurrent multi-server and multi-channel support.
- awareness of the channel, channel user, server and server user contexts.
- full state maniuplation and hot config reload through private messages on
  trusted servers.

and many more

## installation
```sh
# clone the repo
git clone --depth=1 https://github.com/gottaeat/bands
cd bands/

# create a configuration yaml following the specification and example below and
# put it in a path within this repo so that docker can reach it, e.g.
# $REPO_ROOT/files/config.yml

# spin up a container
docker compose run --rm --build=true bands \
    /bin/sh -c "\
        pip install --user --break-system-packages . && \
        bands -c ./files/config.yml"
```

## configuration
### specification
#### root
| key               | necessity     | description                                                                   |
|-------------------|---------------|-------------------------------------------------------------------------------|
| `wolfram_api_key` | optional      | (`str`) wolfram alpha api key for module support                              |
| `openai_key`      | optional      | (`str`) openai key for module support                                         |
| `quote_file`      | __required__  | (`str`) path to read/write channel quotes to and from, generated if not found |
| `doot_file`       | __required__  | (`str`) path to read/write server points to and from, generated if not found  |
| `servers`         | __required__  | list of servers to connect to on startup                                      |

#### servers
| key            | necessity                   | description                                                                      |
|----------------|-----------------------------|----------------------------------------------------------------------------------|
| `name`         | __required__                | (`str`) reference name for the network                                           |
| `address`      | __required__                | (`str`) network address                                                          |
| `port`         | __required__                | (`int`) network port                                                             |
| `passwd`       | optional                    | (`str`) network password                                                         |
| `botname`      | __required__                | (`str`) bot nick+ident                                                           |
| `tls`          | optional                    | (`bool`) enable tls, false by default                                            |
| `verify_tls`   | optional                    | (`bool`) verify tls, false by default                                            |
| `scroll_speed` | optional                    | (`int`) how long the wait before sending multiple lines (fakelag)                |
| `channels`     | __required__                | (`list of str's`) channel list to autojoin on startup                            |
| `allow_admin`  | optional                    | (`bool`) allow authentication and remote control on the server, false by default |
| `secret`       | required __if allow_admin__ | (`str`) authentication secret                                                    |

### example
```yml
wolfram_api_key: "XXXXX-XXXXXXXXXX"
openai_key: "sk-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
quote_file: ./files/quotes.json
doot_file: ./files/doots.json

servers:
  - name: privnet
    address: irc.cooldomain.to
    port: 6697
    passwd: topsekrit
    botname: bands
    tls: true
    channels:
      - "#mychannel"
      - "#mychannel2"
    allow_admin: true
    secret: EsDf/ZcdNp1whuZh
  - name: publicnet
    address: irc.example.com
    port: 6697
    botname: stacks
    tls: true
    verify_tls: true
    scroll_speed: 1
    channels:
      - "#pubchannel"
```

## usage
for user-accesible features, call `?help` in either the context of a channel or
a private message with the bot.

cmdline specific usage is:
```sh
usage: bands [-h] -c C [-d]

bands the IRC bot.

options:
  -h, --help  show this help message and exit
  -c C        Configuration YAML file.
  -d          Enable debugging.
```

## management
1. set at least one of the servers to have `allow_admin` and a `secret`.
2. privmsg the `botname` with `?auth $secret`.
3. call `?rcon help` for a list of management related functionality.
