#!/usr/bin/env python3
"""
Deploy latest BuildAny fixes from sandbox to VPS
- Fixes auto-send (no "hi" needed)
- Fixes inline components (no broken imports)
"""
import subprocess, os, sys

# Files that were changed
FILES_TO_DEPLOY = [
    "/root/buildany/src/app/api/project-chat-init/route.ts",
    "/root/buildany/src/components/Workspace3Col.tsx",
    "/root/buildany/src/app/api/morgan-chat/route.ts",
    "/root/buildany/src/app/api/morgan-generate/route.ts",
]

# Build and restart
os.chdir("/root/buildany")

print("Building BuildAny...")
result = subprocess.run(["npm", "run", "build"], capture_output=True, text=True)
if result.returncode != 0:
    print("❌ Build failed:")
    print(result.stderr[-1000:])
    sys.exit(1)

print("✅ Build successful!")

print("Restarting PM2...")
subprocess.run(["pm2", "restart", "buildany"], check=True)
subprocess.run(["pm2", "save"], check=True)

print("✅ BuildAny restarted with latest fixes!")
print("\nTest:")
print("1. Go to base66.cloud")
print("2. Type: 'I want to build a recipe app'")
print("3. Morgan should auto-reply (no 'hi' needed!)")
