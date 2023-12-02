import time

from threading import Thread

import bands.irc.channel.cmd as ChanCMD
import bands.irc.user.cmd as UserCMD

from bands.colors import ANSIColors
from bands.irc.util import strip_user

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
        self.users = server.users
        self.channel_obj = server.channel_obj
        self.user_obj = server.user_obj

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

                # topic
                # 1. channel topic msg on join
                if (
                    self.socket.address in line_s[0]
                    and line_s[1] == "332"
                    and line_s[2] == self.server.botname
                    and line_s[3] in self.channels
                ):
                    Thread(
                        target=self.handle.channel_topic_msg,
                        args=[line_s[3], line_s[4:]],
                        daemon=True,
                    ).start()

                    continue

                # channel topic meta on join
                if (
                    self.socket.address in line_s[0]
                    and line_s[1] == "333"
                    and line_s[2] == self.server.botname
                    and line_s[3] in self.channels
                ):
                    Thread(
                        target=self.handle.channel_topic_meta,
                        args=[line_s[3], line_s[4], line_s[5]],
                        daemon=True,
                    ).start()

                    continue

                # channel topic msg and meta w/ TOPIC
                if line_s[1] == "TOPIC" and line_s[2] in self.channels:
                    Thread(
                        target=self.handle.channel_topic_msg,
                        args=[line_s[2], line_s[3:]],
                        daemon=True,
                    ).start()

                    Thread(
                        target=self.handle.channel_topic_meta,
                        args=[line_s[2], line_s[0], time.strftime("%s")],
                        daemon=True,
                    ).start()

                    continue

                # PING handling
                if line_s[0] == "PING":
                    Thread(
                        target=self.sock_ops.send_pong, args=[line], daemon=True
                    ).start()

                    continue

                # PONG handling
                if (
                    self.ping_sent
                    and self.socket.address in line_s[0]
                    and line_s[1] == "PONG"
                ):
                    self.pong_received = True
                    self.pong_tstamp = int(time.strftime("%s"))
                    self.logger.debug("received keepalive PONG")

                    continue

                # KILL handling
                if line_s[0] == "ERROR" and line_s[1] == "Killed":
                    self.logger.warning("we got killed")
                    self.socket.connected = False
                    self.server.stop()

                    continue

                # JOIN handling
                if strip_user(line_s[0]) == self.server.botname and line_s[1] == "JOIN":
                    Thread(
                        target=self.handle.join,
                        args=[line_s[0], line_s[2]],
                        daemon=True,
                    ).start()

                    continue

                # INVITE handling
                if line_s[1] == "INVITE":
                    Thread(
                        target=self.handle.invite,
                        args=[strip_user(line_s[0]), line_s[3]],
                        daemon=True,
                    ).start()

                    continue

                # KICK handling
                if line_s[1] == "KICK" and line_s[3] == self.server.botname:
                    Thread(
                        target=self.handle.kick,
                        args=[
                            strip_user(line_s[0]),
                            line_s[2],
                            line_s[4],
                        ],
                        daemon=True,
                    ).start()

                # mode +b handling
                if line_s[1] == "474":
                    Thread(
                        target=self.handle.ban,
                        args=[line_s[3]],
                        daemon=True,
                    ).start()

                    continue

                # PRIVMSG handling
                if line_s[1] == "PRIVMSG":
                    # channel PRIVMSG
                    if line_s[2] in self.channels:
                        for chan in self.channel_obj:
                            if chan.name == line_s[2]:
                                channel = chan
                                break

                        user = strip_user(line_s[0])
                        cmd = line_s[3]
                        args = line_s[4:]

                        if cmd in ChanCMD.CMDS:
                            self.logger.info(
                                "%s%s%s %s %s",
                                f"{ac.BMGN}[{ac.BWHI}{user}",
                                f"{ac.BRED}/",
                                f"{ac.BGRN}{channel.name}{ac.BMGN}]",
                                f"{ac.BCYN}{cmd}",
                                f"{' '.join(args)}{ac.RES}",
                            )

                            Thread(
                                target=self.handle.channel_msg,
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
                    if line_s[2] == self.server.botname:
                        user = strip_user(line_s[0])
                        cmd = line_s[3]
                        args = line_s[4:]

                        self.logger.info(
                            "%s%s%s %s %s",
                            f"{ac.BMGN}[{ac.BWHI}{user}",
                            f"{ac.BRED}/",
                            f"{ac.BGRN}PM{ac.BMGN}]",
                            f"{ac.BCYN}{cmd}",
                            f"{' '.join(args)}{ac.RES}",
                        )

                        if cmd in UserCMD.CMDS:
                            Thread(
                                target=self.handle.user_msg,
                                args=[
                                    user,
                                    cmd,
                                    args,
                                ],
                                daemon=True,
                            ).start()

                            continue

                # NICK handling (user nick changes)
                if line_s[1] == "NICK":
                    user_name = strip_user(line_s[0])
                    user_new_name = line_s[2]

                    Thread(
                        target=self.handle.nick_change,
                        args=[
                            user_name,
                            user_new_name,
                        ],
                        daemon=True,
                    ).start()

                    continue
