"""
Precommands - SQLite database for saved query templates
"""
import sqlite3
import json
import os
from datetime import datetime

DB_PATH = "precommands.db"


def init_db():
    """Initialize the precommands database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS commands (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            template TEXT NOT NULL,
            variables TEXT,
            source_type TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_command(title, template, variables, source_type):
    """Save a new precommand"""
    import uuid

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cmd_id = str(uuid.uuid4())
    created_at = datetime.now().isoformat()
    variables_json = json.dumps(variables) if variables else "[]"

    cursor.execute("""
        INSERT INTO commands (id, title, template, variables, source_type, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (cmd_id, title, template, variables_json, source_type, created_at))

    conn.commit()
    conn.close()

    return cmd_id


def list_commands():
    """Get all precommands"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT id, title, template, variables, source_type, created_at FROM commands ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()

    commands = []
    for row in rows:
        commands.append({
            "id": row[0],
            "title": row[1],
            "template": row[2],
            "variables": json.loads(row[3]) if row[3] else [],
            "source_type": row[4],
            "created_at": row[5]
        })

    return commands


def get_command(cmd_id):
    """Get a single command by ID"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT id, title, template, variables, source_type, created_at FROM commands WHERE id = ?", (cmd_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "id": row[0],
        "title": row[1],
        "template": row[2],
        "variables": json.loads(row[3]) if row[3] else [],
        "source_type": row[4],
        "created_at": row[5]
    }


def run_command(cmd_id, variables):
    """Run a precommand with variable substitution"""
    cmd = get_command(cmd_id)
    if not cmd:
        return None

    template = cmd["template"]

    # Substitute variables using format_map
    result = template
    if variables:
        try:
            result = template.format_map(variables)
        except Exception as e:
            print(f"Variable substitution error: {e}")
            # Use safe fallback
            for key, value in variables.items():
                result = result.replace(f"{{{key}}}", str(value))

    return result


# Initialize on import
init_db()