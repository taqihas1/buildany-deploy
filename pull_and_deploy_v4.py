#!/usr/bin/env python3
"""
Deploy BuildAny latest code from GitHub to VPS
Force overwrites ALL local changes with remote
"""
import subprocess, os

os.chdir("/root/buildany")

print("Force fetching latest from GitHub...")
subprocess.run(["git", "fetch", "origin", "main"], check=True)

print("Force resetting to origin/main...")
subprocess.run(["git", "reset", "--hard", "origin/main"], check=True)

print("Cleaning untracked files...")
subprocess.run(["git", "clean", "-fd"], check=True)

print("Installing dependencies...")
subprocess.run(["npm", "install"], check=True)

print("Building...")
result = subprocess.run(["npm", "run", "build"], capture_output=True, text=True)
if result.returncode != 0:
    print("Build failed:")
    print(result.stderr[-1000:])
    exit(1)

print("✅ Build successful!")

print("Restarting PM2...")
subprocess.run(["pm2", "restart", "buildany"], check=True)
subprocess.run(["pm2", "save"], check=True)

print("\n✅ DEPLOYED! BuildAny is running with latest code!")
