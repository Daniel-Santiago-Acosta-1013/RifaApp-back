BEGIN;

CREATE TABLE IF NOT EXISTS raffles_read (
    id uuid PRIMARY KEY,
    title text NOT NULL,
    description text,
    ticket_price numeric(10,2) NOT NULL,
    currency text NOT NULL,
    total_tickets int NOT NULL,
    status text NOT NULL,
    draw_at timestamptz,
    winner_ticket_id uuid,
    number_start int NOT NULL,
    number_end int NOT NULL,
    number_padding int,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL
);

CREATE INDEX IF NOT EXISTS raffles_read_status_idx ON raffles_read (status);

CREATE TABLE IF NOT EXISTS raffle_numbers_read (
    raffle_id uuid NOT NULL REFERENCES raffles(id) ON DELETE CASCADE,
    number int NOT NULL,
    status text NOT NULL DEFAULT 'available',
    reserved_until timestamptz,
    reservation_id uuid,
    purchase_id uuid,
    participant_id uuid,
    label text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (raffle_id, number)
);

CREATE INDEX IF NOT EXISTS raffle_numbers_read_status_idx ON raffle_numbers_read (raffle_id, status);
CREATE INDEX IF NOT EXISTS raffle_numbers_read_reserved_idx ON raffle_numbers_read (raffle_id, status, reserved_until);

CREATE TABLE IF NOT EXISTS purchases_read (
    purchase_id uuid PRIMARY KEY,
    raffle_id uuid NOT NULL,
    participant_id uuid NOT NULL,
    raffle_title text NOT NULL,
    raffle_status text NOT NULL,
    numbers int[] NOT NULL DEFAULT '{}',
    total_price numeric(10,2) NOT NULL,
    currency text NOT NULL,
    status text NOT NULL,
    payment_method text,
    created_at timestamptz NOT NULL
);

CREATE INDEX IF NOT EXISTS purchases_read_participant_idx ON purchases_read (participant_id);

INSERT INTO raffles_read (
    id, title, description, ticket_price, currency, total_tickets, status,
    draw_at, winner_ticket_id, number_start, number_end, number_padding,
    created_at, updated_at
)
SELECT r.id,
       r.title,
       r.description,
       r.ticket_price,
       r.currency,
       r.total_tickets,
       r.status,
       r.draw_at,
       r.winner_ticket_id,
       COALESCE(r.number_start, 1) AS number_start,
       COALESCE(r.number_start, 1) + r.total_tickets - 1 AS number_end,
       r.number_padding,
       r.created_at,
       r.updated_at
FROM raffles r
ON CONFLICT (id) DO NOTHING;

INSERT INTO raffle_numbers_read (
    raffle_id,
    number,
    status,
    reserved_until,
    reservation_id,
    purchase_id,
    participant_id,
    label,
    updated_at
)
SELECT r.id,
       n,
       CASE
           WHEN t.status IN ('paid', 'sold') THEN 'sold'
           WHEN t.status = 'reserved' AND t.reserved_until > now() THEN 'reserved'
           ELSE 'available'
       END AS status,
       CASE
           WHEN t.status = 'reserved' AND t.reserved_until > now() THEN t.reserved_until
           ELSE NULL
       END AS reserved_until,
       CASE
           WHEN t.status = 'reserved' AND t.reserved_until > now() THEN t.reservation_id
           ELSE NULL
       END AS reservation_id,
       CASE
           WHEN t.status IN ('paid', 'sold') THEN t.purchase_id
           ELSE NULL
       END AS purchase_id,
       CASE
           WHEN t.status IN ('reserved', 'paid', 'sold') THEN t.participant_id
           ELSE NULL
       END AS participant_id,
       CASE
           WHEN r.number_padding IS NULL THEN n::text
           ELSE lpad(n::text, r.number_padding, '0')
       END AS label,
       now() AS updated_at
FROM raffles r
CROSS JOIN LATERAL generate_series(
    COALESCE(r.number_start, 1),
    COALESCE(r.number_start, 1) + r.total_tickets - 1
) AS n
LEFT JOIN tickets t
  ON t.raffle_id = r.id AND t.number = n
ON CONFLICT (raffle_id, number) DO NOTHING;

INSERT INTO purchases_read (
    purchase_id,
    raffle_id,
    participant_id,
    raffle_title,
    raffle_status,
    numbers,
    total_price,
    currency,
    status,
    payment_method,
    created_at
)
SELECT p.id,
       p.raffle_id,
       p.participant_id,
       r.title,
       r.status,
       COALESCE(array_agg(t.number ORDER BY t.number) FILTER (WHERE t.number IS NOT NULL), '{}') AS numbers,
       p.total_price,
       p.currency,
       p.status,
       p.payment_method,
       p.created_at
FROM purchases p
JOIN raffles r ON r.id = p.raffle_id
LEFT JOIN tickets t ON t.purchase_id = p.id
GROUP BY p.id, r.title, r.status
ON CONFLICT (purchase_id) DO NOTHING;

COMMIT;
