#!/bin/bash
# Script to clean up duplicate records and rerun migrations

# Define variables
PROJECT_DIR="/Users/ruchirkulkarni/Library/CloudStorage/OneDrive-CalfusTechnologiesIndiaPrivateLimited/ERP Codes/LensOra/Code"
DB_USER="lensora"
DB_NAME="lensora"
DB_PORT="5433"
DOCKER_CONTAINER="code-lensora_db-1"

echo "====== LensOra Database Cleanup Script ======"
echo "This script will clean up duplicate entries in the validations_log table"
echo "and then rerun the alembic migration to add the unique constraint."

# Step 1: Copy the cleanup SQL to the Docker container
echo -e "\n[1/4] Copying cleanup SQL to Docker container..."
docker cp ${PROJECT_DIR}/cleanup_duplicates.sql ${DOCKER_CONTAINER}:/tmp/

# Step 2: Execute the SQL script in the container
echo -e "\n[2/4] Executing cleanup script in container..."
docker exec -it ${DOCKER_CONTAINER} psql -U ${DB_USER} -d ${DB_NAME} -f /tmp/cleanup_duplicates.sql

# Step 3: Run the alembic migration
echo -e "\n[3/4] Running alembic migrations..."
cd ${PROJECT_DIR} && alembic upgrade head

# Step 4: Verify the unique constraint is in place
echo -e "\n[4/4] Verifying the unique constraint..."
docker exec -it ${DOCKER_CONTAINER} psql -U ${DB_USER} -d ${DB_NAME} -c \
"SELECT c.conname AS constraint_name 
FROM pg_constraint c
JOIN pg_class t ON c.conrelid = t.oid
JOIN pg_namespace s ON t.relnamespace = s.oid
WHERE t.relname = 'validations_log' 
AND c.contype = 'u';"

echo -e "\nCleanup and migration process completed!"