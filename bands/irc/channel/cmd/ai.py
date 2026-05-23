from bands.colors import MIRCColors
from bands.irc.util import unilen

c = MIRCColors()


class AIQuery:

    _SYSTEM_PROMPT = (
        "You are Bands. You are a general purpose bot that interacts with "
        "internet relay chat users. Your lines should be a few sentences at "
        "best even if the user's request requires reasoning for long-form "
        "outputs. If you are asked to explain a concept, answer a question or "
        "display code examples, you simply provide what you are asked for "
        "without repeating what the user said. You cut to the chase, you are "
        "clear and concise. You never use emojis even if explicitly asked to. "
        "You never use LaTeX formatting or markdown even if explicitly asked "
        "to, you respond with plain-text only. Your responses must be "
        "contained within a single paragraph. If you are to respond with a "
        "list, normalize the list into the paragraph. "
    )

    def __init__(self, channel, user, user_args):
        self.channel = channel
        self.user = user
        self.user_args = user_args

        self.logger = self.channel.logger.getChild(self.__class__.__name__)

        self._run()

    def _query(self):
        user_Q = " ".join(self.user_args[0:])

        if unilen(user_Q) > 300:
            return self.channel.send_query(
                f"{c.ERR} query can't be wider than 300 characters."
            )

        try:
            msg = self.channel.server.config.ai.query(self._SYSTEM_PROMPT, user_Q)
        except:
            return self.channel.send_query(f"{c.ERR} query failed.")

        if not msg:
            return self.channel.send_query(f"{c.ERR} no response.")

        self.channel.send_query(f"{c.INFO} {self.user.nick}: {msg}")

    def _run(self):
        if not self.user_args:
            return self.channel.send_query(f"{c.ERR} you must provide a prompt.")

        self._query()
