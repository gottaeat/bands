#!/usr/bin/python
import re
import socket
import ssl
import unicodedata
import urllib.request, urllib.parse
import xmltodict
from bs4 import BeautifulSoup
from json import loads
from time import sleep

# money
binan_url = "https://api.binance.com/api/v3/ticker/price?"
doviz_url = "https://www.doviz.com/api/v10/converterItems"
forbes_url = (
    "https://www.forbes.com/advisor/money-transfer/currency-converter/usd-try/?"
)
tcmb_url = "https://www.tcmb.gov.tr/kurlar/today.xml"
wgb_url = "http://www.worldgovernmentbonds.com/cds-historical-data/turkey/5-years/"
xe_url = "https://www.x-rates.com/calculator/?"
yahoo_url = "https://query1.finance.yahoo.com/v8/finance/chart/"

binan_params = urllib.parse.urlencode({"symbol": "USDTTRY"})
forbes_params = urllib.parse.urlencode({"amount": "1"})
xe_params = urllib.parse.urlencode({"from": "USD", "to": "TRY", "amount": "1"})
yahoo_params = urllib.parse.urlencode({"USDTRY": "X"})

binan_req = binan_url + binan_params
doviz_req = doviz_url
forbes_req = forbes_url + forbes_params
tcmb_req = tcmb_url
wgb_req = wgb_url
xe_req = xe_url + xe_params
yahoo_req = yahoo_url + yahoo_params

# socket
host = socket.gethostbyname("ircd.chat")
port = 6697
addr = (host, port)

channel = "#msstest"
botname = "shart"

senduser = f"USER {botname} {botname} {botname} {botname}\r\n"
sendnick = f"NICK {botname}\r\n"
sendjoin = f"JOIN {channel}\r\n"


# funcs
def sendquery(channel, msg):
    irc.send(f"PRIVMSG {channel} :{msg}\r\n".encode(encoding="UTF-8"))


def unilen(string):
    width = 0
    for i in string:
        if unicodedata.category(i)[0] in ("M", "C"):
            continue
        w = unicodedata.east_asian_width(i)
        if w in ("N", "Na", "H", "A"):
            width += 1
        else:
            width += 2
    return width


def drawbox(string, charset):
    if charset == "double":
        chars = {"1": "╔", "2": "╗", "3": "╚", "4": "╝", "h": "═", "v": "║"}
    elif charset == "single":
        chars = {"1": "┌", "2": "┐", "3": "└", "4": "┘", "h": "─", "v": "│"}
    elif charset == "thic":
        chars = {"1": "╔", "2": "╗", "3": "╚", "4": "╝", "h": "─", "v": "│"}
    else:
        chars = {"1": "+", "2": "+", "3": "+", "4": "+", "h": "-", "v": "|"}
    a = string.split("\n")
    if a[-1] == "":
        a = a[:-1]
    if a[0] == "":
        a = a[1:]
    for i in range(0, len(a)):
        a[i] = re.sub(r"^", chars["v"], a[i])
    width = 0
    for i in range(0, len(a)):
        if unilen(a[i]) > width:
            width = unilen(a[i])
    for i in range(0, len(a)):
        a[i] = f"{a[i]}{(width - unilen(a[i])) * ' '}{chars['v']}"
    a.insert(0, f"{chars['1']}{chars['h'] * (width - 1)}{chars['2']}")
    a.append(f"{chars['3']}{chars['h'] * (width - 1)}{chars['4']}")
    fin = ""
    finlen = len(a)
    for i in range(0, finlen):
        fin += a[i] + "\n"
    return fin


# json apis
def sb_doviz():
    doviz_data = urllib.request.Request(doviz_req)
    try:
        doviz_data = loads(
            urllib.request.urlopen(
                doviz_data,
            )
            .read()
            .decode()
        )
    except:
        return "fucked"
    else:
        if doviz_data["error"] == False:
            doviz_data = doviz_data["data"]["C"]["USD"]
            doviz_buy = doviz_data["buying"]
            doviz_sell = doviz_data["selling"]
            return "{:.6f}".format((doviz_buy + doviz_sell) / 2.0).strip("0")
        else:
            return "fucked"


def sb_binan():
    binan_data = urllib.request.Request(binan_req)
    try:
        binan_data = float(
            loads(
                urllib.request.urlopen(
                    binan_data,
                )
                .read()
                .decode()
            )[
                "price"
            ].rstrip("0")
        )
    except:
        return "fucked"
    else:
        return binan_data


def sb_yahoo():
    yahoo_data = urllib.request.Request(yahoo_req)
    try:
        yahoo_data = loads(urllib.request.urlopen(yahoo_req).read().decode())
    except:
        return "fucked"
    else:
        return yahoo_data["chart"]["result"][0]["meta"]["regularMarketPrice"]


# scrapes
def sb_forbes():
    forbes_data = urllib.request.Request(forbes_req)
    try:
        forbes_data = urllib.request.urlopen(forbes_req).read().decode()
    except:
        return "fucked"
    else:
        try:
            forbessoup = BeautifulSoup(forbes_data, "html.parser")
            forbes_data = forbessoup.find_all("span", {"class": "amount"})[0]
        except:
            return "fucked"
        else:
            return forbes_data.get_text()


def sb_xe():
    xe_data = urllib.request.Request(xe_req)
    try:
        xe_data = urllib.request.urlopen(xe_req).read().decode()
    except:
        return "fucked"
    else:
        try:
            xesoup = BeautifulSoup(xe_data, "html.parser")
            xe_data = xesoup.find_all("span", {"class": "ccOutputRslt"})[0]
        except:
            return "fucked"
        else:
            return xe_data.get_text().split(" ")[0]


# xml
def sb_tcmb():
    context = ssl.create_default_context()
    context.options |= 0x4
    tcmb_data = urllib.request.Request(tcmb_req)
    try:
        tcmb_data = urllib.request.urlopen(tcmb_req, context=context).read().decode()
    except:
        return "fucked"
    else:
        try:
            tcmbparse = xmltodict.parse(tcmb_data)
            tcmbparse = tcmbparse["Tarih_Date"]["Currency"][0]
        except:
            return "fucked"
        else:
            tcmb_buy = float(tcmbparse["ForexBuying"])
            tcmb_sell = float(tcmbparse["ForexSelling"])
            return (tcmb_buy + tcmb_sell) / 2


## exchangerates
def sb_exchanges():
    xchange = "USDTRY\n"
    xchange += f"├ central  → {sb_tcmb()}\n"
    xchange += f"├ xe       → {sb_xe()}\n"
    xchange += f"├ yahoo    → {sb_yahoo()}\n"
    xchange += f"├ forbes   → {sb_forbes()}\n"
    xchange += f"└ dovizcom → {sb_doviz()}\n"
    return xchange


def sb_crypto():
    cchange = "USDTTRY\n"
    cchange += f"└ binance  → {sb_binan()}\n"
    return cchange


## cds
def sb_wgb():
    wgb_data = urllib.request.Request(wgb_req)
    wgbfin = "CDS\n"
    try:
        wgb_data = urllib.request.urlopen(wgb_req).read().decode()
    except:
        wgbfin += f"└ wgb      → fucked"
    else:
        wgbsoup = BeautifulSoup(wgb_data, "html.parser")
        try:
            cds = (
                wgbsoup.find_all("div", {"class": "w3-cell font-open-sans"})[0]
                .get_text()
                .split()[0]
            )
            perc = (
                wgbsoup.find_all("p", string=re.compile("CDS value changed"))[0]
                .get_text()
                .split()
            )
            week, month, year = perc[3], perc[7], perc[11]
        except:
            wgbfin += f"└ wgb      → fucked\n"
        else:
            finprint = f"└ wgb      → {cds}\n"
            finprint += f"  ├ 1w     → {week}\n"
            finprint += f"  ├ 1m     → {month}\n"
            finprint += f"  └ 1y     → {year}"
            wgbfin += finprint
    return wgbfin


## pullall
def pullall():
    alltable = f"{sb_exchanges()}{sb_crypto()}{sb_wgb()}"
    for i in drawbox(alltable, "thic").split("\n"):
        sendquery(channel, i)


# help
def printhelp():
    helptext = "help\n"
    helptext += "├ usage: {?help|?islam|?piss [chatter]}\n"
    helptext += "└ docs : https://www.alislam.org/quran/Holy-Quran-English.pdf\n"
    for i in drawbox(helptext, "thic").split("\n"):
        sendquery(channel, i)


def printpiss(pisser, pissee):
    lolman = "     ë\n"
    lolman += f"   .-║- <- {pisser} \n"
    lolman += "   ╭╰\\\n"
    lolman += "   ┊/ \\\n"
    lolman += "   ┊\n"
    lolman += f" {pissee}\n"
    lolman = drawbox(lolman, "single")
    pismsg = f"{pissee} just got pissed on by {pisser}."
    finmsg = lolman + pismsg

    for i in finmsg.split("\n"):
        sendquery(channel, i)


# colorshit
rex = re.compile("[\x02\x0F\x16\x1D\x1F]|\x03(\d{,2}(,\d{,2})?)?")

# action
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
