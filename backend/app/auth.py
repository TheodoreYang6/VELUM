"""Self-contained account + session layer (no third-party crypto deps).

Design notes
------------
* Passwords are hashed with PBKDF2-HMAC-SHA256 from the standard library, so the
  project keeps its "minimal dependencies" promise — no bcrypt / passlib.
* Sessions are random tokens stored server-side and delivered via an httpOnly
  cookie. A stolen cookie cannot be reversed into a password, and revoked /
  expired tokens are easy to invalidate. There is no signing secret to leak.
* Only the canonical rule documents (PUT /api/rules, POST /api/index/rebuild)
  are gated; the tarot ritual itself stays open for everyone.

Feel free to layer role-based access on top of the ``users`` table later.
"""
from __future__ import annotations

import base64
import hashlib
import secrets
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Optional

COOKIE_NAME = "velum_session"
_PBKDF2_ITERS = 200_000
_SESSION_DAYS = 30
SESSION_MAX_AGE = _SESSION_DAYS * 24 * 3600


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64d(text: str) -> bytes:
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERS)
    return f"pbkdf2_sha256${_PBKDF2_ITERS}${_b64(salt)}${_b64(dk)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iters_s, salt_s, hash_s = stored.split("$")
        iters = int(iters_s)
        salt = _b64d(salt_s)
        expected = _b64d(hash_s)
    except Exception:
        return False
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iters)
    return secrets.compare_digest(dk, expected)


def register_user(
    conn: sqlite3.Connection, username: str, password: str, display: str
) -> dict[str, Any]:
    username = (username or "").strip()
    password = password or ""
    display = (display or "").strip() or username
    if len(username) < 3:
        raise ValueError("用户名至少 3 个字符")
    if len(password) < 6:
        raise ValueError("密码至少 6 个字符")
    if conn.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone():
        raise ValueError("该用户名已被使用")
    user_id = secrets.token_hex(8)
    conn.execute(
        "INSERT INTO users (user_id, username, password, display, created_at) "
        "VALUES (?,?,?,?,?)",
        (
            user_id,
            username,
            hash_password(password),
            display,
            datetime.now().isoformat(timespec="seconds"),
        ),
    )
    conn.commit()
    return {"user_id": user_id, "username": username, "display": display}


def authenticate(
    conn: sqlite3.Connection, username: str, password: str
) -> Optional[dict[str, Any]]:
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username.strip(),)).fetchone()
    if not row:
        return None
    if not verify_password(password, row["password"]):
        return None
    return {"user_id": row["user_id"], "username": row["username"], "display": row["display"]}


def create_session(conn: sqlite3.Connection, user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    now = datetime.now()
    expires = now + timedelta(days=_SESSION_DAYS)
    conn.execute(
        "INSERT INTO auth_tokens (token, user_id, created_at, expires_at) "
        "VALUES (?,?,?,?)",
        (
            token,
            user_id,
            now.isoformat(timespec="seconds"),
            expires.isoformat(timespec="seconds"),
        ),
    )
    conn.commit()
    return token


def user_from_token(
    conn: sqlite3.Connection, token: Optional[str]
) -> Optional[dict[str, Any]]:
    if not token:
        return None
    row = conn.execute("SELECT * FROM auth_tokens WHERE token = ?", (token,)).fetchone()
    if not row:
        return None
    if datetime.now() >= datetime.fromisoformat(row["expires_at"]):
        conn.execute("DELETE FROM auth_tokens WHERE token = ?", (token,))
        conn.commit()
        return None
    u = conn.execute(
        "SELECT user_id, username, display FROM users WHERE user_id = ?",
        (row["user_id"],),
    ).fetchone()
    if not u:
        return None
    return {"user_id": u["user_id"], "username": u["username"], "display": u["display"]}


def delete_session(conn: sqlite3.Connection, token: Optional[str]) -> None:
    if token:
        conn.execute("DELETE FROM auth_tokens WHERE token = ?", (token,))
        conn.commit()
