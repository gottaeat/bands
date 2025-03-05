import json
import ssl
import xml.etree.ElementTree as ET

from dataclasses import dataclass
from threading import Thread

from bs4 import BeautifulSoup

from bands.colors import MIRCColors
from bands.util import get_url

c = MIRCColors()


@dataclass
class WGB:
    cds_1g: float = None
    cds_1w: tuple = None
    cds_1m: tuple = None
    cds_6m: tuple = None
    cds_1y: tuple = None
    cds_2y: tuple = None


class Finance:
    def __init__(self, channel, user, user_args):
        self.channel = channel
        self.user = user  # unused
        self.user_args = user_args  # unused

        self.logger = self.channel.logger.getChild(self.__class__.__name__)

        self.tcmb = None
        self.yahoo = None
        self.forbes = None
        self.xe = None
        self.binance = None
        self.wgb = None

        self._run()

    def _get_tcmb(self):
        tls_context = ssl.create_default_context()
        tls_context.options |= 0x4

        try:
            data = get_url(
                "https://www.tcmb.gov.tr/kurlar/today.xml", tls_context=tls_context
            )
        except:
            self.logger.exception("tcmb GET failed")

        try:
            tcmbxml_tree = ET.ElementTree(ET.fromstring(data))
            tcmbxml_root = tcmbxml_tree.getroot()
            tcmb_buying = float(tcmbxml_root.findall("Currency/ForexBuying")[0].text)
            tcmb_selling = float(tcmbxml_root.findall("Currency/ForexSelling")[0].text)
            self.tcmb = f"{(tcmb_buying + tcmb_selling) / 2:.6f}"
        except:
            self.logger.exception("tcmb parse failed")

    def _get_yahoo(self):
        try:
            data = get_url("https://query1.finance.yahoo.com/v8/finance/chart/USDTRY=X")
        except:
            self.logger.exception("yahoo GET failed")

        try:
            data = json.loads(data)
            self.yahoo = data["chart"]["result"][0]["meta"]["regularMarketPrice"]
        except:
            self.logger.exception("yahoo parse failed")

    def _get_forbes(self):
        try:
            data = get_url(
                "https://www.forbes.com/advisor/money-transfer/currency-converter/usd-try/?amount=1"
            )
        except:
            self.logger.exception("forbes GET failed")

        try:
            soup = BeautifulSoup(data, "html.parser")
            self.forbes = soup.find_all("span", {"class": "amount"})[0].get_text()
        except:
            self.logger.exception("forbes parse failed")

    def _get_xe(self):
        try:
            data = get_url(
                "https://www.x-rates.com/calculator/?from=USD&to=TRY&amount=1"
            )
        except:
            self.logger.exception("xe GET failed")

        try:
            soup = BeautifulSoup(data, "html.parser")
            self.xe = (
                soup.find_all("span", {"class": "ccOutputRslt"})[0]
                .get_text()
                .split(" ")[0]
            )
        except:
            self.logger.exception("xe parse failed")

    def _get_binance(self):
        try:
            data = get_url("https://api.binance.com/api/v3/ticker/price?symbol=USDTTRY")
        except:
            self.logger.exception("binance GET failed")

        try:
            self.binance = float(json.loads(data)["price"].rstrip("0"))
        except:
            self.logger.exception("binance parse failed")

    def _get_wgb(self):
        try:
            data = get_url(
                url="https://www.worldgovernmentbonds.com/wp-json/common/v1/historical",
                extra_headers={
                    "Content-type": "application/json; charset=UTF-8",
                    "Origin": "https://www.worldgovernmentbonds.com",
                },
                data=json.dumps(
                    {
                        "GLOBALVAR": {
                            "FUNCTION": "CDS",
                            "DATE_RIF": "2099-12-31",
                            "OBJ": {
                                "UNIT": "",
                                "DECIMAL": 2,
                                "UNIT_DELTA": "%",
                                "DECIMAL_DELTA": 2,
                            },
                            "COUNTRY1": {
                                "SYMBOL": "13",
                            },
                            "OBJ1": {"DURATA_STRING": "5 Years", "DURATA": 60},
                        }
                    }
                ).encode("utf-8"),
            )
        except:
            self.logger.exception("wgb POST failed")

        try:
            data = json.loads(data)["result"]["hLevel"]

            self.wgb = WGB(
                cds_1g=data["1g"]["lastVal"],
                cds_1w=(data["1w"]["firstVal"], data["1w"]["changeInRange"]),
                cds_1m=(data["1m"]["firstVal"], data["1m"]["changeInRange"]),
                cds_6m=(data["6m"]["firstVal"], data["6m"]["changeInRange"]),
                cds_1y=(data["1y"]["firstVal"], data["1y"]["changeInRange"]),
                cds_2y=(data["2y"]["firstVal"], data["2y"]["changeInRange"]),
            )
        except:
            self.logger.exception("wgb parse failed")

    def _collect(self):
        jobs = [
            Thread(target=self._get_tcmb, daemon=False),
            Thread(target=self._get_yahoo, daemon=False),
            Thread(target=self._get_forbes, daemon=False),
            Thread(target=self._get_xe, daemon=False),
            Thread(target=self._get_binance, daemon=False),
            Thread(target=self._get_wgb, daemon=False),
        ]

        self.channel.send_query(f"{c.INFO} scraping...")

        for job in jobs:
            job.start()

        for job in jobs:
            job.join()

    def _prompt(self):
        msg = ""

        if self.tcmb is not None:
            msg += f"{c.WHITE}→ {c.LRED}central{c.RES} {self.tcmb}\n"

        if self.xe is not None:
            msg += f"{c.WHITE}→ {c.LRED}xe{c.RES}      {self.xe}\n"

        if self.yahoo is not None:
            msg += f"{c.WHITE}→ {c.LRED}yahoo{c.RES}   {self.yahoo}\n"

        if self.forbes is not None:
            msg += f"{c.WHITE}→ {c.LRED}forbes{c.RES}  {self.forbes}\n"

        if msg:
            msg = f"{c.WHITE}USDTRY{c.RES}\n{msg}"

        if self.binance is not None:
            msg += f"{c.WHITE}USDTTRY{c.RES}\n"
            msg += f"{c.WHITE}→ {c.LRED}binance{c.RES} {self.binance}\n"

        if self.wgb is not None:
            msg += f"{c.WHITE}Credit Default Swaps{c.RES}\n"
            for period, value in [
                ("current", self.wgb.cds_1g),
                ("1w", self.wgb.cds_1w),
                ("1m", self.wgb.cds_1m),
                ("6m", self.wgb.cds_6m),
                ("1y", self.wgb.cds_1y),
                ("2y", self.wgb.cds_2y),
            ]:
                if isinstance(value, tuple):
                    msg += f"{c.WHITE}→ {c.LRED}{period}{c.RES}      {value[0]} ({value[1]:.2f})\n"
                else:
                    msg += f"{c.WHITE}→ {c.LRED}{period}{c.RES} {value}\n"

        if not msg:
            msg = f"{c.ERR} none of the APIs answered."

        # self.channel.send_query(drawbox(msg, "thic"))
        self.channel.send_query(msg)

    def _run(self):
        self._collect()
        self._prompt()
