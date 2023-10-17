import argparse
import os

import yaml

from .ai import AI


# pylint: disable=too-many-instance-attributes,too-few-public-methods
class Config:
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


class CLI:
    def __init__(self):
        self.openai_keys_file = None

        self.config_file = None
        self.servers = []

    def _gen_args(self):
        parser_desc = "bands the IRC bot."
        parser_c_help = "Configuration YAML file."

        parser = argparse.ArgumentParser(description=parser_desc)
        parser.add_argument("-c", type=str, required=True, help=parser_c_help)
        args = parser.parse_args()

        self.config_file = args.c

    # pylint: disable=too-many-branches, too-many-statements
    def _parse_yaml(self):
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
            # pylint: disable=raise-missing-from
            raise ValueError("E: openai section in the YAML file is missing.")

        try:
            keys_file = openai["keys_file"]
        except KeyError:
            # pylint: disable=raise-missing-from
            raise ValueError(
                "E: keys_file in openai section in the YAML file is missing."
            )

        if os.path.isfile(keys_file):
            self.openai_keys_file = keys_file
        else:
            raise ValueError(f"E: {keys_file} is not a file")

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

            config = Config()
            config.name = str(server["name"])
            config.address = str(server["address"])
            config.port = int(server["port"])
            config.botname = str(server["botname"])

            if len(server["channels"]) == 0:
                raise ValueError(
                    f"E: no channels provided for server {server['name']}."
                )

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

    def run(self):
        self._gen_args()
        self._parse_yaml()

        # init ai
        ai = AI()
        ai.keys_file = self.openai_keys_file
        ai.run()

        for config in self.servers:
            # pass the same ai to all configs
            config.ai = ai


def run():
    # pylint: disable=invalid-name
    c = CLI()
    c.run()
