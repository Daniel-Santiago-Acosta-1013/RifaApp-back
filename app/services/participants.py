from __future__ import annotations

import uuid

from app.models.schemas import ParticipantCreate


def get_or_create_participant(conn, participant: ParticipantCreate) -> uuid.UUID:
    cur = conn.cursor()
    participant_id: uuid.UUID
    if participant.email:
        cur.execute("SELECT id FROM participants WHERE email = %s", (participant.email,))
        row = cur.fetchone()
        if row:
            participant_id = row[0]
            cur.close()
            return participant_id
    participant_id = uuid.uuid4()
    cur.execute(
        "INSERT INTO participants (id, name, email) VALUES (%s, %s, %s)",
        (participant_id, participant.name, participant.email),
    )
    cur.close()
    return participant_id
