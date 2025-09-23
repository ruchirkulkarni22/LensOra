-- Cleanup script to remove duplicate entries in validations_log table
-- Step 1: Find the duplicates and keep only the one with the highest ID
WITH ranked_rows AS (
    SELECT 
        id,
        ticket_key,
        ROW_NUMBER() OVER (PARTITION BY ticket_key ORDER BY id DESC) as row_num
    FROM 
        validations_log
)
DELETE FROM validations_log
WHERE id IN (
    SELECT id FROM ranked_rows WHERE row_num > 1
);

-- Step 2: Verify no more duplicates exist
SELECT ticket_key, COUNT(*) 
FROM validations_log 
GROUP BY ticket_key 
HAVING COUNT(*) > 1;
