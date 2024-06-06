import urllib.parse
import urllib.request

from bs4 import BeautifulSoup

from bands.colors import MIRCColors

c = MIRCColors()


class HTTPTitle:
    def __init__(self, channel, msg_url):
        self.channel = channel
        self.urls = msg_url
        self._run()

    def _get_title(self, url):
        err_code, data = None, None

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
                    title = soup.title.string
                else:
                    err_code = "No title"
            except:
                err_code = "Parse Error"

        if err_code:
            self.channel.server.logger.warning("%s failed with: %s", __name__, err_code)
            return None

        return title

    def _run(self):
        msg = ""
        for url in self.urls:
            title = self._get_title(url)

            if title is not None:
                msg += f"{c.INFO} {title}\n"

        self.channel.send_query(msg)
