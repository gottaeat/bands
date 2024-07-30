import time
import re

from threading import Lock

from bands.irc.util import strip_color, wrap_bytes
from bands.colors import ANSIColors

ac = ANSIColors()


class SocketOps:
    def __init__(self, server):
        self.server = server
        self.logger = server.logger
        self.socket = server.socket

        self.mutex = Lock()
        self.privmsg_tstamp = int(round(time.time() * 1000))

    # -- receiving -- #
    def decode_data(self, data):
        if not data and not self.socket.halt:
            self.logger.warning("received nothing")
            return self.server.stop()

        data = self.socket.buffer + data

        data_split = data.split(b"\r\n")

        if data_split[-1] != b"":
            self.socket.buffer += data_split[-1]
        else:
            self.socket.buffer = b""

        data_split = data_split[:-1]

        for index, item in enumerate(data_split):
            try:
                data_split[index] = f"{strip_color(item.decode(encoding='UTF-8'))}\r\n"
            except UnicodeDecodeError:
                try:
                    data_split[index] = (
                        f"{strip_color(item.decode(encoding='latin-1'))}\r\n"
                    )
                except:
                    data_split[index] = None
            except:
                data_split[index] = None

        return data_split

    # -- sending -- #
    def send_raw(self, msg):
        self.logger.debug(
            "%s%s", f"{ac.BRED}--> {ac.RES}", strip_color(msg.rstrip("\r\n"))
        )

        try:
            self.socket.conn.send(f"{msg}\r\n".encode(encoding="UTF-8"))
        except:
            if not self.socket.halt:
                self.logger.exception("send failed")

    def send_privmsg(self, msg, target):
        with self.mutex:
            time_past = int(round(time.time() * 1000)) - self.privmsg_tstamp

            if time_past < self.server.scroll_speed:
                time.sleep((self.server.scroll_speed - time_past) / 1000)

            self.send_raw(f"PRIVMSG {target} :{msg}")
            self.privmsg_tstamp = int(round(time.time() * 1000))

    def send_query_hook(self, name, char_limit, msg):
        if "\n" in msg:
            for line in msg.split("\n"):
                if line:
                    if len(line.encode("utf-8")) > char_limit:
                        for item in wrap_bytes(line, char_limit):
                            self.send_privmsg(item, name)
                            time.sleep(self.server.scroll_speed / 1000)
                    else:
                        self.send_privmsg(line, name)
                        time.sleep(self.server.scroll_speed / 1000)
        else:
            if len(msg.encode("utf-8")) > char_limit:
                for item in wrap_bytes(msg, char_limit):
                    self.send_privmsg(item, name)
                    time.sleep(self.server.scroll_speed / 1000)
            else:
                self.send_privmsg(msg, name)
                time.sleep(self.server.scroll_speed / 1000)

    def send_ping(self):
        self.send_raw(f"PING {self.socket.address}")

    def send_pong(self, data):
        self.send_raw(re.sub(r"PING", "PONG", data.rstrip("\r\n")))

    def send_nick(self):
        self.logger.debug("sending NICK")
        self.send_raw(f"NICK {self.server.botname}")

    def send_user(self):
        self.logger.debug("sending USER")

        user_str = f"USER {self.server.botname} {self.server.botname} "
        user_str += f"{self.socket.address} :{self.server.botname}"
        self.send_raw(user_str)

    def send_pass(self):
        self.logger.debug("sending PASS")
        self.send_raw(f"PASS {self.server.passwd}")

    def send_quit(self, reason):
        self.logger.info("sending QUIT: %s", reason)
        self.send_raw(f"QUIT :{reason}")

    def send_join(self, channel):
        self.logger.info("joining %s", channel)
        self.send_raw(f"JOIN {channel}")

    def send_part(self, channel, reason):
        self.logger.info("sending PART to %s, reason: %s", channel, reason)
        self.send_raw(f"PART {channel} :{reason}")
