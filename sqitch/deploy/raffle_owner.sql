BEGIN;

ALTER TABLE raffles ADD COLUMN IF NOT EXISTS owner_id uuid REFERENCES users(id);
ALTER TABLE raffles_read ADD COLUMN IF NOT EXISTS owner_id uuid;

UPDATE raffles_read r
SET owner_id = rw.owner_id
FROM raffles rw
WHERE r.id = rw.id
  AND r.owner_id IS NULL;

COMMIT;
