#!/usr/bin/env python3
"""
Diagnose and fix SQLite schema mismatch on base66.cloud.
Checks actual DB schema vs expected schema.

Usage:
  curl -fsSL https://raw.githubusercontent.com/taqihas1/buildany-deploy/master/fix_schema_mismatch.py | python3
"""

import os
import sys
import sqlite3
import json

def find_project():
    candidates = ["/root/buildany", "/root/buildany-fix", "/var/www/buildany"]
    for c in candidates:
        if os.path.exists(os.path.join(c, "package.json")):
            return c
    try:
        import subprocess
        r = subprocess.run(["pm2", "describe", "buildany"], capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            for line in r.stdout.split("\n"):
                if "exec cwd" in line.lower():
                    parts = [p.strip() for p in line.split("│")]
                    if len(parts) >= 3 and os.path.exists(parts[2]):
                        return parts[2]
    except:
        pass
    return None

PROJECT = find_project()
if not PROJECT:
    print("[ERROR] Could not find buildany project.")
    sys.exit(1)

DB_PATH = os.path.join(PROJECT, "sqlite.db")
if not os.path.exists(DB_PATH):
    DB_PATH = "/root/buildany/sqlite.db"  # fallback

print(f"[INFO] Project: {PROJECT}")
print(f"[INFO] DB: {DB_PATH}")
print(f"[INFO] DB exists: {os.path.exists(DB_PATH)}")
print("="*60)

if not os.path.exists(DB_PATH):
    print("[ERROR] DB file not found!")
    print("[FIX] Creating new empty DB with current schema...")
    # The app will create tables on first use via Drizzle
    open(DB_PATH, 'w').close()
    print(f"[FIX] Created empty DB at {DB_PATH}")
    print("[NEXT] pm2 restart buildany")
    sys.exit(0)

# Connect and inspect
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# List all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
tables = cursor.fetchall()
print(f"\n[SCHEMA] Found {len(tables)} tables:")
for (table_name,) in tables:
    print(f"\n  Table: {table_name}")
    cursor.execute(f'PRAGMA table_info("{table_name}");')
    columns = cursor.fetchall()
    for col in columns:
        cid, name, ctype, notnull, dflt, pk = col
        pk_flag = " PK" if pk else ""
        print(f"    - {name} ({ctype}){pk_flag}")

# Check if any table has 'review_data' column
print("\n" + "="*60)
print("SEARCHING for 'review_data' column...")
found = False
for (table_name,) in tables:
    cursor.execute(f'PRAGMA table_info("{table_name}");')
    columns = cursor.fetchall()
    for col in columns:
        if col[1] == "review_data":
            print(f"[FOUND] Table '{table_name}' has column 'review_data'")
            found = True

if not found:
    print("[RESULT] No table has a 'review_data' column in the actual DB.")
    print("[DIAGNOSIS] The app code is trying to query 'review_data' but it doesn't exist.")
    print("[LIKELY CAUSE] The DB schema was updated but the DB file wasn't migrated.")
    print("")
    print("[FIX OPTIONS]:")
    print("  1. DROP the old tables and let Drizzle recreate them (DATA LOSS)")
    print("  2. ALTER TABLE to add missing columns")
    print("  3. Delete the DB file and start fresh (TOTAL DATA LOSS)")
    print("")
    print("  To delete DB and start fresh:")
    print(f"    rm {DB_PATH}")
    print("    pm2 restart buildany")

conn.close()

# Also check if the error might be in codeReviews table specifically
print("\n" + "="*60)
print("CHECKING code_reviews table (most likely culprit)...")
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
try:
    cursor.execute('PRAGMA table_info("code_reviews");')
    cols = cursor.fetchall()
    if cols:
        print(f"[OK] code_reviews exists with {len(cols)} columns:")
        for c in cols:
            print(f"  - {c[1]}")
    else:
        print("[WARN] code_reviews table exists but has no columns?")
except Exception as e:
    print(f"[ERROR] code_reviews table issue: {e}")
conn.close()

print("\n" + "="*60)
print("RECOMMENDED FIX:")
print("="*60)
print("If you don't care about existing data, the fastest fix is:")
print(f"  rm {DB_PATH}")
print("  pm2 restart buildany")
print("")
print("This will create a fresh DB with the correct schema.")
print("="*60)
