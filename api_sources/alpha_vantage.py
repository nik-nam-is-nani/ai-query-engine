"""
Alpha Vantage API Source - Financial market data
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

from api_sources import BaseAPISource


class AlphaVantageSource(BaseAPISource):
    """Alpha Vantage financial data source"""

    def __init__(self, api_key=None):
        super().__init__(api_key or os.getenv("ALPHA_VANTAGE_API_KEY"), "https://www.alphavantage.co/query")
        self.api_key = self.api_key or "demo"

    def get_schema(self):
        return {
            "tables": {
                "daily_prices": {
                    "columns": [
                        {"name": "date", "type": "date"},
                        {"name": "open", "type": "float"},
                        {"name": "high", "type": "float"},
                        {"name": "low", "type": "float"},
                        {"name": "close", "type": "float"},
                        {"name": "volume", "type": "integer"}
                    ],
                    "row_count": 100
                },
                "global_quote": {
                    "columns": [
                        {"name": "symbol", "type": "string"},
                        {"name": "price", "type": "float"},
                        {"name": "volume", "type": "integer"},
                        {"name": "change", "type": "float"},
                        {"name": "change_percent", "type": "float"}
                    ],
                    "row_count": 1
                }
            }
        }

    def run_query(self, sql):
        table, params, limit = self._parse_simple_select(sql)
        if not table:
            return []

        if table == "daily_prices":
            return self._fetch_daily(params, limit)
        elif table == "global_quote":
            return self._fetch_quote(params)

        return []

    def _fetch_daily(self, params, limit):
        """Fetch daily stock prices"""
        url = self.base_url
        query_params = {
            "function": "TIME_SERIES_DAILY",
            "apikey": self.api_key,
            "outputsize": "compact"
        }

        if "symbol" in params:
            query_params["symbol"] = params["symbol"]

        try:
            response = requests.get(url, params=query_params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                time_series = data.get("Time Series (Daily)", {})

                results = []
                for date, values in list(time_series.items())[:limit]:
                    results.append({
                        "date": date,
                        "open": float(values.get("1. open", 0)),
                        "high": float(values.get("2. high", 0)),
                        "low": float(values.get("3. low", 0)),
                        "close": float(values.get("4. close", 0)),
                        "volume": int(values.get("5. volume", 0))
                    })

                return results

        except Exception as e:
            print(f"Alpha Vantage API error: {e}")

        return []

    def _fetch_quote(self, params):
        """Fetch global quote for a symbol"""
        url = self.base_url
        query_params = {
            "function": "GLOBAL_QUOTE",
            "apikey": self.api_key,
            "symbol": params.get("symbol", "IBM")
        }

        try:
            response = requests.get(url, params=query_params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                quote = data.get("Global Quote", {})

                return [{
                    "symbol": quote.get("01. symbol", ""),
                    "price": float(quote.get("05. price", 0)),
                    "volume": int(quote.get("06. volume", 0)),
                    "change": float(quote.get("09. change", 0)),
                    "change_percent": quote.get("10. change percent", "")
                }]

        except Exception as e:
            print(f"Alpha Vantage API error: {e}")

        return []