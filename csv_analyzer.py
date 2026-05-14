"""
CSV Analyzer - Upload and analyze CSV files
"""
import os
import uuid
import sqlite3
import pandas as pd
from dotenv import load_dotenv

load_dotenv(override=True)

from llm_client import call_llm

# Ensure uploads directory exists
UPLOADS_DIR = "uploads"
os.makedirs(UPLOADS_DIR, exist_ok=True)


def infer_column_type(series):
    """Infer column type from pandas series"""
    dtype = series.dtype

    if pd.api.types.is_bool_dtype(dtype):
        return "boolean"
    elif pd.api.types.is_integer_dtype(dtype):
        return "integer"
    elif pd.api.types.is_float_dtype(dtype):
        return "float"
    elif pd.api.types.is_datetime64_any_dtype(dtype):
        return "datetime"

    # Check for potential geo columns
    col_name_lower = series.name.lower() if series.name else ""
    if any(x in col_name_lower for x in ["lat", "lon", "latitude", "longitude"]):
        return "geo_latitude" if "lat" in col_name_lower else "geo_longitude"
    if any(x in col_name_lower for x in ["country", "city", "state", "region"]):
        return "geo_categorical"

    # Check categorical
    unique_ratio = series.nunique() / max(len(series), 1)
    if unique_ratio < 0.5 and len(series) > 10:
        return "categorical"

    return "string"


def analyze_csv(file):
    """
    Analyze uploaded CSV file and create in-memory SQLite database.

    Returns: {
        source_id: str,
        filename: str,
        schema: dict,
        preview_rows: list,
        column_stats: dict,
        starter_queries: list
    }
    """
    # Save file with UUID
    file_id = str(uuid.uuid4())
    filename = f"{file_id}_{file.filename}"
    filepath = os.path.join(UPLOADS_DIR, filename)

    # Save uploaded file
    file.save(filepath)

    # Read CSV with pandas
    df = pd.read_csv(filepath)

    # Build schema
    schema = {"tables": {}}
    table_name = file.filename.replace(".csv", "").replace(" ", "_")
    columns = []

    column_stats = {}

    for col_name in df.columns:
        col_type = infer_column_type(df[col_name])
        col_info = {
            "name": col_name,
            "type": col_type,
            "nullable": df[col_name].isnull().any()
        }

        # Compute stats
        stats = {}
        if pd.api.types.is_numeric_dtype(df[col_name]):
            stats = {
                "min": float(df[col_name].min()) if not pd.isna(df[col_name].min()) else None,
                "max": float(df[col_name].max()) if not pd.isna(df[col_name].max()) else None,
                "mean": float(df[col_name].mean()) if not pd.isna(df[col_name].mean()) else None,
                "median": float(df[col_name].median()) if not pd.isna(df[col_name].median()) else None,
                "std": float(df[col_name].std()) if not pd.isna(df[col_name].std()) else None,
            }

        stats.update({
            "null_count": int(df[col_name].isnull().sum()),
            "unique_count": int(df[col_name].nunique()),
            "top_5_values": df[col_name].value_counts().head(5).to_dict() if df[col_name].nunique() < 50 else {}
        })

        column_stats[col_name] = stats
        columns.append(col_info)

    schema["tables"][table_name] = {
        "columns": columns,
        "row_count": len(df)
    }

    # Get preview rows (first 20)
    preview_rows = df.head(20).to_dict(orient="records")

    # Create in-memory SQLite and load data
    mem_conn = sqlite3.connect(":memory:")
    df.to_sql(table_name, mem_conn, if_exists="replace", index=False)

    # Detect likely primary key
    pk_columns = []
    for col in df.columns:
        if df[col].nunique() == len(df) and df[col].notna().all():
            pk_columns.append(col)

    # Generate starter queries using LLM
    starter_queries = generate_starter_queries(columns, table_name)

    return {
        "source_id": f"csv-{file_id}",
        "filename": filename,
        "schema": schema,
        "preview_rows": preview_rows,
        "column_stats": column_stats,
        "starter_queries": starter_queries,
        "primary_key": pk_columns[0] if pk_columns else None,
        "connector": mem_conn  # Store for later use
    }


def generate_starter_queries(columns, table_name):
    """Use LLM to generate starter query suggestions"""
    try:
        # Build column info
        col_info = "\n".join([f"- {c['name']}: {c['type']}" for c in columns])

        prompt = f"""You are a data analyst. Given this CSV file with columns:
{col_info}

Suggest 5 natural language queries that would be useful to ask about this data.
Return ONLY a JSON array of 5 strings. No explanation. No markdown.
Example: ["Show total sales by month", "Find top 10 customers by revenue"]"""

        result = call_llm(prompt, json_mode=True)

        if isinstance(result, dict) and "suggestions" in result:
            return result["suggestions"]
        elif isinstance(result, list):
            return result[:5]
        else:
            return get_default_queries(columns, table_name)

    except Exception as e:
        print(f"Error generating starter queries: {e}")
        return get_default_queries(columns, table_name)


def get_default_queries(columns, table_name):
    """Fallback default queries"""
    numeric_cols = [c["name"] for c in columns if c["type"] in ["integer", "float"]]
    categorical_cols = [c["name"] for c in columns if c["type"] == "categorical"]

    queries = [f"Show all rows from {table_name}"]

    if numeric_cols:
        queries.append(f"Show sum of {numeric_cols[0]} grouped by {categorical_cols[0] if categorical_cols else 'all'}")

    if categorical_cols:
        queries.append(f"Count rows by {categorical_cols[0]}")

    queries.extend([
        f"Show top 10 by {numeric_cols[0] if numeric_cols else 'first column'}",
        f"Average of {numeric_cols[0] if numeric_cols else 'first column'}"
    ])

    return queries[:5]