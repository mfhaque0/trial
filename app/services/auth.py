from datetime import datetime, timezone
from werkzeug.security import check_password_hash, generate_password_hash
from app.models.database import connect


def now() -> str: return datetime.now(timezone.utc).isoformat()

def register(database, display_name: str, email: str, password: str) -> int:
    display_name, email = display_name.strip(), email.strip().lower()
    if not 2 <= len(display_name) <= 80: raise ValueError("Enter a display name between 2 and 80 characters.")
    if "@" not in email or len(email) > 254: raise ValueError("Enter a valid email address.")
    if len(password) < 10: raise ValueError("Use a password with at least 10 characters.")
    timestamp = now()
    try:
        with connect(database) as db:
            cursor = db.execute("INSERT INTO users(display_name,email,password_hash,created_at,updated_at) VALUES(?,?,?,?,?)", (display_name, email, generate_password_hash(password), timestamp, timestamp))
            return cursor.lastrowid
    except Exception as error:
        if "UNIQUE" in str(error): raise ValueError("An account with that email already exists.") from None
        raise

def authenticate(database, email: str, password: str):
    with connect(database) as db:
        user = db.execute("SELECT * FROM users WHERE email = ?", (email.strip().lower(),)).fetchone()
    return user if user and check_password_hash(user["password_hash"], password) else None

def get_user(database, user_id: int):
    with connect(database) as db: return db.execute("SELECT id,display_name,email FROM users WHERE id = ?", (user_id,)).fetchone()
