import sqlite3

from threading import Lock


class BandsDB:
    def __init__(self, parent_logger, path):
        self.logger = parent_logger.getChild(self.__class__.__name__)

        self.path = path
        self.mutex = Lock()

        self._init_db()

    def _execute(self, query, params=None, fetch=None):
        if params is None:
            params = ()

        conn = None
        cursor = None

        with self.mutex:
            try:
                conn = sqlite3.connect(self.path, timeout=10, isolation_level=None)
                cursor = conn.execute(query, params)

                if fetch == "one":
                    return cursor.fetchone()
                if fetch == "all":
                    return cursor.fetchall()
            finally:
                try:
                    if cursor is not None:
                        cursor.close()
                finally:
                    if conn is not None:
                        conn.close()

    def _init_db(self):
        statements = (
            (
                """
                CREATE TABLE IF NOT EXISTS channel_settings (
                    server TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    prefix TEXT NOT NULL,
                    PRIMARY KEY (server, channel)
                )
                """,
                "failed creating channel_settings table",
            ),
            (
                """
                CREATE TABLE IF NOT EXISTS disabled_commands (
                    server TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    command TEXT NOT NULL,
                    PRIMARY KEY (server, channel, command)
                )
                """,
                "failed creating disabled_commands table",
            ),
            (
                """
                CREATE TABLE IF NOT EXISTS disabled_hooks (
                    server TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    hook TEXT NOT NULL,
                    PRIMARY KEY (server, channel, hook)
                )
                """,
                "failed creating disabled_hooks table",
            ),
            (
                """
                CREATE TABLE IF NOT EXISTS points (
                    server TEXT NOT NULL,
                    nick_key TEXT NOT NULL,
                    nick TEXT NOT NULL,
                    points INTEGER NOT NULL,
                    PRIMARY KEY (server, nick_key)
                )
                """,
                "failed creating points table",
            ),
            (
                """
                CREATE TABLE IF NOT EXISTS quotes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    server TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    nick_key TEXT NOT NULL,
                    nick TEXT NOT NULL,
                    msg TEXT NOT NULL,
                    timestamp INTEGER NOT NULL
                )
                """,
                "failed creating quotes table",
            ),
            (
                """
                CREATE INDEX IF NOT EXISTS idx_points_server_points
                ON points (server, points DESC, nick ASC)
                """,
                "failed creating idx_points_server_points index",
            ),
            (
                """
                CREATE INDEX IF NOT EXISTS idx_quotes_channel
                ON quotes (server, channel)
                """,
                "failed creating idx_quotes_channel index",
            ),
            (
                """
                CREATE INDEX IF NOT EXISTS idx_quotes_nick
                ON quotes (server, channel, nick_key)
                """,
                "failed creating idx_quotes_nick index",
            ),
        )

        for query, log_msg in statements:
            try:
                self._execute(query)
            except:
                self.logger.exception(log_msg)

        self.logger.info("initialized sqlite database at %s", self.path)

    # - - prefixes - - #
    def get_prefix(self, server, channel):
        try:
            row = self._execute(
                """
                SELECT prefix
                FROM channel_settings
                WHERE server = ? AND channel = ?
                """,
                (server, channel),
                fetch="one",
            )
        except:
            self.logger.exception("getting channel prefix failed")
        else:
            return row[0] if row else "?"

    def set_prefix(self, server, channel, prefix):
        try:
            self._execute(
                """
                INSERT INTO channel_settings (server, channel, prefix)
                VALUES (?, ?, ?)
                ON CONFLICT(server, channel) DO UPDATE SET prefix = excluded.prefix
                """,
                (server, channel, prefix),
            )
        except:
            self.logger.exception("setting channel prefix failed")

    # - - commands - - #
    def enable_command(self, server, channel, command):
        try:
            self._execute(
                """
                DELETE FROM disabled_commands
                WHERE server = ? AND channel = ? AND command = ?
                """,
                (server, channel, command.lower()),
            )
        except:
            self.logger.exception("enabling channel command failed")

    def disable_command(self, server, channel, command):
        try:
            self._execute(
                """
                INSERT OR IGNORE INTO disabled_commands (server, channel, command)
                VALUES (?, ?, ?)
                """,
                (server, channel, command.lower()),
            )
        except:
            self.logger.exception("disabling channel command failed")

    def get_disabled_commands(self, server, channel):
        try:
            rows = self._execute(
                """
                SELECT command
                FROM disabled_commands
                WHERE server = ? AND channel = ?
                ORDER BY command
                """,
                (server, channel),
                fetch="all",
            )
        except:
            self.logger.exception("getting disabled command list failed")
        else:
            return [row[0] for row in rows]

    # - - hooks - - #
    def enable_hook(self, server, channel, hook):
        try:
            self._execute(
                """
                DELETE FROM disabled_hooks
                WHERE server = ? AND channel = ? AND hook = ?
                """,
                (server, channel, hook.lower()),
            )
        except:
            self.logger.exception("enabling channel hook failed")

    def disable_hook(self, server, channel, hook):
        try:
            self._execute(
                """
                INSERT OR IGNORE INTO disabled_hooks (server, channel, hook)
                VALUES (?, ?, ?)
                """,
                (server, channel, hook.lower()),
            )
        except:
            self.logger.exception("disabling channel hook failed")

    def get_disabled_hooks(self, server, channel):
        try:
            rows = self._execute(
                """
                SELECT hook
                FROM disabled_hooks
                WHERE server = ? AND channel = ?
                ORDER BY hook
                """,
                (server, channel),
                fetch="all",
            )
        except:
            self.logger.exception("getting disabled hook list failed")
        else:
            return [row[0] for row in rows]

    # - - points - - #
    def alter_point(self, server, nick, amount):
        try:
            row = self._execute(
                """
                INSERT INTO points (server, nick_key, nick, points)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(server, nick_key) DO UPDATE SET
                    nick = excluded.nick,
                    points = points.points + excluded.points
                RETURNING points
                """,
                (server, nick.lower(), nick, amount),
                fetch="one",
            )
        except:
            self.logger.exception("altering points failed")
        else:
            if row is None:
                self.logger.error("points row was not available after update")

            return row[0]

    def get_point(self, server, nick):
        try:
            return self._execute(
                """
                SELECT nick, points
                FROM points
                WHERE server = ? AND nick_key = ?
                """,
                (server, nick.lower()),
                fetch="one",
            )
        except:
            self.logger.exception("getting points failed")

    def top_points(self, server):
        try:
            return self._execute(
                """
                SELECT nick, points
                FROM points
                WHERE server = ?
                ORDER BY points DESC, nick ASC
                LIMIT 5
                """,
                [server],
                fetch="all",
            )
        except:
            self.logger.exception("getting top points failed")

    # - - quotes - - #
    def add_quote(self, server, channel, nick, msg, timestamp):
        try:
            self._execute(
                """
                INSERT INTO quotes (server, channel, nick_key, nick, msg, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (server, channel, nick.lower(), nick, msg, timestamp),
            )
        except:
            self.logger.exception("saving quote failed")

    def random_quote(self, server, channel, nick=None):
        nick_key = nick.lower() if nick else None

        try:
            return self._execute(
                """
                SELECT nick, msg, timestamp
                FROM quotes
                WHERE server = ? AND channel = ?
                    AND (? IS NULL OR nick_key = ?)
                ORDER BY RANDOM()
                LIMIT 1
                """,
                (server, channel, nick_key, nick_key),
                fetch="one",
            )
        except:
            self.logger.exception("getting random quote failed")
