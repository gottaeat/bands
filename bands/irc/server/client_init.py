import re
import time

from threading import Thread

from bands.colors import ANSIColors

ac = ANSIColors()


class ClientInit:
    def __init__(self, server):
        # server
        self.server = server
        self.logger = self.server.logger.getChild(self.__class__.__name__)
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
    def run(self):
        self.logger.info("%s", f"{ac.BYEL}--> {ac.BWHI}initializing {ac.RES}")

        want_cap = ["multi-prefix"]

        addr_updated = None
        cap_requested = None
        cap_ackd = None

        # CAP stage #1: start cap negotiation
        self.sock_ops.send_raw("CAP LS 302")
        self.logger.debug("sent CAP LS request")

        # CAP stage #2: dud join to use the error as a notifier of the CAP LS
        # being over
        self.sock_ops.send_raw("JOIN :")
        self.logger.debug("sent dud JOIN for CAP LS end notifier")

        if self.server.passwd:
            self.sock_ops.send_pass()

        self.sock_ops.send_nick()
        self.sock_ops.send_user()

        while not self.socket.halt:
            if self.ping_timer_stop and addr_updated and cap_ackd:
                break

            try:
                recv_data = self.socket.conn.recv(512)
            except:
                if self.socket.halt:
                    break

                self.logger.exception("recv error during client_init()")

            data = self.server.sock_ops.decode_data(recv_data)

            if not data:
                continue

            for line in data:
                if not line:
                    continue

                self.logger.debug("%s%s", f"{ac.BBLU}<-- {ac.RES}", line.rstrip("\r\n"))

                line_s = line.split()

                # CAP
                if line_s[1] == "CAP":
                    # CAP stage #3: parse and store server CAPS
                    if line_s[3] == "LS":
                        self.logger.debug("received CAP LS response")

                        if line_s[4] == "*":
                            start_index = 5
                        else:
                            start_index = 4

                        for item in line_s[start_index:]:
                            self.server.caps.append(re.sub(r"^:", "", item))

                        continue

                    # CAP stage #5: if server ACKs our REQ for multi-prefix,
                    # send client details
                    ackd_caps = []
                    if cap_requested and line_s[3] == "ACK":
                        cap_ackd = True

                        self.logger.debug("received CAP ACK, final server CAPs are:")
                        for cap in self.server.caps:
                            self.logger.debug(" - %s", cap)

                        for item in line_s[4:]:
                            ackd_caps.append(re.sub(r"^:", "", item))

                        if "multi-prefix" in ackd_caps:
                            self.logger.debug("server gave us multi-prefix CAP")
                        else:
                            errmsg = "bands relies on multi-prefix CAP, but the "
                            errmsg += "server did not offer it, stopping"
                            self.logger.warning(errmsg)

                            self.socket.connected = False
                            return self.server.stop()

                        if "chghost" in ackd_caps:
                            self.logger.debug("server gave us chghost CAP")
                        else:
                            self.logger.warning("server did not offer chghost CAP")

                        self.sock_ops.send_raw("CAP END")
                        self.logger.debug("ended CAP negotiation")

                        continue

                # CAP stage #4: when the dud 451 shows us the LS of the server
                # is over, send the request for multi-prefix
                if line_s[1] == "451":
                    if "multi-prefix" in self.server.caps:
                        self.logger.debug("server supports multi-prefix CAP")
                    else:
                        errmsg = "bands relies on multi-prefix CAP, but the "
                        errmsg += "server does not support it, stopping"
                        self.logger.warning(errmsg)

                        self.socket.connected = False
                        return self.server.stop()

                    if "chghost" in self.server.caps:
                        self.logger.debug("server supports chghost CAP")
                        want_cap.append("chghost")
                    else:
                        self.logger.warning("server does not support chghost CAP")

                    self.sock_ops.send_raw(f"CAP REQ :{' '.join(want_cap)}")
                    self.logger.debug("requested CAPs from server")
                    cap_requested = True

                    continue

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
                    if not cap_ackd:
                        errmsg = "bands relies on IRCv3 CAPs at a basic level, "
                        errmsg += "but the server did not respond to the CAP "
                        errmsg += "negotiation, stopping"
                        self.logger.warning(errmsg)

                        self.socket.connected = False
                        self.server.stop()

                    self.socket.address = line_s[0].lstrip(":")
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
                self.logger.info("%s", f"{ac.BYEL}--> {ac.BWHI}initialized {ac.RES}")
                break
