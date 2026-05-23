from bs4 import BeautifulSoup

from bands.colors import ANSIColors
from bands.colors import MIRCColors
from bands.irc.util import unilen
from bands.util import get_url

c = MIRCColors()
ac = ANSIColors()


class URLDispatcher:
    def __init__(self, channel, user, urls):
        self.channel = channel
        self.user = user
        self.urls = urls

        self.logger = self.channel.logger.getChild(self.__class__.__name__)

        self._run()

    def _dispatch(self):
        for url in dict.fromkeys(self.urls):
            self._handle_title(url)

    # - - title handler / fallback - - #
    def _handle_title(self, url):
        try:
            data = get_url(url, nobogons=True)
        except:
            return self.logger.exception("title GET failed for %s", url)

        try:
            soup = BeautifulSoup(data, "html.parser")
        except:
            return self.logger.exception("title parse failed for %s", url)

        if soup.title:
            try:
                if not isinstance(soup.title.string, str):
                    return self.logger.exception(
                        "%s title expected to be a str but got %s",
                        url,
                        soup.title.string,
                    )

                title = soup.title.string.strip()

                if unilen(title) > 55:
                    title = f"{title[0:52]}..."
            except:
                return self.logger.exception("title parse failed for %s", url)
        else:
            return self.logger.error("%s has no title", url)

        self.channel.send_query(
            f"{c.GREEN}[{c.LBLUE}LINK{c.GREEN}]{c.RES} {title}{c.RES}\n"
        )

    def _run(self):
        self._dispatch()
