BEGIN;

SELECT 1 FROM raffles_read LIMIT 1;
SELECT 1 FROM raffle_numbers_read LIMIT 1;
SELECT 1 FROM purchases_read LIMIT 1;

ROLLBACK;
