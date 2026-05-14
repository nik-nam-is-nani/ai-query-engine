"""
BaseAPISource - Abstract base class for API data sources
"""
from abc import ABC, abstractmethod


class BaseAPISource(ABC):
    """Base class for API data sources"""

    def __init__(self, api_key=None, base_url=None):
        self.api_key = api_key
        self.base_url = base_url

    @abstractmethod
    def get_schema(self):
        """Return schema dict with tables, columns, types"""
        pass

    @abstractmethod
    def run_query(self, sql):
        """Execute query and return results as list of dicts"""
        pass

    def _parse_simple_select(self, sql):
        """Parse simple SELECT * FROM table [WHERE condition] [LIMIT n]"""
        import re

        # Basic parsing
        match = re.match(r'SELECT\s+\*\s+FROM\s+(\w+)(?:\s+WHERE\s+(.+?))?(?:\s+LIMIT\s+(\d+))?', sql, re.IGNORECASE)

        if not match:
            return None, None, None

        table = match.group(1)
        where = match.group(2)
        limit = int(match.group(3)) if match.group(3) else 100

        # Parse WHERE conditions
        params = {}
        if where:
            # Simple key=value parsing
            conditions = re.split(r'\s+AND\s+', where, flags=re.IGNORECASE)
            for cond in conditions:
                if '=' in cond:
                    parts = cond.split('=')
                    key = parts[0].strip()
                    value = parts[1].strip().strip("'\"")
                    params[key] = value

        return table, params, limit