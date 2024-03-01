import json
import logging

from threading import Lock

from .log import BandsFormatter
from .log import ShutdownHandler


class Doot:
    def __init__(self, debug=None):
        self.logger = None
        self.debug = debug

        self.mutex = Lock()

        self.file = None

        self._first_run()

    def _first_run(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG if self.debug else logging.INFO)

        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG if self.debug else logging.INFO)

        handler.setFormatter(BandsFormatter())

        self.logger.addHandler(handler)
        self.logger.addHandler(ShutdownHandler())

        self.logger.info("initialized")

    def read_doots(self):
        self.logger.debug("reading doots file")

        with open(self.file, "r", encoding="utf-8") as file:
            doots = json.loads(file.read())

        return doots

    def write_doots(self, doots):
        self.logger.debug("writing doots file")

        with open(self.file, "w", encoding="utf-8") as file:
            file.write(json.dumps(doots))

    # generic for other shits to alter doots as well
    # takes a ChannelUser object !
    def alter_doot(self, server, channel_user, amount):
        with self.mutex:
            doots = self.read_doots()

            # entry for server does not exist
            if server.name not in doots["doots"][0].keys():
                doots["doots"][0][server.name] = []

                server.logger.info("created doot entry for: %s", server.name)

            # find user entry
            user_exists = (False, None)
            for index, doot_user_entry in enumerate(doots["doots"][0][server.name]):
                if doot_user_entry["nick"].lower() == channel_user.nick.lower():
                    user_exists = (True, index)
                    break

            # user does not exist, initialize it
            if not user_exists[0]:
                dooted_user_dict = {"nick": channel_user.nick, "doots": amount}

                doots["doots"][0][server.name].append(dooted_user_dict)
            # user exists
            else:
                doots["doots"][0][server.name][user_exists[1]]["doots"] += amount

            self.write_doots(doots)

        # prompt
        if user_exists[0]:
            user_doots = doots["doots"][0][server.name][user_exists[1]]["doots"]
        else:
            user_doots = dooted_user_dict["doots"]

        return user_doots
