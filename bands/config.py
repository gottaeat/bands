import json
import os

import openai
import wolframalpha
import yaml

from .log import set_logger
from .doot import Doot
from .quote import Quote
from .irc.server import Server
from .irc.socket import Socket


class ConfigYAML:
    def __init__(self, config_file, debug=False):
        self.config_file = config_file
        self.debug = debug

        self.yaml_parsed = None

        self.logger = None
        self.servers = []

        self.quote = None
        self.doot = None

        self.wa_client = None
        self.openai_client = None

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

    def _parse_wolfram(self):
        # - - parse yaml - - #
        self.logger.info("processing wolfram_api_key")
        try:
            wolfram_api_key = self.yaml_parsed["wolfram_api_key"]
        except KeyError:
            warn_msg = "wolfram_api_key is not specified in the configuration.\n"
            warn_msg += "functionality requiring wolfram alpha will not work."

            for line in warn_msg.split("\n"):
                self.logger.warning(line)

            return
        except:
            self.logger.exception("%s parsing has failed", self.config_file)

        if not wolfram_api_key:
            self.logger.error("wolfram_api_key cannot be specified then left blank")

        # - - set key - - #
        self.logger.info("creating wolfram alpha client")
        self.wa_client = wolframalpha.Client(wolfram_api_key)

        # - - sanity check - - #
        try:
            self.wa_client.query("temperature in Washington, DC on October 3, 2012")
        except Exception as exc:
            if str(exc) == "Error 1: Invalid appid":
                self.logger.error("wolfram alpha api key is formatted wrong")
            else:
                self.logger.exception("error sanity checking the wolfram alpha api key")

    def _parse_openai(self):
        # - - parse yaml - - #
        self.logger.info("processing openai_key")
        try:
            openai_key = self.yaml_parsed["openai_key"]
        except KeyError:
            warn_msg = "openai_key is not specified in the configuration.\n"
            warn_msg += "functionality requiring openai will not work."

            for line in warn_msg.split("\n"):
                self.logger.warning(line)

            return
        except:
            self.logger.exception("%s parsing has failed", self.config_file)

        if not openai_key:
            self.logger.error("openai_key cannot be specified then left blank")

        # - - sanity check - - #
        self.logger.info("sanity checking the openai key")

        try:
            if openai_key[0:3] != "sk-":
                self.logger.error("%s is not a valid OpenAI key", openai_key)
        except KeyError:
            self.logger.exception("%s is formatted wrong", openai_key)

        # - - set key - - #
        self.logger.info("creating openai client")
        self.openai_client = openai.OpenAI(api_key=openai_key)

    def _parse_quote(self):
        # - - init Quote() - - #
        self.quote = Quote(self.debug)

        # - - parse yaml - - #
        self.logger.info("processing quote file")
        try:
            quote_file = self.yaml_parsed["quote_file"]
        except:
            self.logger.exception("%s parsing has failed", self.config_file)

        if not quote_file:
            self.logger.error("quote_file key cannot blank")

        if not os.path.isfile(quote_file):
            self.logger.warning("%s is not a file, creating", quote_file)

            with open(quote_file, "w", encoding="utf-8") as file:
                file.write(json.dumps({"quotes": [{}]}))

        # - - sanity checks - - #
        self.logger.info("sanity checking the quote file formatting")
        try:
            with open(quote_file, "r", encoding="utf-8") as file:
                quotes = json.loads(file.read())
        except:
            self.logger.exception("parsing %s failed", quote_file)

        if "quotes" not in quotes.keys():
            self.logger.error("%s is formatted wrong", quote_file)

        # - - set quote file - - #
        self.quote.file = quote_file

    def _parse_doot(self):
        # - - init Doot() - - #
        self.doot = Doot(self.debug)

        # - - parse yaml - - #
        self.logger.info("processing doot file")
        try:
            doot_file = self.yaml_parsed["doot_file"]
        except:
            self.logger.exception("%s parsing has failed", self.config_file)

        if not doot_file:
            self.logger.error("doot_file cannot be left blank")

        if not os.path.isfile(doot_file):
            self.logger.warning("%s is not a file, creating", doot_file)

            with open(doot_file, "w", encoding="utf-8") as file:
                file.write(json.dumps({"doots": [{}]}))

        # - - sanity checks - - #
        self.logger.info("sanity checking the doot file formatting")
        try:
            with open(doot_file, "r", encoding="utf-8") as file:
                doots = json.loads(file.read())
        except:
            self.logger.exception("parsing %s failed", doot_file)

        if "doots" not in doots.keys():
            self.logger.error("%s is formatted wrong", doot_file)

        # - - set doot file - - #
        self.doot.file = doot_file

    def parse_servers(self):
        self.logger.info("processing servers")

        # check if servers key exists
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
            if len(self.servers) > 0:
                server_names = []
                for server in self.servers:
                    server_names.append(server.name)

                if server_yaml["name"] in server_names:
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

            # server.channels
            if len(server_yaml["channels"]) == 0:
                self.logger.error("no channels provided for server %s", server.name)

            for channel in server_yaml["channels"]:
                if channel[0] != "#":
                    self.logger.error("channels should start with a #")

                try:
                    server.channels.append(str(channel))
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
                    err_msg = "server secret cannot be specified then left blank"
                    self.logger.error(err_msg)
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
                    err_msg = "server passwd cannot be specified then left blank"
                    self.logger.error(err_msg)
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

            # - - logger - - #
            logger = set_logger(server.name, self.debug)
            server.socket.logger = logger
            server.logger = logger

            # - - append - - #
            server.config = self
            self.servers.append(server)

    def run(self):
        self.logger = set_logger(__name__, self.debug)

        self.load_yaml()

        self._parse_wolfram()
        self._parse_openai()
        self._parse_quote()
        self._parse_doot()

        self.parse_servers()
