import socket
import ssl

from bands.colors import ANSIColors

ac = ANSIColors()


class Socket:
    def __init__(self):
        # yaml
        self.address = None
        self.address_init = None
        self.port = None
        self.tls = None
        self.verify_tls = None

        # logger
        self.logger = None

        # socket
        self.conn = None
        self.buffer = b""

        # state
        self.connected = None
        self.halt = None

    def connect(self):
        self.logger.info("%s", f"{ac.BYEL}--> {ac.BWHI}connecting{ac.RES}")

        # ClientInit() updates the server address with the advertised name in
        # IRC 001, if we're re-connecting, reset it back to the yaml config
        # default
        self.address = self.address_init

        try:
            addr = (socket.gethostbyname(self.address), self.port)
        except:
            self.logger.exception("resolving hostname failed")

        if self.tls:
            ssl_context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS_CLIENT)

            if not self.verify_tls:
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
            else:
                ssl_context.load_default_certs()

        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # libera ircd takes its time, 10 seems to work however
        self.conn.settimeout(10)

        if self.tls:
            self.conn = ssl_context.wrap_socket(self.conn, server_hostname=self.address)

        try:
            self.conn.connect(addr)
        except ssl.SSLCertVerificationError:
            self.logger.exception("attempting to connect with TLS failed")
        except TimeoutError:
            self.logger.exception("connection timed out")
        except:
            self.logger.exception("connection failed")

        self.conn.settimeout(None)

        self.logger.info("%s", f"{ac.BYEL}--> {ac.BWHI}connected{ac.RES}")
        self.connected = True

    def disconnect(self):
        # disconnect() might get called before connect() finishes during retry
        # or stop, or someone else might kill it before disconnect is called,
        # if no conn, don't cause an exception
        if self.conn:
            if self.connected:
                self.logger.warning("shutting down socket (RDWR)")
                try:
                    self.conn.shutdown(socket.SHUT_RDWR)
                except:
                    self.logger.warning("socket shutdown failed")

            self.logger.warning(
                "%s", f"{ac.BYEL}--> {ac.BWHI}closing connection{ac.RES}"
            )
            self.conn.close()

        # remove connection object, set connected state to false and clear the
        # buffer in case this was not a full nuke of the server but a server
        # entering the retry loop
        self.conn = None
        self.connected = False
        self.buffer = b""
