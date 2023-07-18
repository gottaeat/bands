# socket
host = socket.gethostbyname("ircd.chat")
port = 6697
addr = (host, port)

channel = "#msstest"
botname = "shart"

senduser = f"USER {botname} {botname} {botname} {botname}\r\n"
sendnick = f"NICK {botname}\r\n"
sendjoin = f"JOIN {channel}\r\n"


def sendquery(channel, msg):
    irc.send(f"PRIVMSG {channel} :{msg}\r\n".encode(encoding="UTF-8"))


def printhelp():
    helptext = "help\n"
    helptext += "├ usage: {?help|?islam|?piss [chatter]}\n"
    helptext += "└ docs : https://www.alislam.org/quran/Holy-Quran-English.pdf\n"
    for i in drawbox(helptext, "thic").split("\n"):
        sendquery(channel, i)


# strip mIRC colors
rex = re.compile("[\x02\x0F\x16\x1D\x1F]|\x03(\d{,2}(,\d{,2})?)?")

irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
irc = ssl.wrap_socket(irc)
irc.connect(addr)

irc.send(senduser.encode(encoding="UTF-8"))
irc.send(sendnick.encode(encoding="UTF-8"))
irc.send(sendjoin.encode(encoding="UTF-8"))

while True:
    data = rex.sub("", irc.recv(2048).decode(encoding="UTF-8"))
    if data.split()[0] == "PING":
        irc.send(f"PONG {data.split()[1]}\r\n".encode(encoding="UTF-8"))
    if data.split()[1] == "PRIVMSG" and data.split()[2] == channel:
        cmd = data.split()[3]
        if cmd == ":?islam":
            pullall()
        if cmd == ":?help":
            printhelp()
        if cmd == ":?piss":
            pisser = re.sub(r"^:|\![^!]*$", "", data.split()[0])
            pissee = " ".join(data.split()[4:])
            if len(str(pissee)) == 0:
                sendquery(channel, f"{pisser}: on who nigga")
            else:
                if len(str(pissee)) >= 20:
                    sendquery(channel, f"{pisser}: nah")
                else:
                    printpiss(pisser, pissee)
