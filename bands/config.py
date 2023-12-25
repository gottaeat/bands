import json
import os

import yaml


# pylint: disable=too-many-instance-attributes,too-few-public-methods
class ServerConfig:
    def __init__(self):
        self.name = None
        self.address = None
        self.port = None
        self.botname = None
        self.channels = []
        self.secret = None

        self.passwd = None
        self.tls = None
        self.verify_tls = None
        self.scroll_speed = None


class OpenAIConfig:
    def __init__(self):
        self.keys = None


class QuoteConfig:
    def __init__(self):
        self.file = None


class ConfigYAML:
    def __init__(self, config_file):
        self.config_file = config_file

        self.logger = None

        self.openai = None
        self.quote = None
        self.servers = []

        self.yaml_parsed = None

    def _parse_quote(self):
        self.logger.info("parsing quote")

        try:
            quote = self.yaml_parsed["quote"]
        # pylint: disable=bare-except
        except:
            self.logger.exception("%s parsing has failed", self.config_file)

        if not quote:
            self.logger.error("quote section cannot be specified then left blank")

        try:
            quotes_file = quote["quotes_file"]
        except KeyError:
            self.logger.exception(
                "quotes_file in the quote section of the YAML file is missing"
            )

        if not quotes_file:
            self.logger.error("quotes_file cannot be blank")

        if not os.path.isfile(quotes_file):
            self.logger.warning("%s is not a file, creating", quotes_file)

            with open(quotes_file, "w", encoding="utf-8") as file:
                file.write(json.dumps({"quotes": []}))

        quoteconf = QuoteConfig()

        self.logger.info("loading quotes quotes_file")

        try:
            with open(quotes_file, "r", encoding="utf-8") as file:
                quotes = json.loads(file.read())["quotes"]
        # pylint: disable=bare-except
        except:
            self.logger.exception("parsing %s failed", quotes_file)

        self.logger.info("%s quotes found", len(quotes))

        quoteconf.file = quotes_file

        self.quote = quoteconf

    def _parse_openai(self):
        self.logger.info("parsing openai")

        try:
            openai = self.yaml_parsed["openai"]
        except KeyError:
            warnmsg = "openai section in the YAML file is missing.\n"
            warnmsg += "functionality requiring AI() will not work unless\n"
            warnmsg += "reloaded later on by an authorized user."

            for line in warnmsg.split("\n"):
                self.logger.warning(line)

            return  # config.openai == None
        # pylint: disable=bare-except
        except:
            self.logger.exception("%s parsing has failed", self.config_file)

        if not openai:
            self.logger.error("openai section cannot be specified then left blank")

        try:
            keys_file = openai["keys_file"]
        except KeyError:
            self.logger.exception(
                "keys_file in the openai section of the YAML file is missing"
            )

        if not keys_file:
            self.logger.error("keys_file cannot be blank")

        if not os.path.isfile(keys_file):
            self.logger.error("%s is not a file", keys_file)

        oaiconf = OpenAIConfig()

        self.logger.info("loading openai keys_file")

        try:
            with open(keys_file, "r", encoding="utf-8") as file:
                oaiconf.keys = json.loads(file.read())["openai_keys"]
        # pylint: disable=bare-except
        except:
            self.logger.exception("parsing %s failed", keys_file)

        if len(oaiconf.keys) == 0:
            self.logger.error("%s has no keys", keys_file)

        for key in oaiconf.keys:
            try:
                if key["key"][0:3] != "sk-":
                    self.logger.error("%s is not a valid OpenAI key", key["key"])
            except KeyError:
                self.logger.exception("%s formatting is incorrect", keys_file)

        self.openai = oaiconf

    # pylint: disable=too-many-branches,too-many-statements
    def _parse_servers(self):
        # servers
        self.logger.info("parsing servers")

        try:
            servers = self.yaml_parsed["servers"]
        except KeyError:
            self.logger.exception("server section in the YAML file is missing")

        server_must_have = ["name", "address", "port", "botname", "channels", "secret"]

        for server in servers:
            for item in server_must_have:
                if item not in server.keys():
                    self.logger.error("%s is missing from the YAML", item)
                if not server[item]:
                    self.logger.error("%s cannot be blank", item)

            svconf = ServerConfig()

            # server.name
            svconf.name = str(server["name"])

            # server.address
            svconf.address = str(server["address"])

            # server.port
            try:
                svconf.port = int(server["port"])
            except ValueError:
                self.logger.exception("invalid server port")

            if svconf.port <= 0 or svconf.port > 65535:
                self.logger.error("%s is not a valid port number.", svconf.port)

            # server.botname
            svconf.botname = str(server["botname"])

            # server.channels
            if len(server["channels"]) == 0:
                self.logger.error("no channels provided for server %s", server["name"])

            for channel in server["channels"]:
                if channel[0] != "#":
                    self.logger.error("channels should start with a #")

                try:
                    svconf.channels.append(str(channel))
                except ValueError:
                    self.logger.exception("invalid channel name: %s", channel)

            # server.secret
            svconf.secret = str(server["secret"])

            # server.passwd
            try:
                svconf.passwd = str(server["passwd"])
            except KeyError:
                pass

            if svconf.passwd == "None":
                self.logger.error("server passwd cannot be specified then left blank")

            # server.tls
            try:
                if type(server["tls"]).__name__ != "bool":
                    self.logger.error("tls should be a bool")
            except KeyError:
                pass

            try:
                svconf.tls = server["tls"]
            except KeyError:
                svconf.tls = False

            # server.verify_tls
            try:
                if type(server["verify_tls"]).__name__ != "bool":
                    self.logger.error("verify_tls should be a bool")
            except KeyError:
                pass

            try:
                svconf.verify_tls = server["verify_tls"]
            except KeyError:
                svconf.verify_tls = False

            # server.scroll_speed
            try:
                svconf.scroll_speed = int(server["scroll_speed"])
            except ValueError:
                self.logger.exception("invalid server scroll_speed")
            except KeyError:
                svconf.scroll_speed = 0

            self.logger.info("generated ServerConfig() for %s", svconf.name)
            self.servers.append(svconf)

    def parse_yaml(self):
        # yaml->dict
        self.logger.info("loading yaml")

        if os.path.isfile(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as yaml_file:
                    self.yaml_parsed = yaml.load(yaml_file.read(), Loader=yaml.Loader)
            # pylint: disable=bare-except
            except:
                self.logger.exception("%s parsing has failed", self.config_file)
        else:
            self.logger.error("%s is not a file", self.config_file)

        self._parse_openai()
        self._parse_quote()
        self._parse_servers()
