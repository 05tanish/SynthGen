-- Migration: Add database constraints and enums
-- Description: Adds CHECK constraints, proper column types, cascade deletes, and job status enum
-- Date: 2026-09-14

-- ============================================================================
-- 1. Add Job Status Enum Type (SQLite uses TEXT with CHECK constraint)
-- ============================================================================

-- For PostgreSQL (if used):
-- CREATE TYPE job_status_enum AS ENUM ('pending', 'running', 'completed', 'failed');

-- For SQLite, the enum is enforced via CHECK constraint in the model

-- ============================================================================
-- 2. Update Job Table
-- ============================================================================

-- Add ON DELETE CASCADE for foreign keys (requires table recreation in SQLite)
-- This ensures that when a user or dataset is deleted, related jobs are also deleted

-- Note: In SQLite, modifying constraints requires recreating the table
-- The application models now include proper constraints that will be applied on fresh DB creation

-- ============================================================================
-- 3. Update Dataset Table
-- ============================================================================

-- Add CHECK constraints for datasets:
-- - row_count: must be between 1 and 30,000
-- - column_count: must be between 1 and 100  
-- - prompt: max 2,000 characters

-- SQLite example (applied via SQLAlchemy model):
-- ALTER TABLE datasets ADD CONSTRAINT check_row_count_valid CHECK (row_count > 0 AND row_count <= 30000);
-- ALTER TABLE datasets ADD CONSTRAINT check_column_count_valid CHECK (column_count > 0 AND column_count <= 100);
-- ALTER TABLE datasets ADD CONSTRAINT check_prompt_length CHECK (length(prompt) <= 2000);

-- ============================================================================
-- 4. Update User Table
-- ============================================================================

-- Add CHECK constraint for OTP attempts (0-10 range)
-- ALTER TABLE users ADD CONSTRAINT check_otp_attempts_range CHECK (otp_attempts >= 0 AND otp_attempts <= 10);

-- ============================================================================
-- 5. Add Indexes for Performance
-- ============================================================================

-- Composite index for user + created_at on datasets (for pagination)
CREATE INDEX IF NOT EXISTS ix_datasets_user_created ON datasets(user_id, created_at DESC);

-- Composite index for user email + verification status
CREATE INDEX IF NOT EXISTS ix_users_email_verified ON users(email, is_verified);

-- Index on job dataset_id for cascade operations
CREATE INDEX IF NOT EXISTS ix_jobs_dataset_id ON jobs(dataset_id);

-- ============================================================================
-- NOTES FOR EXISTING DATABASES
-- ============================================================================

-- If you have an existing database with data:
-- 1. Back up your database first
-- 2. Check for any existing data that violates the new constraints:
--    - Datasets with row_count outside 1-30,000 range
--    - Datasets with column_count outside 1-100 range
--    - Datasets with prompts longer than 2,000 chars
--    - Users with otp_attempts outside 0-10 range
--    - Jobs with status not in ('pending', 'running', 'completed', 'failed')
-- 3. Clean or migrate that data before applying constraints
-- 4. For SQLite, you may need to use the following pattern to add constraints:
--    a. Create new table with constraints
--    b. Copy data from old table
--    c. Drop old table
--    d. Rename new table

-- Example validation queries:
-- SELECT * FROM datasets WHERE row_count < 1 OR row_count > 30000;
-- SELECT * FROM datasets WHERE column_count < 1 OR column_count > 100;
-- SELECT * FROM datasets WHERE length(prompt) > 2000;
-- SELECT * FROM users WHERE otp_attempts < 0 OR otp_attempts > 10;
-- SELECT * FROM jobs WHERE status NOT IN ('pending', 'running', 'completed', 'failed');

-- ============================================================================
-- ROLLBACK (if needed)
-- ============================================================================

-- To remove constraints (SQLite requires table recreation):
-- DROP INDEX IF EXISTS ix_datasets_user_created;
-- DROP INDEX IF EXISTS ix_users_email_verified;
-- DROP INDEX IF EXISTS ix_jobs_dataset_id;

-- Then recreate tables without constraints using old schema
