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
        self.ping_sent = None
        self.ping_tstamp = None
        self.pong_received = None
        self.pong_tstamp = None
        self.kill_timer = None

    def _ping_sender(self):
        self.logger.debug("PING sender started")

        while not self.socket.halt:
            self.sock_ops.send_ping()
            self.logger.debug("PING sent")

            self.ping_sent = True
            self.ping_tstamp = int(time.strftime("%s"))

            self._pong_timer()
            self._ping_timer()

    def _pong_timer(self):
        self.logger.debug("PONG timer started")

        # sleep till we receive a PONG, if the timeout is exceeded, kill socket
        while not self.pong_received:
            if int(time.strftime("%s")) - self.ping_tstamp > self.server.PONG_TIMEOUT:
                self.logger.warning(
                    "PONG timeout: %s, stopping",
                    self.server.PONG_TIMEOUT,
                )

                if not self.pong_received:
                    self.socket.connected = False
                    self.server.stop()

            time.sleep(1)

        # if we did get a PONG, reset state
        self.ping_sent = None
        self.ping_tstamp = None
        self.pong_received = None
        self.kill_timer = None
        self.logger.debug("PONG timer stopped")

    def _ping_timer(self):
        # we sent a PING, got a PONG, now we sleep for the remaning amount of
        # seconds deducted from 120 seconds since the time we received the PONG
        self.logger.debug("PING timer started")

        if not self.socket.halt:
            sleep_for = self.server.PING_INTERVAL - (
                int(time.strftime("%s")) - self.pong_tstamp
            )

            self.logger.debug("PING timer sleeping for %s", sleep_for)

            time_slept = 0
            while time_slept != sleep_for:
                # if we get a PING from server while we are waiting for sending
                # a PING ourselves, reset the timer.
                if self.kill_timer:
                    sleep_for = self.server.PING_INTERVAL - (
                        int(time.strftime("%s")) - self.pong_tstamp
                    )

                    time_slept = 0
                    self.kill_timer = None

                    self.logger.debug(
                        "PING timer interrupted, sleeping for %s", sleep_for
                    )

                time.sleep(1)
                time_slept += 1

    def run(self):
        self.logger.info("%s", f"{ac.BYEL}--> {ac.BWHI}entered final loop{ac.RES}")

        Thread(target=self._ping_sender, daemon=True).start()

        while not self.socket.halt:
            try:
                recv_data = self.socket.conn.recv(512)
            except:
                self.logger.exception("recv failed")

            data = self.server.sock_ops.decode_data(recv_data)

            if not data:
                continue

            for line in data:
                if not line:
                    continue

                self.logger.debug("%s%s", f"{ac.BBLU}<-- {ac.RES}", line.rstrip("\r\n"))

                line_s = line.split()

                # -- keepalives -- #
                # PING handling
                if line_s[0] == "PING":
                    Thread(
                        target=self.sock_ops.send_pong, args=[line], daemon=True
                    ).start()

                    # if we receive a PING while waiting to send our own, reset
                    # the timer counter
                    self.pong_received = True
                    self.pong_tstamp = int(time.strftime("%s"))
                    self.kill_timer = True

                    continue

                # PONG handling
                if self.ping_sent and line_s[1] == "PONG":
                    self.pong_received = True
                    self.pong_tstamp = int(time.strftime("%s"))
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

                # -- cmd trigger -- #
                # PRIVMSG handling
                if line_s[1] == "PRIVMSG":
                    # channel PRIVMSG
                    if line_s[2] in self.channels:
                        Thread(
                            target=self.handle.channel_msg,
                            args=[line_s[2], line_s[0], line_s[3:]],
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
