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
            number_start int NOT NULL DEFAULT 1,
            number_padding int,
            draw_at timestamptz,
            winner_ticket_id uuid,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        );
        """
    )
    cur.execute(
        "ALTER TABLE raffles ADD COLUMN IF NOT EXISTS number_start int NOT NULL DEFAULT 1;"
    )
    cur.execute("ALTER TABLE raffles ADD COLUMN IF NOT EXISTS number_padding int;")
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
        CREATE TABLE IF NOT EXISTS users (
            id uuid PRIMARY KEY,
            name text NOT NULL,
            email text NOT NULL UNIQUE,
            password_hash text NOT NULL,
            password_salt text NOT NULL,
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
            reserved_at timestamptz,
            reserved_until timestamptz,
            reservation_id uuid,
            purchase_id uuid,
            purchased_at timestamptz DEFAULT now(),
            UNIQUE (raffle_id, number)
        );
        """
    )
    cur.execute("ALTER TABLE tickets ALTER COLUMN purchased_at DROP NOT NULL;")
    cur.execute("ALTER TABLE tickets ADD COLUMN IF NOT EXISTS reserved_at timestamptz;")
    cur.execute(
        "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS reserved_until timestamptz;"
    )
    cur.execute("ALTER TABLE tickets ADD COLUMN IF NOT EXISTS reservation_id uuid;")
    cur.execute("ALTER TABLE tickets ADD COLUMN IF NOT EXISTS purchase_id uuid;")
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS purchases (
            id uuid PRIMARY KEY,
            raffle_id uuid NOT NULL REFERENCES raffles(id) ON DELETE CASCADE,
            participant_id uuid NOT NULL REFERENCES participants(id),
            status text NOT NULL DEFAULT 'confirmed',
            total_price numeric(10,2) NOT NULL CHECK (total_price >= 0),
            currency text NOT NULL,
            payment_method text,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        );
        """
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS purchases_participant_id_idx ON purchases (participant_id);"
    )
    conn.commit()
    cur.close()
