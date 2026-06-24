#!/usr/bin/env python3
"""
Fix Morgan Chat Frontend - Use correct response field
"""
import os, re

BUILDANY_DIR = "/root/buildany"
os.chdir(BUILDANY_DIR)

print("=" * 60)
print("🔧 Fixing Morgan Chat Frontend")
print("=" * 60)

# Fix Workspace3Col.tsx - change data.response to data.content
WS_PATH = "src/components/Workspace3Col.tsx"
with open(WS_PATH) as f:
    content = f.read()

# The bug: frontend uses data.response || data.message || "No response"
# But API returns { content: "..." }
old_pattern = r'const responseText = data\.response \|\| data\.message \|\| "No response";'
new_code = 'const responseText = data.content || data.response || data.message || "No response";'

if old_pattern.replace(r'\.', '.') in content:
    content = content.replace(
        'const responseText = data.response || data.message || "No response";',
        'const responseText = data.content || data.response || data.message || "No response";'
    )
    with open(WS_PATH, "w") as f:
        f.write(content)
    print(f"✅ Fixed: {WS_PATH}")
else:
    print(f"⚠️ Pattern not found in {WS_PATH} - checking...")
    # Try to find the line
    import subprocess
    result = subprocess.run(['grep', '-n', 'responseText', WS_PATH], capture_output=True, text=True)
    print(result.stdout)

# Also check AIChatPanel.tsx if it exists
AICHAT_PATH = "src/components/AIChatPanel.tsx"
if os.path.exists(AICHAT_PATH):
    with open(AICHAT_PATH) as f:
        aichat = f.read()
    if 'data.response' in aichat or 'data.message' in aichat:
        aichat = aichat.replace(
            'data.response || data.message',
            'data.content || data.response || data.message'
        )
        with open(AICHAT_PATH, "w") as f:
            f.write(aichat)
        print(f"✅ Fixed: {AICHAT_PATH}")

# Commit and build
os.system(f"git add {WS_PATH}")
if os.path.exists(AICHAT_PATH):
    os.system(f"git add {AICHAT_PATH}")
os.system('git commit -m "fix: use data.content for Morgan chat responses"')

print("\n🔨 Building...")
build_result = os.system("npm run build")

if build_result == 0:
    print("\n✅ BUILD SUCCESS!")
    os.system("pm2 restart buildany")
    print("🚀 BuildAny restarted!")
    print("\n💡 Morgan chat should now show responses correctly!")
else:
    print("\n❌ BUILD FAILED")
    exit(1)
