# pylint: disable=invalid-name,bare-except
import json
import re
import ssl
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from threading import Thread

from bs4 import BeautifulSoup

from bands.util import drawbox
from bands.util import MIRCColors


# pylint: disable=invalid-name
c = MIRCColors()


# pylint: disable=too-many-instance-attributes,too-few-public-methods
class Finance:
    def __init__(self, channel):
        self.channel = channel

        self.tcmb = None
        self.yahoo = None
        self.forbes = None
        # pylint: disable=invalid-name
        self.xe = None
        self.binance = None
        self.wgb_cds = None
        self.wgb_week = None
        self.wgb_month = None
        self.wgb_year = None

    def _get_tcmb(self):
        req = "https://www.tcmb.gov.tr/kurlar/today.xml"
        context = ssl.create_default_context()
        context.options |= 0x4

        try:
            with urllib.request.urlopen(req, context=context) as f:
                data = f.read().decode()
        except urllib.request.HTTPError as e:
            self.tcmb = f"HTTP {e.code}"
            return
        except urllib.error.URLError as e:
            self.tcmb = f"URL {e.reason.errno}"
            return
        except:
            self.tcmb = "Error"
            return

        try:
            tcmbxml_tree = ET.ElementTree(ET.fromstring(data))
            tcmbxml_root = tcmbxml_tree.getroot()
            tcmb_buying = float(tcmbxml_root.findall("Currency/ForexBuying")[0].text)
            tcmb_selling = float(tcmbxml_root.findall("Currency/ForexSelling")[0].text)

            self.tcmb = (tcmb_buying + tcmb_selling) / 2
        except:
            self.tcmb = "Parse Error"

    def _get_yahoo(self):
        url = "https://query1.finance.yahoo.com/v8/finance/chart/"
        params = urllib.parse.urlencode({"USDTRY": "X"})
        req = url + params

        try:
            with urllib.request.urlopen(req) as f:
                data = json.loads(f.read().decode())
        except urllib.request.HTTPError as e:
            self.yahoo = f"HTTP {e.code}"
            return
        except urllib.error.URLError as e:
            self.yahoo = f"URL {e.reason.errno}"
            return
        except:
            self.yahoo = "Error"
            return

        try:
            self.yahoo = data["chart"]["result"][0]["meta"]["regularMarketPrice"]
        except:
            self.yahoo = "Parse Error"

    def _get_forbes(self):
        url = (
            "https://www.forbes.com/advisor/money-transfer/currency-converter/usd-try/?"
        )
        params = urllib.parse.urlencode({"amount": "1"})
        req = url + params

        try:
            with urllib.request.urlopen(req) as f:
                data = f.read().decode()
        except urllib.request.HTTPError as e:
            self.forbes = f"HTTP {e.code}"
            return
        except urllib.error.URLError as e:
            self.forbes = f"URL {e.reason.errno}"
            return
        except:
            self.forbes = "Error"
            return

        try:
            soup = BeautifulSoup(data, "html.parser")
            self.forbes = soup.find_all("span", {"class": "amount"})[0].get_text()
        except:
            self.forbes = "Parse Error"

    def _get_xe(self):
        url = "https://www.x-rates.com/calculator/?"
        params = urllib.parse.urlencode({"from": "USD", "to": "TRY", "amount": "1"})
        req = url + params

        try:
            with urllib.request.urlopen(req) as f:
                data = f.read().decode()
        except urllib.request.HTTPError as e:
            self.xe = f"HTTP {e.code}"
            return
        except urllib.error.URLError as e:
            self.xe = f"URL {e.reason.errno}"
            return
        except:
            self.xe = "Error"
            return

        try:
            soup = BeautifulSoup(data, "html.parser")
            self.xe = (
                soup.find_all("span", {"class": "ccOutputRslt"})[0]
                .get_text()
                .split(" ")[0]
            )
        except:
            self.xe = "Parse Error"

    def _get_binance(self):
        url = "https://api.binance.com/api/v3/ticker/price?"
        params = urllib.parse.urlencode({"symbol": "USDTTRY"})
        req = url + params

        try:
            with urllib.request.urlopen(req) as f:
                data = f.read().decode()
        except urllib.request.HTTPError as e:
            self.binance = f"HTTP {e.code}"
            return
        except urllib.error.URLError as e:
            self.binance = f"URL {e.reason.errno}"
            return
        except:
            self.binance = "Error"
            return

        try:
            self.binance = float(json.loads(data)["price"].rstrip("0"))
        except:
            self.binance = "Parse Error"

    def _get_wgb(self):
        req = "http://www.worldgovernmentbonds.com/cds-historical-data/turkey/5-years/"

        try:
            with urllib.request.urlopen(req) as f:
                data = f.read().decode()
        except urllib.request.HTTPError as e:
            self.wgb_cds = f"HTTP {e.code}"
            return
        except urllib.error.URLError as e:
            self.wgb_cds = f"URL {e.reason.errno}"
            return
        except:
            self.wgb_cds = "Error"
            return

        try:
            soup = BeautifulSoup(data, "html.parser")

            self.wgb_cds = (
                soup.find_all("div", {"class": "w3-cell font-open-sans"})[0]
                .get_text()
                .split()[0]
            )

            perc = (
                soup.find_all("p", string=re.compile("CDS value changed"))[0]
                .get_text()
                .split()
            )

            self.wgb_week = perc[3]
            self.wgb_month = perc[7]
            self.wgb_year = perc[11]
        except:
            self.wgb_cds = "Parse Error"

    def _collect(self):
        threads = []

        tcmb = Thread(target=self._get_tcmb, daemon=False)
        yahoo = Thread(target=self._get_yahoo, daemon=False)
        forbes = Thread(target=self._get_forbes, daemon=False)
        # pylint: disable=invalid-name
        xe = Thread(target=self._get_xe, daemon=False)
        binance = Thread(target=self._get_binance, daemon=False)
        wgb = Thread(target=self._get_wgb, daemon=False)

        threads.append(tcmb)
        threads.append(yahoo)
        threads.append(forbes)
        threads.append(xe)
        threads.append(binance)
        threads.append(wgb)

        for job in threads:
            job.start()

        for job in threads:
            job.join()

    def print(self):
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

        self.channel.send_query(drawbox(msg, "thic"))
