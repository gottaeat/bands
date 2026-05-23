from bands.colors import MIRCColors

c = MIRCColors()


class Help:
    def __init__(self, channel, user, user_args):
        self.channel = channel
        self.user = user  # unused
        self.user_args = user_args  # unused

        self._run()

    def _run(self):
        from . import CMDS  # pylint: disable=cyclic-import,import-outside-toplevel

        db = self.channel.server.config.db
        server_name = self.channel.server.name
        channel_name = self.channel.name

        prefix = db.get_prefix(server_name, channel_name)
        disabled = set(db.get_disabled_commands(server_name, channel_name))
        has_openai = self.channel.server.config.ai is not None

        # get available cmds
        help_cmds = []
        for cmd, meta in CMDS.items():
            usage = meta["usage"]

            if not usage:
                continue

            if cmd in disabled:
                continue

            if meta["openai"] and not has_openai:
                continue

            formatted_usage = usage.format(prefix=prefix)
            help_cmds.append((cmd, formatted_usage))

        # calculate max width for first column
        cmd_width = 0
        for cmd, _ in help_cmds:
            cmd_text = f"{prefix}{cmd}"
            cmd_width = max(len(cmd_text), cmd_width)

        # prompt
        msg = ""
        for index, (cmd, usage) in enumerate(help_cmds):
            branch = "└" if index == len(help_cmds) - 1 else "├"
            msg += (
                f"{c.WHITE}{branch} {c.LGREEN}{prefix}{cmd:<{cmd_width}}{c.RES} "
                f"{usage}\n"
            )

        self.channel.send_query(msg)
