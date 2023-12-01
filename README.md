# bands
bands is a threaded internet relay chat bot with support for:
- multiple servers and multiple channels per server, concurrently
- holds user and channel context
- ai capabilities via openai with global key rotation
- pluggable command modules that operate within the context of channels and user
  private messages
- per-server secret and authentication via private queries
- privilege separated command execution such as live connection/ai state
  manipulation

and many more

## directory breakdown
```txt
└ bands/
  ├ ai.py                   → AI(): instantiate an openai object to be passed
  │                           down to all all Server()s.
  ├ cli.py                  → CLI(): take in a YAML, get it parsed, create an
  │                           AI() from OpenAIConfig() and Server()+Socket()
  │                           pairs from ServerConfig(), feed the Socket() to
  │                           its respective Server(), spawn a Thread() for
  │                           for every Server().
  ├ colors.py               → ANSI and MIRC escapes for colors and pre-formatted
  │                           prompts.
  ├ config.py               → ConfigYAML(): parse YAML, generate OpenAIConfig()
  │                           and ServerConfig().
  ├ log.py                  → Custom StreamHandler() and Formatter() for 
  │                           logging.
  ├ irc/
  │ ├ socket.py             → Socket(): handle TLS and opening, shutting down
  │ │                         and closing of the TCP socket, TLS, hold the recv
  │ │                         buffer.
  │ ├ util.py               → collection of functions shared by irc/ components.
  │ ├ server/
  │ │ ├ client_init.py      → ClientInit(): send PASS+NICK+USER, update node
  │ │ │                       address.
  │ │ ├ final_loop.py       → FinalLoop(): final infinite loop, handle user and
  │ │ │                       channel PRIVMSGs.
  │ │ ├ handle.py           → Handle(): process IRC actions, respond to user and
  │ │ │                       channel CMDs, generate User() and Channel()
  │ │ │                       instances.
  │ │ ├ server.py           → Server(): connect to a server, establish client
  │ │ │                       initialization, enter the infinite loop.
  │ │ └ socket_ops.py       → SocketOps(): handle recv() and send() related
  │ │                         socket operations and abstractions after a
  │ │                         connection is established.
  │ ├ channel/
  │ │ ├ channel.py          → Channel(): instantiated for every channel joined.
  │ │ │                       store the char limit and allow CMD<->Server()
  │ │ │                       communication.
  │ │ └ cmd/
  │ │   ├ advice.py         → Advice(): provide the user, and if specified, the
  │ │   │                     target, with pre-defined advices, to motivate the
  │ │   │                     target in regard to moving.
  │ │   ├ finance.py        → Finance(): scrape finance APIs: TCMB, Yahoo, XE,
  │ │   │                     Forbes and Binance for forex rates and World
  │ │   │                     Government Bonds for CDS.
  │ │   ├ help.py           → Help(): provide channel-specific CMD help.
  │ │   ├ piss.py           → Piss(): allow for a funny little humorous joke for
  │ │   │                     a fun time between friends.
  │ │   └ tarot.py          → Tarot(): generate stored tarot decks per-user with
  │ │                         openai supported reading when provided with a user
  │ │                         specified question.
  │ └ user/
  │   ├ user.py             → User(): instantiated for every user when the user
  │   │                       PRIVMSGs or uses a CMD within a channel. store
  │   │                       per-user context e.g. tarot deck and question tied
  │   │                       to it.
  │   └ cmd/
  │     ├ auth.py           → Auth(): set the Server().admin attrib when
  │     │                     provided a valid password.
  │     ├ help.py           → Help(): provide user-specific CMD help, depending
  │     │                     on auth level.
  │     ├ openai_handler.py → OpenAIHandler(): allow for displaying or
  │     │                     manipulating the global AI() state.
  │     └ rcon.py           → RCon(): allow for displaying or manipulating the
  │                           connection state.
  └ static/
    ├ advices.json          → file parsed by Advice().
    └ tarot_desc.json       → file parsed by Tarot().
```

## config YAML example
```yml
openai:
    keys_file: /path/to/openai_keys.json

servers:
    - name: example1
      address: irc.example1.com
      port: 6697
      passwd: badactors
      botname: bands
      tls: true
      verify_tls: false
      scroll_speed: 0
      channels:
        - "#goodchannel"
        - "#badchannel"
      secret: verysecret

    - name: example2
      address: irc.example2.com
      port: 6697
      botname: bands
      tls: true
      verify_tls: false
      scroll_speed: 0
      channels:
        - "#goodchannel"
        - "#badchannel"
      secret: verysecret
```

## expected openai keys_file format
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
