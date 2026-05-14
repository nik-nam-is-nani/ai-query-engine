"""
AI SQL Studio - Flask Backend API Server
Complete version with all endpoints
"""
import os
import json
import threading
from flask import Flask, request, jsonify, Response, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

# Load environment variables
load_dotenv(override=True)

app = Flask(__name__, static_folder='dashboard', static_url_path='')
CORS(app)

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max upload
UPLOADS_DIR = "uploads"
os.makedirs(UPLOADS_DIR, exist_ok=True)

# Import modules
from connector_manager import (
    SESSION_STORE, SESSION_LOCK,
    connect_universal, get_connector, get_schema, remove_connection
)
from runtime_engine import (
    JOB_STORE, JOB_LOCK,
    submit_job, get_job, cancel_job, start_workers, get_stream_generator
)
from realtime_monitor import start_monitor, get_metrics
from csv_analyzer import analyze_csv
from api_nl2sql import generate_sql
from xai_engine import explain_endpoint
from autocomplete import autocomplete
from recommender import recommend
from viz_recommender import recommend_viz
from precommands import save_command, list_commands, run_command


# =============================
# STARTUP
# =============================
def initialize_app():
    """Initialize app on startup"""
    print("=" * 50)
    print("AI SQL Studio - Starting Backend")
    print("=" * 50)

    # Start workers
    start_workers()

    # Start monitor
    start_monitor()

    print("Server ready at http://localhost:5000")
    print("=" * 50)


# =============================
# ERROR HANDLING
# =============================
def error_response(message, code, http_status=400):
    """Standard error response format"""
    return jsonify({
        "error": True,
        "message": message,
        "code": code
    }), http_status


# =============================
# ROUTES
# =============================

@app.route('/')
def index():
    """Serve the dashboard"""
    return send_from_directory('.', 'dashboard/index.html')


# ---- Connection Management ----

@app.route('/api/connect-universal', methods=['POST'])
def connect_universal_route():
    """Connect to database or API source"""
    try:
        data = request.json

        if not data or not data.get('type'):
            return error_response("Missing connection type", "INVALID_INPUT", 400)

        result = connect_universal(data)

        return jsonify(result)

    except Exception as e:
        print(f"Connection error: {e}")
        return error_response(str(e), "CONNECTION_FAILED", 500)


@app.route('/api/disconnect', methods=['POST'])
def disconnect_route():
    """Disconnect from a source"""
    try:
        data = request.json
        connection_id = data.get('connection_id')

        if not connection_id:
            return error_response("Missing connection_id", "INVALID_INPUT", 400)

        removed = remove_connection(connection_id)
        if removed:
            return jsonify({"success": True})
        else:
            return error_response("Connection not found", "NOT_FOUND", 404)

    except Exception as e:
        return error_response(str(e), "INTERNAL_ERROR", 500)


# ---- CSV Upload ----

@app.route('/api/upload-csv', methods=['POST'])
def upload_csv_route():
    """Upload and analyze CSV file"""
    try:
        if 'file' not in request.files:
            return error_response("No file provided", "INVALID_INPUT", 400)

        file = request.files['file']
        if not file.filename:
            return error_response("Empty file", "INVALID_INPUT", 400)

        # Analyze CSV
        result = analyze_csv(file)

        # Store in session
        source_id = result["source_id"]
        with SESSION_LOCK:
            SESSION_STORE[source_id] = {
                "type": "csv",
                "connector": result.get("connector"),
                "schema": result["schema"],
                "relationship_graph": {"nodes": [], "edges": []},
                "nickname": file.filename.replace(".csv", ""),
                "created_at": str(source_id)
            }

        return jsonify({
            "source_id": source_id,
            "filename": result["filename"],
            "schema": result["schema"],
            "preview_rows": result["preview_rows"],
            "column_stats": result["column_stats"],
            "starter_queries": result["starter_queries"]
        })

    except Exception as e:
        print(f"CSV upload error: {e}")
        return error_response(str(e), "UPLOAD_FAILED", 500)


# ---- SQL Generation ----

@app.route('/api/generate-sql', methods=['POST'])
def generate_sql_route():
    """Generate SQL from natural language"""
    try:
        data = request.json
        nl_query = data.get('nl_query', '')
        source_id = data.get('source_id')

        if not nl_query:
            return error_response("Missing nl_query", "INVALID_INPUT", 400)

        if not source_id:
            return error_response("Missing source_id", "INVALID_INPUT", 400)

        # Get schema
        schema = get_schema(source_id)
        if not schema:
            return error_response("Source not found", "NOT_FOUND", 404)

        # Generate SQL
        result = generate_sql(nl_query, source_id, schema)

        return jsonify(result)

    except Exception as e:
        print(f"SQL generation error: {e}")
        return error_response(str(e), "GENERATION_FAILED", 500)


# ---- Query Execution ----

@app.route('/api/run-query', methods=['POST'])
def run_query_route():
    """Execute SQL query asynchronously"""
    try:
        data = request.json
        sql = data.get('sql', '')
        source_id = data.get('source_id')

        if not sql:
            return error_response("Missing SQL", "INVALID_INPUT", 400)

        if not source_id:
            return error_response("Missing source_id", "INVALID_INPUT", 400)

        # Submit job
        job_id = submit_job(sql, source_id)

        return jsonify({"job_id": job_id})

    except Exception as e:
        print(f"Query execution error: {e}")
        return error_response(str(e), "EXECUTION_FAILED", 500)


@app.route('/api/query-stream/<job_id>', methods=['GET'])
def query_stream_route(job_id):
    """SSE stream for query progress"""

    def generate():
        for data in get_stream_generator(job_id):
            yield data

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )


@app.route('/api/query-status/<job_id>', methods=['GET'])
def query_status_route(job_id):
    """Get query job status"""
    job = get_job(job_id)
    if not job:
        return error_response("Job not found", "NOT_FOUND", 404)

    return jsonify(job)


@app.route('/api/query/<job_id>', methods=['DELETE'])
def cancel_query_route(job_id):
    """Cancel a running query"""
    cancelled = cancel_job(job_id)
    if cancelled:
        return jsonify({"success": True, "message": "Query cancelled"})
    return error_response("Job not found", "NOT_FOUND", 404)


# ---- XAI Explanation ----

@app.route('/api/explain', methods=['POST'])
def explain_route():
    """Generate SQL explanation"""
    try:
        data = request.json
        nl_query = data.get('nl_query', '')
        sql = data.get('sql', '')
        schema = data.get('schema', {})

        if not nl_query or not sql:
            return error_response("Missing nl_query or sql", "INVALID_INPUT", 400)

        result = explain_endpoint(nl_query, sql, schema)
        return jsonify(result)

    except Exception as e:
        return error_response(str(e), "EXPLANATION_FAILED", 500)


# ---- Autocomplete ----

@app.route('/api/autocomplete', methods=['POST'])
def autocomplete_route():
    """Get autocomplete suggestion"""
    try:
        data = request.json
        partial = data.get('partial', '')
        source_id = data.get('source_id')

        if not partial:
            return jsonify({"suggestion": ""})

        if not source_id:
            return error_response("Missing source_id", "INVALID_INPUT", 400)

        schema = get_schema(source_id)
        if not schema:
            return error_response("Source not found", "NOT_FOUND", 404)

        result = autocomplete(partial, source_id, schema)
        return jsonify(result)

    except Exception as e:
        return error_response(str(e), "AUTOCOMPLETE_FAILED", 500)


# ---- Recommender ----

@app.route('/api/recommendations', methods=['POST'])
def recommendations_route():
    """Get follow-up query suggestions"""
    try:
        data = request.json
        last_query = data.get('last_query', '')
        result_summary = data.get('result_summary', {})
        schema = data.get('schema', {})

        result = recommend(last_query, result_summary, schema)
        return jsonify(result)

    except Exception as e:
        return error_response(str(e), "RECOMMENDATION_FAILED", 500)


# ---- Visualization Recommender ----

@app.route('/api/viz-recommend', methods=['POST'])
def viz_recommend_route():
    """Get visualization recommendations"""
    try:
        data = request.json
        columns = data.get('columns', [])
        sample_rows = data.get('sample_rows', [])

        result = recommend_viz(columns, sample_rows)
        return jsonify(result)

    except Exception as e:
        return error_response(str(e), "VIZ_RECOMMEND_FAILED", 500)


# ---- Precommands ----

@app.route('/api/precommands/list', methods=['GET'])
def precommands_list_route():
    """List all precommands"""
    try:
        commands = list_commands()
        return jsonify({"commands": commands})
    except Exception as e:
        return error_response(str(e), "PRECOMMAND_FAILED", 500)


@app.route('/api/precommands/save', methods=['POST'])
def precommands_save_route():
    """Save a precommand"""
    try:
        data = request.json
        title = data.get('title', '')
        template = data.get('template', '')
        variables = data.get('variables', [])
        source_type = data.get('source_type', 'general')

        if not title or not template:
            return error_response("Missing title or template", "INVALID_INPUT", 400)

        cmd_id = save_command(title, template, variables, source_type)
        return jsonify({"id": cmd_id, "success": True})

    except Exception as e:
        return error_response(str(e), "PRECOMMAND_FAILED", 500)


@app.route('/api/precommands/run', methods=['POST'])
def precommands_run_route():
    """Run a precommand"""
    try:
        data = request.json
        cmd_id = data.get('id')
        variables = data.get('variables', {})

        if not cmd_id:
            return error_response("Missing command id", "INVALID_INPUT", 400)

        result = run_command(cmd_id, variables)
        if result is None:
            return error_response("Command not found", "NOT_FOUND", 404)

        return jsonify({"result": result})

    except Exception as e:
        return error_response(str(e), "PRECOMMAND_FAILED", 500)


# ---- Session Metrics ----

@app.route('/api/session-metrics', methods=['GET'])
def session_metrics_route():
    """Get session metrics"""
    try:
        metrics = get_metrics()
        return jsonify(metrics)
    except Exception as e:
        return error_response(str(e), "METRICS_FAILED", 500)


# ---- Schema ----

@app.route('/api/schema/<source_id>', methods=['GET'])
def schema_route(source_id):
    """Get schema for a source"""
    schema = get_schema(source_id)
    if not schema:
        return error_response("Source not found", "NOT_FOUND", 404)

    return jsonify(schema)


# ---- API Sources ----

@app.route('/api/add-api-source', methods=['POST'])
def add_api_source_route():
    """Add external API source"""
    try:
        data = request.json
        source_type = data.get('source_type', '')
        source_name = data.get('source_name', '')
        api_key = data.get('api_key')
        base_url = data.get('base_url')

        if not source_type or not source_name:
            return error_response("Missing source_type or source_name", "INVALID_INPUT", 400)

        # Import and instantiate the correct source
        if source_type == "NASA Open Data":
            from api_sources.nasa import NASAAPISource
            source = NASAAPISource(api_key)
        elif source_type == "World Bank":
            from api_sources.world_bank import WorldBankSource
            source = WorldBankSource()
        elif source_type == "Alpha Vantage":
            from api_sources.alpha_vantage import AlphaVantageSource
            source = AlphaVantageSource(api_key)
        elif source_type == "CoinGecko":
            from api_sources.coingecko import CoinGeckoSource
            source = CoinGeckoSource(api_key)
        elif source_type == "REST API":
            from api_sources.custom_rest import CustomRESTAdapter
            source = CustomRESTAdapter(base_url, api_key)
        else:
            return error_response(f"Unknown source type: {source_type}", "INVALID_INPUT", 400)

        # Get schema
        schema = source.get_schema()
        if not schema.get("tables"):
            return error_response("Could not infer schema from API", "SCHEMA_INFERENCE_FAILED", 400)

        # Generate starter queries
        from llm_client import call_llm

        col_info = ""
        if "tables" in schema:
            for table, info in schema["tables"].items():
                col_info += f"\n- {table}: {', '.join([c['name'] for c in info.get('columns', [])])}"

        prompt = f"""Given this API with columns: {col_info}
Suggest 5 useful queries. Return ONLY JSON array of strings."""

        try:
            result = call_llm(prompt, json_mode=True)
            starter_queries = result.get("suggestions", []) if isinstance(result, dict) else []
        except:
            starter_queries = []

        # Store in session
        import uuid
        source_id = f"api-{uuid.uuid4().hex[:8]}"

        with SESSION_LOCK:
            SESSION_STORE[source_id] = {
                "type": source_type.lower().replace(" ", "_"),
                "connector": source,
                "schema": schema,
                "relationship_graph": {"nodes": [], "edges": []},
                "nickname": source_name,
                "created_at": str(source_id)
            }

        # Save API key to .env if provided
        if api_key:
            from dotenv import set_key
            key_name = f"{source_type.upper().replace(' ', '_')}_API_KEY"
            set_key('.env', key_name, api_key)

        return jsonify({
            "source_id": source_id,
            "schema": schema,
            "starter_queries": starter_queries
        })

    except Exception as e:
        print(f"Add API source error: {e}")
        return error_response(str(e), "API_SOURCE_FAILED", 500)


# =============================
# MAIN
# =============================

if __name__ == '__main__':
    print("=" * 50)
    print("AI SQL Studio API Server")
    print("=" * 50)
    print("Server running at: http://localhost:5000")
    print("Dashboard: http://localhost:5000")
    print("=" * 50)

    # Initialize
    initialize_app()

    # Run
    app.run(debug=True, port=5000, host='0.0.0.0', threaded=True)