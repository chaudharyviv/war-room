-- Add collaboration columns to incidents table (missing after schema update)
-- Run this against your PostgreSQL database, e.g.:
--   psql $DATABASE_URL -f add_collaboration_columns.sql
--   or execute in your DB client

ALTER TABLE incidents
  ADD COLUMN IF NOT EXISTS collaboration_active BOOLEAN DEFAULT false,
  ADD COLUMN IF NOT EXISTS collaboration_teams JSONB DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS collaboration_consensus JSONB NULL;
