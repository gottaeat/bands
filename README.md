# bands
bands is an internet relay chat bot.

## features
- all relevant portions of rfc 1459 and 2812 is covered, with support for
  certain ircv3 caps (chghost, multi-prefix).
- can concurrently handle multiple servers, and multiple channels per server, at
  once.
- handles channel and server-wide commands.
- allows for state manipulation through private messages on trusted servers.
- has openai support with key rotation for modules to take advantage of.

and many more

## installation
### main namespace
```sh
git clone --depth=1 https://github.com/gottaeat/bands
cd bands/

pip install .
```

### dockerized
```sh
git clone --depth=1 https://github.com/gottaeat/bands
cd bands/

sudo docker build -t bands-pyenv .

sudo docker run --rm \
    -v ./files:/home/bands/files \
    -v .:/home/bands/repo \
    bands-pyenv \
    bash -c "\
        cd repo/ && pip install . && \
        bands -c ./files/config.yml"

```

## usage
for the channel, server and state specific commands, call `?help` in either
a channel or in private messages with the bot. cmdline specific usage is:
```sh
usage: bands [-h] -c C [-d]

bands the IRC bot.

options:
  -h, --help  show this help message and exit
  -c C        Configuration YAML file.
  -d          Enable debugging.
```

## config YAML example
```yml
openai:
    keys_file: ./files/openai_keys.json

quote:
    quotes_file: ./files/quotes.json

doot:
    doots_file: ./files/doots.json

servers:
    - name: example
      address: irc.example.com
      port: 6697
      passwd: topsekrit
      botname: bands
      tls: true
      verify_tls: false
      scroll_speed: 0
      channels:
        - "#mychannel"
        - "#mychannel2"
      allow_admin: true
      secret: EsDf/ZcdNp1whuZh
    - name: publicnet
      address: irc.public.net
      port: 6697
      botname: bandsette
      tls: true
      verify_tls: true
      scroll_speed: 1
      channels:
        - "#publicchannel"
```

## expected openai.keys_file formatting
```json
{
  "openai_keys": [
      {
        "key": "sk-"
      },
      {
        "key": "sk-"
      }
    ]
}
```
