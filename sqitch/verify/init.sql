SELECT 1 FROM raffles LIMIT 1;
SELECT 1 FROM participants LIMIT 1;
SELECT 1 FROM users LIMIT 1;
SELECT 1 FROM tickets LIMIT 1;
SELECT 1 FROM purchases LIMIT 1;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'raffles'
          AND column_name = 'number_start'
    ) THEN
        RAISE EXCEPTION 'raffles.number_start is missing';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'raffles'
          AND column_name = 'number_padding'
    ) THEN
        RAISE EXCEPTION 'raffles.number_padding is missing';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'tickets'
          AND column_name = 'purchased_at'
    ) THEN
        RAISE EXCEPTION 'tickets.purchased_at is missing';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'tickets'
          AND column_name = 'reserved_at'
    ) THEN
        RAISE EXCEPTION 'tickets.reserved_at is missing';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'tickets'
          AND column_name = 'reserved_until'
    ) THEN
        RAISE EXCEPTION 'tickets.reserved_until is missing';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'tickets'
          AND column_name = 'reservation_id'
    ) THEN
        RAISE EXCEPTION 'tickets.reservation_id is missing';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'tickets'
          AND column_name = 'purchase_id'
    ) THEN
        RAISE EXCEPTION 'tickets.purchase_id is missing';
    END IF;
END $$;
