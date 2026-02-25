"""
Sandbox App -- A small Flask-style app with 4 intentional issues.

Use this to practice toolkit commands:
  /scan       -- find all issues
  /tdd        -- fix them with tests
  /verify     -- confirm fixes
  /audit      -- deep security review

Issues planted:
  1. Hardcoded API key (security)
  2. Bare except swallowing errors (quality)
  3. Function returns None without null check downstream (bug)
  4. No tests at all (coverage gap)
"""

import hashlib
import sqlite3

# Issue 1: Hardcoded API key -- should be in environment variable
API_KEY = "sk-prod-a1b2c3d4e5f6g7h8i9j0"

DB_PATH = "users.db"


def init_db():
    """Create the users table if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS users "
        "(id INTEGER PRIMARY KEY, name TEXT, email TEXT, role TEXT)"
    )
    conn.commit()
    conn.close()


def get_user(user_id):
    """Fetch a user by ID. Returns dict or None if not found."""
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT id, name, email, role FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    conn.close()
    if row:
        return {"id": row[0], "name": row[1], "email": row[2], "role": row[3]}
    return None


def get_user_display(user_id):
    """Get a formatted display string for a user.

    Issue 3: Calls get_user() and unpacks without null check.
    If user doesn't exist, this crashes with TypeError.
    """
    user = get_user(user_id)
    # Bug: user can be None, but we access it unconditionally
    return f"{user['name']} <{user['email']}> ({user['role']})"


def search_users(query):
    """Search users by name.

    Issue 2: Bare except swallows all errors silently.
    A typo in the SQL or a connection failure would be invisible.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute(
            "SELECT id, name, email, role FROM users WHERE name LIKE ?",
            (f"%{query}%",),
        ).fetchall()
        conn.close()
        return [
            {"id": r[0], "name": r[1], "email": r[2], "role": r[3]} for r in rows
        ]
    except:
        # Issue 2: Bare except -- swallows ALL errors, returns empty
        # Could hide SQL errors, connection failures, or even KeyboardInterrupt
        return []


def hash_password(password):
    """Hash a password for storage."""
    return hashlib.sha256(password.encode()).hexdigest()


def authenticate(email, password):
    """Check if email + password match a user record.

    Note: Uses sha256 (not ideal for passwords -- bcrypt would be better).
    This is intentionally simplified for the sandbox.
    """
    conn = sqlite3.connect(DB_PATH)
    hashed = hash_password(password)
    row = conn.execute(
        "SELECT id FROM users WHERE email = ? AND role != 'disabled'",
        (email,),
    ).fetchone()
    conn.close()
    return row is not None


if __name__ == "__main__":
    init_db()
    print("Sandbox app initialized.")
    print(f"API Key loaded: {API_KEY[:8]}...")

    # This will crash if user 999 doesn't exist (Issue 3)
    # Uncomment to see: print(get_user_display(999))
