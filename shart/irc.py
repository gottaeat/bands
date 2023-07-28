import re
import socket
import ssl
import sys
import signal

from .modules.finance import Finance
from .modules.piss import Piss
from .util import drawbox


# pylint: disable=too-few-public-methods
class IRC:
    def __init__(self):
        self.net = None
        self.port = None
        self.channel = None
        self.botname = None

        self.tls = None
        self.noverify = None

        self.conn = None

    def _send_raw(self, msg):
        self.conn.send(f"{msg}\r\n".encode(encoding="UTF-8"))

    def _send_query(self, msg):
        self._send_raw(f"PRIVMSG {self.channel} :{msg}")

    def _send_pong(self):
        self._send_raw(f"PING {self.botname}")

    def _send_user(self):
        self._send_raw(
            f"USER {self.botname} {self.botname} {self.botname} {self.botname}"
        )

    def _send_nick(self):
        self._send_raw(f"NICK {self.botname}")

    def _send_join(self):
        self._send_raw(f"JOIN {self.channel}")

    # pylint: disable=unused-argument
    def _signal_handler(self, signum, frame):
        signame = signal.Signals(signum).name

        if signame in {"SIGINT", "SIGTERM"}:
            msg = f"caught {signame}."

        print(f"\n{msg}")
        self._send_raw(f"QUIT :{msg}")
        self.conn.close()
        sys.exit(0)

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

    # pylint: disable=too-many-branches
    def connect(self):
        addr = (socket.gethostbyname(self.net), self.port)

        if self.tls:
            ssl_context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS_CLIENT)

            if self.noverify:
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
            else:
                ssl_context.check_hostname = True

        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conn.settimeout(5)

        if self.tls:
            if self.noverify:
                self.conn = ssl_context.wrap_socket(self.conn)
            else:
                self.conn = ssl_context.wrap_socket(self.conn, server_hostname=self.net)

        # pylint: disable=raise-missing-from
        try:
            self.conn.connect(addr)
        except ssl.SSLCertVerificationError as exc_msg:
            raise ValueError(f"E: Attempting to connect with TLS failed:\n{exc_msg}")
        except TimeoutError as exc_msg:
            raise ValueError(f"E: Connection timed out:\n{exc_msg}")

        self.conn.settimeout(None)

        signal.signal(signal.SIGINT, self._signal_handler)

        # pylint: disable=anomalous-backslash-in-string
        mirc_strip = re.compile("[\x02\x0F\x16\x1D\x1F]|\x03(\d{,2}(,\d{,2})?)?")

        while True:
            data = mirc_strip.sub("", self.conn.recv(2048).decode(encoding="UTF-8"))
            if len(data) == 0:
                self.conn.close()
                raise ValueError("E: received nothing.")

            print(data, end="")

            if data.split()[0] == "PING":
                self._send_pong()

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
