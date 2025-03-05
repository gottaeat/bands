import json
import logging
import os
import re
import threading

import openai
import wolframalpha
import yaml

from bs4 import BeautifulSoup

from .util import get_url
from .doot import Doot
from .quote import Quote
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
        self.quote = None
        self.doot = None
        self.wa_client = None
        self.openai_client = None
        self.openai_model = None
        self.piped_url = "pipedapi.drgns.space"
        self.sc_client_id = None

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
        # fmt: off
        msg  = f"{ac.BWHI}{ac.BRED}socket{ac.RES}\n"
        msg += f"{ac.BWHI}├ {ac.BGRN}address      {ac.RES}{server.socket.address}{ac.RES}\n"
        msg += f"{ac.BWHI}├ {ac.BGRN}port         {ac.RES}{server.socket.port}{ac.RES}\n"
        msg += f"{ac.BWHI}├ {ac.BGRN}tls          {ac.RES}{server.socket.tls}{ac.RES}\n"
        msg += f"{ac.BWHI}└ {ac.BGRN}verify_tls   {ac.RES}{server.socket.verify_tls}{ac.RES}\n"
        msg += f"{ac.BWHI}{ac.BRED}server{ac.RES}\n"
        msg += f"{ac.BWHI}├ {ac.BGRN}botname      {ac.RES}{server.botname}{ac.RES}\n"
        msg += f"{ac.BWHI}├ {ac.BGRN}channels     {ac.RES}{server.channels_init}{ac.RES}\n"
        msg += f"{ac.BWHI}├ {ac.BGRN}allow_admin  {ac.RES}{server.allow_admin}{ac.RES}\n"
        msg += f"{ac.BWHI}├ {ac.BGRN}secret       {ac.RES}{server.secret}{ac.RES}\n"
        msg += f"{ac.BWHI}├ {ac.BGRN}passwd       {ac.RES}{server.passwd}{ac.RES}\n"
        msg += f"{ac.BWHI}├ {ac.BGRN}scroll_speed {ac.RES}{server.scroll_speed}{ac.RES}\n"
        msg += f"{ac.BWHI}└ {ac.BGRN}burst_limit  {ac.RES}{server.burst_limit}{ac.RES}"
        # fmt: on

        for line in msg.split("\n"):
            server.logger.info(line)

    def _gen_sc_client_id(self):
        # modified version of the client_id generation functionailty of
        # https://github.com/3jackdaws/soundcloud-lib which is copyright of
        # Ian Murphy, licensed under MIT.
        self.logger.info("generating soundcloud client_id")

        try:
            data = get_url("https://soundcloud.com/hospitalrecords/polaris-distant")
        except:
            self.logger.exception("GET failed")

        try:
            data = BeautifulSoup(data, "html.parser")
        except:
            self.logger.exception("parse failed")

        scripts = data.findAll("script", attrs={"src": True})
        if not scripts:
            self.logger.error("no scripts fouund with src attrib")

        scripts_list = []
        for script in scripts:
            src = script["src"]
            if "cookielaw.org" not in src:
                scripts_list.append(src)

        for script in scripts_list:
            if isinstance(script, str):
                try:
                    script_data = get_url(script)
                except:
                    self.logger.exception("script GET failed")

                client_id = re.findall(r"client_id=([a-zA-Z0-9]+)", script_data)

                if client_id:
                    self.sc_client_id = client_id[0]
                    break

        if not self.sc_client_id:
            self.logger.error("no client_id found")

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
        self.logger.info("processing openai")
        try:
            openai_yaml = self.yaml_parsed["openai"]
        except KeyError:
            warn_msg = "openai is not specified in the configuration.\n"
            warn_msg += "functionality requiring openai will not work."

            for line in warn_msg.split("\n"):
                self.logger.warning(line)

            return
        except:
            self.logger.exception("%s parsing has failed", self.config_file)

        if not openai_yaml:
            self.logger.error("openai cannot be specified then left blank")

        # - - openai.key - - #
        if "key" not in openai_yaml.keys():
            self.logger.error("openai.key is missing from the YAML")

        if not openai_yaml["key"]:
            self.logger.error("openai.key cannot be blank")

        openai_key = openai_yaml["key"]

        self.logger.info("sanity checking openai.key")

        try:
            if openai_key[0:3] != "sk-":
                self.logger.error("%s is not a valid OpenAI key", openai_key)
        except KeyError:
            self.logger.exception("%s is formatted wrong", openai_key)

        # - - create client - - #
        self.logger.info("creating openai client")
        self.openai_client = openai.OpenAI(api_key=openai_key)

        # - - get list of models - - #
        self.logger.info("getting list of models")
        try:
            models = self.openai_client.models.list().dict()["data"]
        except:
            self.logger.exception("could not get list of models")

        non_text_match = [
            "embedding",
            "vision",
            "tts",
            "whisper",
            "dall",
            "audio",
            "realtime",
            "moderation",
        ]
        models_list = sorted(
            [
                model["id"]
                for model in models
                if not any(keyword in model["id"] for keyword in non_text_match)
            ]
        )

        if not models_list:
            self.logger.error("models list retrieved from OpenAI is empty")

        # - - openai.model - - #
        if "model" not in openai_yaml.keys():
            self.logger.error("openai.model is missing from the YAML")

        if not openai_yaml["model"]:
            self.logger.error("openai.model cannot be blank")

        openai_model = openai_yaml["model"]

        if openai_model not in models_list:
            warn_msg = f"{openai_model} is not valid, model should be one of:\n"
            for model in models_list:
                warn_msg += f" - {model}\n"

            for line in warn_msg.rstrip("\n").split("\n"):
                self.logger.warning(line)

            self.logger.error("invalid model")

        # - - set model - - #
        self.openai_model = openai_model

    def _parse_piped(self):
        # - - parse yaml - - #
        self.logger.info("processing piped_url")
        try:
            piped_url = self.yaml_parsed["piped_url"]
        except KeyError:
            warn_msg = "piped_url is not specified in the configuration.\n"
            warn_msg += f"will use the fallback value of {self.piped_url}"

            for line in warn_msg.split("\n"):
                self.logger.warning(line)

            return
        except:
            self.logger.exception("%s parsing has failed", self.config_file)

        if not piped_url:
            self.logger.error("piped_url cannot be specified then left blank")

        if not bool(
            re.compile(r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.[A-Za-z]{2,})+$").match(
                piped_url
            )
        ):
            self.logger.error("%s is not a fqdn", piped_url)

        self.piped_url = piped_url

    def _parse_quote(self):
        # - - init Quote() - - #
        self.quote = Quote(self.logger)

        # - - parse yaml - - #
        self.logger.info("processing quote file")
        try:
            quote_file = self.yaml_parsed["quote_file"]
        except KeyError:
            quote_file = "/data/quotes.json"

            warn_msg = "quote_file key was not specified, using /data/quotes.json"
            self.logger.warning(warn_msg)

        if not quote_file:
            self.logger.error("quote_file key cannot blank")

        if not os.path.isfile(quote_file):
            self.logger.warning("%s is not a file, creating", quote_file)

            try:
                with open(quote_file, "w", encoding="utf-8") as file:
                    file.write(json.dumps({"quotes": [{}]}))
            except FileNotFoundError:
                self.logger.exception("could not create %s", quote_file)

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
        self.doot = Doot(self.logger)

        # - - parse yaml - - #
        self.logger.info("processing doot file")
        try:
            doot_file = self.yaml_parsed["doot_file"]
        except KeyError:
            doot_file = "/data/doots.json"

            warn_msg = "doot_file key was not specified, using /data/doots.json."
            self.logger.warning(warn_msg)

        if not doot_file:
            self.logger.error("doot_file cannot be left blank")

        if not os.path.isfile(doot_file):
            self.logger.warning("%s is not a file, creating", doot_file)

            try:
                with open(doot_file, "w", encoding="utf-8") as file:
                    file.write(json.dumps({"doots": [{}]}))
            except FileNotFoundError:
                self.logger.exception("could not create %s", doot_file)

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
                err_msg = "burst_limit/scroll_speed both have to be non-0 "
                err_msg += "values if one of them is defined as a non-0 value"
                self.logger.error(err_msg)

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

        func_threads = []
        for config_func in [
            self._gen_sc_client_id,
            self._parse_wolfram,
            self._parse_openai,
            self._parse_piped,
            self._parse_quote,
            self._parse_doot,
            self.parse_servers,
        ]:
            func_thread = threading.Thread(target=config_func)
            func_threads.append(func_thread)

        for func_thread in func_threads:
            if self.halt:
                break

            func_thread.start()

        for func_thread in func_threads:
            func_thread.join()
