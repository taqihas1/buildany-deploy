#!/usr/bin/env python3
"""
Verify the generated project works
"""
import os, requests

PROJECT_ID = "0dcad071-0b51-46be-ae6b-cbbfa31a8c4a"
PROJECT_DIR = f"/data/projects/{PROJECT_ID}"

print("=" * 60)
print("🔍 Verifying Generated Project")
print("=" * 60)

# 1. Check files exist
print("\n1. Files generated:")
for root, dirs, files in os.walk(os.path.join(PROJECT_DIR, "src")):
    for f in files:
        print(f"   ✅ {os.path.join(root, f).replace(PROJECT_DIR, '')}")

# 2. Check build output
out_dir = os.path.join(PROJECT_DIR, "out")
if os.path.exists(out_dir):
    print(f"\n2. Build output exists: {out_dir}")
    for f in os.listdir(out_dir):
        print(f"   📄 {f}")
else:
    print(f"\n2. ❌ No build output at {out_dir}")

# 3. Check if preview API can serve it
print("\n3. Testing preview API...")
try:
    res = requests.get(f"http://localhost:3000/api/preview/{PROJECT_ID}", timeout=10)
    print(f"   Status: {res.status_code}")
    if res.status_code == 200:
        print("   ✅ Preview is accessible!")
    else:
        print(f"   ⚠️ Response: {res.text[:100]}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# 4. Check project status in DB
print("\n4. Project status:")
import sqlite3
conn = sqlite3.connect("/root/buildany/sqlite.db")
cursor = conn.cursor()
cursor.execute("SELECT status, name FROM projects WHERE id = ?", (PROJECT_ID,))
row = cursor.fetchone()
if row:
    print(f"   Status: {row[0]}")
    print(f"   Name: {row[1]}")
else:
    print("   ❌ Project not found in DB")
conn.close()

print("\n✅ Verification complete!")
