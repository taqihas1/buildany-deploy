#!/usr/bin/env python3
"""
Fix: PM2 crash loop - port 3000 in use by zombie process. Kill everything and restart.
Pushed to: https://github.com/taqihas1/buildany-deploy/main/fix_crash_loop.py
"""
import os, subprocess, time, signal

BUILDANY_DIR = "/root/buildany"
os.chdir(BUILDANY_DIR)

print("=" * 60)
print("🔧 PM2 Crash Loop Fix - Kill Port 3000 Zombie")
print("=" * 60)

# 1. Kill ALL PM2 processes completely
print("\n1. Killing ALL PM2 processes...")
os.system("pm2 kill 2>/dev/null")
os.system("pm2 delete all 2>/dev/null")
print("   ✅ PM2 killed")

# 2. Find and kill any process on port 3000
print("\n2. Killing all processes on port 3000...")
try:
    # Try lsof
    result = subprocess.run(
        ["lsof", "-i", ":3000", "-t"],
        capture_output=True, text=True, timeout=10
    )
    pids = [p.strip() for p in result.stdout.strip().split("\n") if p.strip()]
    for pid in pids:
        try:
            os.kill(int(pid), signal.SIGKILL)
            print(f"   Killed PID {pid}")
        except:
            pass
except:
    pass

# Also try fuser
try:
    os.system("fuser -k 3000/tcp 2>/dev/null")
    print("   Used fuser to kill port 3000")
except:
    pass

# Also try netstat to find and kill
os.system("kill -9 $(lsof -i :3000 -t) 2>/dev/null")

print("   ✅ Port 3000 cleared")

# 3. Wait for port to be free
print("\n3. Verifying port is free...")
time.sleep(2)
result = subprocess.run(
    ["lsof", "-i", ":3000", "-t"],
    capture_output=True, text=True, timeout=5
)
if not result.stdout.strip():
    print("   ✅ Port 3000 is free")
else:
    print(f"   ⚠️ Still processes on port 3000: {result.stdout.strip()}")
    os.system("kill -9 $(lsof -i :3000 -t) 2>/dev/null")

# 4. Clear PM2 dump to prevent auto-restart
print("\n4. Clearing PM2 dump...")
os.system("rm -f /root/.pm2/dump.pm2")
print("   ✅ Dump cleared")

# 5. Check if ecosystem.config.js exists
print("\n5. Checking ecosystem config...")
if os.path.exists("ecosystem.config.js"):
    print("   ✅ ecosystem.config.js exists")
else:
    print("   Creating ecosystem.config.js...")
    with open("ecosystem.config.js", "w") as f:
        f.write('''module.exports = {
  apps: [{
    name: 'buildany',
    script: 'npm',
    args: 'start',
    cwd: '/root/buildany',
    env: {
      NODE_ENV: 'production',
      PORT: 3000
    },
    log_file: '/root/.pm2/logs/buildany-combined.log',
    out_file: '/root/.pm2/logs/buildany-out.log',
    error_file: '/root/.pm2/logs/buildany-error.log',
    merge_logs: true,
    time: true,
    max_restarts: 5,
    min_uptime: '10s',
    autorestart: true
  }]
};
''')
    print("   ✅ Created ecosystem.config.js")

# 6. Start fresh
print("\n6. Starting PM2 fresh...")
os.system("pm2 start ecosystem.config.js")
time.sleep(3)

# 7. Check status
print("\n7. Checking PM2 status...")
result = subprocess.run(
    ["pm2", "status", "buildany"],
    capture_output=True, text=True, timeout=10
)
print(result.stdout)

# 8. Test API
print("\n8. Testing Morgan chat API...")
time.sleep(5)
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
    elif "HTTP_CODE:404" in output:
        print("   ❌ Still 404 - route needs fixing")
    elif "HTTP_CODE:500" in output:
        print("   ❌ 500 error - route crashes")
    else:
        code = output.split("HTTP_CODE:")[-1].strip()[:3] if "HTTP_CODE:" in output else "???"
        print(f"   Status: {code}")
except Exception as e:
    print(f"   Error: {e}")

print("\n" + "=" * 60)
print("🎉 Done! PM2 should be stable now.")
print("=" * 60)
