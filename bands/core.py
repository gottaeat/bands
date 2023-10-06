import time
import signal
import socket
import ssl
import sys


class Core:
    USER_NICKLIMIT = 30

    def __init__(self):
        self.net = None
        self.port = None
        self.channel = None
        self.botname = None

        self.tls = None
        self.noverify = None

        self.scroll_speed = None

        self.conn = None

    def send_raw(self, msg):
        self.conn.send(f"{msg}\r\n".encode(encoding="UTF-8"))

    def send_query(self, msg):
        self.send_raw(f"PRIVMSG {self.channel} :{msg}")

    def send_query_split(self, msg):
        for line in msg.split("\n"):
            self.send_query(line)
            time.sleep(self.scroll_speed)

    def send_pong(self):
        self.send_raw(f"PING {self.botname}")

    def _send_user(self):
        self.send_raw(
            f"USER {self.botname} {self.botname} {self.botname} {self.botname}"
        )

    def _send_nick(self):
        self.send_raw(f"NICK {self.botname}")

    def _send_join(self):
        self.send_raw(f"JOIN {self.channel}")

    # pylint: disable=unused-argument
    def _signal_handler(self, signum, frame):
        signame = signal.Signals(signum).name

        if signame in {"SIGINT", "SIGTERM"}:
            msg = f"caught {signame}."
            self.send_raw(f"QUIT :{msg}")
            self.conn.close()
            sys.exit(0)

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

        self._send_user()
        self._send_nick()
        self._send_join()

        signal.signal(signal.SIGINT, self._signal_handler)
