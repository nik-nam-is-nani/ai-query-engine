"""
NASA API Source - Planetary data from NASA Open API
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

from api_sources import BaseAPISource


class NASAAPISource(BaseAPISource):
    """NASA Open API data source"""

    def __init__(self, api_key=None):
        super().__init__(api_key or os.getenv("NASA_API_KEY"), "https://api.nasa.gov")
        self.api_key = self.api_key or "DEMO_KEY"

    def get_schema(self):
        return {
            "tables": {
                "apod": {
                    "columns": [
                        {"name": "date", "type": "date"},
                        {"name": "title", "type": "string"},
                        {"name": "explanation", "type": "string"},
                        {"name": "url", "type": "string"},
                        {"name": "hdurl", "type": "string"},
                        {"name": "media_type", "type": "string"},
                        {"name": "copyright", "type": "string"}
                    ],
                    "row_count": 1
                }
            }
        }

    def run_query(self, sql):
        table, params, limit = self._parse_simple_select(sql)
        if not table:
            return []

        if table == "apod":
            return self._fetch_apod(params, limit)

        return []

    def _fetch_apod(self, params, limit):
        """Fetch Astronomy Picture of the Day"""
        url = f"{self.base_url}/planetary/apod"

        query_params = {"api_key": self.api_key}

        if "date" in params:
            query_params["date"] = params["date"]

        try:
            response = requests.get(url, params=query_params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    return data[:limit]
                return [data]
        except Exception as e:
            print(f"NASA API error: {e}")

        return []