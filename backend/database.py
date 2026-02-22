# ============================================================
# database.py
# ============================================================

import os
import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not configured")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(
    DATABASE_URL,
    pool_size=3,
    max_overflow=2,
    echo=False
)

AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def run_schema_migrations():
    """
    Add any missing columns to existing tables (e.g. after code deploy).
    Safe to run on every startup; Render and other hosts pick this up automatically.
    """
    async with engine.begin() as conn:
        await conn.execute(text("""
            ALTER TABLE incidents
            ADD COLUMN IF NOT EXISTS collaboration_active BOOLEAN DEFAULT false,
            ADD COLUMN IF NOT EXISTS collaboration_teams JSONB DEFAULT '[]'::jsonb,
            ADD COLUMN IF NOT EXISTS collaboration_consensus JSONB NULL
        """))
    logger.info("✅ Schema migrations applied (collaboration columns)")