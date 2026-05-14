"""
Recommender - Suggest follow-up queries based on results
"""
from dotenv import load_dotenv

load_dotenv(override=True)

from llm_client import call_llm


def recommend(last_query, result_summary, schema):
    """
    Generate follow-up query suggestions.

    Args:
        last_query: str - the SQL that was just executed
        result_summary: dict with 'columns' and 'rows' keys
        schema: dict - database schema

    Returns: { suggestions: [...] }
    """
    # Build schema description
    schema_desc = ""
    if "tables" in schema:
        for table, info in schema["tables"].items():
            schema_desc += f"\n- {table}"
            if "columns" in info:
                cols = ", ".join([c["name"] for c in info["columns"][:5]])
                schema_desc += f": {cols}"

    # Build result summary
    columns_str = ", ".join(result_summary.get("columns", []))
    sample_rows = result_summary.get("rows", [])[:3]
    sample_str = "\n".join([str(row) for row in sample_rows]) if sample_rows else "No data"

    prompt = f"""A user just ran this SQL query: "{last_query}"
The result had these columns: {columns_str}
Sample rows: {sample_str}
Database schema: {schema_desc}

Suggest 5 natural language follow-up queries the user might want to run next.
Return a JSON array of 5 strings. Only the array. No explanation. No markdown.
Example: ["Show sales trend over time", "Find top performing categories"]"""

    try:
        result = call_llm(prompt, json_mode=True)

        if isinstance(result, dict) and "suggestions" in result:
            return {"suggestions": result["suggestions"]}
        elif isinstance(result, list):
            return {"suggestions": result[:5]}

    except Exception as e:
        print(f"Recommender error: {e}")

    return {"suggestions": [
        "Show results over time",
        "Group by category",
        "Find top values",
        "Compare to average",
        "Filter for specific criteria"
    ]}