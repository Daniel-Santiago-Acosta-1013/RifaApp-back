from __future__ import annotations


def ensure_schema(conn) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS raffles (
            id uuid PRIMARY KEY,
            title text NOT NULL,
            description text,
            ticket_price numeric(10,2) NOT NULL CHECK (ticket_price > 0),
            currency text NOT NULL DEFAULT 'USD',
            total_tickets int NOT NULL CHECK (total_tickets > 0),
            status text NOT NULL DEFAULT 'open',
            draw_at timestamptz,
            winner_ticket_id uuid,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        );
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS participants (
            id uuid PRIMARY KEY,
            name text NOT NULL,
            email text UNIQUE,
            created_at timestamptz NOT NULL DEFAULT now()
        );
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS tickets (
            id uuid PRIMARY KEY,
            raffle_id uuid NOT NULL REFERENCES raffles(id) ON DELETE CASCADE,
            participant_id uuid NOT NULL REFERENCES participants(id),
            number int NOT NULL,
            status text NOT NULL DEFAULT 'paid',
            purchased_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (raffle_id, number)
        );
        """
    )
    conn.commit()
    cur.close()
