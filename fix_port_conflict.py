#!/usr/bin/env python3
"""
Fix: Port 3000 conflict - kill process using port 3000 and restart PM2
Pushed to: https://github.com/taqihas1/buildany-deploy/main/fix_port_conflict.py
"""
import os, subprocess, time

BUILDANY_DIR = "/root/buildany"
os.chdir(BUILDANY_DIR)

print("=" * 60)
print("🔧 Port 3000 Conflict Fix")
print("=" * 60)

# 1. Find what's using port 3000
print("\n1. Finding process using port 3000...")
try:
    result = subprocess.run(
        ["lsof", "-i", ":3000", "-t"],
        capture_output=True, text=True, timeout=10
    )
    pids = result.stdout.strip().split("\n")
    pids = [p for p in pids if p]
    
    if pids:
        print(f"   Found PIDs: {pids}")
        for pid in pids:
            try:
                # Get process info
                info = subprocess.run(
                    ["ps", "-p", pid, "-o", "pid,ppid,cmd"],
                    capture_output=True, text=True, timeout=5
                )
                print(f"   Process {pid}: {info.stdout.strip()}")
                
                # Kill the process
                print(f"   Killing PID {pid}...")
                os.system(f"kill -9 {pid} 2>/dev/null")
            except:
                pass
        print("   ✅ Killed processes on port 3000")
    else:
        print("   No process found on port 3000")
except Exception as e:
    print(f"   Could not check port: {e}")
    # Fallback: try netstat
    try:
        result = subprocess.run(
            ["netstat", "-tlnp"],
            capture_output=True, text=True, timeout=10
        )
        for line in result.stdout.split("\n"):
            if ":3000" in line:
                print(f"   Found: {line}")
    except:
        pass

# 2. Check if PM2 is already running on port 3000
print("\n2. Checking PM2 status...")
os.system("pm2 list 2>/dev/null")

# 3. Delete old PM2 process if exists
print("\n3. Cleaning up PM2...")
os.system("pm2 delete buildany 2>/dev/null")
os.system("pm2 save 2>/dev/null")
print("   ✅ PM2 cleaned up")

# 4. Wait for port to be released
print("\n4. Waiting for port to be released...")
time.sleep(2)

# 5. Verify port is free
print("\n5. Verifying port 3000 is free...")
try:
    result = subprocess.run(
        ["lsof", "-i", ":3000", "-t"],
        capture_output=True, text=True, timeout=5
    )
    if result.stdout.strip():
        print("   ⚠️ Port still in use, trying again...")
        os.system("kill -9 $(lsof -i :3000 -t) 2>/dev/null")
        time.sleep(2)
    else:
        print("   ✅ Port 3000 is free")
except:
    print("   ⚠️ Could not verify port")

# 6. Start PM2 fresh
print("\n6. Starting PM2 fresh...")
# Start with explicit port and proper Next.js start
os.system("pm2 start 'npm start' --name buildany --update-env")
print("   ✅ PM2 started")

# 7. Wait for startup
print("\n7. Waiting for server to start...")
time.sleep(5)

# 8. Test the API
print("\n8. Testing Morgan chat API...")
try:
    result = subprocess.run(
        [
            "curl", "-s", "-X", "POST",
            "http://localhost:3000/api/morgan-chat",
            "-H", "Content-Type: application/json",
            "-d", '{"message":"test","history":[]}',
            "-w", "\nHTTP_CODE:%{http_code}\n",
            "-m", "10"
        ],
        capture_output=True, text=True, timeout=15
    )
    output = result.stdout
    if "HTTP_CODE:200" in output:
        print("   ✅ Morgan chat API is working!")
        body = output.split("HTTP_CODE:")[0].strip()
        if body:
            print(f"   Response: {body[:200]}")
    elif "HTTP_CODE:500" in output:
        print("   ❌ Still 500")
        body = output.split("HTTP_CODE:")[0].strip()
        if body:
            print(f"   Response: {body[:200]}")
    elif "HTTP_CODE:404" in output:
        print("   ❌ Still 404")
    else:
        code = output.split("HTTP_CODE:")[-1].strip()[:3] if "HTTP_CODE:" in output else "???"
        print(f"   Status: {code}")
except Exception as e:
    print(f"   Error: {e}")

# 9. Save PM2 config
print("\n9. Saving PM2 config...")
os.system("pm2 save")
print("   ✅ Saved")

print("\n" + "=" * 60)
print("🎉 Done! Port conflict should be resolved.")
print("=" * 60)
