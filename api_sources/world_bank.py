"""
World Bank API Source - Global development data
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

from api_sources import BaseAPISource


class WorldBankSource(BaseAPISource):
    """World Bank API data source"""

    def __init__(self, api_key=None):
        super().__init__(api_key, "https://api.worldbank.org/v2")

    def get_schema(self):
        return {
            "tables": {
                "indicators": {
                    "columns": [
                        {"name": "country", "type": "string"},
                        {"name": "year", "type": "integer"},
                        {"name": "indicator", "type": "string"},
                        {"name": "value", "type": "float"},
                        {"name": "countryiso3code", "type": "string"}
                    ],
                    "row_count": 100
                }
            }
        }

    def run_query(self, sql):
        table, params, limit = self._parse_simple_select(sql)
        if not table:
            return []

        if table == "indicators":
            return self._fetch_indicators(params, limit)

        return []

    def _fetch_indicators(self, params, limit):
        """Fetch World Bank indicators"""
        url = f"{self.base_url}/en/indicator/NY.GDP.MKTP.CD"

        query_params = {"format": "json", "per_page": min(limit, 100)}

        if "country" in params:
            query_params["country"] = params["country"]

        if "year" in params:
            url = f"{self.base_url}/country/{params['country']}/indicator/NY.GDP.MKTP.CD"
            query_params["date"] = params["year"]

        try:
            response = requests.get(url, params=query_params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 1:
                    results = []
                    for item in data[1][:limit]:
                        results.append({
                            "country": item.get("country", {}).get("value", ""),
                            "year": item.get("date", ""),
                            "indicator": item.get("indicator", {}).get("value", ""),
                            "value": item.get("value"),
                            "countryiso3code": item.get("countryiso3code", "")
                        })
                    return results
        except Exception as e:
            print(f"World Bank API error: {e}")

        return []