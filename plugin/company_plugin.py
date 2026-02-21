import re

# =============================
# 🔐 SCHEMA GUARD
# =============================
def has_tables(conn, required_tables):
    cur = conn.cursor()
    try:
        cur.execute("SHOW TABLES")
        existing = {row[0].lower() for row in cur.fetchall()}
        return all(t.lower() in existing for t in required_tables)
    finally:
        cur.close()


# =============================
# 🧠 BASIC DETECTORS
# =============================
def is_company_query(q):
    q = q.lower()
    keys = [
        "salary", "salaries",
        "employee", "employees",
        "bonus", "bonuses",
        "increment", "raise", "hike", "increase", "growth",
        "cost", "costs", "expensive",
        "department", "departments",
        "project", "projects",
        "name", "names",
        "average", "total", "highest", "lowest", "top", "most"
    ]
    return any(k in q for k in keys)


def is_filter_query(q):
    return any(op in q for op in [">", "<", "="])


def is_count_query(q):
    q = q.lower()
    return "how many" in q or "count" in q or "number of" in q


def extract_top_n(q):
    m = re.search(r"(top|highest)\s+(\d+)", q.lower())
    return int(m.group(2)) if m else None


def detect_increment_intent(q):
    q = q.lower()
    return any(w in q for w in ["raise", "increment", "hike", "increase", "growth"])


# =============================
# 🧠 NAME EXTRACTION
# =============================
STOPWORDS = {
    "salary", "salaries", "of", "the", "employee", "employees", "who", "is", "has", "have",
    "show", "give", "me", "what", "how", "much", "list", "all", "with", "and", "or",
    "greater", "less", "than", "above", "below", "many", "are", "there",
    "raise", "increment", "hike", "increase", "growth",
    "highest", "top", "lowest", "min", "max", "most", "best",
    "department", "departments", "project", "projects", "name", "names",
    "average", "total", "cost", "company", ">", "<", "="
}

def detect_person_name(q):
    words = [w for w in q.lower().split() if w not in STOPWORDS and not w.isdigit()]
    name = " ".join(words).strip()
    return name if name else None


def detect_two_people(q):
    q = q.lower()
    if " or " not in q:
        return None, None

    left, right = q.split(" or ", 1)

    def clean(x):
        words = [w for w in x.split() if w not in STOPWORDS and not w.isdigit()]
        return " ".join(words).strip()

    p1 = clean(left)
    p2 = clean(right)
    if p1 and p2:
        return p1, p2
    return None, None


# =============================
# 🏢 DEPARTMENT HELPERS
# =============================
def detect_department_name(q):
    q = q.lower()
    if "department" in q:
        before = q.split("department", 1)[0].strip()
        tokens = before.split()
        if tokens:
            return tokens[-1]
    return None


def detect_min_employee_count(q):
    m = re.search(r"(more than|over|at least|>=|greater than)\s+(\d+)", q.lower())
    if m:
        return int(m.group(2))
    m2 = re.search(r"(\d+)\s+employees?", q.lower())
    if m2:
        return int(m2.group(1))
    return None


# =============================
# 🧩 MAIN PLUGIN
# =============================
def try_handle_company_query(query, tables, conn):
    q = query.lower().strip()

    # 🔐 HARD SCHEMA GUARD
    if not has_tables(conn, ["employees", "salaries"]):
        return None

    # =============================
    # SIMPLE LIST QUERIES
    # =============================
    if "employee" in q and "name" in q:
        return "SELECT emp_name FROM employees;"

    if "department" in q and "name" in q:
        return "SELECT dept_name FROM departments;"

    if "project" in q and "name" in q:
        return "SELECT project_name FROM projects;"

    if not is_company_query(q) or is_count_query(q):
        return None

    # =============================
    # COMPANY COST
    # =============================
    if "cost" in q and "company" in q:
        print("🧠 [Company Plugin] Company cost detected")
        return """
SELECT e.emp_name,
       SUM(s.basic_salary) + COALESCE(SUM(b.amount),0) AS total_cost
FROM employees e
LEFT JOIN salaries s ON e.emp_id = s.emp_id
LEFT JOIN bonuses b ON e.emp_id = b.emp_id
GROUP BY e.emp_name
ORDER BY total_cost DESC
LIMIT 1;
"""

    # =============================
    # COMPARISON BETWEEN TWO PEOPLE
    # =============================
    p1, p2 = detect_two_people(q)
    if p1 and p2:
        print("🧠 [Company Plugin] Salary comparison detected")
        return f"""
SELECT e.emp_name, s.basic_salary
FROM employees e
JOIN salaries s ON e.emp_id = s.emp_id
WHERE s.effective_date = (SELECT MAX(effective_date) FROM salaries WHERE emp_id = e.emp_id)
AND (LOWER(e.emp_name) LIKE '%{p1}%' OR LOWER(e.emp_name) LIKE '%{p2}%')
ORDER BY s.basic_salary DESC;
"""

    # =============================
    # BIGGEST INCREMENT
    # =============================
    if detect_increment_intent(q):
        print("🧠 [Company Plugin] Increment detected")
        return """
SELECT e.emp_name, (s1.basic_salary - s2.basic_salary) AS increment_amount
FROM salaries s1
JOIN salaries s2 ON s1.emp_id = s2.emp_id
JOIN employees e ON e.emp_id = s1.emp_id
WHERE s1.effective_date = (SELECT MAX(effective_date) FROM salaries WHERE emp_id = s1.emp_id)
AND s2.effective_date = (
    SELECT MAX(effective_date) FROM salaries
    WHERE emp_id = s1.emp_id AND effective_date < s1.effective_date
)
ORDER BY increment_amount DESC
LIMIT 1;
"""

    # =============================
    # TOP / HIGHEST SALARY
    # =============================
    if "highest" in q or "top" in q or "most paid" in q:
        n = extract_top_n(q) or 1
        print("🧠 [Company Plugin] Salary ranking detected")
        return f"""
SELECT e.emp_name, s.basic_salary
FROM employees e
JOIN salaries s ON e.emp_id = s.emp_id
WHERE s.effective_date = (SELECT MAX(effective_date) FROM salaries WHERE emp_id = e.emp_id)
ORDER BY s.basic_salary DESC
LIMIT {n};
"""

    # =============================
    # PERSON SALARY (FINAL FALLBACK)
    # =============================
    person = detect_person_name(q)
    if person:
        print("🧠 [Company Plugin] Person salary lookup")
        return f"""
SELECT e.emp_name, s.basic_salary
FROM employees e
JOIN salaries s ON e.emp_id = s.emp_id
WHERE s.effective_date = (SELECT MAX(effective_date) FROM salaries WHERE emp_id = e.emp_id)
AND LOWER(e.emp_name) LIKE '%{person}%';
"""

    return None
