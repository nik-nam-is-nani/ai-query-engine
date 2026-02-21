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
def is_shop_query(q):
    q = q.lower()
    keys = [
        "product", "products",
        "price", "prices", "cost", "expensive",
        "sale", "sales", "sold",
        "customer", "customers",
        "stock", "quantity",
        "category",
        "total", "most", "highest", "top",
        "name", "names",
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
    "product", "products", "price", "prices", "of", "the", "which", "is", "has", "have",
    "show", "give", "me", "what", "how", "much", "list", "all", "with", "and", "or",
    "greater", "less", "than", "above", "below", "many", "are", "there",
    "highest", "top", "lowest", "min", "max", "most", "best",
    "sold", "sale", "sales",
    "category", "customer", "customers",
    "stock", "quantity", "total",
    ">", "<", "="
}

def detect_product_name(q):
    words = [w for w in q.lower().split() if w not in STOPWORDS and not w.isdigit()]
    name = " ".join(words).strip()
    return name if name else None


def detect_two_products(q):
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
# 🔎 HELPERS
# =============================
def extract_price_threshold(q, direction="below"):
    if direction == "below":
        m = re.search(r"(below|less than|<)\s+(\d+)", q.lower())
    else:
        m = re.search(r"(above|more than|>)\s+(\d+)", q.lower())
    return int(m.group(2)) if m else None


def detect_min_quantity(q):
    m = re.search(r"(more than|over|at least|>=)\s+(\d+)", q.lower())
    if m:
        return int(m.group(2))
    m2 = re.search(r"(\d+)\s+(sold|units?)", q.lower())
    if m2:
        return int(m2.group(1))
    return None


def detect_category_name(q):
    q = q.lower()
    if "category" in q:
        before = q.split("category", 1)[0].strip().split()
        if before:
            return before[-1]
    return None


# =============================
# 🧩 MAIN PLUGIN
# =============================
def try_handle_shop_query(query, tables, conn):
    q = query.lower().strip()

    # 🔐 HARD SCHEMA GUARD
    if not has_tables(conn, ["products"]):
        return None

    if not is_shop_query(q) or is_count_query(q):
        return None

    # =============================
    # SIMPLE LIST QUERIES
    # =============================
    if "product" in q and "name" in q:
        return "SELECT product_name FROM products;"

    if "customer" in q and "name" in q and has_tables(conn, ["customers"]):
        return "SELECT cust_name FROM customers;"

    # =============================
    # PRICE FILTERS (BEFORE GENERAL PRICE)
    # =============================
    price_below = extract_price_threshold(q, "below")
    if price_below is not None:
        print("🧠 [Shop Plugin] Products below price")
        return f"""
SELECT *
FROM products
WHERE price < {price_below}
ORDER BY price;
"""

    price_above = extract_price_threshold(q, "above")
    if price_above is not None:
        print("🧠 [Shop Plugin] Products above price")
        return f"""
SELECT *
FROM products
WHERE price > {price_above}
ORDER BY price;
"""

    # =============================
    # PRICE OF PRODUCT
    # =============================
    if "price" in q or "cost" in q:
        print("🧠 [Shop Plugin] Product price")
        prod = detect_product_name(q)
        if prod:
            return f"""
SELECT product_name, price
FROM products
WHERE LOWER(product_name) LIKE '%{prod}%';
"""
        return """
SELECT product_name, price
FROM products
ORDER BY price DESC;
"""

    # =============================
    # LOW STOCK
    # =============================
    if "low" in q and "stock" in q:
        print("🧠 [Shop Plugin] Low stock")
        return """
SELECT product_name, stock_quantity
FROM products
WHERE stock_quantity < 10
ORDER BY stock_quantity;
"""

    # =============================
    # MOST SOLD PRODUCT
    # =============================
    if ("most sold" in q or "highest sold" in q or "top selling" in q) and has_tables(conn, ["sales"]):
        print("🧠 [Shop Plugin] Most sold product")
        n = extract_top_n(q) or 1
        return f"""
SELECT p.product_name, SUM(s.quantity) AS total_sold
FROM sales s
JOIN products p ON p.product_id = s.product_id
GROUP BY p.product_id, p.product_name
ORDER BY total_sold DESC
LIMIT {n};
"""

    # =============================
    # PRODUCTS SOLD MORE THAN N
    # =============================
    if "sold" in q and ("more" in q or "over" in q) and has_tables(conn, ["sales"]):
        n = detect_min_quantity(q) or 1
        print("🧠 [Shop Plugin] Products sold more than N")
        return f"""
SELECT p.product_name, SUM(s.quantity) AS total_sold
FROM sales s
JOIN products p ON p.product_id = s.product_id
GROUP BY p.product_id, p.product_name
HAVING SUM(s.quantity) > {n}
ORDER BY total_sold DESC;
"""

    # =============================
    # TOTAL SALES
    # =============================
    if "total" in q and "sales" in q and has_tables(conn, ["sales"]):
        print("🧠 [Shop Plugin] Total sales")
        return """
SELECT SUM(total_amount) AS total_sales_revenue
FROM sales;
"""

    # =============================
    # TOTAL SALES BY PRODUCT / CATEGORY
    # =============================
    if "total" in q and "sales" in q and has_tables(conn, ["sales"]):
        print("🧠 [Shop Plugin] Total sales by product/category")
        cat = detect_category_name(q)
        if cat:
            return f"""
SELECT p.category, SUM(s.total_amount) AS category_sales
FROM sales s
JOIN products p ON p.product_id = s.product_id
WHERE LOWER(p.category) LIKE '%{cat}%'
GROUP BY p.category
ORDER BY category_sales DESC;
"""
        return """
SELECT p.product_name, SUM(s.total_amount) AS product_sales
FROM sales s
JOIN products p ON p.product_id = s.product_id
GROUP BY p.product_id, p.product_name
ORDER BY product_sales DESC;
"""

    # =============================
    # TOP CUSTOMER
    # =============================
    if "customer" in q and ("most" in q or "highest" in q) and has_tables(conn, ["customers", "sales"]):
        print("🧠 [Shop Plugin] Top customer")
        return """
SELECT c.cust_name, SUM(s.total_amount) AS total_spent
FROM sales s
JOIN customers c ON c.cust_id = s.cust_id
GROUP BY c.cust_id, c.cust_name
ORDER BY total_spent DESC
LIMIT 1;
"""

    # =============================
    # COMPARISON BETWEEN TWO PRODUCTS
    # =============================
    p1, p2 = detect_two_products(q)
    if p1 and p2:
        print("🧠 [Shop Plugin] Product comparison")
        return f"""
SELECT product_name, price
FROM products
WHERE LOWER(product_name) LIKE '%{p1}%' OR LOWER(product_name) LIKE '%{p2}%'
ORDER BY price DESC;
"""

    # =============================
    # PRODUCT SALES (FALLBACK)
    # =============================
    prod = detect_product_name(q)
    if prod and ("sales" in q or "sold" in q) and has_tables(conn, ["sales"]):
        print("🧠 [Shop Plugin] Product sales")
        return f"""
SELECT p.product_name, SUM(s.quantity) AS total_sold, SUM(s.total_amount) AS revenue
FROM sales s
JOIN products p ON p.product_id = s.product_id
WHERE LOWER(p.product_name) LIKE '%{prod}%'
GROUP BY p.product_id, p.product_name;
"""

    return None
