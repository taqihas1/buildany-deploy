#!/usr/bin/env python3
"""
Diagnose why project is not showing on homepage and why files are missing.

Usage:
  curl -fsSL https://raw.githubusercontent.com/taqihas1/buildany-deploy/master/diag_project.py | python3
"""

import os
import sys
import sqlite3

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
    DB_PATH = "/root/buildany/sqlite.db"

print(f"[INFO] DB: {DB_PATH}")
print("="*60)

if not os.path.exists(DB_PATH):
    print("[ERROR] DB not found!")
    sys.exit(1)

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Get all projects
cursor.execute("SELECT id, name, user_id, status, prompt, created_at, updated_at FROM projects ORDER BY created_at DESC LIMIT 10;")
projects = cursor.fetchall()

print(f"\n[PROJECTS] {len(projects)} projects in DB:")
for p in projects:
    print(f"  {p['id']} | {p['name']} | user={p['user_id']} | status={p['status']} | updated={p['updated_at']}")

# Count projects by user
if projects:
    cursor.execute("SELECT user_id, COUNT(*) as count FROM projects GROUP BY user_id;")
    user_counts = cursor.fetchall()
    print(f"\n[PROJECTS BY USER]:")
    for uc in user_counts:
        print(f"  user={uc['user_id']}: {uc['count']} projects")

# Check files for the latest project
if projects:
    latest = projects[0]
    print(f"\n[FILES FOR LATEST PROJECT] {latest['id']}:")
    cursor.execute('SELECT path, LENGTH(content) as size, language, is_generated FROM project_files WHERE project_id = ? ORDER BY path;', (latest['id'],))
    files = cursor.fetchall()
    if files:
        print(f"  {len(files)} files:")
        for f in files:
            gen = "[GEN]" if f['is_generated'] else "[SRC]"
            print(f"    {gen} {f['path']} ({f['size']} bytes, {f['language']})")
    else:
        print("  [NONE] No files found for this project!")

# Check conversations for the latest project
if projects:
    latest = projects[0]
    print(f"\n[CONVERSATIONS FOR {latest['id']}]:")
    cursor.execute('SELECT role, content, model, created_at FROM conversations WHERE project_id = ? ORDER BY created_at DESC LIMIT 5;', (latest['id'],))
    convos = cursor.fetchall()
    for c in convos:
        content = c['content'][:80] if c['content'] else "(empty)"
        print(f"  [{c['role']}] {content}... (model: {c['model']})")

# Check tasks for the latest project
if projects:
    latest = projects[0]
    print(f"\n[TASKS FOR {latest['id']}]:")
    cursor.execute('SELECT title, status, type, error_log FROM tasks WHERE project_id = ? ORDER BY created_at DESC LIMIT 5;', (latest['id'],))
    tasks = cursor.fetchall()
    for t in tasks:
        err = f" | ERR: {t['error_log'][:50]}" if t['error_log'] else ""
        print(f"  [{t['status']}] {t['title']} ({t['type']}){err}")

conn.close()

print("\n" + "="*60)
print("DIAGNOSIS:")
print("="*60)
if not projects:
    print("❌ NO PROJECTS IN DB — project creation is failing")
elif not files:
    print("⚠️  Project exists but NO FILES — Kelly failed to generate")
    print("   Check PM2 logs for API key or generation errors")
else:
    print(f"✅ Project has {len(files)} files")
    print("   If not showing in UI, check browser console for errors")

print("\nCheck PM2 logs:")
print("  pm2 logs buildany --lines 50 --nostream")
print("="*60)
