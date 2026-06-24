#!/usr/bin/env python3
"""
Fix Workspace3Col.tsx - Morgan chat response field
"""
import os

BUILDANY_DIR = "/root/buildany"
os.chdir(BUILDANY_DIR)

WS_PATH = "src/components/Workspace3Col.tsx"
with open(WS_PATH) as f:
    content = f.read()

# Fix the exact line
content = content.replace(
    'const responseText = data.response || data.message || "No response";',
    'const responseText = data.content || data.response || data.message || "No response";'
)

with open(WS_PATH, "w") as f:
    f.write(content)

print("✅ Fixed Workspace3Col.tsx")

# Commit and build
os.system("git add " + WS_PATH)
os.system('git commit -m "fix: Workspace3Col use data.content for Morgan"')

print("\n🔨 Building...")
build_result = os.system("npm run build")

if build_result == 0:
    print("\n✅ BUILD SUCCESS!")
    os.system("pm2 restart buildany")
    print("🚀 Morgan chat FIXED! Try it now!")
else:
    print("\n❌ BUILD FAILED")
    exit(1)
