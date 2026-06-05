#!/usr/bin/env python3
"""Audit production SQLite for abuse signals. Run on Fly: fly ssh console -C 'python3 /app/scripts/audit_production_db.py'"""
import os
import sqlite3
from pathlib import Path

DB = os.getenv("DATABASE_PATH", "/data/cineai.db")
if not Path(DB).exists():
    DB = str(Path(__file__).resolve().parents[1] / "cineai.db")


def main():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    print(f"Database: {DB}\n")

    print("=== USERS ===")
    for r in c.execute(
        "SELECT user_id, username, email, signup_date FROM users ORDER BY user_id"
    ):
        print(r)

    print("\n=== INTERACTIONS BY USER (who actually uses the app) ===")
    for r in c.execute(
        """
        SELECT u.user_id, u.username, u.email, COUNT(i.id) AS n,
               MIN(i.created_at), MAX(i.created_at)
        FROM users u
        LEFT JOIN user_interactions i ON i.user_id = u.user_id
        GROUP BY u.user_id
        ORDER BY n DESC
        """
    ):
        print(r)

    print("\n=== RECOMMENDATION SNAPSHOTS (cache regen timestamps) ===")
    for r in c.execute(
        """
        SELECT user_id, kind, generated_at, expires_at
        FROM recommendation_snapshots
        ORDER BY generated_at DESC
        """
    ):
        print(r)

    print("\n=== USERS WITH ACCOUNTS BUT ZERO INTERACTIONS ===")
    for r in c.execute(
        """
        SELECT u.user_id, u.username, u.email, u.signup_date
        FROM users u
        LEFT JOIN user_interactions i ON i.user_id = u.user_id
        WHERE i.id IS NULL
        ORDER BY u.signup_date
        """
    ):
        print(r)

    conn.close()


if __name__ == "__main__":
    main()
