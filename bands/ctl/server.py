import socket

from .command import CTLCommand


class CTLServer:
    CTL_HOST = "0.0.0.0"
    MAX_REQUEST_BYTES = 65536
    REQUEST_TIMEOUT = 5

    def __init__(self, config, parent_logger):
        self.config = config
        self.logger = parent_logger.getChild(self.__class__.__name__)

        self.ctl_port = config.ctl_port
        self.listener = None

    def _listen(self):
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listener.bind((self.CTL_HOST, self.ctl_port))
        self.listener.listen(5)
        self.listener.settimeout(1)

        self.logger.info("started listening on %s:%s", self.CTL_HOST, self.ctl_port)

    def _read_request(self, conn):
        payload = b""

        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break

            payload += chunk
            if len(payload) > self.MAX_REQUEST_BYTES:
                raise ValueError("request is too large")

        return payload.decode("utf-8").strip()

    def _handle_client(self, conn, addr):
        response = None

        try:
            request = self._read_request(conn)
        except:
            response = "request failed"
            self.logger.warning("reading request failed", exc_info=True)

        try:
            logger = self.logger.getChild(addr[0])
            response = CTLCommand(self.config, logger, request).run()
        except:
            response = "request failed"
            self.logger.warning("creating response to request failed", exc_info=True)

        if not response:
            response = "request failed"
            self.logger.warning("generated empty response")

        try:
            conn.sendall(response.encode("utf-8"))
        except:
            self.logger.warning("sending response failed", exc_info=True)

        conn.close()

    def run(self):
        self._listen()

        while not self.config.halt:
            try:
                conn, addr = self.listener.accept()
                conn.settimeout(self.REQUEST_TIMEOUT)
            except TimeoutError:
                continue
            except:
                if self.config.halt:
                    break

                self.logger.warning("accept failed", exc_info=True)
                continue

            self._handle_client(conn, addr)

    def stop(self):
        if self.listener:
            self.logger.warning("stopping listener")
            self.listener.close()
