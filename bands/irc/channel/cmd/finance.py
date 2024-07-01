import json
import re
import ssl
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from threading import Thread

from bs4 import BeautifulSoup

from bands.colors import MIRCColors


c = MIRCColors()


class Finance:
    def __init__(self, channel, user, user_args):
        self.channel = channel
        self.user = user  # unused
        self.user_args = user_args  # unused

        self.tcmb = None
        self.yahoo = None
        self.forbes = None
        self.xe = None
        self.binance = None
        self.wgb_cds = None
        self.wgb_week = None
        self.wgb_month = None
        self.wgb_year = None

        self._run()

    def _get_tcmb(self):
        tls_context = ssl.create_default_context()
        tls_context.options |= 0x4

        try:
            with urllib.request.urlopen(
                "https://www.tcmb.gov.tr/kurlar/today.xml", context=tls_context
            ) as f:
                data = f.read().decode()
        except urllib.request.HTTPError as e:
            err_msg = f"HTTP {e.code}"
        except urllib.error.URLError as e:
            err_msg = f"URL {e.reason.errno}"
        except Exception as exc:
            err_msg = "GET failed"
            self.channel.server.logger.warning("%s failed with:\n%s", __name__, exc)

        try:
            if err_msg:  # pylint: disable=used-before-assignment
                self.tcmb = err_msg
        except NameError:
            try:
                tcmbxml_tree = ET.ElementTree(ET.fromstring(data))
                tcmbxml_root = tcmbxml_tree.getroot()
                tcmb_buying = float(
                    tcmbxml_root.findall("Currency/ForexBuying")[0].text
                )
                tcmb_selling = float(
                    tcmbxml_root.findall("Currency/ForexSelling")[0].text
                )

                self.tcmb = (tcmb_buying + tcmb_selling) / 2
            except Exception as exc:
                self.tcmb = "Parse failed"
                self.channel.server.logger.warning("%s failed with:\n%s", __name__, exc)

    def _get_yahoo(self):
        try:
            with urllib.request.urlopen(
                "https://query1.finance.yahoo.com/v8/finance/chart/USDTRY=X"
            ) as f:
                data = json.loads(f.read().decode())
        except urllib.request.HTTPError as e:
            err_msg = f"HTTP {e.code}"
        except urllib.error.URLError as e:
            err_msg = f"URL {e.reason.errno}"
        except Exception as exc:
            err_msg = "GET failed"
            self.channel.server.logger.warning("%s failed with:\n%s", __name__, exc)

        try:
            if err_msg:  # pylint: disable=used-before-assignment
                self.yahoo = err_msg
        except NameError:
            try:
                self.yahoo = data["chart"]["result"][0]["meta"]["regularMarketPrice"]
            except Exception as exc:
                self.yahoo = "Parse failed"
                self.channel.server.logger.warning("%s failed with:\n%s", __name__, exc)

    def _get_forbes(self):
        try:
            with urllib.request.urlopen(
                "https://www.forbes.com/advisor/money-transfer/currency-converter/usd-try/?amount=1"
            ) as f:
                data = f.read().decode()
        except urllib.request.HTTPError as e:
            err_msg = f"HTTP {e.code}"
        except urllib.error.URLError as e:
            err_msg = f"URL {e.reason.errno}"
        except Exception as exc:
            err_msg = "GET failed"
            self.channel.server.logger.warning("%s failed with:\n%s", __name__, exc)

        try:
            if err_msg:  # pylint: disable=used-before-assignment
                self.forbes = err_msg
        except NameError:
            try:
                soup = BeautifulSoup(data, "html.parser")
                self.forbes = soup.find_all("span", {"class": "amount"})[0].get_text()
            except Exception as exc:
                self.forbes = "Parse failed"
                self.channel.server.logger.warning("%s failed with:\n%s", __name__, exc)

    def _get_xe(self):
        try:
            with urllib.request.urlopen(
                "https://www.x-rates.com/calculator/?from=USD&to=TRY&amount=1"
            ) as f:
                data = f.read().decode()
        except urllib.request.HTTPError as e:
            err_msg = f"HTTP {e.code}"
        except urllib.error.URLError as e:
            err_msg = f"URL {e.reason.errno}"
        except Exception as exc:
            err_msg = "GET failed"
            self.channel.server.logger.warning("%s failed with:\n%s", __name__, exc)

        try:
            if err_msg:  # pylint: disable=used-before-assignment
                self.xe = err_msg
        except NameError:
            try:
                soup = BeautifulSoup(data, "html.parser")
                self.xe = (
                    soup.find_all("span", {"class": "ccOutputRslt"})[0]
                    .get_text()
                    .split(" ")[0]
                )
            except:
                self.xe = "Parse failed"
                self.channel.server.logger.warning("%s failed with:\n%s", __name__, exc)

    def _get_binance(self):
        try:
            with urllib.request.urlopen(
                "https://api.binance.com/api/v3/ticker/price?symbol=USDTTRY"
            ) as f:
                data = f.read().decode()
        except urllib.request.HTTPError as e:
            err_msg = f"HTTP {e.code}"
        except urllib.error.URLError as e:
            err_msg = f"URL {e.reason.errno}"
        except Exception as exc:
            err_msg = "GET failed"
            self.channel.server.logger.warning("%s failed with:\n%s", __name__, exc)

        try:
            if err_msg:  # pylint: disable=used-before-assignment
                self.binance = err_msg
        except NameError:
            try:
                self.binance = float(json.loads(data)["price"].rstrip("0"))
            except Exception as exc:
                self.binance = "Parse failed"
                self.channel.server.logger.warning("%s failed with:\n%s", __name__, exc)

    def _get_wgb(self):
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        user_agent += "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        headers = {"User-Agent": user_agent}

        request = urllib.request.Request(
            "http://www.worldgovernmentbonds.com/cds-historical-data/turkey/5-years/",
            headers=headers,
        )

        try:
            with urllib.request.urlopen(request) as f:
                data = f.read().decode()
        except urllib.request.HTTPError as e:
            err_msg = f"HTTP {e.code}"
        except urllib.error.URLError as e:
            err_msg = f"URL {e.reason.errno}"
        except Exception as exc:
            err_msg = "GET failed"
            self.channel.server.logger.warning("%s failed with:\n%s", __name__, exc)

        try:
            if err_msg:  # pylint: disable=used-before-assignment
                self.wgb_cds = err_msg
        except NameError:
            try:
                soup = BeautifulSoup(data, "html.parser")

                cds_td = None
                td_elem = soup.find_all("td")
                for td in td_elem:
                    td = td.get_text()
                    if "Current CDS" in td:
                        cds_td = td.split()
                        break

                if not cds_td:
                    self.wgb_cds = "Parse failed"
                    self.channel.server.logger.warning(
                        "%s failed with:\n%s",
                        __name__,
                        "element containing current CDS was not found",
                    )

                    return

                self.wgb_cds = cds_td[2]
            except Exception as exc:
                self.wgb_cds = "Parse failed"
                self.channel.server.logger.warning("%s failed with:\n%s", __name__, exc)

            if cds_td:
                try:
                    perc = (
                        soup.find_all("p", string=re.compile("CDS value changed"))[0]
                        .get_text()
                        .split()
                    )

                    if len(perc) == 0:
                        self.wgb_cds = "Parse failed"
                        self.channel.server.logger.warning(
                            "%s failed with:\n%s",
                            __name__,
                            "element containing historical CDS was not found",
                        )

                        return

                    self.wgb_week = perc[3]
                    self.wgb_month = perc[7]
                    self.wgb_year = perc[11]
                except Exception as exc:
                    self.wgb_cds = "Parse failed"
                    self.wgb_week = None
                    self.channel.server.logger.warning(
                        "%s failed with:\n%s", __name__, exc
                    )

    def _collect(self):
        jobs = [
            Thread(target=self._get_tcmb),
            Thread(target=self._get_yahoo),
            Thread(target=self._get_forbes),
            Thread(target=self._get_xe),
            Thread(target=self._get_binance),
            Thread(target=self._get_wgb),
        ]

        self.channel.send_query(f"{c.INFO} scraping...")

        for job in jobs:
            job.start()

        for job in jobs:
            job.join()

    def _run(self):
        self._collect()

        msg = f"{c.WHITE}USDTRY{c.RES}\n"
        msg += f"{c.WHITE}├ {c.LRED}central {c.LBLUE}→{c.RES} {self.tcmb}\n"
        msg += f"{c.WHITE}├ {c.LRED}xe      {c.LBLUE}→{c.RES} {self.xe}\n"
        msg += f"{c.WHITE}├ {c.LRED}yahoo   {c.LBLUE}→{c.RES} {self.yahoo}\n"
        msg += f"{c.WHITE}└ {c.LRED}forbes  {c.LBLUE}→{c.RES} {self.forbes}\n"
        msg += f"{c.WHITE}USDTTRY{c.RES}\n"
        msg += f"{c.WHITE}└ {c.LRED}binance {c.LBLUE}→{c.RES} {self.binance}\n"
        msg += f"{c.WHITE}CDS{c.RES}\n"
        msg += f"{c.WHITE}└ {c.LRED}wgb     {c.LBLUE}→{c.RES} {self.wgb_cds}\n"

        if self.wgb_week:
            msg += f"  {c.WHITE}├ {c.LRED}1w    {c.LBLUE}→{c.RES} {self.wgb_week}\n"
            msg += f"  {c.WHITE}├ {c.LRED}1m    {c.LBLUE}→{c.RES} {self.wgb_month}\n"
            msg += f"  {c.WHITE}└ {c.LRED}1y    {c.LBLUE}→{c.RES} {self.wgb_year}"

        # self.channel.send_query(drawbox(msg, "thic"))
        self.channel.send_query(msg)
