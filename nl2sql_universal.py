import mysql.connector
import joblib
import re

from plugin.company_plugin import try_handle_company_query
from plugin.hospital_plugin import try_handle_hospital_query
from plugin.shop_plugin import try_handle_shop_query
from plugin.college_plugin import try_handle_college_query
from api_nl2sql import generate_sql_via_api, test_api_connection
from sql_guard import enforce_user_constraints


# =============================
# LOAD ML MODEL (OPTIONAL)
# =============================
try:
    intent_model = joblib.load("intent_model_fixed.pkl")
    print("[OK] ML Intent model loaded")
except Exception:
    print("[!] ML model not loaded, running without ML")
    intent_model = None

# Test API connection on startup
from api_nl2sql import test_api_connection
api_available = test_api_connection()


# =============================
# MYSQL CONNECTION
# =============================
def get_connection(db_name):
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="pandu",   # CHANGE THIS
        database=db_name
    )


# =============================
# LOAD SCHEMA
# =============================
def load_schema(conn):
    tables = {}
    cur = conn.cursor()
    try:
        cur.execute("SHOW TABLES")
        for (t,) in cur.fetchall():
            cur.execute(f"DESCRIBE {t}")
            cols = [row[0] for row in cur.fetchall()]
            tables[t] = {"columns": cols}
    finally:
        cur.close()
    return tables


# =============================
# COUNT INFERENCE
# =============================
def infer_base_table_for_count(q, tables):
    q = q.lower()
    for t in tables:
        t_lower = t.lower()
        if t_lower in q or t_lower.rstrip("s") in q:
            return t
    return list(tables.keys())[0]


# =============================
# SALARY FILTER PARSER
# =============================
def parse_salary_filter(q):
    q = q.lower()
    m = re.search(r"(>=|<=|>|<)\s*(\d+)", q)
    if not m:
        return None, None
    return m.group(1), m.group(2)


# =============================
# NL EXISTENCE HANDLER
# =============================
def try_handle_existence_query(q, conn, tables):
    q_low = q.lower()

    if not any(w in q_low for w in ["exist", "available", "present"]):
        return False

    cur = conn.cursor()

    if "employee" in q_low:
        temp = q_low
        for w in ["is", "does", "employee", "present", "exist", "exists", "available", "there", "any", "in", "company"]:
            temp = temp.replace(w, "")
        name = temp.strip().title()
        if not name:
            cur.close()
            return False

        cur.execute(
            "SELECT 1 FROM employees WHERE LOWER(emp_name) LIKE %s LIMIT 1",
            (f"%{name.lower()}%",)
        )
        if cur.fetchone():
            print(f"✅ Yes, employee '{name}' exists")
        else:
            print(f"❌ No, employee '{name}' not found")
        cur.close()
        return True

    cur.close()
    return False


# =============================
# UNIVERSAL SQL BUILDER (FALLBACK)
# =============================
def build_universal_sql(query, tables):
    q = query.lower().strip()

    # COUNT
    if "how many" in q or "count" in q or "number of" in q:
        base = infer_base_table_for_count(q, tables)
        return f"SELECT COUNT(*) FROM {base};"

    # NAME LISTING
    if "name" in q or "names" in q:
        for t, info in tables.items():
            for c in info["columns"]:
                if c.lower().endswith("_name"):
                    return f"SELECT {c} FROM {t};"

    # TABLE INFERENCE
    base_table = None
    for t in tables:
        t_lower = t.lower()
        if t_lower in q or t_lower.rstrip("s") in q:
            base_table = t
            break
    if not base_table:
        base_table = list(tables.keys())[0]

    # SALARY FILTER
    if "salary" in q and "employees" in tables and "salaries" in tables:
        op, val = parse_salary_filter(q)
        if op and val:
            return f"""
SELECT e.*
FROM employees e
JOIN salaries s ON e.emp_id = s.emp_id
WHERE s.basic_salary {op} {val};
"""

    return f"SELECT * FROM {base_table};"


# =============================
# UNIVERSAL ROUTER ENGINE
# =============================
def generate_sql_and_execute(db, q):
    conn = get_connection(db)
    try:
        tables = load_schema(conn)

        # Check query complexity
        word_count = len(q.split())

        # 0) Try AI API first (most powerful)
        api_sql = generate_sql_via_api(q, tables, db)

        # FIX 1: Only accept valid API responses
        if api_sql and "INSUFFICIENT" not in api_sql:
            print("[AI] Routed to: AI API (NL2SQL)")
            # Apply guardrail to enforce user constraints
            validated_sql = enforce_user_constraints(api_sql, q)
            if validated_sql != api_sql:
                print("[Guardrail] Fixed SQL constraints")
            return validated_sql

        # FIX 2: Only run plugins for short queries (word_count <= 4)
        # 1) Company
        if word_count <= 4:
            sql = try_handle_company_query(q, tables, conn)
            if sql:
                print("Routed to: Company Plugin")
                return enforce_user_constraints(sql, q)

        # 2) Hospital
        if word_count <= 4:
            sql = try_handle_hospital_query(q, tables, conn)
            if sql:
                print("Routed to: Hospital Plugin")
                return enforce_user_constraints(sql, q)

        # 3) Shop
        if word_count <= 4:
            sql = try_handle_shop_query(q, tables, conn)
            if sql:
                print("Routed to: Shop Plugin")
                return enforce_user_constraints(sql, q)

        # 4) College
        if word_count <= 4:
            sql = try_handle_college_query(q, tables, conn)
            if sql:
                print("Routed to: College Plugin")
                return enforce_user_constraints(sql, q)

        # 5) Existence (LAST)
        handled = try_handle_existence_query(q, conn, tables)
        if handled:
            return None

        # 6) Universal fallback
        print("Routed to: Universal Engine")
        sql = build_universal_sql(q, tables)

        # FIX 3: Always validate final SQL
        return enforce_user_constraints(sql, q)
    finally:
        conn.close()


# =============================
# CLI MODE
# =============================
def main():
    db = input("Enter DB name: ").strip()
    conn = get_connection(db)

    tables = load_schema(conn)
    print("🗂️ Detected tables:", list(tables.keys()))

    if not tables:
        print("❌ No tables found in database!")
        return

    print("\n🤖 UNIVERSAL NL2SQL ENGINE READY!\n")

    while True:
        q = input("Ask (or 'exit'): ").strip()
        if q.lower() == "exit":
            break
        if not q:
            continue

        sql = generate_sql_and_execute(db, q)

        if not sql:
            print("ℹ️ Query handled without SQL.")
            continue

        print("\n🛠️ Final SQL:\n", sql)

        cur = conn.cursor()
        try:
            cur.execute(sql)
            for r in cur.fetchall():
                print(r)
        except Exception as e:
            print("❌ SQL Error:", e)


if __name__ == "__main__":
    main()
