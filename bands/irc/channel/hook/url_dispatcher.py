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
            except socket.gaierror as exc:
                self.logger.warning("cannot resolve %s\n:%s", url, exc)
                self.urls.remove(url)

            # check if url host is a bogon
            if ipaddress.ip_address(url_ip).is_private:
                self.logger.warning("%s resolves to %s", url, url_ip)
                self.urls.remove(url)

    def _dispatch(self):
        for url in self.urls:
            self._print_url_to_log(url)
            self._handle_title(url)

    def _print_url_to_log(self, url):
        msg = f"{ac.BYEL}{self.user.nick} "
        msg += f"{ac.BMGN}({ac.LCYN}{self.user.login}{ac.BMGN}) "
        msg += f"{ac.BRED}¦ {ac.BCYN}{url}{ac.RES}"
        self.logger.info(msg)

    # - - handlers - - #
    def _handle_title(self, url):
        data, err_msg = get_url(url)

        if err_msg:
            self.logger.warning("%s caused:\n%", url, err_msg)
            return

        try:
            soup = BeautifulSoup(data, "html.parser")

            if soup.title:
                title = soup.title.string.strip()

                if len(title) > 55:
                    title = f"{title[0:52]}..."
            else:
                self.logger.warning("%s caused: no title", url)
                return
        except Exception as exc:
            self.logger.warning("%s caused:\n%", url, exc)
            return

        self.channel.send_query(
            f"{c.GREEN}[{c.LBLUE}LINK{c.GREEN}]{c.RES} {title}{c.RES}\n"
        )

    def _run(self):
        self._prechecks()
        self._dispatch()
