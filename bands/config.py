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
        self.allow_admin = None
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


class DootConfig:
    def __init__(self):
        self.file = None


class ConfigYAML:
    def __init__(self, config_file):
        self.config_file = config_file

        self.logger = None

        self.openai = None
        self.quote = None
        self.doot = None
        self.servers = []

        self.yaml_parsed = None

    def _parse_doot(self):
        self.logger.info("processing doot file")

        try:
            doot_file = self.yaml_parsed["doot_file"]
        # pylint: disable=bare-except
        except:
            self.logger.exception("%s parsing has failed", self.config_file)

        if not doot_file:
            self.logger.error("doot_file cannot be left blank")

        if not os.path.isfile(doot_file):
            self.logger.warning("%s is not a file, creating", doot_file)

            with open(doot_file, "w", encoding="utf-8") as file:
                file.write(json.dumps({"doots": [{}]}))

        self.logger.info("sanity checking the doot file formatting")

        try:
            with open(doot_file, "r", encoding="utf-8") as file:
                doots = json.loads(file.read())
        # pylint: disable=bare-except
        except:
            self.logger.exception("parsing %s failed", doot_file)

        if "doots" not in doots.keys():
            self.logger.error("%s is formatted wrong", doot_file)

        self.doot = DootConfig()
        self.doot.file = doot_file

    def _parse_quote(self):
        self.logger.info("processing quote file")

        try:
            quote_file = self.yaml_parsed["quote_file"]
        # pylint: disable=bare-except
        except:
            self.logger.exception("%s parsing has failed", self.config_file)

        if not quote_file:
            self.logger.error("quote_file key cannot blank")

        if not os.path.isfile(quote_file):
            self.logger.warning("%s is not a file, creating", quote_file)

            with open(quote_file, "w", encoding="utf-8") as file:
                file.write(json.dumps({"quotes": [{}]}))

        self.logger.info("sanity checking the quote file formatting")

        try:
            with open(quote_file, "r", encoding="utf-8") as file:
                quotes = json.loads(file.read())
        # pylint: disable=bare-except
        except:
            self.logger.exception("parsing %s failed", quote_file)

        if "quotes" not in quotes.keys():
            self.logger.error("%s is formatted wrong", quote_file)

        self.quote = QuoteConfig()
        self.quote.file = quote_file

    def _parse_openai(self):
        self.logger.info("processing openai_key_file")

        try:
            openai_key_file = self.yaml_parsed["openai_key_file"]
        except KeyError:
            warn_msg = "openai_key_file key is missing in the YAML file. "
            warn_msg += "functionality\nrequiring AI() will not work unless "
            warn_msg += "reloaded later on by an\nauthorized user."

            for line in warn_msg.split("\n"):
                self.logger.warning(line)

            return
        # pylint: disable=bare-except
        except:
            self.logger.exception("%s parsing has failed", self.config_file)

        if not openai_key_file:
            self.logger.error("openai_key_file cannot be specified then left blank")

        if not os.path.isfile(openai_key_file):
            self.logger.error("%s is not a file", openai_key_file)

        self.logger.info("sanity checking the openai key file formatting")

        try:
            with open(openai_key_file, "r", encoding="utf-8") as file:
                openai_keys = json.loads(file.read())["openai_keys"]
        # pylint: disable=bare-except
        except:
            self.logger.exception("parsing %s failed", openai_key_file)

        if len(openai_keys) == 0:
            self.logger.error("%s has no keys", openai_key_file)

        for key in openai_keys:
            try:
                if key["key"][0:3] != "sk-":
                    self.logger.error("%s is not a valid OpenAI key", key["key"])
            except KeyError:
                self.logger.exception("%s formatting is incorrect", openai_key_file)

        self.openai = OpenAIConfig()
        self.openai.keys = openai_keys

    # pylint: disable=too-many-branches,too-many-statements
    def _parse_servers(self):
        # servers
        self.logger.info("processing servers")

        try:
            servers = self.yaml_parsed["servers"]
        except KeyError:
            self.logger.exception("servers section in the YAML file is missing")

        server_must_have = ["name", "address", "port", "botname", "channels"]

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

            # server.allow_admin
            try:
                if type(server["allow_admin"]).__name__ != "bool":
                    self.logger.error("allow_admin should be a bool")
            except KeyError:
                pass

            try:
                svconf.allow_admin = server["allow_admin"]
            except KeyError:
                svconf.allow_admin = False

            # server.secret
            try:
                svconf.secret = str(server["secret"])
            except KeyError:
                pass

            if svconf.secret == "None":
                self.logger.error("server secret cannot be specified then left blank")

            # wanted auth bot no secret provided
            if svconf.allow_admin and not svconf.secret:
                self.logger.error("allow_admin enabled but no secret provided")

            if svconf.secret and not svconf.allow_admin:
                self.logger.error("secret provided without enabling allow_admin")

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
        self._parse_doot()
        self._parse_servers()
