import re
import socket
import ssl

from .finance import Finance
from .piss import Piss
from .util import drawbox


# pylint: disable=too-few-public-methods
class IRC:
    def __init__(self):
        self.net = None
        self.port = None
        self.channel = None
        self.botname = None
        self.conn = None

    def _send_query(self, msg):
        self.conn.send(f"PRIVMSG {self.channel} :{msg}\r\n".encode(encoding="UTF-8"))

    def _print_help(self):
        helptext = "help\n"
        helptext += "├ usage: {?help|?islam|?piss [chatter]}\n"
        helptext += "└ docs : https://www.alislam.org/quran/Holy-Quran-English.pdf\n"

        for i in drawbox(helptext, "thic").split("\n"):
            self._send_query(i)

    def _print_finance(self):
        finance = Finance()
        finance.collect()

        msg = "USDTRY\n"
        msg += f"├ central  → {finance.tcmb}\n"
        msg += f"├ xe       → {finance.xe}\n"
        msg += f"├ yahoo    → {finance.yahoo}\n"
        msg += f"└ forbes   → {finance.forbes}\n"
        msg += "USDTTRY\n"
        msg += f"└ binance  → {finance.binance}\n"
        msg += "CDS\n"
        msg += f"└ wgb      → {finance.wgb_cds}\n"

        if finance.wgb_week is not None:
            msg += f"  ├ 1w     → {finance.wgb_week}\n"
            msg += f"  ├ 1m     → {finance.wgb_month}\n"
            msg += f"  └ 1y     → {finance.wgb_year}"

        for i in drawbox(msg, "thic").split("\n"):
            self._send_query(i)

    def _print_piss(self, pisser, pissee):
        if len(str(pissee)) == 0:
            self._send_query(f"{pisser}: on who nigga")
        else:
            if len(str(pissee)) >= 20:
                self._send_query(f"{pisser}: nah")
            else:
                piss = Piss()
                piss.pisser = pisser
                piss.pissee = pissee
                for line in piss.printpiss().split("\n"):
                    self._send_query(line)

    def connect(self):
        senduser = (
            f"USER {self.botname} {self.botname} {self.botname} {self.botname}\r\n"
        )
        sendnick = f"NICK {self.botname}\r\n"
        sendjoin = f"JOIN {self.channel}\r\n"

        print(f"net     : {self.net}")
        print(f"port    : {self.port}")
        print(f"channel : {self.channel}")
        print(f"nick    : {self.botname}\n")
        print(f"senduser: {senduser}")
        print(f"sendnick: {sendnick}")
        print(f"sendjoin: {sendjoin}")

        addr = (socket.gethostbyname(self.net), self.port)

        ssl_context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS_CLIENT)
        ssl_context.check_hostname = True

        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conn = ssl_context.wrap_socket(self.conn, server_hostname=self.net)

        try:
            self.conn.connect(addr)
        except ssl.SSLCertVerificationError:
            self.conn.close()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.conn = ssl_context.wrap_socket(self.conn)
            self.conn.connect(addr)

        self.conn.send(senduser.encode(encoding="UTF-8"))
        self.conn.send(sendnick.encode(encoding="UTF-8"))
        self.conn.send(sendjoin.encode(encoding="UTF-8"))

        # pylint: disable=anomalous-backslash-in-string
        mirc_strip = re.compile("[\x02\x0F\x16\x1D\x1F]|\x03(\d{,2}(,\d{,2})?)?")

        while True:
            data = mirc_strip.sub("", self.conn.recv(2048).decode(encoding="UTF-8"))
            print(data, end="")
            if data.split()[0] == "PING":
                self.conn.send(f"PONG {data.split()[1]}\r\n".encode(encoding="UTF-8"))

            if data.split()[1] == "PRIVMSG" and data.split()[2] == self.channel:
                cmd = data.split()[3]

                if cmd == ":?islam":
                    self._print_finance()

                if cmd == ":?help":
                    self._print_help()

                if cmd == ":?piss":
                    pisser = re.sub(r"^:|\![^!]*$", "", data.split()[0])
                    pissee = " ".join(data.split()[4:])
                    self._print_piss(pisser, pissee)
