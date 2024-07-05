import datetime
import ipaddress
import json
import socket
import urllib.parse

from bs4 import BeautifulSoup

from bands.colors import ANSIColors
from bands.colors import MIRCColors
from bands.util import get_url

c = MIRCColors()
ac = ANSIColors()


class URLDispatcher:
    _PIPED_INSTANCE = "pipedapi-libre.kavin.rocks"

    def __init__(self, channel, user, urls):
        self.channel = channel
        self.user = user
        self.urls = urls

        self.logger = self.channel.logger.getChild(self.__class__.__name__)

        self._run()

    @staticmethod
    def _numfmt(num):
        num = int(num)

        if num >= 1_000_000_000:
            retnum = (f"{num / 1_000_000_000:.2f}", "B")
        elif num >= 1_000_000:
            retnum = (f"{num / 1_000_000:.2f}", "M")
        elif num >= 1_000:
            retnum = (f"{num / 1_000:.2f}", "K")
        else:
            retnum = (str(num), "")

        return f"{retnum[0].rstrip('0').rstrip('.')}{retnum[1]}"

    @staticmethod
    def _mktstamp(seconds):
        seconds = int(seconds)
        days, remainder = divmod(seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)

        if days > 0:
            return f"{days:02}:{hours:02}:{minutes:02}:{seconds:02}"
        if hours > 0:
            return f"{hours:02}:{minutes:02}:{seconds:02}"
        if minutes > 0:
            return f"{minutes:02}:{ seconds:02}"
        return f"00:{seconds:02}"

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
            if "/watch?v=" in url or "/playlist?list=" in url:
                try:
                    self._handle_yt(url)
                except:
                    self._handle_title(url)
            else:
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

    def _handle_yt(self, url):
        # get id
        try:
            yt_id = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)["v"]
            yt_type = "streams"
        except KeyError:
            try:
                yt_id = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)["list"]
                yt_type = "playlists"
            except KeyError:
                self.logger.exception('neither "list" or "v" exists as a query somehow')

        if len(yt_id) != 1:
            self.logger.error("too many queries of the same type")

        yt_id = yt_id[0]

        # hit up piped api
        try:
            data = get_url(f"https://{self._PIPED_INSTANCE}/{yt_type}/{yt_id}")
        except:
            self.logger.exception("GET failed")

        # check json
        try:
            data = json.loads(data)
        except:
            self.logger.exception("parse failed")

        try:
            if data["error"]:
                self.logger.error('json contains the key "error"')
        except KeyError:
            pass

        # dispatch to handler
        if yt_type == "streams":
            self._handle_yt_video(data)
        else:
            self._handle_yt_playlist(data)

    def _handle_yt_video(self, data):
        # parse json
        data_must_have = [
            "title",
            "duration",
            "views",
            "likes",
            "dislikes",
            "uploaded",
            "uploader",
            "uploaderVerified",
            "uploaderSubscriberCount",
        ]

        for key in data_must_have:
            if key not in data.keys():
                self.logger.error("%s is missing from json", key)

        # video metadata
        vid_title = data["title"]
        if len(vid_title) > 35:
            vid_title = f"{vid_title[0:32]}..."

        vid_len = self._mktstamp(data["duration"])
        vid_views = self._numfmt(data["views"])
        vid_likes = self._numfmt(data["likes"])
        vid_dislikes = self._numfmt(data["dislikes"])
        vid_tstamp = datetime.datetime.utcfromtimestamp(int(data["uploaded"]) / 1000)

        # uploader metadata
        uploader = data["uploader"]
        if len(uploader) > 15:
            uploader = f"{uploader[0:12]}..."
        uploader_verified = "✓" if data["uploaderVerified"] else ""
        uploader_subs = self._numfmt(data["uploaderSubscriberCount"])

        # prompt
        msg = f"{c.GREEN}[{c.LRED}You{c.WHITE}Tube{c.GREEN}]"
        msg += f"[{c.LBLUE}{vid_len}{c.GREEN}] {c.WHITE}{vid_title} "
        msg += f"{c.LBLUE}by {c.LGREEN}{uploader}{c.WHITE}{uploader_verified} "
        msg += f"{c.LBLUE}({c.LCYAN}{uploader_subs} subs{c.LBLUE}) "
        msg += f"{c.LRED}@{c.LCYAN} {vid_tstamp}UTC {c.LBLUE}¦ "
        msg += f"{c.WHITE}{vid_views} {c.LCYAN}views {c.LBLUE}¦ "
        msg += f"{c.WHITE}{vid_likes}↑{c.LRED}↓{vid_dislikes}{c.RES}"
        self.channel.send_query(msg)

    def _handle_yt_playlist(self, data):
        # parse json
        data_must_have = [
            "name",
            "uploader",
            "videos",
        ]

        for key in data_must_have:
            if key not in data.keys():
                self.logger.error("%s is missing from json", key)

        # playlist metadata
        pl_title = data["name"]
        if len(pl_title) > 35:
            pl_title = f"{pl_title[0:32]}..."

        pl_videos = data["videos"]

        # uploader metadata
        pl_uploader = data["uploader"]
        if pl_uploader:
            if len(pl_uploader) > 15:
                pl_uploader = f"{pl_uploader[0:12]}..."
        else:
            pl_uploader = "YouTube"

        # prompt
        msg = f"{c.GREEN}[{c.LRED}You{c.WHITE}Tube{c.GREEN}]"
        msg += f"[{c.LBLUE}PLAYLIST{c.GREEN}] {c.WHITE}{pl_title} "
        msg += f"{c.LBLUE}by {c.LGREEN}{pl_uploader} {c.LBLUE}¦ "
        msg += f"{c.LCYAN}length: {c.WHITE}{pl_videos}{c.RES}"
        self.channel.send_query(msg)

    def _run(self):
        self._prechecks()
        self._dispatch()
