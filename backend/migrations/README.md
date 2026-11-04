# Database Migrations

This directory contains SQL migration scripts for the SynthGen application.

## Migration Files

1. **add_constraints_and_enums.sql** - Initial constraints and enums setup
2. **add_progress_column.sql** - Adds progress_percent column to jobs table

## Running Migrations

### For Railway (PostgreSQL)

#### Option 1: Using Railway CLI
```bash
# Login to Railway
railway login

# Link to your project
railway link

# Run migration
railway run psql $DATABASE_URL -f migrations/add_progress_column.sql
```

#### Option 2: Using Railway Dashboard
1. Go to your Railway project dashboard
2. Click on your PostgreSQL database
3. Click "Query" tab
4. Copy and paste the SQL from `add_progress_column.sql`
5. Click "Execute"

#### Option 3: Using psql directly
```bash
# Get DATABASE_URL from Railway dashboard
psql "your-database-url-here" -f migrations/add_progress_column.sql
```

### For Local Development (SQLite)

```bash
# SQLite automatically creates missing columns when using SQLAlchemy
# No manual migration needed - just restart the backend

# Or manually:
sqlite3 backend/agentic.db < migrations/add_progress_column_sqlite.sql
```

### For Local Development (PostgreSQL)

```bash
psql -h localhost -U your_username -d your_database -f migrations/add_progress_column.sql
```

## Verifying Migrations

After running migrations, verify the column exists:

### PostgreSQL
```sql
SELECT column_name, data_type, column_default 
FROM information_schema.columns 
WHERE table_name = 'jobs' AND column_name = 'progress_percent';
```

### SQLite
```sql
PRAGMA table_info(jobs);
```

## Creating New Migrations

When adding new columns or tables:

1. Create a new `.sql` file in this directory
2. Name it descriptively: `add_feature_name.sql`
3. Include date and description in comments
4. Test locally before deploying
5. Document in this README
6. Run on Railway after deployment

## Production Deployment Checklist

Before deploying new code that requires database changes:

1. ✅ Test migration locally
2. ✅ Backup production database (Railway auto-backups)
3. ✅ Run migration on production
4. ✅ Verify migration success
5. ✅ Deploy new application code

## Troubleshooting

### Error: "column does not exist"
This means the migration hasn't been run yet. Run the appropriate migration script.

### Error: "column already exists"
The migration has already been run. You can safely ignore this or add `IF NOT EXISTS` clauses.

### Rollback a Migration
Each migration file should include a rollback section (commented out). Uncomment and run to revert.

## Example: Adding a New Column

```sql
-- Migration: Add new_column to table_name
-- Date: YYYY-MM-DD
-- Description: Purpose of this column

-- Forward migration
ALTER TABLE table_name ADD COLUMN IF NOT EXISTS new_column VARCHAR(255) DEFAULT '';

-- Rollback (commented out)
-- ALTER TABLE table_name DROP COLUMN IF EXISTS new_column;

-- Verify
SELECT column_name, data_type FROM information_schema.columns 
WHERE table_name = 'table_name' AND column_name = 'new_column';
```
