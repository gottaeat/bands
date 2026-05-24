import time

from threading import Thread

import bands.irc.user.cmd as UserCMD

from bands.colors import ANSIColors

from .handle import Handle

ac = ANSIColors()


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

        # timer
        self.activity_tstamp = int(time.strftime("%s"))
        self.pong_received = False

    # - - liveness checks - - #
    def _keepalive_loop(self):
        self.logger.debug("keepalive started")

        while not self.socket.halt:
            # check if it's been 60 seconds since last activity, ignore if so
            if (
                int(time.strftime("%s")) - self.activity_tstamp
                < self.server.PING_INTERVAL
            ):
                time.sleep(1)
                continue

            # it's been 60 seconds or more since we've last received any activity
            # from the socket, send a ping and log the time
            self.pong_received = False
            ping_tstamp = int(time.strftime("%s"))

            self.sock_ops.send_ping()
            self.logger.warning(
                "received nothing for %s seconds, sent keepalive PING",
                self.server.PING_INTERVAL,
            )

            # wait for the pong
            while not self.socket.halt and not self.pong_received:
                if int(time.strftime("%s")) - ping_tstamp > self.server.PONG_TIMEOUT:
                    self.logger.warning(
                        "server didn't respond to keepalive PING for %s seconds, stopping",
                        self.server.PONG_TIMEOUT,
                    )
                    self.socket.connected = False
                    self.server.stop()
                    return

                time.sleep(1)

            self.pong_received = False

    def run(self):
        self.logger.info("%s", f"{ac.BYEL}--> {ac.BWHI}entered final loop{ac.RES}")

        # start keepalive thread
        Thread(target=self._keepalive_loop, daemon=True).start()

        # initial joins
        self.logger.info(
            "%s", f"{ac.BYEL}--> {ac.BWHI}performing initial joins{ac.RES}"
        )

        for channel in self.server.channels_init:
            self.sock_ops.send_join(channel)

        while not self.socket.halt:
            try:
                recv_data = self.socket.conn.recv(512)
            except:
                if self.socket.halt:
                    break

                self.logger.exception("recv failed")

            data = self.server.sock_ops.decode_data(recv_data)

            if not data:
                continue

            for line in data:
                if not line:
                    continue

                self.logger.debug("%s%s", f"{ac.BBLU}<-- {ac.RES}", line.rstrip("\r\n"))

                line_s = line.split()

                # on every line received from socket, update the activity timestamp
                self.activity_tstamp = int(time.strftime("%s"))

                # -- keepalives -- #
                # PING handling
                if line_s[0] == "PING":
                    Thread(
                        target=self.sock_ops.send_pong, args=[line], daemon=True
                    ).start()

                    continue

                # PONG handling
                if line_s[1] == "PONG":
                    self.pong_received = True
                    self.logger.debug("PONG received")

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

                # CHGHOST handling
                if line_s[1] == "CHGHOST" and "chghost" in self.server.caps:
                    Thread(
                        target=self.handle.chghost,
                        args=[line_s[0], line_s[2], line_s[3]],
                        daemon=True,
                    ).start()

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
                        args=[line_s[0], line_s[2], line_s[3], line_s[4:]],
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

                # PART handling
                if line_s[1] == "PART":
                    Thread(
                        target=self.handle.part,
                        args=[line_s[0], line_s[2], line_s[3:]],
                        daemon=True,
                    ).start()

                    continue

                # MODE handling
                if line_s[1] == "MODE":
                    Thread(
                        target=self.handle.mode,
                        args=[line_s[0], line_s[2], line_s[3], line_s[4:]],
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
                        args=[line_s[0], line_s[3]],
                        daemon=True,
                    ).start()

                    continue

                # bot banned
                if line_s[1] == "474":
                    Thread(
                        target=self.handle.bot_ban, args=[line_s[3]], daemon=True
                    ).start()

                    continue

                # bot not invited
                if line_s[1] == "473":
                    Thread(
                        target=self.handle.bot_invite_only,
                        args=[line_s[3]],
                        daemon=True,
                    ).start()

                    continue

                # -- cmd trigger -- #
                # PRIVMSG handling
                if line_s[1] == "PRIVMSG":
                    # channel PRIVMSG
                    if line_s[2].lower() in self.channels:
                        Thread(
                            target=self.handle.channel_msg,
                            args=[line_s[2], line_s[0], line_s[3:]],
                            daemon=True,
                        ).start()

                        continue

                    # user PRIVMSG
                    if (
                        line_s[2].lower() == self.server.botname.lower()
                        and line_s[3] in UserCMD.CMDS
                    ):
                        Thread(
                            target=self.handle.user_msg,
                            args=[line_s[0], line_s[3], line_s[4:]],
                            daemon=True,
                        ).start()
