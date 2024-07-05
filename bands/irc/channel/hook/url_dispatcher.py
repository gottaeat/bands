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
        self.sc_client_id = self.channel.server.config.sc_client_id

        self._run()

    @staticmethod
    def _numfmt(num):
        num = int(num)

        if num == 0:
            return str(num)

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
            url_netloc = urllib.parse.urlparse(url).netloc

            if "/watch?v=" in url or "/playlist?list=" in url:
                try:
                    self._handle_yt(url)
                except:
                    self._handle_title(url)
            elif url_netloc in (
                "on.soundcloud.com",
                "soundcloud.com",
                "api.soundcloud.com",
            ):
                try:
                    self._handle_sc(url)
                except:
                    self._handle_title(url)
            else:
                self._handle_title(url)

    # - - title handler / fallback - - #
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

    # - - youtube handlers - - #
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

    # - - soundcloud handlers - - #
    def _handle_sc(self, url):
        # follow all links except for api
        if urllib.parse.urlparse(url).netloc != "api.soundcloud.com":
            try:
                with urllib.request.urlopen(url) as f:
                    url = f.geturl()
            except:
                self.logger.exception("failed following the link")

        # make resolve url
        resolve_url = "https://api-v2.soundcloud.com/resolve"
        resolve_url += f"?url={url}&client_id={self.sc_client_id}"

        # hit up soundcloud api
        try:
            data = get_url(resolve_url)
        except:
            self.logger.exception("GET failed")

        # check json
        try:
            data = json.loads(data)
        except:
            self.logger.exception("parse failed")

        try:
            track_kind = data["kind"]
        except KeyError:
            self.logger.exception('"kind" key is missing from the json')

        # dispatch to handler
        if track_kind not in ("playlist", "system-playlist", "track"):
            self.logger.error("%s is not a recognized kind", track_kind)

        # track
        if track_kind == "track":
            self._handle_sc_track(data)
            return

        # playlists/sets/album
        if track_kind == "playlist":
            self._handle_sc_playlist(data)
            return

        # system-playlist
        if track_kind == "system-playlist":
            self._handle_sc_station(data)

    def _handle_sc_track(self, data):
        # parse json
        data_must_have = [
            "created_at",
            "duration",
            "likes_count",
            "playback_count",
            "publisher_metadata",
            "reposts_count",
            "title",
            "user",
        ]

        for key in data_must_have:
            if key not in data.keys():
                self.logger.error("%s is missing from track json", key)

        user_must_have = [
            "followers_count",
            "username",
            "verified",
        ]

        for key in user_must_have:
            if key not in data["user"].keys():
                self.logger.error("%s is missing from user json", key)

        # uploader metadata
        uploader_name = data["user"]["username"]
        uploader_verified = "✓" if data["user"]["verified"] else ""
        uploader_subs = self._numfmt(data["user"]["followers_count"])

        if len(uploader_name) > 15:
            uploader_name = f"{uploader_name[0:12]}..."

        # track metadata
        track_title = data["title"]

        if data["publisher_metadata"] is not None:
            # if uploader specified an artist, put that as part of track
            if "artist" in data["publisher_metadata"].keys():
                track_artist = data["publisher_metadata"]["artist"]

                if track_artist.lower().strip() != uploader_name.lower().strip():
                    if len(track_artist) > 10:
                        track_artist = f"{track_artist[0:8]}..."

                        track_title = f"{track_artist} - {track_title}"

        if len(track_title) > 35:
            track_title = f"{track_title[0:32]}..."

        track_len = self._mktstamp(data["duration"] / 1000)
        track_tstamp = datetime.datetime.fromisoformat(data["created_at"].rstrip("Z"))
        track_views = self._numfmt(data["playback_count"])
        track_likes = self._numfmt(data["likes_count"])
        track_reposts = self._numfmt(data["reposts_count"])

        # prompt
        msg = f"{c.GREEN}[{c.ORANGE}SoundCloud{c.GREEN}]"
        msg += f"[{c.LBLUE}{track_len}{c.GREEN}] "
        msg += f"{c.WHITE}{track_title} "
        msg += f"{c.LBLUE}by {c.LGREEN}{uploader_name}"
        msg += f"{c.WHITE}{uploader_verified} "
        msg += f"{c.LBLUE}({c.LCYAN}{uploader_subs} subs{c.LBLUE}) "
        msg += f"{c.LRED}@ {c.LCYAN}{track_tstamp}UTC {c.LBLUE}¦ "
        msg += f"{c.WHITE}{track_views} {c.LCYAN}views {c.LBLUE}¦ "
        msg += f"{c.WHITE}{track_likes}{c.LRED}♥ "
        msg += f"{c.WHITE}{track_reposts}{c.LGREEN}⇌{c.RES}"
        self.channel.send_query(msg)

    def _handle_sc_playlist(self, data):
        # parse json
        data_must_have = [
            "created_at",
            "duration",
            "is_album",
            "likes_count",
            "reposts_count",
            "title",
            "track_count",
            "user",
        ]

        for key in data_must_have:
            if key not in data.keys():
                self.logger.error("%s is missing from track json", key)

        user_must_have = [
            "followers_count",
            "username",
            "verified",
        ]

        for key in user_must_have:
            if key not in data["user"].keys():
                self.logger.error("%s is missing from user json", key)

        # uploader metadata
        uploader_name = data["user"]["username"]
        uploader_verified = "✓" if data["user"]["verified"] else ""
        uploader_subs = self._numfmt(data["user"]["followers_count"])

        if len(uploader_name) > 15:
            uploader_name = f"{uploader_name[0:12]}..."

        # playlist metadata
        pl_title = data["title"]

        if len(pl_title) > 35:
            pl_title = f"{pl_title[0:32]}..."

        pl_len = self._mktstamp(data["duration"] / 1000)
        pl_tstamp = datetime.datetime.fromisoformat(data["created_at"].rstrip("Z"))
        pl_likes = self._numfmt(data["likes_count"])
        pl_reposts = self._numfmt(data["reposts_count"])
        pl_track_len = data["track_count"]

        # prompt
        msg = f"{c.GREEN}[{c.ORANGE}SoundCloud{c.GREEN}]"

        if data["is_album"]:
            msg += f"[{c.LBLUE}ALBUM{c.GREEN}]"
        else:
            msg += f"[{c.LBLUE}PLAYLIST{c.GREEN}]"

        msg += f"[{c.LBLUE}{pl_track_len} tracks{c.LRED}¦"
        msg += f"{c.LBLUE}{pl_len}{c.GREEN}] "
        msg += f"{c.WHITE}{pl_title} "
        msg += f"{c.LBLUE}by {c.LGREEN}{uploader_name}"
        msg += f"{c.WHITE}{uploader_verified} "
        msg += f"{c.LBLUE}({c.LCYAN}{uploader_subs} subs{c.LBLUE}) "
        msg += f"{c.LRED}@ {c.LCYAN}{pl_tstamp}UTC {c.LBLUE}¦ "
        msg += f"{c.WHITE}{pl_likes}{c.LRED}♥ "
        msg += f"{c.WHITE}{pl_reposts}{c.LGREEN}⇌{c.RES}"
        self.channel.send_query(msg)

    def _handle_sc_station(self, data):
        # parse json
        data_must_have = [
            "description",
            "likes_count",
        ]

        for key in data_must_have:
            if key not in data.keys():
                self.logger.error("%s is missing from track json", key)

        station_based_on = data["description"]
        if len(station_based_on) > 50:
            station_based_on = f"{station_based_on[0:47]}..."

        station_likes = self._numfmt(data["likes_count"])

        msg = f"{c.GREEN}[{c.ORANGE}SoundCloud{c.GREEN}]"
        msg += f"[{c.LBLUE}STATION{c.GREEN}] "
        msg += f"{c.WHITE}{station_based_on} {c.LBLUE}¦ "
        msg += f"{c.WHITE}{station_likes}{c.LRED}♥{c.RES}"
        self.channel.send_query(msg)

    def _run(self):
        self._prechecks()
        self._dispatch()
