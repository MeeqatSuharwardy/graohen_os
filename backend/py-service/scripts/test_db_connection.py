#!/usr/bin/env python3
"""
Test database connection. Run from backend/py-service: python3 scripts/test_db_connection.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(_env_path)

from app.config import settings
from app.core.database import init_db, close_db


async def main():
    if not settings.DATABASE_URL:
        print("FAIL: DATABASE_URL not set in .env")
        sys.exit(1)
    print("Testing database connection...")
    try:
        await init_db()
        await close_db()
        print("OK: Database connection successful")
        sys.exit(0)
    except Exception as e:
        print(f"FAIL: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
