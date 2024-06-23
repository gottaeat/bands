import ipaddress
import socket
import urllib.parse
import urllib.request

from bs4 import BeautifulSoup

from bands.colors import MIRCColors
from bands.colors import ANSIColors

c = MIRCColors()
ac = ANSIColors()


class HTTPTitle:
    def __init__(self, channel, user, urls):
        self.channel = channel
        self.user = user
        self.urls = urls
        self._run()

    def _get_title(self, url):
        err_code, data = None, None

        # check if url host is a bogon
        url_hostname = urllib.parse.urlparse(url).hostname

        try:
            url_ip = socket.gethostbyname(url_hostname)
        except socket.gaierror as exc:
            self.channel.server.logger.warning(
                '"%s" while trying to resolve url %s', exc.strerror, url
            )
            return

        if ipaddress.ip_address(url_ip).is_private:
            self.channel.server.logger.warning(
                "%s resolves to a bogon (%s)", url, url_ip
            )
            return

        # scrape
        try:
            with urllib.request.urlopen(url) as f:
                data = f.read().decode()
        except urllib.request.HTTPError as e:
            err_code = f"HTTP {e.code}"
        except urllib.error.URLError as e:
            err_code = f"URL {e.reason.errno}"
        except:
            err_code = "UnknownError"

        if data:
            try:
                soup = BeautifulSoup(data, "html.parser")

                if soup.title:
                    title = soup.title.string.strip()

                    if len(title) > 55:
                        title = f"{title[0:52]}..."
                else:
                    err_code = "No title"
            except:
                err_code = "Parse Error"

        if err_code:
            self.channel.server.logger.warning("%s failed with: %s", __name__, err_code)
            return

        return title

    def _print_url_to_log(self, url):
        self.channel.server.logger.info(
            "%s%s%s%s%s %s",
            f"{ac.BMGN}[{ac.BYEL}HOOK",
            f"{ac.BRED}¦",
            f"{ac.BWHI}{self.user.nick} ({self.user.login})",
            f"{ac.BRED}¦",
            f"{ac.BGRN}{self.channel.name}{ac.BMGN}]",
            f"{ac.BCYN}{url}{ac.RES}",
        )

    def _run(self):
        # dedup
        self.urls = list(dict.fromkeys(self.urls))

        for url in self.urls:
            self._print_url_to_log(url)

            title = self._get_title(url)

            if title is not None:
                self.channel.send_query(
                    f"{c.GREEN}[{c.LBLUE}LINK{c.GREEN}]{c.RES} {title}{c.RES}\n"
                )
