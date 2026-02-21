"""
AI SQL Studio - Flask Backend API Server
"""
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import mysql.connector
import os

# Import the NL2SQL modules
from nl2sql_universal import generate_sql_and_execute
from nlp_preprocessor import preprocess_query

app = Flask(__name__, static_folder='dashboard', static_url_path='')
CORS(app)

# Database configuration
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "pandu"
}

# Store current connection state
current_db = {"name": None, "connected": False}

def get_db_connection(db_name=None):
    """Get database connection"""
    try:
        conn = mysql.connector.connect(
            host=DB_CONFIG["host"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            database=db_name
        )
        return conn
    except mysql.connector.Error as e:
        print(f"MySQL Error: {e}")
        return None
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

@app.route('/')
def index():
    """Serve the dashboard"""
    return send_from_directory('.', 'dashboard/index.html')

# ============================================
# API ENDPOINTS
# ============================================

@app.route('/api/databases', methods=['GET'])
def get_databases():
    """Get list of available databases"""
    try:
        conn = get_db_connection(None)
        if not conn:
            return jsonify({"success": False, "error": "Could not connect to MySQL"}), 500
        
        cursor = conn.cursor()
        cursor.execute("SHOW DATABASES")
        databases = [db[0] for db in cursor.fetchall() if db[0] not in ('information_schema', 'mysql', 'performance_schema', 'sys')]
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "databases": databases
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/connect', methods=['GET'])
def connect_db():
    """Connect to a specific database"""
    db_name = request.args.get('db', '')
    
    if not db_name:
        return jsonify({"success": False, "error": "No database name provided"}), 400
    
    try:
        print(f"Attempting to connect to database: {db_name}")
        conn = get_db_connection(db_name)
        if not conn:
            current_db["name"] = None
            current_db["connected"] = False
            return jsonify({
                "success": False,
                "error": "Could not connect to database",
                "connected": False
            }), 500
        
        # Test connection
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT 1")
            # mysql-connector requires consuming results before closing the cursor/connection
            cursor.fetchone()
        finally:
            cursor.close()
            conn.close()
        
        current_db["name"] = db_name
        current_db["connected"] = True
        
        return jsonify({
            "success": True,
            "database": db_name,
            "connected": True,
            "message": f"Successfully connected to {db_name}"
        })
        
    except Exception as e:
        print(f"Connection error: {e}")
        current_db["name"] = None
        current_db["connected"] = False
        return jsonify({
            "success": False,
            "error": str(e),
            "connected": False
        }), 500


@app.route('/api/tables', methods=['GET'])
def get_tables():
    """Get tables for current or specified database"""
    db_name = request.args.get('db') or current_db.get('name')
    
    if not db_name or not current_db.get('connected'):
        return jsonify({"success": False, "error": "Not connected to any database"}), 400
    
    try:
        conn = get_db_connection(db_name)
        if not conn:
            return jsonify({"success": False, "error": "Could not connect to database"}), 500
        
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES")
        tables = [t[0] for t in cursor.fetchall()]
        
        # Get table schemas
        schemas = {}
        for table in tables:
            cursor.execute(f"DESCRIBE {table}")
            columns = [{"name": col[0], "type": col[1]} for col in cursor.fetchall()]
            schemas[table] = columns
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "tables": tables,
            "schemas": schemas,
            "database": db_name
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/table-data', methods=['GET'])
def get_table_data():
    """Get data from a specific table"""
    db_name = request.args.get('db') or current_db.get('name')
    table_name = request.args.get('name', '')
    limit = int(request.args.get('limit', 100))
    
    if not db_name or not current_db.get('connected'):
        return jsonify({"success": False, "error": "Not connected to any database"}), 400
    
    if not table_name:
        return jsonify({"success": False, "error": "No table name provided"}), 400
    
    try:
        conn = get_db_connection(db_name)
        if not conn:
            return jsonify({"success": False, "error": "Could not connect to database"}), 500
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute(f"SELECT * FROM {table_name} LIMIT {limit}")
        results = cursor.fetchall()
        
        # Get column info
        columns = list(results[0].keys()) if results else []
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "data": results,
            "columns": columns,
            "table": table_name,
            "count": len(results)
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/generate-sql', methods=['POST'])
def generate_sql():
    """Generate SQL from natural language"""
    try:
        data = request.json
        query = data.get('query', '')
        database = data.get('database') or current_db.get('name')
        
        if not query:
            return jsonify({"success": False, "error": "No query provided"}), 400
        
        if not database or not current_db.get('connected'):
            return jsonify({"success": False, "error": "Please connect to a database first"}), 400
        
        # Preprocess the query
        clean_q = preprocess_query(query)
        
        # Generate SQL
        sql = generate_sql_and_execute(database, clean_q)
        
        if sql:
            return jsonify({
                "success": True,
                "sql": sql,
                "query": query
            })
        else:
            return jsonify({
                "success": False,
                "error": "Could not generate SQL for this query"
            }), 400
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/run-query', methods=['POST'])
def run_query():
    """Execute SQL query"""
    conn = None
    cursor = None
    try:
        data = request.json or {}
        sql = (data.get('sql') or '').strip()
        database = data.get('database') or current_db.get('name')

        if not sql:
            return jsonify({"success": False, "error": "No SQL provided"}), 400

        if not database or not current_db.get('connected'):
            return jsonify({"success": False, "error": "Please connect to a database first"}), 400

        conn = get_db_connection(database)
        if not conn:
            return jsonify({
                "success": False,
                "error": "Could not connect to database"
            }), 500

        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql)

        if cursor.with_rows:
            results = cursor.fetchall()
            columns = list(cursor.column_names) if cursor.column_names else []
            return jsonify({
                "success": True,
                "results": results,
                "columns": columns,
                "row_count": len(results)
            })

        conn.commit()
        return jsonify({
            "success": True,
            "results": [],
            "columns": [],
            "row_count": cursor.rowcount,
            "message": "Statement executed successfully"
        })

    except mysql.connector.Error as e:
        # SQL/user errors should be surfaced to the UI (not a 500)
        return jsonify({
            "success": False,
            "error": e.msg or str(e),
            "mysql_errno": getattr(e, "errno", None),
            "mysql_sqlstate": getattr(e, "sqlstate", None)
        }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


if __name__ == '__main__':
    print("=" * 50)
    print("AI SQL Studio API Server")
    print("=" * 50)
    print("Server running at: http://localhost:5000")
    print("Dashboard: http://localhost:5000")
    print("=" * 50)
    app.run(debug=True, port=5000, host='0.0.0.0')
