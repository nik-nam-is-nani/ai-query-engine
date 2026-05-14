"""
Custom REST API Source - Generic REST API adapter
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

from api_sources import BaseAPISource


class CustomRESTAdapter(BaseAPISource):
    """Generic REST API adapter that auto-detects response structure"""

    def __init__(self, base_url, api_key=None, headers=None):
        super().__init__(api_key, base_url)
        self.custom_headers = headers or {}

    def get_schema(self):
        # Try to fetch sample data and infer schema
        schema = {"tables": {}}

        headers = self.custom_headers.copy()
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            response = requests.get(self.base_url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()

                if isinstance(data, list) and len(data) > 0:
                    # Array response
                    table_name = "api_data"
                    columns = []
                    if isinstance(data[0], dict):
                        for key, value in data[0].items():
                            col_type = self._infer_type(value)
                            columns.append({"name": key, "type": col_type})

                    schema["tables"][table_name] = {
                        "columns": columns,
                        "row_count": len(data)
                    }

                elif isinstance(data, dict):
                    # Object response - might contain nested arrays
                    for key, value in data.items():
                        if isinstance(value, list) and len(value) > 0:
                            table_name = key
                            columns = []
                            if isinstance(value[0], dict):
                                for col_key, col_val in value[0].items():
                                    col_type = self._infer_type(col_val)
                                    columns.append({"name": col_key, "type": col_type})

                            schema["tables"][table_name] = {
                                "columns": columns,
                                "row_count": len(value)
                            }

        except Exception as e:
            print(f"Custom REST API schema error: {e}")

        return schema

    def run_query(self, sql):
        table, params, limit = self._parse_simple_select(sql)
        if not table:
            return []

        headers = self.custom_headers.copy()
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            # Determine URL
            if table == "api_data":
                url = self.base_url
            else:
                url = f"{self.base_url}/{table}"

            # Merge params
            if params:
                response = requests.get(url, headers=headers, params=params, timeout=10)
            else:
                response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()

                # Find the data array
                if isinstance(data, list):
                    return data[:limit]
                elif isinstance(data, dict):
                    if table in data and isinstance(data[table], list):
                        return data[table][:limit]
                    # Find any list value
                    for key, value in data.items():
                        if isinstance(value, list):
                            return value[:limit]

        except Exception as e:
            print(f"Custom REST API query error: {e}")

        return []

    def _infer_type(self, value):
        """Infer column type from value"""
        if isinstance(value, bool):
            return "boolean"
        elif isinstance(value, int):
            return "integer"
        elif isinstance(value, float):
            return "float"
        return "string"