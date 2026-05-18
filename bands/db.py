import os
import sqlite3

from contextlib import contextmanager
from threading import Lock


class BandsDB:
    def __init__(self, parent_logger, path):
        self.logger = parent_logger.getChild(self.__class__.__name__)

        self.path = path
        self.mutex = Lock()

        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.path)

    def _init_db(self):
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)

        # tables and indexes for: prefix + command|hook toggle + points + quotes
        self.execute_script("""
            CREATE TABLE IF NOT EXISTS channel_settings (
                server TEXT NOT NULL,
                channel TEXT NOT NULL,
                prefix TEXT NOT NULL,
                PRIMARY KEY (server, channel)
            );

            CREATE TABLE IF NOT EXISTS disabled_commands (
                server TEXT NOT NULL,
                channel TEXT NOT NULL,
                command TEXT NOT NULL,
                PRIMARY KEY (server, channel, command)
            );

            CREATE TABLE IF NOT EXISTS disabled_hooks (
                server TEXT NOT NULL,
                channel TEXT NOT NULL,
                hook TEXT NOT NULL,
                PRIMARY KEY (server, channel, hook)
            );

            CREATE TABLE IF NOT EXISTS points (
                server TEXT NOT NULL,
                nick_key TEXT NOT NULL,
                nick TEXT NOT NULL,
                points INTEGER NOT NULL,
                PRIMARY KEY (server, nick_key)
            );

            CREATE INDEX IF NOT EXISTS idx_points_server_points
            ON points (server, points DESC, nick ASC);

            CREATE TABLE IF NOT EXISTS quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                server TEXT NOT NULL,
                channel TEXT NOT NULL,
                nick_key TEXT NOT NULL,
                nick TEXT NOT NULL,
                msg TEXT NOT NULL,
                timestamp INTEGER NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_quotes_channel
            ON quotes (server, channel);

            CREATE INDEX IF NOT EXISTS idx_quotes_nick
            ON quotes (server, channel, nick_key);
            """)

        self.logger.info("initialized sqlite database at %s", self.path)

    def execute(self, query, params=None):
        if params is None:
            params = []
        with self.mutex, self._connect() as conn:
            conn.execute(query, params)

    def execute_script(self, query):
        with self.mutex, self._connect() as conn:
            conn.executescript(query)

    def fetchone(self, query, params=None):
        if params is None:
            params = []
        with self.mutex, self._connect() as conn:
            return conn.execute(query, params).fetchone()

    def fetchall(self, query, params=None):
        if params is None:
            params = []
        with self.mutex, self._connect() as conn:
            return conn.execute(query, params).fetchall()

    @contextmanager
    def transaction(self):
        with self.mutex, self._connect() as conn:
            yield conn

    # irc.user.cmd.rcon
    def get_prefix(self, server, channel):
        row = self.fetchone(
            """
            SELECT prefix
            FROM channel_settings
            WHERE server = ? AND channel = ?
            """,
            (server, channel),
        )

        return row[0] if row else "?"

    def set_prefix(self, server, channel, prefix):
        self.execute(
            """
            INSERT INTO channel_settings (server, channel, prefix)
            VALUES (?, ?, ?)
            ON CONFLICT(server, channel) DO UPDATE SET prefix = excluded.prefix
            """,
            (server, channel, prefix),
        )

    def command_disabled(self, server, channel, command):
        row = self.fetchone(
            """
            SELECT 1
            FROM disabled_commands
            WHERE server = ? AND channel = ? AND command = ?
            """,
            (server, channel, command.lower()),
        )

        return row is not None

    def disable_command(self, server, channel, command):
        self.execute(
            """
            INSERT OR IGNORE INTO disabled_commands (server, channel, command)
            VALUES (?, ?, ?)
            """,
            (server, channel, command.lower()),
        )

    def enable_command(self, server, channel, command):
        self.execute(
            """
            DELETE FROM disabled_commands
            WHERE server = ? AND channel = ? AND command = ?
            """,
            (server, channel, command.lower()),
        )

    def disabled_commands(self, server, channel):
        rows = self.fetchall(
            """
            SELECT command
            FROM disabled_commands
            WHERE server = ? AND channel = ?
            ORDER BY command
            """,
            (server, channel),
        )

        return [row[0] for row in rows]

    # irc.user.cmd.rcon
    def hook_disabled(self, server, channel, hook):
        row = self.fetchone(
            """
            SELECT 1
            FROM disabled_hooks
            WHERE server = ? AND channel = ? AND hook = ?
            """,
            (server, channel, hook.lower()),
        )

        return row is not None

    def disable_hook(self, server, channel, hook):
        self.execute(
            """
            INSERT OR IGNORE INTO disabled_hooks (server, channel, hook)
            VALUES (?, ?, ?)
            """,
            (server, channel, hook.lower()),
        )

    def enable_hook(self, server, channel, hook):
        self.execute(
            """
            DELETE FROM disabled_hooks
            WHERE server = ? AND channel = ? AND hook = ?
            """,
            (server, channel, hook.lower()),
        )

    def disabled_hooks(self, server, channel):
        rows = self.fetchall(
            """
            SELECT hook
            FROM disabled_hooks
            WHERE server = ? AND channel = ?
            ORDER BY hook
            """,
            (server, channel),
        )

        return [row[0] for row in rows]

    # irc.channel.cmd.point + irc.channel.cmd.blackjack
    def alter_point(self, server, nick, amount):
        nick_key = nick.lower()

        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO points (server, nick_key, nick, points)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(server, nick_key) DO UPDATE SET
                    nick = excluded.nick,
                    points = points.points + excluded.points
                """,
                (server, nick_key, nick, amount),
            )
            row = conn.execute(
                """
                SELECT points
                FROM points
                WHERE server = ? AND nick_key = ?
                """,
                (server, nick_key),
            ).fetchone()

        return row[0]

    def get_point(self, server, nick):
        return self.fetchone(
            """
            SELECT nick, points
            FROM points
            WHERE server = ? AND nick_key = ?
            """,
            (server, nick.lower()),
        )

    # irc.channel.cmd.point
    def top_points(self, server, limit=5):
        limit = max(1, min(int(limit), 50))

        return self.fetchall(
            """
            SELECT nick, points
            FROM points
            WHERE server = ?
            ORDER BY points DESC, nick ASC
            LIMIT ?
            """,
            (server, limit),
        )

    # irc.channel.cmd.quote
    def add_quote(self, server, channel, nick, msg, timestamp):
        self.execute(
            """
            INSERT INTO quotes (server, channel, nick_key, nick, msg, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (server, channel, nick.lower(), nick, msg, timestamp),
        )

    def random_quote(self, server, channel, nick=None):
        params = [server, channel]
        nick_clause = ""

        if nick is not None:
            nick_clause = "AND nick_key = ?"
            params.append(nick.lower())

        return self.fetchone(
            f"""
            SELECT nick, msg, timestamp
            FROM quotes
            WHERE server = ? AND channel = ? {nick_clause}
            ORDER BY RANDOM()
            LIMIT 1
            """,
            params,
        )
