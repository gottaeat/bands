# bands
bands is an internet relay chat bot daemon.

## features
- covers all relevant portions of rfc's 1459 and 2812.
- ircv3 caps supported are `chghost` and `multi-prefix`.
- concurrent multi-server and multi-channel support.
- awareness of the channel, channel user, server and server user contexts.
- state manipulation and config rehash via plaintext over TCP.
- sqlite for stateful changes, in-memory for the rest.
- openai responses api support for modules.

## modules
### channel commands
a channel command is a query that starts with a channel's configured prefix, the
default being `?`. successfully ran recognized commands are ratelimited per
channel.

| command | class         | description                                             |
| ------- | ------------- | ------------------------------------------------------- |
| `ai`    | `AIQuery()`   | query a stateless question via the openai responses api |
| `bj`    | `BlackJack()` | wager blackjack bets via user points                    |
| `help`  | `Help()`      | print commands enabled for the channel context          |
| `point` | `Point()`     | give/remove points from users, show server-wide stats   |
| `quote` | `Quote()`     | add/get channel-wide quotes from users                  |
| `tarot` | `Tarot()`     | pull a deck and ask openai for a reading                |

### channel hooks
hooks match on defined regex and run the handler for it. like commands, hooks
are ratelimited.

| hook             | class             | description                            |
| ---------------- | ----------------- | -------------------------------------- |
| `url_dispatcher` | `URLDispatcher()` | match on URLs and print the page title |

### private messages
direct `PRIVMSG` commands to the bot use the hardcoded `?` prefix and are
ratelimited per server user.

| command | class    | description                     |
| ------- | -------- | ------------------------------- |
| `help`  | `Help()` | print private message commands  |
| `ping`  | `Ping()` | reply pong                      |

### control
main bot process is `bandsd` and by default starts listening on `0.0.0.0:1337`
for control commands. `bandsctl` is the reference client implementation that
talks to `bandsd`.

__WARNING__: comms are done over plain TCP, so do _NOT_ expose it to the global
internet.

| command      | description                                                   |
| ------------ | ------------------------------------------------------------- |
| `help`       | print c&c help                                                |
| `rehash` [1] | reload config and parse any new servers                       |
| `debug`      | toggle debug logging or print the current log level           |
| `status`     | display detailed info about servers, channels and their users |
| `cmd`        | enable/disable or list disabled commands for a channel        |
| `usercmd`    | enable/disable or list disabled user commands                 |
| `hook`       | enable/disable or list disabled hooks for a channel           |
| `prefix`     | set the command prefix for a channel                          |
| `connect`    | connect to a loaded server                                    |
| `dc` [2]     | disconnect from and remove all handling of a server           |
| `raw`        | send a raw iorc line to a server                              |
| `join`       | join a channel                                                |
| `part`       | part a channel                                                |
| `say`        | send a message to a channel                                   |

__[1]__ `rehash` reloads yaml and parses server definitions. it skips servers
which are already loaded. it does not reparse `openai_key`, `sqlite_file` or
`ctl_port`.

__[2]__ `dc` removes the server from the live in-memory server list. use
`rehash` to load it from the config again before calling `connect`.

## installation
```sh
# 1. get the compose file
curl -LO \
    https://raw.githubusercontent.com/gottaeat/bands/master/docker-compose.yml

# 2. create the volume mount
mkdir data/; cd data/

# 3. create a config.yml within this directory following the spec and the
#    example below

# 4. compose up
cd ../
docker compose up -d
```

## configuration
### specification
#### root
| key           | necessity    | type   | description                               |
| ------------- | ------------ | ------ | ----------------------------------------- |
| `openai_key`  | optional     | `str`  | openai api key for module support         |
| `sqlite_file` | optional     | `str`  | path to the sqlite database [1]           |
| `ctl_port`    | optional     | `int`  | port for the `bandsctl` tcp listener [2]  |
| `servers`     | __required__ | `list` | list of servers to connect to on startup  |

__[1]__ if not specified, defaults to `/data/bands.sqlite3`. bands will create
the parent directory and initialize the database if it does not exist.

__[2]__ if not specified, defaults to `1337`. the listener binds to `0.0.0.0`;
publish or firewall it accordingly.

#### servers
| key            | necessity                    | type   | description                                                         |
| -------------- | ---------------------------- | ------ | ------------------------------------------------------------------- |
| `name`         | __required__                 | `str`  | reference name for the network                                      |
| `address`      | __required__                 | `str`  | network address                                                     |
| `port`         | __required__                 | `int`  | network port                                                        |
| `passwd`       | optional                     | `str`  | network password                                                    |
| `botname`      | __required__                 | `str`  | bot nick+ident                                                      |
| `tls`          | optional                     | `bool` | enable tls, false by default                                        |
| `verify_tls`   | optional                     | `bool` | verify tls, false by default                                        |
| `scroll_speed` | required __if burst_limit__  | `int`  | how long the wait before sending multiple lines (fakelag)           |
| `burst_limit`  | required __if scroll_speed__ | `int`  | amount of messages allowed before scroll_speed sleep timer kicks in |
| `channels`     | __required__                 | `list` | channel list to autojoin on startup                                 |

### example
```yml
sqlite_file: "/data/bands.sqlite3"
ctl_port: 1337

openai_key: "sk-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"

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
  - name: publicnet
    address: irc.example.com
    port: 6697
    botname: stacks
    tls: true
    verify_tls: true
    scroll_speed: 1
    burst_limit: 2
    channels:
      - "#pubchannel"
```

## usage
### server
```sh
usage: bandsd [-h] -c C [-d]

bands the irc bot ver. <version>

options:
  -h, --help  show this help message and exit
  -c C        path to config yaml
  -d          enable debug
```

### client
```sh
usage: bandsctl [-h] [-H CTL_HOST] [-p CTL_PORT] ...

bandsctl

positional arguments:
  command      ctl command

options:
  -h, --help   show this help message and exit
  -H CTL_HOST  host
  -p CTL_PORT  port
```
