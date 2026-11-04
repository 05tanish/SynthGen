#!/bin/bash
# Script to run database migrations on Railway
# Usage: ./run_migration.sh [migration_file.sql]

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}SynthGen Database Migration Runner${NC}"
echo ""

# Check if migration file is provided
if [ -z "$1" ]; then
    echo -e "${RED}Error: No migration file specified${NC}"
    echo "Usage: ./run_migration.sh <migration_file.sql>"
    echo ""
    echo "Available migrations:"
    ls -1 *.sql
    exit 1
fi

MIGRATION_FILE="$1"

# Check if file exists
if [ ! -f "$MIGRATION_FILE" ]; then
    echo -e "${RED}Error: Migration file '$MIGRATION_FILE' not found${NC}"
    exit 1
fi

echo -e "Migration file: ${YELLOW}$MIGRATION_FILE${NC}"
echo ""

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo -e "${YELLOW}DATABASE_URL not found in environment${NC}"
    echo "Please provide your Railway PostgreSQL connection string:"
    echo "(Format: postgresql://user:pass@host:5432/dbname)"
    read -r DATABASE_URL
fi

# Confirm before running
echo ""
echo -e "${YELLOW}WARNING: You are about to run this migration on the database:${NC}"
echo "$DATABASE_URL" | sed 's/:\/\/.*@/:\/\/***:***@/'  # Hide password
echo ""
echo "Migration preview:"
head -n 20 "$MIGRATION_FILE"
echo ""
read -p "Continue with migration? (yes/no): " -r
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "Migration cancelled"
    exit 0
fi

# Run migration
echo ""
echo -e "${GREEN}Running migration...${NC}"

if psql "$DATABASE_URL" -f "$MIGRATION_FILE"; then
    echo ""
    echo -e "${GREEN}✓ Migration completed successfully!${NC}"
    
    # If this is the progress column migration, verify it
    if [[ "$MIGRATION_FILE" == *"progress"* ]]; then
        echo ""
        echo "Verifying progress_percent column..."
        psql "$DATABASE_URL" -c "SELECT column_name, data_type, column_default FROM information_schema.columns WHERE table_name = 'jobs' AND column_name = 'progress_percent';"
    fi
else
    echo ""
    echo -e "${RED}✗ Migration failed!${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}Done! You can now deploy your updated application code.${NC}"
