from __future__ import annotations

import secrets

from fastapi import HTTPException

from app.core.security import hash_password
from app.db.connection import fetch_one
from app.models.schemas import UserLogin


def login_user(payload: UserLogin) -> dict:
    row = fetch_one(
        """
        SELECT id, name, email, password_hash, password_salt, created_at
        FROM users
        WHERE email = %s
        """,
        (payload.email,),
    )
    if not row:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    salt = bytes.fromhex(row["password_salt"])
    password_hash = hash_password(payload.password, salt)
    if not secrets.compare_digest(row["password_hash"], password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {
        "id": str(row["id"]),
        "name": row["name"],
        "email": row["email"],
        "created_at": row["created_at"],
    }
