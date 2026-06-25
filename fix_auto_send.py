#!/usr/bin/env python3
"""
Fix auto-send prompt from URL - remove chatMessages.length > 0 check
"""
import os

BUILDANY_DIR = "/root/buildany"
os.chdir(BUILDANY_DIR)

print("🔧 Fixing auto-send prompt logic...")

with open("src/components/Workspace3Col.tsx") as f:
    content = f.read()

# Find and fix the condition
old = "if (promptFromUrl && !autoSentRef.current && chatMessages.length > 0) {"
new = "if (promptFromUrl && !autoSentRef.current) {"

if old in content:
    content = content.replace(old, new)
    print("✅ Removed chatMessages.length > 0 check")
    
    with open("src/components/Workspace3Col.tsx", "w") as f:
        f.write(content)
    
    # Commit and build
    os.system("git add src/components/Workspace3Col.tsx")
    os.system("git commit -m 'fix: auto-send prompt from URL without chat length check'")
    
    print("\n🔨 Building...")
    result = os.system("npm run build")
    
    if result == 0:
        print("\n✅ BUILD SUCCESS!")
        os.system("pm2 restart buildany")
        print("🚀 BuildAny restarted!")
        print("\n💡 Now the prompt from homepage will auto-send to Morgan!")
    else:
        print("\n❌ BUILD FAILED")
        exit(1)
else:
    print("⚠️ Pattern not found - checking current code...")
    # Show the relevant section
    if "autoSentRef" in content:
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if "autoSentRef" in line:
                print(f"Line {i}: {line.strip()}")
                for j in range(i, min(i+5, len(lines))):
                    print(f"  {j}: {lines[j].strip()}")
                break
