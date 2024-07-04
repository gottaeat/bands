import ipaddress
import socket
import urllib.parse

from bs4 import BeautifulSoup

from bands.colors import ANSIColors
from bands.colors import MIRCColors
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

    def _prechecks(self):
        # dedup
        self.urls = list(dict.fromkeys(self.urls))

        for url in self.urls:
            url_hostname = urllib.parse.urlparse(url).hostname

            # resolve first
            try:
                url_ip = socket.gethostbyname(url_hostname)
            except socket.gaierror:
                self.logger.warning("cannot resolve %s\n:%s", url)
                self.urls.remove(url)

            # check if url host is a bogon
            if ipaddress.ip_address(url_ip).is_private:
                self.logger.warning("%s resolves to %s", url, url_ip)
                self.urls.remove(url)

    def _dispatch(self):
        for url in self.urls:
            self._handle_title(url)

    # - - handlers - - #
    def _handle_title(self, url):
        try:
            data = get_url(url)
        except:
            self.logger.exception("title GET failed")

        try:
            soup = BeautifulSoup(data, "html.parser")

            if soup.title:
                title = soup.title.string.strip()

                if len(title) > 55:
                    title = f"{title[0:52]}..."
            else:
                self.logger.error("%s has no title", url)
        except:
            self.logger.exception("title parse failed")

        self.channel.send_query(
            f"{c.GREEN}[{c.LBLUE}LINK{c.GREEN}]{c.RES} {title}{c.RES}\n"
        )

    def _run(self):
        self._prechecks()
        self._dispatch()
