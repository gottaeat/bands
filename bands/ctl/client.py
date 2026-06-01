import argparse
import logging
import shlex
import socket

from bands.log import set_root_logger

CTL_HOST = "127.0.0.1"
CTL_PORT = 1337


class CTLClient:
    def __init__(self):
        self.logger = None
        self.ctl_host = None
        self.ctl_port = None
        self.command = None

    def _gen_args(self):
        parser = argparse.ArgumentParser(description="bandsctl")
        parser.add_argument(
            "-H",
            dest="ctl_host",
            default=CTL_HOST,
            help="host",
        )
        parser.add_argument(
            "-p",
            dest="ctl_port",
            default=CTL_PORT,
            type=int,
            help="port",
        )
        parser.add_argument("command", nargs=argparse.REMAINDER, help="ctl command")

        args = parser.parse_args()

        self.ctl_host = args.ctl_host
        self.ctl_port = args.ctl_port
        self.command = shlex.join(args.command)

    def _read_response(self, conn):
        response = b""

        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break

            response += chunk

        return response.decode("utf-8")

    def _send_request(self, request):
        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        response = None

        try:
            conn.connect((self.ctl_host, self.ctl_port))
            conn.sendall(request.encode("utf-8"))
            conn.shutdown(socket.SHUT_WR)
            response = self._read_response(conn)
        except:
            conn.close()
            self.logger.exception(
                "request failed for %s:%s", self.ctl_host, self.ctl_port
            )

        conn.close()
        return response

    def run(self):
        self._gen_args()

        set_root_logger()
        self.logger = logging.getLogger("bandsctl")

        response = self._send_request(self.command)

        if response:
            for line in response.split("\n"):
                self.logger.info(line)
        else:
            self.logger.error("no response received")


def run():
    ctl = CTLClient()
    ctl.run()
