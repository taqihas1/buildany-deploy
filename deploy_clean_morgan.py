#!/usr/bin/env python3
"""
Deploy the clean morgan-generate route.ts
"""
import os, subprocess

BUILDANY_DIR = "/root/buildany"
os.chdir(BUILDANY_DIR)

print("🔧 Deploying clean morgan-generate...")

# The file was already written by the assistant, just commit and build
os.system("git add src/app/api/morgan-generate/route.ts")
os.system("git commit -m 'fix: clean sanitizer with proper regex'")

print("\n🔨 Building...")
result = subprocess.run(["npm", "run", "build"], capture_output=True, text=True)

if result.returncode == 0:
    print("\n✅ BUILD SUCCESS!")
    os.system("pm2 restart buildany")
    print("🚀 BuildAny restarted!")
else:
    print("\n❌ BUILD FAILED")
    print(result.stdout[-1000:])
    print(result.stderr[-500:])
    exit(1)
