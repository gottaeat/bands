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
### 1. stable
```sh
# 1. get the compose file
mkdir bands/; cd bands/
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

### 2. dev
```sh
# 1. clone the repo
git clone --depth=1 https://github.com/gottaeat/bands
cd bands/

# 2. uncomment the `build' key and comment out the `image' key inside
#    docker-compose.yml to build the image instead of using the one from ghcr

# 3. create the volume mount
mkdir data/; cd data/

# 4. create a config.yml within this directory following the spec and the
#    example below

# 5. compose up
cd ../;
docker compose up -d
```

## configuration
### specification
#### root
| key               | necessity     | description                                               |
|-------------------|---------------|-----------------------------------------------------------|
| `wolfram_api_key` | optional      | (`str`) wolfram alpha api key for module support          |
| `openai`          | optional      | root key for the openai-related configuration             |
| `piped_url`       | optional      | (`str`) fqdn to make piped api requests to [1]            |
| `quote_file`      | optional      | (`str`) path to read/write channel quotes to and from [2] |
| `doot_file`       | optional      | (`str`) path to read/write server points to and from [2]  |
| `servers`         | __required__  | list of servers to connect to on startup                  |

__[1]__ if none specified, will fall back to a default that may or may not be
available to make api calls to.

__[2]__ `quote_file` and `doot_file` keys, if not specified, will default to
`/data/quotes.json` and `/data/doots.json` respectively. regardless of the
values being specified, if they do not exist, bands will attempt to create and
initialize the files.

#### openai
| key     | necessity    | description                                        |
|---------|--------------|----------------------------------------------------|
| `key`   | __required__ | (`str`) openai api key for module support          |
| `model` | __required__ | (`str`) openai model name to be used in modules[1] |

__[1]__ model names are sanity checked against a list of text-only openai
models, to see the complete list, just bring up the bot with a random value for
the `model` key.

#### servers
| key            | necessity                    | description                                                                      |
|----------------|------------------------------|----------------------------------------------------------------------------------|
| `name`         | __required__                 | (`str`) reference name for the network                                           |
| `address`      | __required__                 | (`str`) network address                                                          |
| `port`         | __required__                 | (`int`) network port                                                             |
| `passwd`       | optional                     | (`str`) network password                                                         |
| `botname`      | __required__                 | (`str`) bot nick+ident                                                           |
| `tls`          | optional                     | (`bool`) enable tls, false by default                                            |
| `verify_tls`   | optional                     | (`bool`) verify tls, false by default                                            |
| `scroll_speed` | required __if burst_speed__  | (`int`) how long the wait before sending multiple lines (fakelag)                |
| `burst_speed`  | required __if scroll_speed__ | (`int`) amount of messages allowed before scroll_speed sleep timer kicks in      |
| `channels`     | __required__                 | (`list of str's`) channel list to autojoin on startup                            |
| `allow_admin`  | optional                     | (`bool`) allow authentication and remote control on the server, false by default |
| `secret`       | required __if allow_admin__  | (`str`) authentication secret                                                    |

### example
```yml
wolfram_api_key: "XXXXX-XXXXXXXXXX"
piped_url: "pipedapi.myfavinstance.net"
openai:
    key: "sk-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
    model: 'gpt-4o-mini'

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
for user-accesible features, call `?help` in either the context of a channel or
a private message with the bot.

cmdline specific usage is:
```sh
usage: bands [-h] -c C [-d]

bands the irc bot ver. <version>

options:
  -h, --help  show this help message and exit
  -c C        path to config yaml
  -d          enable debug
```

## management
1. set at least one of the servers to have `allow_admin` and a `secret`.
2. privmsg the `botname` with `?auth $secret`.
3. call `?rcon help` for a list of management related functionality.
