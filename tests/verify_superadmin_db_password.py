#!/usr/bin/env python3
"""Focused DB verification for lcorreaq@gmail.com password reset bug."""
import asyncio
import json
import os
from pathlib import Path

import bcrypt
from motor.motor_asyncio import AsyncIOMotorClient


APP_DIR = Path("/app")
REPORT_DIR = APP_DIR / "test_reports"
EMAIL = "lcorreaq@gmail.com"
NEW_PASSWORD = "IUDigital2026"
OLD_PASSWORD = "Chocolate2026!"


def load_env(path: Path):
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ[key] = value.strip().strip('"').strip("'")


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


async def main():
    load_env(APP_DIR / "backend" / ".env")
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]
    user = await db.users.find_one({"email": EMAIL}, {"_id": 0, "password": 1, "role": 1, "active": 1, "must_change_password": 1, "email": 1})
    result = {"email": EMAIL, "checks": {}, "passed": False}
    try:
        result["checks"]["user_exists"] = bool(user)
        result["checks"]["role_superadmin"] = user and user.get("role") == "superadmin"
        result["checks"]["active_true"] = user and user.get("active") is True
        result["checks"]["must_change_password_false"] = user and user.get("must_change_password") is False
        password_hash = user.get("password") if user else ""
        result["checks"]["bcrypt_hash_present"] = password_hash.startswith(("$2a$", "$2b$", "$2y$"))
        result["checks"]["new_password_matches_hash"] = bool(user and verify_password(NEW_PASSWORD, password_hash))
        result["checks"]["old_password_rejected_by_hash"] = bool(user and not verify_password(OLD_PASSWORD, password_hash))
        result["passed"] = all(result["checks"].values())
    finally:
        client.close()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "superadmin_db_password_result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
