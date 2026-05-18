# bands
bands is an internet relay chat bot.

## features
- covers all relevant portions of rfc's 1459 and 2812.
- ircv3 caps supported are `chghost` and `multi-prefix`.
- concurrent multi-server and multi-channel support.
- awareness of the channel, channel user, server and server user contexts.
- state manipulation and hot config reload through private messages on trusted
  servers.
- sqlite for stateful changes, in-memory for the rest.
- openai responses api support for channel ai modules.

## modules
### channel commands
channel commands use the channel's configured prefix. the default prefix is `?`.

| command | class         | description                                                   |
| ------- | ------------- | ------------------------------------------------------------- |
| `ai`    | `AIQuery()`   | ask openai a short question                                   |
| `bj`    | `BlackJack()` | wager blackjack bets via user points                          |
| `help`  | `Help()`      | print commands enabled for the channel context                |
| `point` | `Point()`     | give/remove points from users, show server-wide stats         |
| `quote` | `Quote()`     | add/get channel-wide quotes from users                        |
| `tarot` | `Tarot()`     | pull a deck and ask openai for a reading                      |

### channel hooks
hooks match on defined regex and run the handler for it.

| hook             | class             | description                                |
| ---------------- | ----------------- | ------------------------------------------ |
| `url_dispatcher` | `URLDispatcher()` | match on URLs and print the page title     |

### private-message commands
commands to be queried within `PRIVMSG`s directly to the bot, outside of a channel.

| command | class    | description                                       |
| ------- | -------- | ------------------------------------------------- |
| `auth`  | `Auth()` | authenticate as a bot admin to run `RCon()` CMDs. |
| `help`  | `Help()` | print commands for bot `PRIVMSG`s                 |
| `rcon`  | `RCon()` | admin-only remote control                         |

### rcon
`rcon` is only enabled on servers where `allow_admin` is set on boot. the user
must `?auth` first.

| command   | description                                         |
| --------- | --------------------------------------------------- |
| `connect` | connect to a server defined in the configuration    |
| `dc`      | disconnect from one or more servers                 |
| `debug`   | toggle debug on/off or print the current log level  |
| `hook`    | enable/disable/list disabled hooks for a channel    |
| `join`    | join channels                                       |
| `part`    | part channels                                       |
| `prefix`  | set the command prefix for a channel                |
| `raw`     | sends a raw irc line to a server                    |
| `rehash`  | reloads yaml and parses any new servers             |
| `say`     | send a message to a channel                         |
| `cmd`     | enable/disable/list disabled commands for a channel |
| `status`  | print active servers, channels and users            |

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
| `servers`     | __required__ | `list` | list of servers to connect to on startup  |

__[1]__ if not specified, defaults to `/data/bands.sqlite3`. bands will create
and initialize the database if it does not exist.

#### servers
| key            | necessity                    | type   | description                                                             |
| -------------- | ---------------------------- | ------ | ----------------------------------------------------------------------- |
| `name`         | __required__                 | `str`  | reference name for the network                                          |
| `address`      | __required__                 | `str`  | network address                                                         |
| `port`         | __required__                 | `int`  | network port                                                            |
| `passwd`       | optional                     | `str`  | network password                                                        |
| `botname`      | __required__                 | `str`  | bot nick+ident                                                          |
| `tls`          | optional                     | `bool` | enable tls, false by default                                            |
| `verify_tls`   | optional                     | `bool` | verify tls, false by default                                            |
| `scroll_speed` | required __if burst_limit__  | `int`  | how long the wait before sending multiple lines (fakelag)               |
| `burst_limit`  | required __if scroll_speed__ | `int`  | amount of messages allowed before scroll_speed sleep timer kicks in     |
| `channels`     | __required__                 | `list` | channel list to autojoin on startup                                     |
| `allow_admin`  | optional                     | `bool` | allow authentication and remote control on the server, false by default |
| `secret`       | required __if allow_admin__  | `str`  | authentication secret                                                   |

### example
```yml
sqlite_file: "/data/bands.sqlite3"

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
    allow_admin: true
    secret: EsDf/ZcdNp1whuZh
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
```sh
usage: bands [-h] -c C [-d]

bands the irc bot ver. <version>

options:
  -h, --help  show this help message and exit
  -c C        path to config yaml
  -d          enable debug
```

## runtime management
1. set at least one of the servers to have `allow_admin` and a `secret`.
2. privmsg the `botname` with `?auth $secret`.
3. call `?rcon help` for a list of management related functionality.
