#!/usr/bin/env python3
"""
Manually initialize the database (create tables) on the VPS.
Run from backend/py-service: python3 scripts/init_db.py
"""
import asyncio
import sys
from pathlib import Path

# Add project root so app imports work
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Load .env before config
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(_env_path)
    print(f"Loaded .env from {_env_path}")
else:
    print(f"Warning: .env not found at {_env_path}")

from app.config import settings
from app.core.database import init_db, close_db


async def main():
    if not settings.DATABASE_URL:
        print("ERROR: DATABASE_URL not set. Add it to backend/py-service/.env")
        sys.exit(1)
    print("Connecting to database and creating tables...")
    await init_db()
    await close_db()
    print("Done. Tables created: users, drive_files, stored_emails")


if __name__ == "__main__":
    asyncio.run(main())
