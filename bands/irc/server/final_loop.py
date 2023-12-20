import time

from threading import Thread

import bands.irc.channel.cmd as ChanCMD
import bands.irc.user.cmd as UserCMD

from bands.colors import ANSIColors
from bands.irc.util import chop_userline

from .handle import Handle

ac = ANSIColors()


# pylint: disable=too-many-instance-attributes,too-few-public-methods
class FinalLoop:
    def __init__(self, server):
        # server
        self.server = server
        self.logger = server.logger
        self.socket = server.socket
        self.sock_ops = server.sock_ops

        # handler init
        self.handle = Handle(server)

        # user and channels
        self.channels = server.channels
        self.channel_obj = server.channel_obj
        self.users = server.users

        # timer
        self.ping_sent = None
        self.ping_tstamp = None
        self.pong_received = None
        self.pong_tstamp = None

    def _ping_timer(self):
        self.logger.debug("started keepalive PING sender")

        while not self.socket.halt:
            self.sock_ops.send_ping()
            self.ping_sent = True
            self.ping_tstamp = int(time.strftime("%s"))

            self.logger.debug("sent keepalive PING")

            self._pong_timer()

            time_till_pong = int(time.strftime("%s")) - self.pong_tstamp
            time_sleep = self.server.PING_INTERVAL - time_till_pong

            self.logger.debug("keepalive PONG sender: sleeping for %s", time_sleep)

            time.sleep(time_sleep)

    def _pong_timer(self):
        self.logger.debug("started keepalive PONG timer")

        while not self.pong_received:
            if int(time.strftime("%s")) - self.ping_tstamp > self.server.PONG_TIMEOUT:
                self.logger.warning(
                    "did not get a PONG after %s seconds",
                    self.server.PONG_TIMEOUT,
                )

                if not self.pong_received:
                    self.socket.connected = False
                    self.server.stop()

            time.sleep(1)

        self.ping_sent = None
        self.ping_tstamp = None
        self.pong_received = None
        self.logger.debug("stopped keepalive PONG timer")

    # pylint: disable=too-many-branches,too-many-statements
    def run(self):
        self.logger.info("%s entered the loop %s", f"{ac.BYEL}-->{ac.BWHI}", ac.RES)

        Thread(target=self._ping_timer, daemon=True).start()

        # pylint: disable=too-many-nested-blocks
        while not self.socket.halt:
            try:
                recv_data = self.socket.conn.recv(512)
            # pylint: disable=bare-except
            except:
                self.logger.exception("recv failed")

            data = self.server.sock_ops.decode_data(recv_data)

            if not data:
                continue

            for line in data:
                if not line:
                    continue

                self.logger.debug("%s %s", f"{ac.BBLU}<--{ac.RES}", line.rstrip("\r\n"))

                line_s = line.split()

                # -- keepalives -- #
                # PING handling
                if line_s[0] == "PING":
                    Thread(
                        target=self.sock_ops.send_pong, args=[line], daemon=True
                    ).start()

                    continue

                # PONG handling
                if self.ping_sent and line_s[1] == "PONG":
                    self.pong_received = True
                    self.pong_tstamp = int(time.strftime("%s"))
                    self.logger.debug("received keepalive PONG")

                    continue

                # -- topic -- #
                # initial topic message
                if line_s[1] == "332":
                    Thread(
                        target=self.handle.initial_topic_msg,
                        args=[line_s[3], line_s[4:]],
                        daemon=True,
                    ).start()

                    continue

                # initial topic meta
                if line_s[1] == "333":
                    Thread(
                        target=self.handle.initial_topic_meta,
                        args=[line_s[3], line_s[4], line_s[5]],
                        daemon=True,
                    ).start()

                    continue

                # TOPIC handling
                if line_s[1] == "TOPIC":
                    Thread(
                        target=self.handle.topic,
                        args=[line_s[2], line_s[0], line_s[3:]],
                        daemon=True,
                    ).start()

                    continue

                # WHO handling
                if line_s[1] == "352":
                    Thread(
                        target=self.handle.who,
                        args=[line_s[3], line_s[7], line_s[4], line_s[5], line_s[8]],
                        daemon=True,
                    ).start()

                    continue

                # NICK handling
                if line_s[1] == "NICK":
                    Thread(
                        target=self.handle.nick,
                        args=[
                            line_s[0],
                            line_s[2],
                        ],
                        daemon=True,
                    ).start()

                    continue

                # JOIN handling
                if line_s[1] == "JOIN":
                    Thread(
                        target=self.handle.join,
                        args=[line_s[0], line_s[2]],
                        daemon=True,
                    ).start()

                    continue

                # KICK handling
                if line_s[1] == "KICK":
                    Thread(
                        target=self.handle.kick,
                        args=[line_s[0], line_s[2], line_s[3], line_s[4]],
                        daemon=True,
                    ).start()

                    continue

                # QUIT handling
                if line_s[1] == "QUIT":
                    Thread(
                        target=self.handle.quit,
                        args=[line_s[0], line_s[2:]],
                        daemon=True,
                    ).start()

                    continue

                # -- bot self related -- #
                # bot KILL handling
                if line_s[0] == "ERROR" and line_s[1] == "Killed":
                    self.logger.warning("we got killed")
                    self.socket.connected = False
                    self.server.stop()

                    continue

                # bot INVITE handling
                if line_s[1] == "INVITE":
                    Thread(
                        target=self.handle.bot_invite,
                        args=[chop_userline(line_s[0])["nick"], line_s[3]],
                        daemon=True,
                    ).start()

                    continue

                # bot banned
                if line_s[1] == "474":
                    Thread(
                        target=self.handle.bot_ban, args=[line_s[3]], daemon=True
                    ).start()

                    continue

                # -- cmd trigger -- #
                # PRIVMSG handling
                if line_s[1] == "PRIVMSG":
                    # channel PRIVMSG
                    if line_s[2] in self.channels and line_s[3] in ChanCMD.CMDS:
                        Thread(
                            target=self.handle.channel_msg,
                            args=[line_s[2], line_s[0], line_s[3], line_s[4:]],
                            daemon=True,
                        ).start()

                        continue

                    # user PRIVMSG
                    if line_s[2] == self.server.botname and line_s[3] in UserCMD.CMDS:
                        Thread(
                            target=self.handle.user_msg,
                            args=[line_s[0], line_s[3], line_s[4:]],
                            daemon=True,
                        ).start()

                        continue
