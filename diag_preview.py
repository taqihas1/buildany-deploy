#!/usr/bin/env python3
"""
Diagnose why preview didn't generate for a BuildAny project.
Checks DB, files, and preview HTML.

Usage:
  curl -fsSL https://raw.githubusercontent.com/taqihas1/buildany-deploy/master/diag_preview.py | python3
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
    DB_PATH = "/root/buildany/sqlite.db"

print(f"[INFO] Project: {PROJECT}")
print(f"[INFO] DB: {DB_PATH}")
print("="*60)

if not os.path.exists(DB_PATH):
    print("[ERROR] DB not found!")
    sys.exit(1)

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Get latest project
cursor.execute("SELECT id, name, status, prompt, updated_at FROM projects ORDER BY updated_at DESC LIMIT 5;")
projects = cursor.fetchall()

print(f"\n[PROJECTS] Latest 5 projects:")
for p in projects:
    print(f"  {p['id']} | {p['name']} | status={p['status']} | updated={p['updated_at']}")

if not projects:
    print("[ERROR] No projects found in DB!")
    sys.exit(1)

# Use the most recently updated project
latest = projects[0]
project_id = latest['id']
print(f"\n[CHECKING] Project: {project_id} (name: {latest['name']})")
print("="*60)

# Check project_files
cursor.execute('SELECT id, path, LENGTH(content) as content_length, language, is_generated FROM project_files WHERE project_id = ? ORDER BY path;', (project_id,))
files = cursor.fetchall()

print(f"\n[FILES] {len(files)} files in project_files table:")
if files:
    for f in files:
        gen = "[GEN]" if f['is_generated'] else "[SRC]"
        print(f"  {gen} {f['path']} ({f['content_length']} bytes, {f['language']})")
else:
    print("  [NONE] No files found!")

# Check if preview HTML exists
public_dir = os.path.join(PROJECT, "public")
preview_file = os.path.join(public_dir, f"preview-{project_id}.html")
print(f"\n[PREVIEW] Checking: {preview_file}")
print(f"  Exists: {os.path.exists(preview_file)}")
if os.path.exists(preview_file):
    size = os.path.getsize(preview_file)
    print(f"  Size: {size} bytes")
    with open(preview_file, 'r') as f:
        first_line = f.readline().strip()
    print(f"  First line: {first_line[:100]}")
else:
    # Check all preview files
    previews = [f for f in os.listdir(public_dir) if f.startswith('preview-')] if os.path.exists(public_dir) else []
    print(f"  Other previews in public/: {previews}")

# Check conversations for build messages
cursor.execute('SELECT role, content, model, created_at FROM conversations WHERE project_id = ? ORDER BY created_at DESC LIMIT 10;', (project_id,))
convos = cursor.fetchall()

print(f"\n[CONVERSATIONS] Last 10 messages:")
for c in convos:
    content_preview = c['content'][:100] if c['content'] else "(empty)"
    print(f"  [{c['role']}] {content_preview}... (model: {c['model']})")

# Check tasks
cursor.execute('SELECT title, status, type, error_log FROM tasks WHERE project_id = ? ORDER BY created_at DESC LIMIT 10;', (project_id,))
tasks = cursor.fetchall()

print(f"\n[TASKS] {len(tasks)} tasks:")
for t in tasks:
    err = f" | ERROR: {t['error_log'][:100]}" if t['error_log'] else ""
    print(f"  [{t['status']}] {t['title']} ({t['type']}){err}")

# Check code_reviews
cursor.execute('SELECT id, status, result, error_message, created_at FROM code_reviews WHERE project_id = ? ORDER BY created_at DESC LIMIT 3;', (project_id,))
reviews = cursor.fetchall()
print(f"\n[CODE REVIEWS] {len(reviews)} reviews:")
for r in reviews:
    err = f" | ERROR: {r['error_message'][:100]}" if r['error_message'] else ""
    print(f"  [{r['status']}] {err}")

conn.close()

print("\n" + "="*60)
print("DIAGNOSIS:")
print("="*60)
if not files:
    print("❌ NO FILES GENERATED — Kelly's code generation failed")
    print("   Check PM2 logs for LLM API errors")
elif not os.path.exists(preview_file):
    print("⚠️  FILES EXIST but PREVIEW HTML was not created")
    print("   The generateAndServePreview() function failed")
    print("   Check PM2 logs for preview generation errors")
else:
    print("✅ Files AND preview exist")
    print("   Preview might not be showing due to frontend issue")

print("\nTo check PM2 logs:")
print("  pm2 logs buildany --lines 100 --nostream")
print("="*60)
