import json
import re
import ssl
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup


# pylint: disable=too-many-instance-attributes,too-few-public-methods
class Finance:
    def __init__(self):
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

        with urllib.request.urlopen(req, context=context) as f:
            data = f.read().decode()

        tcmbxml_tree = ET.ElementTree(ET.fromstring(data))
        tcmbxml_root = tcmbxml_tree.getroot()
        tcmb_buying = float(tcmbxml_root.findall("Currency/ForexBuying")[0].text)
        tcmb_selling = float(tcmbxml_root.findall("Currency/ForexSelling")[0].text)

        self.tcmb = (tcmb_buying + tcmb_selling) / 2

    def _get_yahoo(self):
        url = "https://query1.finance.yahoo.com/v8/finance/chart/"
        params = urllib.parse.urlencode({"USDTRY": "X"})
        req = url + params

        with urllib.request.urlopen(req) as f:
            data = json.loads(f.read().decode())

        self.yahoo = data["chart"]["result"][0]["meta"]["regularMarketPrice"]

    def _get_forbes(self):
        url = (
            "https://www.forbes.com/advisor/money-transfer/currency-converter/usd-try/?"
        )
        params = urllib.parse.urlencode({"amount": "1"})
        req = url + params

        with urllib.request.urlopen(req) as f:
            data = f.read().decode()

        soup = BeautifulSoup(data, "html.parser")

        self.forbes = soup.find_all("span", {"class": "amount"})[0].get_text()

    def _get_xe(self):
        url = "https://www.x-rates.com/calculator/?"
        params = urllib.parse.urlencode({"from": "USD", "to": "TRY", "amount": "1"})
        req = url + params

        with urllib.request.urlopen(req) as f:
            data = f.read().decode()

        soup = BeautifulSoup(data, "html.parser")

        self.xe = (
            soup.find_all("span", {"class": "ccOutputRslt"})[0].get_text().split(" ")[0]
        )

    def _get_binance(self):
        url = "https://api.binance.com/api/v3/ticker/price?"
        params = urllib.parse.urlencode({"symbol": "USDTTRY"})
        req = url + params

        with urllib.request.urlopen(req) as f:
            data = f.read().decode()

        self.binance = float(json.loads(data)["price"].rstrip("0"))

    def _get_wgb(self):
        req = "http://www.worldgovernmentbonds.com/cds-historical-data/turkey/5-years/"

        with urllib.request.urlopen(req) as f:
            data = f.read().decode()

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

    def collect(self):
        self._get_tcmb()
        self._get_yahoo()
        self._get_forbes()
        self._get_xe()
        self._get_binance()
        self._get_wgb()
