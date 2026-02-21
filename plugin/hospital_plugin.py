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
def is_hospital_query(q):
    q = q.lower()
    keys = [
        "patient", "patients",
        "doctor", "doctors",
        "treatment", "treatments",
        "bill", "bills", "cost", "expensive",
        "admission", "admissions",
        "department", "departments",
        "name", "names",
        "total", "average", "highest", "lowest", "top", "most"
    ]
    return any(k in q for k in keys)


def is_count_query(q):
    q = q.lower()
    return "how many" in q or "count" in q or "number of" in q


def extract_top_n(q):
    m = re.search(r"(top|highest)\s+(\d+)", q.lower())
    return int(m.group(2)) if m else None


# =============================
# 🧠 NAME EXTRACTION
# =============================
STOPWORDS = {
    "patient", "patients", "doctor", "doctors", "of", "the", "who", "is", "has", "have",
    "show", "give", "me", "what", "how", "much", "list", "all", "with", "and", "or",
    "greater", "less", "than", "above", "below", "many", "are", "there",
    "highest", "top", "lowest", "min", "max", "most", "best",
    "department", "departments", "treatment", "treatments",
    "bill", "bills", "cost", "total", "today", "admission", "admissions",
    ">", "<", "="
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


def detect_min_patient_count(q):
    m = re.search(r"(more than|over|at least|>=|greater than)\s+(\d+)", q.lower())
    if m:
        return int(m.group(2))
    m2 = re.search(r"(\d+)\s+(patients?|doctors?)", q.lower())
    if m2:
        return int(m2.group(1))
    return None


# =============================
# 🧩 MAIN PLUGIN
# =============================
def try_handle_hospital_query(query, tables, conn):
    q = query.lower().strip()

    # 🔐 HARD SCHEMA GUARD
    if not has_tables(conn, ["patients"]):
        return None

    if not is_hospital_query(q) or is_count_query(q):
        return None

    # =============================
    # SIMPLE LIST QUERIES
    # =============================
    if "patient" in q and "name" in q:
        return "SELECT pat_name FROM patients;"

    if "doctor" in q and "name" in q and has_tables(conn, ["doctors"]):
        return "SELECT doc_name FROM doctors;"

    if "treatment" in q and "name" in q and has_tables(conn, ["treatments"]):
        return "SELECT treatment_name FROM treatments;"

    # =============================
    # TODAY'S ADMISSIONS
    # =============================
    if "today" in q and ("admission" in q or "admitted" in q) and has_tables(conn, ["admissions"]):
        print("🧠 [Hospital Plugin] Today's admissions")
        return """
SELECT *
FROM admissions
WHERE admission_date = CURDATE();
"""

    # =============================
    # TOTAL BILL OF PATIENT
    # =============================
    if "total" in q and "bill" in q:
        print("🧠 [Hospital Plugin] Total bill detected")
        name = detect_person_name(q)
        if name:
            return f"""
SELECT p.pat_name, SUM(p.bill) AS total_bill
FROM patients p
WHERE LOWER(p.pat_name) LIKE '%{name}%';
"""
        return """
SELECT p.pat_name, SUM(p.bill) AS total_bill
FROM patients p
GROUP BY p.pat_name
ORDER BY total_bill DESC
LIMIT 1;
"""

    # =============================
    # MOST EXPENSIVE TREATMENT
    # =============================
    if ("most expensive" in q or "highest cost" in q or "costliest" in q) and has_tables(conn, ["treatments"]):
        print("🧠 [Hospital Plugin] Most expensive treatment")
        n = extract_top_n(q) or 1
        return f"""
SELECT *
FROM treatments
ORDER BY cost DESC
LIMIT {n};
"""

    # =============================
    # DEPARTMENT WITH MOST PATIENTS
    # =============================
    if "most patients" in q and "department" in q and has_tables(conn, ["departments", "doctors"]):
        print("🧠 [Hospital Plugin] Department with most patients")
        return """
SELECT d.dept_name, COUNT(p.pat_id) AS patient_count
FROM departments d
JOIN doctors dd ON dd.dept_id = d.dept_id
JOIN patients p ON p.doc_id = dd.doc_id
GROUP BY d.dept_name
ORDER BY patient_count DESC
LIMIT 1;
"""

    # =============================
    # DEPTS WITH MORE THAN N PATIENTS
    # =============================
    if "department" in q and "patients" in q and ("more" in q or "over" in q) and has_tables(conn, ["departments", "doctors"]):
        n = detect_min_patient_count(q) or 1
        print("🧠 [Hospital Plugin] Departments with more than N patients")
        return f"""
SELECT d.dept_name, COUNT(p.pat_id) AS cnt
FROM departments d
JOIN doctors dd ON dd.dept_id = d.dept_id
JOIN patients p ON p.doc_id = dd.doc_id
GROUP BY d.dept_name
HAVING COUNT(p.pat_id) > {n};
"""

    # =============================
    # TOTAL BILL PER DEPARTMENT
    # =============================
    if "total" in q and "bill" in q and "department" in q and has_tables(conn, ["departments", "doctors"]):
        dept = detect_department_name(q)
        print("🧠 [Hospital Plugin] Total bill per department")
        if dept:
            return f"""
SELECT d.dept_name, SUM(p.bill) AS total_bill
FROM departments d
JOIN doctors dd ON dd.dept_id = d.dept_id
JOIN patients p ON p.doc_id = dd.doc_id
WHERE LOWER(d.dept_name) LIKE '%{dept}%'
GROUP BY d.dept_name;
"""
        return """
SELECT d.dept_name, SUM(p.bill) AS total_bill
FROM departments d
JOIN doctors dd ON dd.dept_id = d.dept_id
JOIN patients p ON p.doc_id = dd.doc_id
GROUP BY d.dept_name
ORDER BY total_bill DESC;
"""

    # =============================
    # COMPARISON BETWEEN TWO PATIENTS
    # =============================
    p1, p2 = detect_two_people(q)
    if p1 and p2:
        print("🧠 [Hospital Plugin] Patient bill comparison")
        return f"""
SELECT p.pat_name, p.bill
FROM patients p
WHERE LOWER(p.pat_name) LIKE '%{p1}%' OR LOWER(p.pat_name) LIKE '%{p2}%'
ORDER BY p.bill DESC;
"""

    # =============================
    # PERSON BILL (FINAL FALLBACK)
    # =============================
    person = detect_person_name(q)
    if person and "bill" in q:
        print("🧠 [Hospital Plugin] Person bill lookup")
        return f"""
SELECT p.pat_name, p.bill
FROM patients p
WHERE LOWER(p.pat_name) LIKE '%{person}%';
"""

    return None
