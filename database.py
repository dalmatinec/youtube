import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import config


@contextmanager
def get_conn():
    conn = sqlite3.connect(config.DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_seen TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                platform TEXT,
                url TEXT,
                created_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS premium (
                user_id INTEGER PRIMARY KEY,
                expires_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS broadcasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER,
                audience TEXT,
                total INTEGER,
                sent INTEGER,
                failed INTEGER,
                created_at TEXT
            )
            """
        )
        conn.commit()


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------- users / downloads (как было) ----------

def register_user(user_id: int, username: str | None):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users (user_id, username, first_seen) VALUES (?, ?, ?)",
            (user_id, username or "", _now().isoformat()),
        )
        conn.commit()


def all_user_ids() -> list[int]:
    with get_conn() as conn:
        rows = conn.execute("SELECT user_id FROM users").fetchall()
    return [r[0] for r in rows]


def log_download(user_id: int, platform: str, url: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO downloads (user_id, platform, url, created_at) VALUES (?, ?, ?, ?)",
            (user_id, platform, url, _now().isoformat()),
        )
        conn.commit()


def downloads_last_24h(user_id: int) -> int:
    since = (_now() - timedelta(hours=24)).isoformat()
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT COUNT(*) FROM downloads WHERE user_id = ? AND created_at >= ?",
            (user_id, since),
        )
        return cur.fetchone()[0]


def user_stats(user_id: int) -> dict:
    with get_conn() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM downloads WHERE user_id = ?", (user_id,)
        ).fetchone()[0]
        rows = conn.execute(
            "SELECT platform, COUNT(*) FROM downloads WHERE user_id = ? GROUP BY platform",
            (user_id,),
        ).fetchall()
    return {"total": total, "by_platform": dict(rows)}


def global_stats() -> dict:
    with get_conn() as conn:
        users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        downloads = conn.execute("SELECT COUNT(*) FROM downloads").fetchone()[0]
        rows = conn.execute(
            "SELECT platform, COUNT(*) FROM downloads GROUP BY platform"
        ).fetchall()
    return {"users": users, "downloads": downloads, "by_platform": dict(rows)}


# ---------- settings (обязательный канал и т.п.) ----------

def get_setting(key: str) -> str | None:
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row[0] if row and row[0] else None


def set_setting(key: str, value: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        conn.commit()


# ---------- premium ----------

def premium_expiry(user_id: int) -> datetime | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT expires_at FROM premium WHERE user_id = ?", (user_id,)
        ).fetchone()
    if not row:
        return None
    return datetime.fromisoformat(row[0])


def is_premium(user_id: int) -> bool:
    expiry = premium_expiry(user_id)
    return bool(expiry and expiry > _now())


def grant_premium(user_id: int, days: int) -> datetime:
    """Продлевает премиум на `days` от текущей даты окончания (или от сейчас, если премиума не было)."""
    current = premium_expiry(user_id)
    base = current if current and current > _now() else _now()
    new_expiry = base + timedelta(days=days)
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO premium (user_id, expires_at) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET expires_at = excluded.expires_at",
            (user_id, new_expiry.isoformat()),
        )
        conn.commit()
    return new_expiry


def revoke_premium(user_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM premium WHERE user_id = ?", (user_id,))
        conn.commit()


def premium_user_ids() -> set[int]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT user_id FROM premium WHERE expires_at > ?", (_now().isoformat(),)
        ).fetchall()
    return {r[0] for r in rows}


def free_user_ids() -> set[int]:
    return set(all_user_ids()) - premium_user_ids()


# ---------- broadcasts ----------

def log_broadcast(admin_id: int, audience: str, total: int, sent: int, failed: int):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO broadcasts (admin_id, audience, total, sent, failed, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (admin_id, audience, total, sent, failed, _now().isoformat()),
        )
        conn.commit()


def broadcast_history(limit: int = 10) -> list[tuple]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT audience, total, sent, failed, created_at FROM broadcasts ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return rows
