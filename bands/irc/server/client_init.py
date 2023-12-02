import time

from threading import Thread

from bands.colors import ANSIColors

ac = ANSIColors()


# pylint: disable=too-many-instance-attributes
class ClientInit:
    # pylint: disable=too-few-public-methods
    def __init__(self, server):
        # server
        self.server = server
        self.logger = server.logger
        self.socket = server.socket
        self.sock_ops = server.sock_ops

        # timer
        self.ping_sent = None
        self.ping_tstamp = None
        self.pong_received = None
        self.ping_timer_stop = None
        self.ping_timer_halt = None

    # client_init timer
    def _pong_timer(self):
        self.logger.debug("started PONG timer")

        while not self.ping_timer_stop:
            if int(time.strftime("%s")) - self.ping_tstamp > self.server.PONG_TIMEOUT:
                self.logger.warning(
                    "did not get a PONG after %s seconds",
                    self.server.PONG_TIMEOUT,
                )

                if not self.ping_timer_stop:
                    self.socket.connected = False
                    self.server.stop()

            time.sleep(1)

        self.ping_timer_halt = True
        self.logger.debug("stopped PONG timer")

    # stage 1: send NICK and USER, update address, send PING, hand over to channel handling
    # pylint: disable=too-many-statements,too-many-branches
    def run(self):
        self.logger.info("%s initing client %s", f"{ac.BYEL}-->{ac.BWHI}", ac.RES)

        addr_updated = None

        if self.server.passwd:
            self.sock_ops.send_pass()

        self.sock_ops.send_nick()
        self.sock_ops.send_user()

        while not self.socket.halt:
            if self.ping_timer_stop and addr_updated:
                break

            try:
                recv_data = self.socket.conn.recv(512)
            # pylint: disable=bare-except
            except:
                self.logger.exception("recv error during client_init()")

            data = self.server.sock_ops.decode_data(recv_data)

            if not data:
                continue

            for line in data:
                if not line:
                    continue

                self.logger.debug("%s %s", f"{ac.BBLU}<--{ac.RES}", line.rstrip("\r\n"))

                line_s = line.split(' ')

                # respond to PING
                if line_s[0] == "PING":
                    Thread(
                        target=self.sock_ops.send_pong, args=[line], daemon=True
                    ).start()

                    continue

                # fix name colissions
                if line_s[1] == "433":
                    self.logger.info("nick colission occured, updating")
                    self.server.botname = f"{self.server.botname}0"

                    self.sock_ops.send_nick()
                    self.sock_ops.send_user()

                    continue

                # password protection
                if line_s[1] == "464":
                    if self.server.passwd:
                        self.logger.warning("incorrect password")
                    else:
                        self.logger.warning("a password is required")

                    self.server.stop()

                    continue

                # welcome msg, need to update the address to match the node we round robined
                # to for sending the pong
                if line_s[1] == "001":
                    self.socket.address = line_s[0]
                    addr_updated = True
                    self.logger.debug("updated address")

                    continue

                # need to send ping before joins for networks like rizon
                # 376: end of motd, 422: no motd found, 221: server-wide mode set for user
                if line_s[1] in ("376", "422", "221") and not self.ping_sent:
                    self.sock_ops.send_ping()
                    self.logger.debug("sent PING before JOINs")

                    self.ping_sent = True
                    self.ping_tstamp = int(time.strftime("%s"))

                    Thread(target=self._pong_timer, daemon=True).start()

                    continue
                # wait for the pong, if we received it, switch to _loop()
                if (
                    self.ping_sent
                    and self.socket.address in line_s[0]
                    and line_s[1] == "PONG"
                ):
                    self.pong_received = True
                    self.ping_timer_stop = True
                    self.logger.debug("received PONG")

                    continue

        while not self.socket.halt:
            if not self.ping_timer_halt:
                time.sleep(1)
            else:
                self.logger.info("%s init done %s", f"{ac.BYEL}-->{ac.BWHI}", ac.RES)
                break
