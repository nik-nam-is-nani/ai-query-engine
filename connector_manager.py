"""
Connector Manager - Database connection management with schema discovery
"""
import uuid
import threading
import mysql.connector
import psycopg2
import sqlite3
import requests
from abc import ABC, abstractmethod
from dotenv import load_dotenv

load_dotenv(override=True)

# Thread-safe session store
SESSION_STORE = {}
SESSION_LOCK = threading.Lock()


class BaseConnector(ABC):
    """Abstract base class for all database connectors"""

    @abstractmethod
    def connect(self, **kwargs):
        """Establish connection to the database"""
        pass

    @abstractmethod
    def get_schema(self):
        """Return schema dict with tables, columns, types"""
        pass

    @abstractmethod
    def run_query(self, sql):
        """Execute SQL query and return results"""
        pass

    @abstractmethod
    def get_query_plan(self, sql):
        """Return query execution plan"""
        pass

    @abstractmethod
    def disconnect(self):
        """Close the connection"""
        pass


class MySQLConnector(BaseConnector):
    def __init__(self):
        self.conn = None
        self.config = {}

    def connect(self, host, port, user, password, database):
        self.config = {"host": host, "port": port, "user": user, "password": password, "database": database}
        self.conn = mysql.connector.connect(**self.config)
        return self.conn

    def get_schema(self):
        schema = {"tables": {}}
        relationship_graph = {"nodes": [], "edges": []}

        cursor = self.conn.cursor()
        cursor.execute("SHOW TABLES")
        tables = [t[0] for t in cursor.fetchall()]

        for table in tables:
            # Get columns
            cursor.execute(f"DESCRIBE {table}")
            columns = []
            for col in cursor.fetchall():
                columns.append({
                    "name": col[0],
                    "type": col[1],
                    "nullable": col[2] == "YES",
                    "key": col[3],
                    "default": col[4],
                    "extra": col[5]
                })

            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
            row_count = cursor.fetchone()[0]

            schema["tables"][table] = {
                "columns": columns,
                "row_count": row_count
            }
            relationship_graph["nodes"].append({"id": table, "label": table, "type": "table"})

            # Find foreign keys
            cursor.execute(f"""
                SELECT COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
                FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND REFERENCED_TABLE_NAME IS NOT NULL
            """, (self.config.get("database"), table))
            fks = cursor.fetchall()
            for fk in fks:
                relationship_graph["edges"].append({
                    "from": table,
                    "to": fk[1],
                    "label": f"{fk[0]} → {fk[2]}"
                })

        cursor.close()
        return schema, relationship_graph

    def run_query(self, sql):
        cursor = self.conn.cursor(dictionary=True)
        cursor.execute(sql)
        results = cursor.fetchall() if cursor.with_rows else []
        cursor.close()
        return results

    def get_query_plan(self, sql):
        cursor = self.conn.cursor()
        cursor.execute(f"EXPLAIN {sql}")
        plan = cursor.fetchall()
        cursor.close()
        return plan

    def disconnect(self):
        if self.conn:
            self.conn.close()


class PostgreSQLConnector(BaseConnector):
    def __init__(self):
        self.conn = None
        self.config = {}

    def connect(self, host, port, user, password, database):
        self.config = {
            "host": host,
            "port": port or 5432,
            "user": user,
            "password": password,
            "database": database
        }
        self.conn = psycopg2.connect(**self.config)
        return self.conn

    def get_schema(self):
        schema = {"tables": {}}
        relationship_graph = {"nodes": [], "edges": []}

        cursor = self.conn.cursor()

        # Get tables
        cursor.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        """)
        tables = [t[0] for t in cursor.fetchall()]

        for table in tables:
            # Get columns
            cursor.execute(f"""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = %s
            """, (table,))
            columns = []
            for col in cursor.fetchall():
                columns.append({
                    "name": col[0],
                    "type": col[1],
                    "nullable": col[2] == "YES",
                    "default": col[3]
                })

            # Get row count
            cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
            row_count = cursor.fetchone()[0]

            schema["tables"][table] = {
                "columns": columns,
                "row_count": row_count
            }
            relationship_graph["nodes"].append({"id": table, "label": table, "type": "table"})

            # Get foreign keys
            cursor.execute(f"""
                SELECT
                    kcu.column_name,
                    ccu.table_name AS foreign_table,
                    ccu.column_name AS foreign_column
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu ON ccu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_name = %s
            """, (table,))
            fks = cursor.fetchall()
            for fk in fks:
                relationship_graph["edges"].append({
                    "from": table,
                    "to": fk[1],
                    "label": f"{fk[0]} → {fk[2]}"
                })

        cursor.close()
        return schema, relationship_graph

    def run_query(self, sql):
        cursor = self.conn.cursor(dictionary=True)
        cursor.execute(sql)
        results = cursor.fetchall() if cursor.with_rows else []
        cursor.close()
        return results

    def get_query_plan(self, sql):
        cursor = self.conn.cursor()
        cursor.execute(f"EXPLAIN {sql}")
        plan = cursor.fetchall()
        cursor.close()
        return plan

    def disconnect(self):
        if self.conn:
            self.conn.close()


class SQLiteConnector(BaseConnector):
    def __init__(self):
        self.conn = None

    def connect(self, database_path):
        self.conn = sqlite3.connect(database_path)
        return self.conn

    def get_schema(self):
        schema = {"tables": {}}
        relationship_graph = {"nodes": [], "edges": []}

        cursor = self.conn.cursor()

        # Get tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [t[0] for t in cursor.fetchall()]

        for table in tables:
            # Get columns
            cursor.execute(f'PRAGMA table_info("{table}")')
            columns = []
            for col in cursor.fetchall():
                columns.append({
                    "name": col[1],
                    "type": col[2],
                    "nullable": not col[3],
                    "default": col[4],
                    "pk": col[5]
                })

            # Get row count
            cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
            row_count = cursor.fetchone()[0]

            schema["tables"][table] = {
                "columns": columns,
                "row_count": row_count
            }
            relationship_graph["nodes"].append({"id": table, "label": table, "type": "table"})

            # Get foreign keys
            cursor.execute(f'PRAGMA foreign_key_list("{table}")')
            fks = cursor.fetchall()
            for fk in fks:
                relationship_graph["edges"].append({
                    "from": table,
                    "to": fk[2],
                    "label": f"{fk[3]} → {fk[4]}"
                })

        cursor.close()
        return schema, relationship_graph

    def run_query(self, sql):
        cursor = self.conn.cursor()
        cursor.execute(sql)
        results = cursor.fetchall()
        columns = [description[0] for description in cursor.description] if cursor.description else []
        cursor.close()
        return [dict(zip(columns, row)) for row in results] if columns else results

    def get_query_plan(self, sql):
        cursor = self.conn.cursor()
        cursor.execute(f"EXPLAIN QUERY PLAN {sql}")
        plan = cursor.fetchall()
        cursor.close()
        return plan

    def disconnect(self):
        if self.conn:
            self.conn.close()


class RESTConnector(BaseConnector):
    def __init__(self):
        self.api_url = None
        self.api_key = None
        self.source_name = None

    def connect(self, api_url, api_key, source_name):
        self.api_url = api_url
        self.api_key = api_key
        self.source_name = source_name

    def get_schema(self):
        # Try to fetch sample data and infer schema
        schema = {"tables": {}}
        relationship_graph = {"nodes": [], "edges": []}

        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            response = requests.get(self.api_url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()

                # Handle different response formats
                if isinstance(data, list) and len(data) > 0:
                    # It's an array, treat as single table
                    table_name = self.source_name or "api_data"
                    columns = []
                    if isinstance(data[0], dict):
                        for key, value in data[0].items():
                            col_type = "string"
                            if isinstance(value, int):
                                col_type = "integer"
                            elif isinstance(value, float):
                                col_type = "float"
                            elif isinstance(value, bool):
                                col_type = "boolean"
                            columns.append({"name": key, "type": col_type})

                    schema["tables"][table_name] = {
                        "columns": columns,
                        "row_count": len(data)
                    }
                    relationship_graph["nodes"].append({"id": table_name, "label": table_name, "type": "api"})

                elif isinstance(data, dict):
                    # Multiple endpoints or nested data
                    for key, value in data.items():
                        if isinstance(value, list) and len(value) > 0:
                            table_name = key
                            columns = []
                            if isinstance(value[0], dict):
                                for col_key, col_val in value[0].items():
                                    col_type = "string"
                                    if isinstance(col_val, int):
                                        col_type = "integer"
                                    elif isinstance(col_val, float):
                                        col_type = "float"
                                    elif isinstance(col_val, bool):
                                        col_type = "boolean"
                                    columns.append({"name": col_key, "type": col_type})

                            schema["tables"][table_name] = {
                                "columns": columns,
                                "row_count": len(value)
                            }
                            relationship_graph["nodes"].append({"id": table_name, "label": table_name, "type": "api"})

        except Exception as e:
            print(f"Error fetching API schema: {e}")

        return schema, relationship_graph

    def run_query(self, sql):
        # Basic SQL to API mapping - simplified
        # Parse SELECT * FROM table WHERE column = value
        import re
        match = re.match(r'SELECT\s+\*\s+FROM\s+(\w+)(?:\s+WHERE\s+(.+?))?(?:\s+LIMIT\s+(\d+))?', sql, re.IGNORECASE)

        if not match:
            return []

        table_name = match.group(1)
        where_clause = match.group(2)
        limit = int(match.group(3)) if match.group(3) else 100

        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        params = {}
        if where_clause:
            # Simple WHERE parsing
            if "=" in where_clause:
                col, val = where_clause.split("=", 1)
                params[col.strip()] = val.strip().strip("'\"")

        try:
            response = requests.get(self.api_url, headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    return data[:limit]
        except Exception as e:
            print(f"API query error: {e}")

        return []

    def get_query_plan(self, sql):
        return [{"operation": "API fetch", "details": "REST API call"}]

    def disconnect(self):
        pass


def create_connection(connection_type, config):
    """Factory function to create appropriate connector"""
    connectors = {
        "MySQL": MySQLConnector,
        "PostgreSQL": PostgreSQLConnector,
        "Postgres": PostgreSQLConnector,
        "SQLite": SQLiteConnector,
        "REST API": RESTConnector
    }

    connector_class = connectors.get(connection_type)
    if not connector_class:
        raise ValueError(f"Unsupported connection type: {connection_type}")

    return connector_class()


def connect_universal(data):
    """
    Universal connection endpoint handler.
    Accepts database or API connection config.
    Returns connection_id, schema, relationship_graph.
    """
    conn_type = data.get("type", "")

    connector = create_connection(conn_type, data)
    connection_id = str(uuid.uuid4())

    # Connect based on type
    if conn_type == "MySQL":
        connector.connect(
            host=data.get("host"),
            port=data.get("port", 3306),
            user=data.get("user"),
            password=data.get("password"),
            database=data.get("database")
        )
    elif conn_type == "PostgreSQL" or conn_type == "Postgres":
        connector.connect(
            host=data.get("host"),
            port=data.get("port", 5432),
            user=data.get("user"),
            password=data.get("password"),
            database=data.get("database")
        )
    elif conn_type == "SQLite":
        connector.connect(data.get("database"))
    elif conn_type == "REST API":
        connector.connect(
            api_url=data.get("api_url"),
            api_key=data.get("api_key"),
            source_name=data.get("source_name")
        )

    # Get schema
    schema, relationship_graph = connector.get_schema()

    # Store in session
    with SESSION_LOCK:
        SESSION_STORE[connection_id] = {
            "type": conn_type.lower(),
            "connector": connector,
            "schema": schema,
            "relationship_graph": relationship_graph,
            "nickname": data.get("source_name") or data.get("database", "Untitled"),
            "created_at": str(uuid.uuid1())
        }

    return {
        "connection_id": connection_id,
        "status": "connected",
        "schema": schema,
        "relationship_graph": relationship_graph
    }


def get_connector(connection_id):
    """Get connector from session store"""
    with SESSION_LOCK:
        session = SESSION_STORE.get(connection_id)
        return session["connector"] if session else None


def get_schema(connection_id):
    """Get schema from session store"""
    with SESSION_LOCK:
        session = SESSION_STORE.get(connection_id)
        return session["schema"] if session else None


def remove_connection(connection_id):
    """Remove connection from session store"""
    with SESSION_LOCK:
        if connection_id in SESSION_STORE:
            session = SESSION_STORE[connection_id]
            if "connector" in session:
                try:
                    session["connector"].disconnect()
                except:
                    pass
            del SESSION_STORE[connection_id]
            return True
    return False