#!/usr/bin/env python3
"""
Direct fix for Workspace3Col.tsx - use sed
"""
import os, subprocess

BUILDANY_DIR = "/root/buildany"
os.chdir(BUILDANY_DIR)

print("🔧 Direct fix for Workspace3Col.tsx")

# Use sed to replace the exact line
result = subprocess.run([
    "sed", "-i",
    's/const responseText = data.response || data.message || "No response";/const responseText = data.content || data.response || data.message || "No response";/g',
    "src/components/Workspace3Col.tsx"
], capture_output=True, text=True)

# Verify
with open("src/components/Workspace3Col.tsx") as f:
    content = f.read()

if 'data.content || data.response || data.message' in content:
    print("✅ Fix applied to Workspace3Col.tsx")
    
    # Git add
    subprocess.run(["git", "add", "src/components/Workspace3Col.tsx"])
    subprocess.run(["git", "commit", "-m", "fix: Workspace3Col use data.content"])
    
    # Build
    print("\n🔨 Building...")
    build = subprocess.run(["npm", "run", "build"], capture_output=True, text=True)
    if build.returncode == 0:
        print("✅ BUILD SUCCESS!")
        subprocess.run(["pm2", "restart", "buildany"])
        print("🚀 Restarted! Morgan chat should work now!")
    else:
        print("❌ BUILD FAILED")
        print(build.stderr[-500:])
else:
    print("❌ Fix NOT applied - checking file...")
    # Show lines around the issue
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'responseText' in line:
            print(f"Line {i+1}: {line}")
