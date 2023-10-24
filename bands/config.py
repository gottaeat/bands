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
        self.channels = None
        self.secret = None

        self.tls = False
        self.verify_tls = False
        self.scroll_speed = 0

        self.ai = None


class ConfigYAML:
    def __init__(self, config_file):
        self.config_file = config_file

        self.logger = None

        self.openai_keys = None
        self.servers = []

    # pylint: disable=too-many-branches, too-many-statements
    def parse_yaml(self):
        self.logger.info(
            "parsing configuration",
        )
        if os.path.isfile(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as yaml_file:
                    yaml_parsed = yaml.load(yaml_file.read(), Loader=yaml.Loader)
            # pylint: disable=broad-exception-caught
            except Exception:
                self.logger.exception("%s parsing has failed", self.config_file)
        else:
            self.logger.error("%s is not a file", self.config_file)

        # openai
        try:
            openai = yaml_parsed["openai"]
        except KeyError:
            openai = None

            warnmsg = "openai section in the YAML file is missing, functionality "
            warnmsg += "requiring AI() will not work unless reloaded later on "
            warnmsg += "by the admin user"
            self.logger.warning(
                warnmsg,
            )
        except TypeError:
            self.logger.exception(
                "%s parsing has failed",
                self.config_file,
            )

        if openai:
            self.logger.info(
                "openai section found",
            )
            try:
                keys_file = openai["keys_file"]
            except KeyError:
                self.logger.exception(
                    "keys_file in openai section in the YAML file is missing",
                )
            if not os.path.isfile(keys_file):
                self.logger.error(
                    "%s is not a file",
                    keys_file,
                )

            self.logger.info(
                "parsing openai keys_file",
            )
            try:
                with open(keys_file, "r", encoding="utf-8") as file:
                    self.openai_keys = json.loads(file.read())["openai_keys"]
            # pylint: disable=broad-exception-caught
            except Exception:
                self.logger.exception(
                    "parsing %s failed",
                    keys_file,
                )

            if len(self.openai_keys) == 0:
                self.logger.error(
                    "%s has no keys",
                    keys_file,
                )

            for key in self.openai_keys:
                try:
                    if key["key"][0:3] != "sk-":
                        self.logger.error(
                            "%s is not a valid OpenAI key",
                            key["key"],
                        )
                except KeyError:
                    self.logger.exception(
                        "%s formatting is incorrect",
                        keys_file,
                    )

        # servers
        self.logger.info(
            "parsing servers",
        )
        try:
            servers = yaml_parsed["servers"]
        except KeyError:
            self.logger.exception(
                "server section in the YAML file is missing",
            )

        server_must_have = [
            "name",
            "address",
            "port",
            "botname",
            "channels",
            "secret",
        ]

        for server in servers:
            for item in server_must_have:
                if item not in server.keys():
                    self.logger.error(
                        "%s is missing from the YAML.",
                        item,
                    )

            config = ServerConfig()
            config.name = str(server["name"])
            config.address = str(server["address"])
            config.port = int(server["port"])
            config.botname = str(server["botname"])

            if len(server["channels"]) == 0:
                self.logger.error(
                    "no channels provided for server %s",
                    server["name"],
                )

            for channel in server["channels"]:
                if channel[0] != "#":
                    self.logger.error(
                        "channels should start with a #",
                    )

            config.channels = server["channels"]
            config.secret = str(server["secret"])

            try:
                if type(server["tls"]).__name__ != "bool":
                    self.logger.error(
                        "tls should be a bool",
                    )

                config.tls = server["tls"]
            except KeyError:
                pass

            try:
                if type(server["verify_tls"]).__name__ != "bool":
                    self.logger.error(
                        "verify_tls should be a bool",
                    )

                config.verify_tls = server["verify_tls"]
            except KeyError:
                pass

            try:
                config.scroll_speed = int(server["scroll_speed"])
            except KeyError:
                pass

            self.logger.info(
                "generated Server() for %s",
                config.name,
            )
            self.servers.append(config)
