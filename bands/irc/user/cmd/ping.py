class Ping:
    def __init__(self, user, user_obj, user_args):
        self.user = user
        self.user_obj = user_obj  # unused
        self.user_args = user_args

        self._run()

    def _run(self):
        self.user.send_query("pong")
