#!/usr/bin/env python3
"""
Deploy BuildAny latest code from GitHub to VPS
Force resets to latest (discards ALL local changes)
"""
import subprocess, os

os.chdir("/root/buildany")

print("Resetting to clean state...")
subprocess.run(["git", "reset", "--hard", "HEAD"], check=True)
subprocess.run(["git", "clean", "-fd"], check=True)

print("Pulling latest code from GitHub...")
result = subprocess.run(["git", "pull", "origin", "main"], capture_output=True, text=True)
print(result.stdout)
if result.returncode != 0:
    print("Git pull failed:", result.stderr)
    exit(1)

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
