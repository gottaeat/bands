from .url_dispatcher import URLDispatcher

HOOKS = {
    "url_dispatcher": {
        "class": URLDispatcher,
        "pattern": r"https?://[^\s]+",
    },
}
