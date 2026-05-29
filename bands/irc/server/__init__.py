import time

from bands.colors import ANSIColors

from .socket_ops import SocketOps
from .client_init import ClientInit
from .final_loop import FinalLoop

ac = ANSIColors()


class Server:
    USER_NICKLIMIT = 30

    # time to wait for the PONG to arrive
    PONG_TIMEOUT = 30
    # received nothing for N seconds, send PING
    PING_INTERVAL = 120
    # wait for N seconds between reattempting reconnects
    RECONNECT_DELAY = 30

    def __init__(self, socket):
        # args
        self.socket = socket

        # config
        self.name = None
        self.botname = None
        self.channels_init = []
        self.passwd = None
        self.scroll_speed = None
        self.burst_limit = None
        self.config = None

        # logger
        self.logger = None

        # socket_ops
        self.sock_ops = None
        # running = True: run() is handling this server, it might be:
        #   - still getting connected via socket.connect()
        #   - calling ClientInit()
        #   - entered the infinite loop of FinalLoop()
        #   - connection died, socket+server state got flushed, and is in the
        #     loop of reconnecting back to the server
        self.running = False
        # wanted = True: this died on its own, i still want to handle for this
        #                server
        # wanted = False: i killed this
        self.wanted = True

        # ircv3
        self.caps = []

        # channels + users
        self.channels = {}
        self.users = {}

    def run(self):
        # a server is deemed wanted until bot is going down because of SIGINT
        # or a CTL command wants to disconnect
        self.wanted = True

        # this server is currently being handled by a runner
        self.running = True

        try:
            # until bands is going down or until CTL says we don't want this
            # server, keep running it
            while self.wanted and not self.config.halt:
                try:
                    # this is set to false for two reasons:
                    #   1. in a fresh init of a socket halt is None, we set it
                    #      to false
                    #   2. server.stop() was called because of an exception etc.
                    #      and that set halt to true, but we want to retry now
                    self.socket.halt = False

                    # ConfigYAML gave Server a Socket, connect to it, then give
                    # the SocketOps yourself (Server) so IRC bits can send/recv
                    self.socket.connect()
                    self.sock_ops = SocketOps(self)

                    # init the client -> if you die, we get hit with
                    # server.stop(), but wanted will still be true, so we'll run
                    # this loop again.
                    cl_init = ClientInit(self)
                    cl_init.run()

                    # if init didn't call server.stop(), we enter the final recv
                    # loop
                    if not self.socket.halt:
                        fin_loop = FinalLoop(self)
                        fin_loop.run()
                except SystemExit:
                    # logger exception/error calls sys.exit(), its ok for that
                    # to kill the connection.
                    #
                    # if the thing that logged it didn't call stop() before it
                    # call stop() yourself, and hand it off to the retry block
                    # below
                    #
                    # state here is
                    #   - wanted: True, socket.halt: False, running: True
                    if not self.socket.halt:
                        self.stop()
                except:
                    # something happened, log it, and stop(), hand it off to the
                    # retry block below IF this server didn't get DC'd by CTL or
                    # if the bot isn't going down
                    if self.wanted and not self.config.halt:
                        self.logger.warning("server run failed", exc_info=True)
                    if not self.socket.halt:
                        self.stop()

                # if CTL told us to DC, or if the bot is going down, don't
                # reconnect, if NOT, sleep for RECONNECT_DELAY and attempt a
                # reconnect
                if self.wanted and not self.config.halt:
                    self.logger.warning(
                        "%s", f"{ac.BYEL}--> {ac.BWHI}reconnecting{ac.RES}"
                    )

                    # sleep in increments of 1 till RECONNECT_DELAY so SIGINT
                    # or CTL can tell us to stop in the middle
                    slept = 0
                    while (
                        self.wanted
                        and not self.config.halt
                        and slept < self.RECONNECT_DELAY
                    ):
                        time.sleep(1)
                        slept += 1
        finally:
            # run()ner is gone, CTL/SIGINT told us to stop
            self.running = False

    def stop(self, reconnect=True, send_quit=True):
        self.logger.warning("%s", f"{ac.BYEL}--> {ac.BWHI}stopping{ac.RES}")

        # if we're not reconnecting, we are no longer wanted
        if not reconnect:
            self.wanted = False

        self.socket.halt = True

        if send_quit and self.socket.connected and self.sock_ops is not None:
            try:
                self.sock_ops.send_quit("mom said no.")
            except:
                self.logger.warning("sending quit failed")

        # shutdown + close socket, then remove socket-related state
        self.socket.disconnect()

        # remove learned IRC state
        self.sock_ops = None
        self.caps = []
        self.channels = {}
        self.users = {}
