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
def is_college_query(q):
    q = q.lower()
    keys = [
        "student", "students",
        "marks", "grades", "score",
        "topper", "highest", "lowest", "top",
        "subject", "subjects",
        "department", "departments", "dept",
        "year", "semester", "sem",
        "average", "name", "names"
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
    "student", "students", "marks", "mark", "of", "the", "who", "is", "has", "have",
    "show", "give", "me", "what", "how", "much", "list", "all", "with", "and", "or",
    "greater", "less", "than", "above", "below", "many", "are", "there",
    "topper", "highest", "lowest", "top", "min", "max", "most", "best",
    "department", "departments", "dept",
    "subject", "subjects", "year", "semester", "sem",
    "average", "score", "grade",
    ">", "<", "="
}

def detect_student_name(q):
    words = [w for w in q.lower().split() if w not in STOPWORDS and not w.isdigit()]
    name = " ".join(words).strip()
    return name if name else None


def detect_two_students(q):
    q = q.lower()
    if " or " not in q:
        return None, None

    left, right = q.split(" or ", 1)

    def clean(x):
        words = [w for w in x.split() if w not in STOPWORDS and not w.isdigit()]
        return " ".join(words).strip()

    s1 = clean(left)
    s2 = clean(right)
    if s1 and s2:
        return s1, s2
    return None, None


# =============================
# 🔎 HELPERS
# =============================
def detect_subject_name(q):
    q = q.lower()
    subjects = ["maths", "physics", "chemistry", "english", "computer", "science"]
    for sub in subjects:
        if sub in q:
            return sub
    if "subject" in q:
        parts = q.split("subject", 1)[0].split()
        if parts:
            return parts[-1]
    return None


def detect_department_name(q):
    q = q.lower()
    depts = ["cse", "ece", "it", "mech", "civil"]
    for d in depts:
        if d in q:
            return d
    if "department" in q or "dept" in q:
        before = q.split("department", 1)[0].strip().split()
        if before:
            return before[-1]
    return None


def detect_min_marks(q):
    m = re.search(r"(more than|above|greater than|>=)\s+(\d+)", q.lower())
    if m:
        return int(m.group(2))
    return None


def detect_year(q):
    m = re.search(r"(year|sem|semester)\s+(\d+)", q.lower())
    return int(m.group(2)) if m else None


# =============================
# 🧩 MAIN PLUGIN
# =============================
def try_handle_college_query(query, tables, conn):
    q = query.lower().strip()

    # 🔐 HARD SCHEMA GUARD
    if not has_tables(conn, ["students", "marks"]):
        return None

    if not is_college_query(q) or is_count_query(q):
        return None

    # =============================
    # SIMPLE LIST QUERIES
    # =============================
    if "student" in q and "name" in q:
        return "SELECT name FROM students;"

    if "subject" in q and "name" in q:
        return "SELECT DISTINCT subject FROM marks;"

    # =============================
    # YEAR / SEMESTER FILTER
    # =============================
    year = detect_year(q)
    if year and ("year" in q or "semester" in q or "sem" in q):
        print("🧠 [College Plugin] Year/Semester filter")
        return f"""
SELECT s.name, m.subject, m.marks
FROM students s
JOIN marks m ON s.id = m.student_id
WHERE s.year = {year}
ORDER BY s.name, m.subject;
"""

    # =============================
    # STUDENTS ABOVE CERTAIN MARKS
    # =============================
    min_marks = detect_min_marks(q)
    if min_marks is not None:
        print("🧠 [College Plugin] Students above marks")
        return f"""
SELECT s.name, m.subject, m.marks
FROM students s
JOIN marks m ON s.id = m.student_id
WHERE m.marks > {min_marks}
ORDER BY m.marks DESC;
"""

    # =============================
    # AVERAGE MARKS
    # =============================
    if "average" in q and "marks" in q:
        print("🧠 [College Plugin] Average marks")
        subject = detect_subject_name(q)
        dept = detect_department_name(q)

        if subject and dept:
            return f"""
SELECT s.dept, AVG(m.marks) AS avg_marks
FROM students s
JOIN marks m ON s.id = m.student_id
WHERE LOWER(s.dept) LIKE '%{dept}%' AND LOWER(m.subject) LIKE '%{subject}%'
GROUP BY s.dept;
"""

        if subject:
            return f"""
SELECT AVG(m.marks) AS avg_marks
FROM marks m
WHERE LOWER(m.subject) LIKE '%{subject}%';
"""

        return """
SELECT s.name, AVG(m.marks) AS avg_marks
FROM students s
JOIN marks m ON s.id = m.student_id
GROUP BY s.id, s.name
ORDER BY avg_marks DESC;
"""

    # =============================
    # TOPPER / HIGHEST MARKS
    # =============================
    if "topper" in q or "highest" in q or "top" in q:
        print("🧠 [College Plugin] Topper detected")
        subject = detect_subject_name(q)
        dept = detect_department_name(q)
        n = extract_top_n(q) or 1

        if dept:
            return f"""
SELECT s.name, AVG(m.marks) AS avg_marks
FROM students s
JOIN marks m ON s.id = m.student_id
WHERE LOWER(s.dept) LIKE '%{dept}%'
GROUP BY s.id, s.name
ORDER BY avg_marks DESC
LIMIT {n};
"""

        if subject:
            return f"""
SELECT s.name, m.marks
FROM students s
JOIN marks m ON s.id = m.student_id
WHERE LOWER(m.subject) LIKE '%{subject}%'
ORDER BY m.marks DESC
LIMIT {n};
"""

        return f"""
SELECT s.name, m.subject, m.marks
FROM students s
JOIN marks m ON s.id = m.student_id
ORDER BY m.marks DESC
LIMIT {n};
"""

    # =============================
    # STUDENTS BY DEPARTMENT
    # =============================
    if "department" in q or "dept" in q:
        print("🧠 [College Plugin] Department query")
        dept = detect_department_name(q)
        if dept:
            return f"""
SELECT name, year
FROM students
WHERE LOWER(dept) LIKE '%{dept}%'
ORDER BY name;
"""
        return """
SELECT dept, COUNT(*) AS student_count
FROM students
GROUP BY dept
ORDER BY student_count DESC;
"""

    # =============================
    # COMPARISON BETWEEN TWO STUDENTS
    # =============================
    s1, s2 = detect_two_students(q)
    if s1 and s2:
        print("🧠 [College Plugin] Student comparison")
        return f"""
SELECT s.name, m.subject, m.marks
FROM students s
JOIN marks m ON s.id = m.student_id
WHERE LOWER(s.name) LIKE '%{s1}%' OR LOWER(s.name) LIKE '%{s2}%'
ORDER BY m.subject, m.marks DESC;
"""

    # =============================
    # MARKS OF STUDENT
    # =============================
    if "marks" in q:
        print("🧠 [College Plugin] Student marks")
        stu = detect_student_name(q)
        if stu:
            return f"""
SELECT s.name, m.subject, m.marks
FROM students s
JOIN marks m ON s.id = m.student_id
WHERE LOWER(s.name) LIKE '%{stu}%'
ORDER BY m.subject;
"""

    # =============================
    # FINAL FALLBACK: STUDENT MARKS
    # =============================
    stu = detect_student_name(q)
    if stu:
        print("🧠 [College Plugin] Student marks fallback")
        return f"""
SELECT s.name, m.subject, m.marks
FROM students s
JOIN marks m ON s.id = m.student_id
WHERE LOWER(s.name) LIKE '%{stu}%'
ORDER BY m.subject;
"""

    return None
