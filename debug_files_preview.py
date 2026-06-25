#!/usr/bin/env python3
"""
Debug why files/preview aren't showing
"""
import os, requests, json

PROJECT_ID = "0dcad071-0b51-46be-ae6b-cbbfa31a8c4a"
PROJECT_DIR = f"/data/projects/{PROJECT_ID}"

print("=" * 60)
print("🔍 Debugging Files/Preview Issue")
print("=" * 60)

# 1. Check if files exist on disk
print("\n1. Files on disk:")
if os.path.exists(PROJECT_DIR):
    for root, dirs, files in os.walk(PROJECT_DIR):
        if "node_modules" in root or ".git" in root:
            continue
        level = root.replace(PROJECT_DIR, '').count(os.sep)
        indent = ' ' * 2 * level
        print(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 2 * (level + 1)
        for f in files[:10]:  # Limit output
            print(f"{subindent}{f}")
        if len(files) > 10:
            print(f"{subindent}... and {len(files)-10} more")
else:
    print("   ❌ Project directory doesn't exist!")

# 2. Check API response
print("\n2. API /api/project-files response:")
try:
    res = requests.get(f"http://localhost:3000/api/project-files?projectId={PROJECT_ID}", timeout=10)
    data = res.json()
    print(f"   Status: {res.status_code}")
    print(f"   Files count: {len(data.get('files', []))}")
    if data.get('files'):
        for f in data['files'][:5]:
            print(f"   📄 {f.get('path', 'unknown')}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# 3. Check project status
print("\n3. Project status:")
try:
    res = requests.get(f"http://localhost:3000/api/project-status?projectId={PROJECT_ID}", timeout=10)
    data = res.json()
    print(f"   Status: {data.get('status', 'unknown')}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# 4. Check build output
print("\n4. Build output (out/ directory):")
out_dir = os.path.join(PROJECT_DIR, "out")
if os.path.exists(out_dir):
    files = os.listdir(out_dir)
    print(f"   Files: {files}")
else:
    print("   ❌ No out/ directory - build didn't produce output")

print("\n✅ Debug complete!")
