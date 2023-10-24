import re
import socket
import ssl
import time

from threading import Thread

from .util import decode_data
from .util import strip_user
from .util import strip_color

from .channel import Channel
from .user import User

from .modules.advice import Advice
from .modules.finance import Finance
from .modules.help import Help
from .modules.piss import Piss
from .modules.tarot import Tarot

from .modules.auth import Auth
from .modules.openai_handler import OpenAIHandler


# pylint: disable=too-many-instance-attributes,too-many-branches
class Server:
    USER_NICKLIMIT = 30

    def __init__(self):
        # ServerConfig()<-AI()<-CLI()<-ConfigYAML()
        self.ai = None

        # haul in the same logger
        self.logger = None

        # ServerConfig()<-CLI()<-ConfigYAML()
        self.name = None
        self.address = None
        self.port = None
        self.botname = None
        self.channels = None
        self.secret = None
        self.tls = None
        self.verify_tls = None
        self.scroll_speed = None

        # channels: not overwriting the channels attrib since that is used for
        # faster lookups
        self.channel_obj = []

        # admin user
        self.admin = None

        # Server-wide socket
        self.conn = None

        # halt when cli.py catches TERM/INT
        self.halt = None
        self.connected = None

    # - - query handling - - #
    def send_raw(self, msg):
        self.conn.send(f"{msg}\r\n".encode(encoding="UTF-8"))

        self.logger.debug(
            "<- %s",
            strip_color(msg),
        )

    def _send_pong(self, data):
        self.send_raw(re.sub(r"PING", "PONG", data.rstrip("\r\n")))

    def _send_nick(self):
        self.send_raw(f"NICK {self.botname}")

        self.logger.info(
            "sending NICK",
        )

    def _send_user(self):
        self.send_raw(
            f"USER {self.botname} {self.botname} {self.address} :{self.botname}"
        )

        self.logger.info(
            "sending USER",
        )

    def _send_quit(self, reason):
        self.send_raw(f"QUIT :{reason}")

        self.logger.info(
            "sent QUIT: %s",
            reason,
        )

    def _send_join(self, channel):
        self.send_raw(f"JOIN {channel}")

        self.logger.info(
            "joining %s",
            channel,
        )

    # -- arg handling -- #
    def _handle_cmd(self, channel, user, cmd, user_args):
        if cmd == ":?advice":
            Advice(channel).print(user, user_args)

        if cmd == ":?bands":
            Finance(channel).print()

        if cmd == ":?help":
            Help(channel).print()

        if cmd == ":?piss":
            Piss(channel).print(user, user_args)

        if cmd == ":?tarot":
            Tarot(channel).print(user_args)

    def _handle_pm(self, user, cmd, user_args):
        user_instance = User(self)
        user_instance.name = user
        user_instance.char_limit = 512 - len(f"PRIVMSG {user} :".encode("utf-8"))

        if cmd == ":?auth":
            Auth(user_instance).print(user_args)

        if cmd == ":?openai":
            OpenAIHandler(user_instance).print(user_args)

        del user_instance

    def _gen_channel(self, channel_name):
        chan = Channel(self)
        chan.name = channel_name
        self.channel_obj.append(chan)

        self.logger.info("generated channel %s", chan.name)

    def _handle_join(self, botname_with_vhost, channel_name):
        channel_name = re.sub(r"^:", "", channel_name)

        if len(self.channel_obj) == 0 or channel_name not in self.channels:
            self.channels.append(channel_name)
            self._gen_channel(channel_name)

        for chan in self.channel_obj:
            if chan.name == channel_name:
                channel = chan
                break

        if not channel.char_limit:
            channel.char_limit = 508 - len(
                f"{botname_with_vhost} PRIVMSG {channel.name} :\r\n".encode("utf-8")
            )

            self.logger.info(
                "char_limit for %s is set to %s", channel.name, channel.char_limit
            )

    def _handle_invite(self, user, channel_name):
        self._send_join(channel_name)

        self.logger.info("%s has invited us to %s", user, channel_name)

    def _handle_kick(self, user, channel_name, reason):
        self._send_join(channel_name)

        self.logger.info("%s has kicked us from %s for: %s", user, channel_name, reason)

    def _handle_ban(self, channel_name):
        if channel_name in self.channels:
            self.channels.remove(channel_name)

        for chan in self.channel_obj:
            if chan.name == channel_name:
                self.channel_obj.remove(channel_name)

        self.logger.info("we are banned from %s, removing from lists", channel_name)

        if len(self.channels) == 0:
            self.logger.info("channels list is empty, quitting")

            self.stop()

    # -- stages -- #
    # stage 1: open socket that we will pass around for the entire server instance
    def _connect(self):
        self.logger.info("connecting to %s", self.name)

        addr = (socket.gethostbyname(self.address), self.port)

        if self.tls:
            ssl_context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS_CLIENT)

            if not self.verify_tls:
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
            else:
                ssl_context.check_hostname = True

        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # libera ircd takes its time, 10 seems to work however
        self.conn.settimeout(10)

        if self.tls:
            if not self.verify_tls:
                self.conn = ssl_context.wrap_socket(self.conn)
            else:
                self.conn = ssl_context.wrap_socket(
                    self.conn, server_hostname=self.address
                )

        try:
            self.conn.connect(addr)
        except ssl.SSLCertVerificationError:
            self.logger.exception(
                "attempting to connect with TLS failed",
            )
        except TimeoutError:
            self.logger.exception(
                "connection timed out",
            )

        self.conn.settimeout(None)

        self.connected = True

    # stage 2: send NICK and USER, update address, send PING, hand over to channel handling
    def _send_client(self):
        addr_updated = False
        pong_received = False
        sent_ping = False

        self._send_nick()
        self._send_user()

        while not self.halt:
            data = decode_data(self.conn.recv(512))

            if not data:
                errmsg = "decoding error while trying to grab the network "
                errmsg += "welcome message for %s"
                self.logger.error(errmsg, self.name)

            if len(data) == 0:
                self.conn.close()

                self.logger.error(
                    "received nothing",
                )

            for line in data:
                self.logger.debug("<- %s", line.rstrip("\r\n"))

                if line.split()[0] == "PING":
                    Thread(target=self._send_pong, args=[line], daemon=True).start()

                # fix name colissions
                if line.split()[1] == "433":
                    self.botname = f"{self.botname}0"

                    self._send_nick()
                    self._send_user()

                # welcome msg, need to update the address to match the node we round robined
                # to for sending the pong
                if line.split()[1] == "001":
                    self.address = line.split()[0]

                    addr_updated = True

                # need to send ping before joins for networks like rizon
                # 376: end of motd, 422: no motd found, 221: server-wide mode set for user
                if line.split()[1] in ("376", "422", "221") and not sent_ping:
                    self.send_raw(f"PING {self.address}")

                    self.logger.info("sent PING before JOINs")

                    sent_ping = True
                    ping_tstamp = int(time.strftime("%s"))

                # wait for the pong, if we received it, switch to _loop()
                try:
                    if sent_ping:
                        if (
                            self.address in line.split()[0]
                            and line.split()[1] == "PONG"
                        ):
                            pong_received = True

                            self.logger.info("received PONG")

                        if int(time.strftime("%s")) - ping_tstamp > 30:
                            self.conn.close()

                            self.logger.error(
                                "%s never responded to the PING, closing connection",
                                self.name,
                            )
                except UnboundLocalError:
                    continue

            if pong_received and addr_updated:
                break

    # stage 3: final infinite loop
    def _loop(self):
        # pylint: disable=too-many-nested-blocks
        while not self.halt:
            data = decode_data(self.conn.recv(512))

            if not data:
                continue

            if len(data) == 0:
                self.conn.close()

                self.logger.error("received nothing")

            for line in data:
                self.logger.debug("<- %s", line.rstrip("\r\n"))

                # PING handling
                if line.split()[0] == "PING":
                    Thread(target=self._send_pong, args=[line], daemon=True).start()

                # JOIN handling
                if (
                    strip_user(line.split()[0]) == self.botname
                    and line.split()[1] == "JOIN"
                ):
                    Thread(
                        target=self._handle_join,
                        args=[line.split()[0], line.split()[2]],
                        daemon=True,
                    ).start()

                # INVITE handling
                if line.split()[1] == "INVITE":
                    Thread(
                        target=self._handle_invite,
                        args=[strip_user(line.split()[0]), line.split()[3]],
                        daemon=True,
                    ).start()

                # KICK handling
                if line.split()[1] == "KICK" and line.split()[3] == self.botname:
                    Thread(
                        target=self._handle_kick,
                        args=[
                            strip_user(line.split()[0]),
                            line.split()[2],
                            line.split()[4],
                        ],
                        daemon=True,
                    ).start()

                # mode +b handling
                if line.split()[1] == "474":
                    Thread(
                        target=self._handle_ban,
                        args=[line.split()[3]],
                        daemon=True,
                    ).start()

                # PRIVMSG handling
                if line.split()[1] == "PRIVMSG":
                    # channel PRIVMSG
                    if line.split()[2] in self.channels:
                        for chan in self.channel_obj:
                            if chan.name == line.split()[2]:
                                channel = chan
                                break

                        user = strip_user(line.split()[0])
                        cmd = line.split()[3]
                        args = line.split()[4:]

                        self.logger.info(
                            "[%s<-%s] %s %s", channel.name, user, cmd, " ".join(args)
                        )

                        Thread(
                            target=self._handle_cmd,
                            args=[
                                channel,
                                user,
                                cmd,
                                args,
                            ],
                            daemon=True,
                        ).start()

                    # user PRIVMSG
                    if line.split()[2] == self.botname:
                        user = strip_user(line.split()[0])
                        cmd = line.split()[3]
                        args = line.split()[4:]

                        self.logger.info("[PM<-%s] %s %s", user, cmd, " ".join(args))

                        Thread(
                            target=self._handle_pm,
                            args=[
                                user,
                                cmd,
                                args,
                            ],
                            daemon=True,
                        ).start()

    # -- CLI() interactions -- #
    def run(self):
        self._connect()
        self._send_client()

        for channel in self.channels:
            self._send_join(channel)

        self._loop()

    def stop(self):
        self.halt = True

        if self.connected:
            self._send_quit("going out cold.")

        self.conn.close()
