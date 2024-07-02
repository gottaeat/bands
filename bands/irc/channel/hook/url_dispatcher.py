import ipaddress
import socket
import urllib.parse
import urllib.request

from bs4 import BeautifulSoup

from bands.colors import MIRCColors
from bands.colors import ANSIColors

c = MIRCColors()
ac = ANSIColors()


class URLDispatcher:
    def __init__(self, channel, user, urls):
        self.channel = channel
        self.user = user
        self.urls = urls
        self._run()

    def _prechecks(self):
        # dedup
        self.urls = list(dict.fromkeys(self.urls))

        print(self.urls)

        for url in self.urls:
            url_hostname = urllib.parse.urlparse(url).hostname

            # resolve first
            try:
                url_ip = socket.gethostbyname(url_hostname)
            except socket.gaierror as exc:
                err_msg = f"_prechecks() failed: cannot resolve {url}: {exc}"
                self.channel.server.logger.warning("%s: \n%s", __name__, err_msg)

                self.urls.remove(url)

            # check if url host is a bogon
            if ipaddress.ip_address(url_ip).is_private:
                err_msg = f"_prechecks() failed: {url} resolves to a bogon ({url_ip})"
                self.channel.server.logger.warning("%s: \n%s", __name__, err_msg)

                self.urls.remove(url)

    def _dispatch(self):
        for url in self.urls:
            self._print_url_to_log(url)
            self._handle_title(url)

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

    # - - handlers - - #
    def _handle_title(self, url):
        # scrape
        try:
            with urllib.request.urlopen(url) as f:
                data = f.read().decode()
        except urllib.request.HTTPError as e:
            err_msg = f"HTTP {e.code}"
        except urllib.error.URLError as e:
            err_msg = f"URL {e.reason.errno}"
        except Exception as exc:
            err_msg = exc

        try:
            if err_msg:  # pylint: disable=used-before-assignment
                err_msg = f"_handle_title() GET failed with: {err_msg}"
                self.channel.server.logger.warning("%s: \n%s", __name__, err_msg)
        except NameError:
            try:
                soup = BeautifulSoup(data, "html.parser")

                if soup.title:
                    title = soup.title.string.strip()

                    if len(title) > 55:
                        title = f"{title[0:52]}..."
                else:
                    err_msg = "No title"
            except Exception as exc:
                err_msg = exc

        try:
            if err_msg:  # pylint: disable=used-before-assignment
                err_msg = f"_handle_title() Parse failed with: {err_msg}"
                self.channel.server.logger.warning("%s: \n%s", __name__, err_msg)
        except NameError:
            if title is not None:
                self.channel.send_query(
                    f"{c.GREEN}[{c.LBLUE}LINK{c.GREEN}]{c.RES} {title}{c.RES}\n"
                )

    def _run(self):
        self._prechecks()
        self._dispatch()
