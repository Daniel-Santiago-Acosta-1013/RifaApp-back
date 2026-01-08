from __future__ import annotations

import secrets
import uuid

from fastapi import HTTPException

from app.core.security import hash_password
from app.db.connection import run_transaction
from app.models.schemas import UserRegister


def register_user(payload: UserRegister) -> dict:
    def _handler(conn):
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE email = %s", (payload.email,))
        if cur.fetchone():
            cur.close()
            raise HTTPException(status_code=409, detail="Email already registered")
        user_id = uuid.uuid4()
        salt = secrets.token_bytes(16)
        password_hash = hash_password(payload.password, salt)
        cur.execute(
            """
            INSERT INTO users (id, name, email, password_hash, password_salt)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (user_id, payload.name, payload.email, password_hash, salt.hex()),
        )
        cur.execute(
            "SELECT id, name, email, created_at FROM users WHERE id = %s",
            (user_id,),
        )
        row = cur.fetchone()
        cur.close()
        return {
            "id": str(row[0]),
            "name": row[1],
            "email": row[2],
            "created_at": row[3],
        }

    return run_transaction(_handler)
