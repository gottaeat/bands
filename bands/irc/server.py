import re
import socket
import ssl
import time

from threading import Thread

from bands.colors import ANSIColors

from .util import strip_user
from .util import strip_color

from .channel import Channel
from .channel import cmd as CCMD

from .user import User
from .user import cmd as UCMD

ac = ANSIColors()


# pylint: disable=too-many-instance-attributes,too-many-branches
class Server:
    USER_NICKLIMIT = 30

    _PONG_TIMEOUT = 60
    _PING_INTERVAL = 120

    _CHANNEL_CMDS = {
        ":?advice": CCMD.Advice,
        ":?bands": CCMD.Finance,
        ":?help": CCMD.Help,
        ":?piss": CCMD.Piss,
        ":?tarot": CCMD.Tarot,
    }

    _USER_CMDS = {
        ":?auth": UCMD.Auth,
        ":?help": UCMD.Help,
        ":?openai": UCMD.OpenAIHandler,
        ":?rcon": UCMD.RCon,
    }

    def __init__(self):
        # ServerConfig()<-AI()<-CLI()<-ConfigYAML()
        self.ai = None

        # to alter the list of Server()s
        self.cli = None

        # haul in the same logger
        self.logger = None

        # ServerConfig()<-CLI()<-ConfigYAML()
        self.name = None
        self.address = None
        self.port = None
        self.botname = None
        self.channels = None
        self.passwd = None
        self.secret = None
        self.tls = None
        self.verify_tls = None
        self.scroll_speed = None

        # channels: not overwriting the channels attrib since that is used for
        # faster lookups
        self.channel_obj = []

        # users
        self.users = []
        self.user_obj = []
        self.admin = None

        # server-wide socket
        self.conn = None
        self.buffer = b""

        # state
        self.halt = None
        self.connected = None

        # client_init
        self.client_init_ping_sent = None
        self.client_init_ping_tstamp = None
        self.client_init_pong_received = None
        self.client_init_pong_timer_stop = None
        self.client_init_pong_timer_halt = None

        # loop
        self.loop_ping_sent = None
        self.loop_ping_tstamp = None
        self.loop_pong_received = None
        self.loop_pong_tstamp = None

    # -- sending -- #
    def send_raw(self, msg):
        self.logger.debug(
            "%s %s", f"{ac.BRED}-->{ac.RES}", strip_color(msg.rstrip("\r\n"))
        )

        try:
            self.conn.send(f"{msg}\r\n".encode(encoding="UTF-8"))
        # pylint: disable=bare-except
        except:
            if not self.halt:
                self.logger.exception("send failed")

    def _send_ping(self):
        self.send_raw(f"PING {self.address}")

    def _send_pong(self, data):
        self.send_raw(re.sub(r"PING", "PONG", data.rstrip("\r\n")))

    def _send_nick(self):
        self.logger.debug("sending NICK")
        self.send_raw(f"NICK {self.botname}")

    def _send_user(self):
        self.logger.debug("sending USER")
        self.send_raw(
            f"USER {self.botname} {self.botname} {self.address} :{self.botname}"
        )

    def _send_pass(self):
        self.logger.debug("sending PASS")
        self.send_raw(f"PASS {self.passwd}")

    def _send_quit(self, reason):
        self.logger.info("sending QUIT: %s", reason)
        self.send_raw(f"QUIT :{reason}")

    def _send_join(self, channel):
        self.logger.info("joining %s", channel)
        self.send_raw(f"JOIN {channel}")

    # -- receiving -- #
    # pylint: disable=inconsistent-return-statements
    def _decode_data(self, data):
        if len(data) == 0:
            if not self.halt:
                self.logger.warning("received nothing")
                self.stop()
                return

        data = self.buffer + data

        data_split = data.split(b"\r\n")

        if data_split[-1] != b"":
            self.buffer += data_split[-1]
        else:
            self.buffer = b""

        data_split = data_split[:-1]

        for index, item in enumerate(data_split):
            try:
                data_split[index] = f"{strip_color(item.decode(encoding='UTF-8'))}\r\n"
            except UnicodeDecodeError:
                try:
                    data_split[
                        index
                    ] = f"{strip_color(item.decode(encoding='UTF-8'))}\r\n"
                # pylint: disable=bare-except
                except:
                    data_split[index] = None
            # pylint: disable=bare-except
            except:
                data_split[index] = None

        return data_split

    # -- context handling -- #
    def _gen_channel(self, channel_name):
        # self.channels
        if channel_name not in self.channels:
            self.channels.append(channel_name)

            self.logger.debug("added %s to channels", channel_name)

        # self.channel_obj
        channel_objs = []
        for chan in self.channel_obj:
            channel_objs.append(chan.name)

        if channel_name not in channel_objs:
            chan = Channel(self)
            chan.name = channel_name
            self.channel_obj.append(chan)

            self.logger.debug("generated channel object for %s", channel_name)

    def _gen_user(self, user_name):
        # self.users
        if user_name not in self.channels:
            self.users.append(user_name)

        # self.user_obj
        user_objs = []
        for user in self.user_obj:
            user_objs.append(user.name)

        if user_name not in user_objs:
            user = User(self)
            user.name = user_name
            user.char_limit = 512 - len(f"PRIVMSG {user} :".encode("utf-8"))

            self.user_obj.append(user)

            self.logger.debug(
                "generated user object for %s (%s)", user.name, user.char_limit
            )

    # -- cmd handling -- #
    def _handle_channel_msg(self, channel, user_name, cmd, user_args):
        self._gen_user(user_name)

        for user_obj in self.user_obj:
            if user_obj.name == user_name:
                user = user_obj
                break

        tstamp = int(time.strftime("%s"))

        if not channel.tstamp:
            channel.tstamp = tstamp

            self._CHANNEL_CMDS[cmd](channel, user, user_args)

            return

        if user_name != self.admin:
            if tstamp - channel.tstamp < 2:
                self.logger.warning(
                    "ignoring cmd %s in %s (ratelimited)", cmd, channel.name
                )

                return

        channel.tstamp = tstamp

        self._CHANNEL_CMDS[cmd](channel, user, user_args)

    def _handle_pm(self, user_name, cmd, user_args):
        if len(self.user_obj) == 0 or user_name not in self.users:
            self._gen_user(user_name)

        for user_obj in self.user_obj:
            if user_obj.name == user_name:
                user = user_obj
                break

        tstamp = int(time.strftime("%s"))

        if not user.tstamp:
            user.tstamp = tstamp

            self._USER_CMDS[cmd](user, user_args)

            return

        if user_name != self.admin:
            if tstamp - user.tstamp < 2:
                self.logger.warning(
                    "ignoring cmd %s in %s (ratelimited)", cmd, user.name
                )

                return

        user.tstamp = tstamp

        self._USER_CMDS[cmd](user, user_args)

    # -- irc handling -- #
    def _handle_join(self, botname_with_vhost, channel_name):
        channel_name = re.sub(r"^:", "", channel_name)

        self._gen_channel(channel_name)

        for chan in self.channel_obj:
            if chan.name == channel_name:
                channel = chan
                break

        if not channel.char_limit:
            channel.char_limit = 512 - len(
                f"{botname_with_vhost} PRIVMSG {channel.name} :\r\n".encode("utf-8")
            )

            self.logger.debug(
                "char_limit for %s is set to %s", channel.name, channel.char_limit
            )

    def _handle_invite(self, user, channel_name):
        self.logger.info("%s has invited us to %s", user, channel_name)
        self._send_join(channel_name)

    def _handle_kick(self, user, channel_name, reason):
        self.logger.info("%s has kicked us from %s for: %s", user, channel_name, reason)
        self._send_join(channel_name)

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

    def _handle_nick_change(self, user_name, user_new_name):
        if user_name in self.users:
            self.logger.debug(
                "%s changed their nick to %s, updating the user_obj",
                user_name,
                user_new_name,
            )

            self.users.remove(user_name)
            self.users.append(user_new_name)

            for user_obj in self.user_obj:
                if user_obj.name == user_name:
                    user = user_obj
                    break

            user.name = user_new_name

            if user_name == self.admin:
                self.logger.debug(
                    "%s was also set as the admin user, updating",
                    user_name,
                )

                self.admin = user_new_name

    # -- timers -- #
    # _client_init timer
    def _client_init_pong_timer(self):
        self.logger.debug("started PONG timer")

        while not self.client_init_pong_timer_stop:
            if (
                int(time.strftime("%s")) - self.client_init_ping_tstamp
                > self._PONG_TIMEOUT
            ):
                self.logger.warning(
                    "did not get a PONG after %s seconds",
                    self._PONG_TIMEOUT,
                )

                if not self.client_init_pong_timer_stop:
                    self.connected = False
                    self.stop()

            time.sleep(1)

        self.client_init_pong_timer_halt = True
        self.logger.debug("stopped PONG timer")

    # _loop timers
    def _loop_ping_timer(self):
        self.logger.debug("started keepalive PING sender")

        while not self.halt:
            self._send_ping()
            self.loop_ping_sent = True
            self.loop_ping_tstamp = int(time.strftime("%s"))

            self.logger.debug("sent keepalive PING")

            self._loop_pong_timer()

            time_till_pong = int(time.strftime("%s")) - self.loop_pong_tstamp
            time_sleep = self._PING_INTERVAL - time_till_pong

            self.logger.debug("keepalive PONG sender: sleeping for %s", time_sleep)

            time.sleep(time_sleep)

    def _loop_pong_timer(self):
        self.logger.debug("started keepalive PONG timer")

        while not self.loop_pong_received:
            if int(time.strftime("%s")) - self.loop_ping_tstamp > self._PONG_TIMEOUT:
                self.logger.warning(
                    "did not get a PONG after %s seconds",
                    self._PONG_TIMEOUT,
                )

                if not self.loop_pong_received:
                    self.connected = False
                    self.stop()

            time.sleep(1)

        self.loop_ping_sent = None
        self.loop_ping_tstamp = None
        self.loop_pong_received = None
        self.logger.debug("stopped keepalive PONG timer")

    # -- stages -- #
    # stage 1: open socket that we will pass around for the entire server instance
    def _connect(self):
        self.logger.info("%s connecting %s", f"{ac.BYEL}-->{ac.BWHI}", ac.RES)

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

        self.logger.info("%s connected %s", f"{ac.BYEL}-->{ac.BWHI}", ac.RES)
        self.connected = True

    # stage 2: send NICK and USER, update address, send PING, hand over to channel handling
    # pylint: disable=too-many-statements
    def _client_init(self):
        self.logger.info("%s initing client %s", f"{ac.BYEL}-->{ac.BWHI}", ac.RES)

        addr_updated = None

        if self.passwd:
            self._send_pass()

        self._send_nick()
        self._send_user()

        while not self.halt:
            if self.client_init_pong_timer_stop and addr_updated:
                break

            try:
                recv_data = self.conn.recv(512)
            # pylint: disable=bare-except
            except:
                self.logger.exception("recv error during _client_init()")

            data = self._decode_data(recv_data)

            if not data:
                continue

            for line in data:
                if not line:
                    continue

                self.logger.debug("%s %s", f"{ac.BBLU}<--{ac.RES}", line.rstrip("\r\n"))

                # respond to PING
                if line.split()[0] == "PING":
                    Thread(target=self._send_pong, args=[line], daemon=True).start()

                    continue

                # fix name colissions
                if line.split()[1] == "433":
                    self.logger.info("nick colission occured, updating")
                    self.botname = f"{self.botname}0"

                    self._send_nick()
                    self._send_user()

                    continue

                # password protection
                if line.split()[1] == "464":
                    if self.passwd:
                        self.logger.warning("incorrect password")
                    else:
                        self.logger.warning("a password is required")

                    self.stop()

                    continue

                # welcome msg, need to update the address to match the node we round robined
                # to for sending the pong
                if line.split()[1] == "001":
                    self.address = line.split()[0]
                    addr_updated = True
                    self.logger.debug("updated address")

                    continue

                # need to send ping before joins for networks like rizon
                # 376: end of motd, 422: no motd found, 221: server-wide mode set for user
                if (
                    line.split()[1] in ("376", "422", "221")
                    and not self.client_init_ping_sent
                ):
                    self._send_ping()
                    self.logger.debug("sent PING before JOINs")

                    self.client_init_ping_sent = True
                    self.client_init_ping_tstamp = int(time.strftime("%s"))

                    Thread(target=self._client_init_pong_timer, daemon=True).start()

                    continue

                # wait for the pong, if we received it, switch to _loop()
                if (
                    self.client_init_ping_sent
                    and self.address in line.split()[0]
                    and line.split()[1] == "PONG"
                ):
                    self.client_init_pong_received = True
                    self.client_init_pong_timer_stop = True
                    self.logger.debug("received PONG")

                    continue

        while not self.halt:
            if not self.client_init_pong_timer_halt:
                time.sleep(1)
            else:
                self.logger.info("%s init done %s", f"{ac.BYEL}-->{ac.BWHI}", ac.RES)
                break

    # stage 3: final infinite loop
    def _loop(self):
        self.logger.info("%s entered the loop %s", f"{ac.BYEL}-->{ac.BWHI}", ac.RES)

        Thread(target=self._loop_ping_timer, daemon=True).start()

        # pylint: disable=too-many-nested-blocks
        while not self.halt:
            try:
                recv_data = self.conn.recv(512)
            # pylint: disable=bare-except
            except:
                self.logger.exception("recv failed")

            data = self._decode_data(recv_data)

            if not data:
                continue

            for line in data:
                if not line:
                    continue

                self.logger.debug("%s %s", f"{ac.BBLU}<--{ac.RES}", line.rstrip("\r\n"))

                # PING handling
                if line.split()[0] == "PING":
                    Thread(target=self._send_pong, args=[line], daemon=True).start()
                    continue

                # PONG handling
                if (
                    self.client_init_ping_sent
                    and self.address in line.split()[0]
                    and line.split()[1] == "PONG"
                ):
                    self.loop_pong_received = True
                    self.loop_pong_tstamp = int(time.strftime("%s"))
                    self.logger.debug("received keepalive PONG")

                    continue

                # KILL handling
                if line.split()[0] == "ERROR" and line.split()[1] == "Killed":
                    self.logger.warning("we got killed")
                    self.connected = False
                    self.stop()

                    continue

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

                    continue

                # INVITE handling
                if line.split()[1] == "INVITE":
                    Thread(
                        target=self._handle_invite,
                        args=[strip_user(line.split()[0]), line.split()[3]],
                        daemon=True,
                    ).start()

                    continue

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

                    continue

                # mode +b handling
                if line.split()[1] == "474":
                    Thread(
                        target=self._handle_ban,
                        args=[line.split()[3]],
                        daemon=True,
                    ).start()

                    continue

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

                        if cmd in self._CHANNEL_CMDS:
                            self.logger.info(
                                "%s%s%s %s %s",
                                f"{ac.BMGN}[{ac.BWHI}{user}",
                                f"{ac.BRED}/",
                                f"{ac.BGRN}{channel.name}{ac.BMGN}]",
                                f"{ac.BCYN}{cmd}",
                                f"{' '.join(args)}{ac.RES}",
                            )

                            Thread(
                                target=self._handle_channel_msg,
                                args=[
                                    channel,
                                    user,
                                    cmd,
                                    args,
                                ],
                                daemon=True,
                            ).start()

                            continue

                    # user PRIVMSG
                    if line.split()[2] == self.botname:
                        user = strip_user(line.split()[0])
                        cmd = line.split()[3]
                        args = line.split()[4:]

                        self.logger.info(
                            "%s%s%s %s %s",
                            f"{ac.BMGN}[{ac.BWHI}{user}",
                            f"{ac.BRED}/",
                            f"{ac.BGRN}PM{ac.BMGN}]",
                            f"{ac.BCYN}{cmd}",
                            f"{' '.join(args)}{ac.RES}",
                        )

                        if cmd in self._USER_CMDS:
                            Thread(
                                target=self._handle_pm,
                                args=[
                                    user,
                                    cmd,
                                    args,
                                ],
                                daemon=True,
                            ).start()

                            continue

                # NICK handling (user nick changes)
                if line.split()[1] == "NICK":
                    user_name = strip_user(line.split()[0])
                    user_new_name = line.split()[2]

                    Thread(
                        target=self._handle_nick_change,
                        args=[
                            user_name,
                            user_new_name,
                        ],
                        daemon=True,
                    ).start()

                    continue

    # -- CLI() interactions -- #
    def run(self):
        self._connect()
        self._client_init()

        if not self.halt:
            self.logger.info("%s joining channels %s", f"{ac.BYEL}-->{ac.BWHI}", ac.RES)
            for channel in self.channels:
                self._send_join(channel)

            self._loop()

    def stop(self):
        self.logger.warning("%s stopping %s", f"{ac.BYEL}-->{ac.BWHI}", ac.RES)
        self.halt = True

        if self.connected:
            try:
                self._send_quit("quitting.")
            # pylint: disable=bare-except
            except:
                self.logger.warning("sending quit failed")

        self.logger.debug("shutting down socket (RDWR)")
        self.conn.shutdown(socket.SHUT_RDWR)

        self.logger.warning(
            "%s closing connection %s", f"{ac.BYEL}-->{ac.BWHI}", ac.RES
        )
        self.conn.close()

        self.logger.info("removing %s from servers list", self.name)
        self.cli.servers.remove(self)
