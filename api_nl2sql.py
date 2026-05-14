import os
import json
from typing import Optional

# =============================
# 🔑 LOAD API KEY
# =============================
def load_api_key():
    """Load API key from the API_key.txt file"""
    key_path = os.path.join("API_datamanager", "API_key.txt")
    try:
        with open(key_path, "r") as f:
            return f.read().strip()
    except Exception as e:
        print("[!] Failed to load API key:", e)
        return None


# =============================
# 🧠 API-BASED NL2SQL CONVERTER
# =============================
def generate_sql_via_api(query: str, tables: dict, db_name: str) -> Optional[str]:
    """
    Use AI API to convert natural language to SQL query.
    Returns SQL query string or None if failed.
    """
    API_KEY = load_api_key()
    if not API_KEY:
        return None

    # Build schema context
    schema_info = f"Database: {db_name}\nTables:\n"
    for table_name, table_info in tables.items():
        cols = ", ".join(table_info.get("columns", []))
        schema_info += f"  - {table_name}: ({cols})\n"

    # Create prompt for SQL generation
    prompt = f"""You are an expert SQL generator.

Convert user questions into SQL queries.

OUTPUT RULES:
- Output ONLY SQL.
- No explanations.
- No text.
- No markdown.

STRICT CONSTRAINT RULES:
- Every condition mentioned MUST appear in SQL.
- Never skip filters.
- Never skip numbers.
- Never replace numbers.
- Never assume values.
- If user specifies limit/top → MUST use exact value.
- If user says department N → use dept_id = N.
- If user specifies year → interpret:
  "after 2022" → > '2022-01-01'
  "before 2022" → < '2022-01-01'

INTERPRETATION RULES:
- inactive → status='inactive'
- active → status='active'
- developers → job_title='Developer'
- salary → basic_salary
- earn more than → >
- earn less than → <
- at least → >=
- at most → <=

SQL RULES:
- Always qualify columns with table aliases.
- Use joins when data is in multiple tables.
- If sorting implied (top, highest) → ORDER BY DESC.
- Never add conditions not mentioned.
- Never use IS NOT NULL unless user asked.
- Never default LIMIT.
- Never hallucinate columns.

DATABASE SCHEMA:
{schema_info}

USER QUESTION:
{query}

SQL:"""

    try:
        import requests
        
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Using OpenAI-compatible API endpoint
        payload = {
            "model": "arcee-ai/trinity-large-preview:free",
            "messages": [
                {"role": "system", "content": "You are an expert SQL query generator. Output ONLY SQL, no explanations, no markdown, no comments."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 500,
            "temperature": 0.1
        }
        
        # Try different API endpoints
        endpoints = [
            "https://openrouter.ai/api/v1/chat/completions",
            "https://api.openai.com/v1/chat/completions"
        ]
        
        for endpoint in endpoints:
            try:
                response = requests.post(
                    endpoint,
                    headers=headers,
                    json=payload,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    raw_content = result["choices"][0]["message"]["content"].strip()
                    
                    # Clean up any markdown code blocks
                    sql_query = raw_content.replace("```sql", "").replace("```", "").strip()
                    
                    print(f"[AI] Generated SQL: {sql_query}")
                    return sql_query
                else:
                    print(f"[!] API Error ({endpoint}): {response.status_code}")
                    continue
            except Exception as e:
                print(f"[!] Failed endpoint {endpoint}: {e}")
                continue
        
        return None
        
    except ImportError:
        print("[!] requests library not installed. Install with: pip install requests")
        return None
    except Exception as e:
        print(f"[!] API Error: {e}")
        return None


# =============================
# 🧪 TEST API CONNECTION
# =============================
def test_api_connection():
    """Test if the API is working"""
    API_KEY = load_api_key()
    if not API_KEY:
        print("[!] No API key found")
        return False
    
    try:
        import requests
        
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "arcee-ai/trinity-large-preview:free",
            "messages": [{"role": "user", "content": "Say 'API working!' if you can read this"}],
            "max_tokens": 50
        }
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=15
        )
        
        if response.status_code == 200:
            print("[OK] API connection successful!")
            return True
        else:
            print(f"[!] API error: {response.status_code}")
            return False
            
    except ImportError:
        print("[!] requests library not installed")
        return False
    except Exception as e:
        print(f"[!] Connection failed: {e}")
        return False


# =============================
# 🎯 NEW NL2SQL API ENDPOINT HANDLER
# =============================
from dotenv import load_dotenv

load_dotenv(override=True)

from llm_client import call_llm
from connector_manager import get_schema
from xai_engine import generate_explanation
from sql_guard import validate_and_fix


def generate_sql(nl_query, source_id, schema=None):
    """
    Convert natural language query to SQL.

    Returns: { sql, explanation, guardrail_events }
    """
    # Get schema if not provided
    if schema is None:
        schema = get_schema(source_id)

    # Build schema description
    schema_str = ""
    if "tables" in schema:
        for table, info in schema["tables"].items():
            schema_str += f"\nTable: {table}\n"
            if "columns" in info:
                for col in info["columns"]:
                    schema_str += f"  - {col['name']} ({col.get('type', 'unknown')})\n"

    prompt = f"""You are an expert SQL generator. Given the following database schema:
{schema_str}
Convert this natural language query to valid SQL:
"{nl_query}"
Return ONLY the SQL query. No explanation. No markdown. No backticks."""

    try:
        sql = call_llm(prompt)

        # Clean up SQL
        sql = sql.strip().strip('```').strip()

        # Generate explanation
        explanation = generate_explanation(nl_query, sql, schema)

        # Validate and fix SQL
        validation = validate_and_fix(sql, schema)
        if not validation["valid"]:
            return {
                "sql": sql,
                "explanation": explanation,
                "guardrail_events": validation["guardrail_events"],
                "error": validation["reason"]
            }

        return {
            "sql": validation["sql"],
            "explanation": explanation,
            "guardrail_events": validation["guardrail_events"]
        }

    except Exception as e:
        print(f"Error generating SQL: {e}")
        return {
            "sql": "",
            "explanation": {},
            "guardrail_events": [],
            "error": str(e)
        }


if __name__ == "__main__":
    test_api_connection()
