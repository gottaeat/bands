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

        self.openai_keys = None
        self.servers = []

    # pylint: disable=too-many-branches, too-many-statements
    def parse_yaml(self):
        if os.path.isfile(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as yaml_file:
                    yaml_parsed = yaml.load(yaml_file.read(), Loader=yaml.Loader)
            except Exception as exc:
                # pylint: disable=raise-missing-from
                raise ValueError(f"E: {self.config_file} parsing has failed:\n{exc}")
        else:
            raise ValueError(f"E: {self.config_file} is not a file.")

        # openai
        try:
            openai = yaml_parsed["openai"]
        except KeyError:
            openai = None

            warnmsg = "W: openai section in the YAML file is missing, functionality "
            warnmsg += "requiring AI() will not work."
            print(warnmsg)

        if openai:
            try:
                keys_file = openai["keys_file"]
            except KeyError:
                # pylint: disable=raise-missing-from
                raise ValueError(
                    "E: keys_file in openai section in the YAML file is missing."
                )

            if not os.path.isfile(keys_file):
                raise ValueError(f"E: {keys_file} is not a file")

            try:
                with open(keys_file, "r", encoding="utf-8") as file:
                    self.openai_keys = json.loads(file.read())["openai_keys"]
            except Exception as exc:
                # pylint: disable=raise-missing-from
                raise ValueError(f"E: parsing {keys_file} failed:\n{exc}")

            if len(self.openai_keys) == 0:
                raise ValueError(f"E: {keys_file} has no keys.")

            for key in self.openai_keys:
                try:
                    if key["key"][0:3] != "sk-":
                        raise ValueError(f"E: {key['key']} is not a valid OpenAI key.")
                except KeyError:
                    # pylint: disable=raise-missing-from
                    raise ValueError(f"E: {keys_file} formatting is incorrect.")

        # servers
        try:
            servers = yaml_parsed["servers"]
        except KeyError:
            # pylint: disable=raise-missing-from
            raise ValueError("E: server section in the YAML file is missing.")

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
                    raise ValueError(f"E: {item} is missing from the YAML.")

            config = ServerConfig()
            config.name = str(server["name"])
            config.address = str(server["address"])
            config.port = int(server["port"])
            config.botname = str(server["botname"])

            if len(server["channels"]) == 0:
                raise ValueError(
                    f"E: no channels provided for server {server['name']}."
                )

            for channel in server["channels"]:
                if channel[0] != "#":
                    raise ValueError("E: channels should start with a #.")

            config.channels = server["channels"]
            config.secret = str(server["secret"])

            try:
                if type(server["tls"]).__name__ != "bool":
                    raise ValueError("E: tls should be a bool.")

                config.tls = server["tls"]
            except KeyError:
                pass

            try:
                if type(server["verify_tls"]).__name__ != "bool":
                    raise ValueError("E: verify_tls should be a bool.")

                config.verify_tls = server["verify_tls"]
            except KeyError:
                pass

            try:
                config.scroll_speed = int(server["scroll_speed"])
            except KeyError:
                pass

            self.servers.append(config)
