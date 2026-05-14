"""
XAI Engine - Explainable AI for SQL queries
"""
import json
from dotenv import load_dotenv

load_dotenv(override=True)

from llm_client import call_llm


def generate_explanation(nl_query, sql, schema):
    """
    Generate detailed explanation of SQL query.

    Returns dict with keys:
    - intent, intent_category, confidence_score, confidence_label
    - tables_used, columns_used, filters_applied, aggregations
    - joins_performed, sort_order, limit_applied, plain_english
    - assumptions_made, alternative_interpretations, risk_flags, token_trace
    """
    # Build schema string for prompt
    schema_str = ""
    if "tables" in schema:
        for table, info in schema["tables"].items():
            schema_str += f"\nTable: {table}\n"
            if "columns" in info:
                for col in info["columns"]:
                    schema_str += f"  - {col['name']} ({col.get('type', 'unknown')})\n"

    prompt = f"""You are an AI explainability engine for SQL queries.
Natural language query: "{nl_query}"
Generated SQL: "{sql}"
Schema: {schema_str}

Return a JSON object with these exact keys:
- intent: one-line description of what the query does
- intent_category: one of [filtering, aggregation, ranking, joining, comparison, trend]
- confidence_score: float 0.0 to 1.0 representing your certainty the SQL matches the intent
- confidence_label: one of [High, Medium, Low]
- tables_used: list of table names referenced
- columns_used: list of column names referenced
- filters_applied: list of filter conditions as readable strings
- aggregations: list of aggregation operations as readable strings
- joins_performed: list of join descriptions
- sort_order: description of ORDER BY or "none"
- limit_applied: integer or null
- plain_english: 1-2 sentence human-readable summary
- assumptions_made: list of assumptions the SQL made about the query
- alternative_interpretations: list of other ways the query could be interpreted
- risk_flags: list of performance or correctness warnings
- token_trace: object mapping key phrases from nl_query to the SQL clause they produced

Return ONLY valid JSON. No markdown. No backtick fences."""

    try:
        result = call_llm(prompt, json_mode=True)

        # Validate result has required keys
        required_keys = [
            "intent", "intent_category", "confidence_score", "confidence_label",
            "tables_used", "columns_used", "filters_applied", "aggregations",
            "joins_performed", "sort_order", "limit_applied", "plain_english",
            "assumptions_made", "alternative_interpretations", "risk_flags", "token_trace"
        ]

        for key in required_keys:
            if key not in result:
                result[key] = [] if key in ["tables_used", "columns_used", "filters_applied",
                    "aggregations", "joins_performed", "assumptions_made",
                    "alternative_interpretations", "risk_flags"] else (
                    "none" if key == "sort_order" else "Unknown"
                )

        return result

    except Exception as e:
        print(f"Error generating explanation: {e}")
        return get_fallback_explanation(nl_query, sql)


def get_fallback_explanation(nl_query, sql):
    """Return safe fallback when LLM fails"""
    # Simple heuristics for fallback
    import re

    tables = re.findall(r'FROM\s+(\w+)', sql, re.IGNORECASE) + re.findall(r'JOIN\s+(\w+)', sql, re.IGNORECASE)
    columns = re.findall(r'SELECT\s+(.*?)\s+FROM', sql, re.IGNORECASE)
    has_limit = "LIMIT" in sql.upper()
    has_order = "ORDER BY" in sql.upper()
    has_group = "GROUP BY" in sql.upper()

    aggregations = []
    if "COUNT" in sql.upper(): aggregations.append("COUNT")
    if "SUM" in sql.upper(): aggregations.append("SUM")
    if "AVG" in sql.upper(): aggregations.append("AVG")
    if "MAX" in sql.upper(): aggregations.append("MAX")
    if "MIN" in sql.upper(): aggregations.append("MIN")

    return {
        "intent": nl_query,
        "intent_category": "query",
        "confidence_score": 0.5,
        "confidence_label": "Medium",
        "tables_used": tables,
        "columns_used": [],
        "filters_applied": [],
        "aggregations": aggregations,
        "joins_performed": [],
        "sort_order": "yes" if has_order else "none",
        "limit_applied": 1000 if has_limit else None,
        "plain_english": "Query executed successfully",
        "assumptions_made": ["Query assumed standard SQL syntax"],
        "alternative_interpretations": [],
        "risk_flags": [],
        "token_trace": {}
    }


def explain_endpoint(nl_query, sql, schema):
    """Standalone /api/explain endpoint handler"""
    return generate_explanation(nl_query, sql, schema)