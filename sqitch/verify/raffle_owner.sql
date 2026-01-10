SELECT 1
FROM information_schema.columns
WHERE table_name = 'raffles' AND column_name = 'owner_id';

SELECT 1
FROM information_schema.columns
WHERE table_name = 'raffles_read' AND column_name = 'owner_id';
