import logging
import os

import openai
import yaml

from .ai import BandsAI
from .db import BandsDB
from .irc.server import Server
from .irc.socket import Socket
from .colors import ANSIColors

ac = ANSIColors()


class ConfigYAML:
    def __init__(self, config_file, parent_logger):
        self.config_file = config_file
        self.logger = parent_logger.getChild(self.__class__.__name__)

        self.halt = None

        self.yaml_parsed = None

        self.servers = {}
        self.db = None
        self.ai = None

    def load_yaml(self):
        self.logger.info("loading configuration")

        if os.path.isfile(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as yaml_file:
                    self.yaml_parsed = yaml.load(yaml_file.read(), Loader=yaml.Loader)
            except:
                self.logger.exception("%s parsing has failed", self.config_file)
        else:
            self.logger.error("%s is not a file", self.config_file)

    def _gen_prompt(self, server):
        msg = (
            f"{ac.BWHI}{ac.BRED}socket{ac.RES}\n"
            f"{ac.BWHI}├ {ac.BGRN}address      {ac.RES}{server.socket.address}{ac.RES}\n"
            f"{ac.BWHI}├ {ac.BGRN}port         {ac.RES}{server.socket.port}{ac.RES}\n"
            f"{ac.BWHI}├ {ac.BGRN}tls          {ac.RES}{server.socket.tls}{ac.RES}\n"
            f"{ac.BWHI}└ {ac.BGRN}verify_tls   {ac.RES}{server.socket.verify_tls}{ac.RES}\n"
            f"{ac.BWHI}{ac.BRED}server{ac.RES}\n"
            f"{ac.BWHI}├ {ac.BGRN}botname      {ac.RES}{server.botname}{ac.RES}\n"
            f"{ac.BWHI}├ {ac.BGRN}channels     {ac.RES}{server.channels_init}{ac.RES}\n"
            f"{ac.BWHI}├ {ac.BGRN}allow_admin  {ac.RES}{server.allow_admin}{ac.RES}\n"
            f"{ac.BWHI}├ {ac.BGRN}secret       {ac.RES}{server.secret}{ac.RES}\n"
            f"{ac.BWHI}├ {ac.BGRN}passwd       {ac.RES}{server.passwd}{ac.RES}\n"
            f"{ac.BWHI}├ {ac.BGRN}scroll_speed {ac.RES}{server.scroll_speed}{ac.RES}\n"
            f"{ac.BWHI}└ {ac.BGRN}burst_limit  {ac.RES}{server.burst_limit}{ac.RES}"
        )

        for line in msg.split("\n"):
            server.logger.info(line)

    def _parse_openai_key(self):
        self.logger.info("processing openai_key")

        try:
            openai_key = self.yaml_parsed["openai_key"]
        except KeyError:
            warn_msg = (
                "openai_key is not specified in the configuration.\n"
                "functionality requiring openai will not work."
            )

            for line in warn_msg.split("\n"):
                self.logger.warning(line)

            return
        except:
            self.logger.exception("%s parsing has failed", self.config_file)

        if not openai_key:
            self.logger.error("openai_key cannot be specified then left blank")

        self.logger.info("sanity checking openai_key")

        try:
            if openai_key[0:3] != "sk-":
                self.logger.error("%s is not a valid OpenAI key", openai_key)
        except KeyError:
            self.logger.exception("%s is formatted wrong", openai_key)

        self.logger.info("creating openai client")
        openai_client = openai.OpenAI(api_key=openai_key)

        self.logger.info("creating BandsAI")
        self.ai = BandsAI(self.logger, openai_client)

    def _parse_db(self):
        self.logger.info("processing sqlite_file")

        try:
            sqlite_file = self.yaml_parsed["sqlite_file"]
        except KeyError:
            sqlite_file = "/data/bands.sqlite3"

            self.logger.warning(
                "sqlite_file key was not specified, using /data/bands.sqlite3"
            )

        if not sqlite_file:
            self.logger.error("sqlite_file cannot be left blank")

        sqlite_directory = os.path.dirname(sqlite_file)
        if sqlite_directory:
            try:
                os.makedirs(sqlite_directory, exist_ok=True)
            except:
                self.logger.exception("creating sqlite database directory failed")

        self.db = BandsDB(self.logger, sqlite_file)

    def parse_servers(self):
        self.logger.info("processing servers")

        try:
            servers = self.yaml_parsed["servers"]
        except KeyError:
            self.logger.exception("servers section in the YAML file is missing")

        # check for root keys that must be present
        server_must_have = ["name", "address", "port", "botname", "channels"]

        for server_yaml in servers:
            for item in server_must_have:
                if item not in server_yaml.keys():
                    self.logger.error("%s is missing from the YAML", item)
                if not server_yaml[item]:
                    self.logger.error("%s cannot be blank", item)

            # check if server exists in case we are rehashing
            if self.servers and server_yaml["name"].lower() in self.servers.keys():
                self.logger.warning(
                    "skipping %s, already in servers", server_yaml["name"]
                )
                continue

            # - - socket - - #
            self.logger.info("generating Socket() for %s", server_yaml["name"])
            socket = Socket()

            # socket.address
            socket.address = str(server_yaml["address"])

            # socket.port
            try:
                socket.port = int(server_yaml["port"])
            except ValueError:
                self.logger.exception("invalid server port")

            if socket.port <= 0 or socket.port > 65535:
                self.logger.error("%s is not a valid port number.", socket.port)

            # socket.tls
            try:
                if type(server_yaml["tls"]).__name__ != "bool":
                    self.logger.error("tls should be a bool")
            except KeyError:
                pass

            try:
                socket.tls = server_yaml["tls"]
            except KeyError:
                socket.tls = False

            # socket.verify_tls
            try:
                if type(server_yaml["verify_tls"]).__name__ != "bool":
                    self.logger.error("verify_tls should be a bool")
            except KeyError:
                pass

            try:
                socket.verify_tls = server_yaml["verify_tls"]
            except KeyError:
                socket.verify_tls = False

            # - - server - - #
            self.logger.info("generating Server() for %s", server_yaml["name"])
            server = Server(socket)

            # server.name
            server.name = str(server_yaml["name"])

            # server.botname
            server.botname = str(server_yaml["botname"])

            # server.channels_init
            if not server_yaml["channels"]:
                self.logger.error("no channels provided for server %s", server.name)

            for channel in server_yaml["channels"]:
                if channel[0] != "#":
                    self.logger.error("channels should start with a #")

                try:
                    server.channels_init.append(str(channel))
                except ValueError:
                    self.logger.exception("invalid channel name: %s", channel)

            # server.allow_admin
            try:
                if type(server_yaml["allow_admin"]).__name__ != "bool":
                    self.logger.error("allow_admin should be a bool")
            except KeyError:
                pass

            try:
                server.allow_admin = server_yaml["allow_admin"]
            except KeyError:
                server.allow_admin = False

            # server.secret
            try:
                if server_yaml["secret"] is None:
                    self.logger.error(
                        "server secret cannot be specified then left blank"
                    )
                else:
                    server.secret = str(server_yaml["secret"])
            except KeyError:
                pass

            # wanted auth bot no secret provided
            if server.allow_admin and not server.secret:
                self.logger.error("allow_admin enabled but no secret provided")

            if server.secret and not server.allow_admin:
                self.logger.error("secret provided without enabling allow_admin")

            # server.passwd
            try:
                if server_yaml["passwd"] is None:
                    self.logger.error(
                        "server passwd cannot be specified then left blank"
                    )
                else:
                    server.passwd = str(server_yaml["passwd"])
            except KeyError:
                pass

            # server.scroll_speed
            try:
                server.scroll_speed = int(server_yaml["scroll_speed"])
            except ValueError:
                self.logger.exception("invalid server scroll_speed")
            except KeyError:
                server.scroll_speed = 0

            # server.burst_limit
            try:
                server.burst_limit = int(server_yaml["burst_limit"])
            except ValueError:
                self.logger.exception("invalid server burst_limit")
            except KeyError:
                server.burst_limit = 0

            if (server.burst_limit == 0 and server.scroll_speed != 0) or (
                server.scroll_speed == 0 and server.burst_limit != 0
            ):
                self.logger.error(
                    "burst_limit/scroll_speed both have to be non-0 values if "
                    "one of them is defined as a non-0 value"
                )

            # - - logger - - #
            logger = logging.getLogger(server.name)
            server.socket.logger = logger.getChild(socket.__class__.__name__)
            server.logger = logger

            # - - append - - #
            server.config = self
            self.servers[server.name.lower()] = server

            # - - gen prompt - - #
            self._gen_prompt(server)

    def run(self):
        self.load_yaml()

        for config_func in (
            self._parse_openai_key,
            self._parse_db,
            self.parse_servers,
        ):
            if self.halt:
                break

            config_func()
