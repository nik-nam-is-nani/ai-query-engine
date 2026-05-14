"""
Autocomplete - Natural language query autocomplete with caching
"""
import threading
from dotenv import load_dotenv

load_dotenv(override=True)

from llm_client import call_llm

# Cache for completions
COMPLETION_CACHE = {}
CACHE_MAX_SIZE = 20
COMPLETION_LOCK = threading.Lock()


def autocomplete(partial, source_id, schema):
    """
    Generate autocomplete suggestion for partial query.

    Returns: { suggestion: str }
    """
    # Build cache key
    cache_key = partial[:40] + source_id

    # Check cache first
    with COMPLETION_LOCK:
        if cache_key in COMPLETION_CACHE:
            cached = COMPLETION_CACHE[cache_key]
            # Evict if cache too large
            if len(COMPLETION_CACHE) > CACHE_MAX_SIZE:
                oldest = list(COMPLETION_CACHE.keys())[0]
                del COMPLETION_CACHE[oldest]
            return {"suggestion": cached}

    # Build schema description
    schema_desc = ""
    if "tables" in schema:
        for table, info in schema["tables"].items():
            schema_desc += f"\nTable: {table}\n"
            if "columns" in info:
                for col in info["columns"]:
                    schema_desc += f"  - {col['name']} ({col.get('type', 'unknown')})\n"

    prompt = f"""You are an autocomplete engine for a natural language SQL query interface.
Database schema: {schema_desc}
The user has typed: "{partial}"
Complete this query naturally. Return ONLY the completion — the text AFTER what the user typed.
No repetition of what was typed. No explanation. Maximum 15 words."""

    try:
        suggestion = call_llm(prompt)

        # Cache the result
        with COMPLETION_LOCK:
            COMPLETION_CACHE[cache_key] = suggestion

        return {"suggestion": suggestion}

    except Exception as e:
        print(f"Autocomplete error: {e}")
        return {"suggestion": ""}