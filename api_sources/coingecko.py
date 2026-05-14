"""
CoinGecko API Source - Cryptocurrency market data
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

from api_sources import BaseAPISource


class CoinGeckoSource(BaseAPISource):
    """CoinGecko cryptocurrency data source"""

    def __init__(self, api_key=None):
        super().__init__(api_key or os.getenv("COINGECKO_API_KEY"), "https://api.coingecko.com/api/v3")
        # CoinGecko doesn't require API key for basic endpoints

    def get_schema(self):
        return {
            "tables": {
                "coins": {
                    "columns": [
                        {"name": "id", "type": "string"},
                        {"name": "symbol", "type": "string"},
                        {"name": "name", "type": "string"},
                        {"name": "current_price", "type": "float"},
                        {"name": "market_cap", "type": "float"},
                        {"name": "total_volume", "type": "float"},
                        {"name": "price_change_24h", "type": "float"},
                        {"name": "price_change_percentage_24h", "type": "float"},
                        {"name": "last_updated", "type": "datetime"}
                    ],
                    "row_count": 100
                },
                "prices": {
                    "columns": [
                        {"name": "coin", "type": "string"},
                        {"name": "price", "type": "float"},
                        {"name": "change_24h", "type": "float"}
                    ],
                    "row_count": 10
                }
            }
        }

    def run_query(self, sql):
        table, params, limit = self._parse_simple_select(sql)
        if not table:
            return []

        if table == "coins":
            return self._fetch_coins(limit)
        elif table == "prices":
            return self._fetch_prices(params)

        return []

    def _fetch_coins(self, limit):
        """Fetch top cryptocurrencies by market cap"""
        url = f"{self.base_url}/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": min(limit, 100),
            "page": 1,
            "sparkline": "false"
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                results = []
                for coin in data[:limit]:
                    results.append({
                        "id": coin.get("id", ""),
                        "symbol": coin.get("symbol", ""),
                        "name": coin.get("name", ""),
                        "current_price": coin.get("current_price"),
                        "market_cap": coin.get("market_cap"),
                        "total_volume": coin.get("total_volume"),
                        "price_change_24h": coin.get("price_change_24h"),
                        "price_change_percentage_24h": coin.get("price_change_percentage_24h"),
                        "last_updated": coin.get("last_updated")
                    })
                return results

        except Exception as e:
            print(f"CoinGecko API error: {e}")

        return []

    def _fetch_prices(self, params):
        """Fetch simple price for specific coins"""
        url = f"{self.base_url}/simple/price"
        coin_ids = params.get("id", "bitcoin,ethereum").split(",")

        query_params = {
            "ids": ",".join(coin_ids),
            "vs_currencies": "usd",
            "include_24hr_change": "true"
        }

        try:
            response = requests.get(url, params=query_params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                results = []
                for coin, prices in data.items():
                    results.append({
                        "coin": coin,
                        "price": prices.get("usd"),
                        "change_24h": prices.get("usd_24h_change")
                    })
                return results

        except Exception as e:
            print(f"CoinGecko API error: {e}")

        return []