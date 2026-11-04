-- Migration: Add progress_percent column to jobs table
-- Date: 2026-11-04
-- Description: Adds progress tracking support for generation jobs

-- Add progress_percent column (defaults to 0 for existing rows)
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS progress_percent INTEGER DEFAULT 0;

-- Update existing jobs to have 0% progress
UPDATE jobs SET progress_percent = 0 WHERE progress_percent IS NULL;

-- For PostgreSQL: Add comment
COMMENT ON COLUMN jobs.progress_percent IS 'Job progress percentage (0-100)';

-- Verify
SELECT column_name, data_type, column_default 
FROM information_schema.columns 
WHERE table_name = 'jobs' AND column_name = 'progress_percent';
