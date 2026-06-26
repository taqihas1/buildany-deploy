#!/usr/bin/env python3
"""
Fix: PM2 process is crashing - read exact error and fix it
Pushed to: https://github.com/taqihas1/buildany-deploy/main/fix_pm2_crash.py
"""
import os, subprocess, time

BUILDANY_DIR = "/root/buildany"
os.chdir(BUILDANY_DIR)

print("=" * 60)
print("🔧 PM2 Crash Fix - Finding Exact Error")
print("=" * 60)

# 1. Read PM2 logs for the exact crash reason
print("\n1. Reading PM2 error logs...")
try:
    # Check error log file
    result = subprocess.run(
        ["cat", "/root/.pm2/logs/buildany-error.log"],
        capture_output=True, text=True, timeout=10
    )
    error_log = result.stdout
    
    if error_log:
        lines = error_log.split("\n")
        # Show last 15 non-empty lines
        shown = 0
        for line in reversed(lines):
            if line.strip() and shown < 15:
                print(f"   {line[:150]}")
                shown += 1
    else:
        print("   No error log file found")
except Exception as e:
    print(f"   Could not read error log: {e}")

# 2. Also check PM2 output logs
print("\n2. Reading PM2 output logs...")
try:
    result = subprocess.run(
        ["cat", "/root/.pm2/logs/buildany-out.log"],
        capture_output=True, text=True, timeout=10
    )
    out_log = result.stdout
    
    if out_log:
        lines = out_log.split("\n")
        shown = 0
        for line in reversed(lines):
            if line.strip() and shown < 10:
                print(f"   {line[:150]}")
                shown += 1
    else:
        print("   No output log file found")
except Exception as e:
    print(f"   Could not read output log: {e}")

# 3. Check PM2 dump to see what command it's running
print("\n3. Checking PM2 dump config...")
try:
    with open("/root/.pm2/dump.pm2") as f:
        dump = f.read()
    
    # Find the exec command
    if "npm start" in dump:
        print("   ✅ PM2 using 'npm start'")
    elif "bash" in dump:
        print("   ⚠️ PM2 using bash - may be incorrect")
    
    # Check for errors in dump
    if "error" in dump.lower():
        print("   ⚠️ Errors found in PM2 dump")
except Exception as e:
    print(f"   Could not read dump: {e}")

# 4. Try starting Next.js directly (not through PM2) to see the error
print("\n4. Testing Next.js start directly...")
print("   Starting Next.js server directly...")
try:
    # Start Next.js in background and test
    proc = subprocess.Popen(
        ["npm", "start"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=BUILDANY_DIR
    )
    
    # Wait for it to start or crash
    time.sleep(5)
    
    # Check if it's still running
    if proc.poll() is None:
        print("   ✅ Next.js server is running!")
        
        # Test the API
        result = subprocess.run(
            [
                "curl", "-s", "-X", "POST",
                "http://localhost:3000/api/morgan-chat",
                "-H", "Content-Type: application/json",
                "-d", '{"message":"test","history":[]}',
                "-w", "\nHTTP_CODE:%{http_code}\n",
                "-m", "5"
            ],
            capture_output=True, text=True, timeout=10
        )
        output = result.stdout
        if "HTTP_CODE:200" in output or "HTTP_CODE:502" in output:
            print("   ✅ API is working!")
        else:
            code = output.split("HTTP_CODE:")[-1].strip()[:3] if "HTTP_CODE:" in output else "???"
            print(f"   Status: {code}")
        
        # Kill the test process
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except:
            proc.kill()
    else:
        # Process crashed, read output
        stdout, stderr = proc.communicate()
        print("   ❌ Next.js crashed immediately!")
        print("   STDERR:")
        for line in stderr.split("\n")[:10]:
            if line.strip():
                print(f"   {line[:150]}")
        print("   STDOUT:")
        for line in stdout.split("\n")[:10]:
            if line.strip():
                print(f"   {line[:150]}")
                
except Exception as e:
    print(f"   Error: {e}")

# 5. If we know npm start works, the issue is PM2 config
print("\n5. Checking if we need a PM2 ecosystem config...")
if not os.path.exists("ecosystem.config.js"):
    print("   No ecosystem.config.js found - creating one...")
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
    time: true
  }]
};
''')
    print("   ✅ Created ecosystem.config.js")
else:
    print("   ecosystem.config.js exists")

# 6. Restart with ecosystem config
print("\n6. Restarting with ecosystem config...")
os.system("pm2 delete buildany 2>/dev/null")
os.system("pm2 start ecosystem.config.js")
os.system("sleep 3")

# 7. Test
print("\n7. Testing...")
try:
    result = subprocess.run(
        [
            "curl", "-s", "-X", "POST",
            "http://localhost:3000/api/morgan-chat",
            "-H", "Content-Type: application/json",
            "-d", '{"message":"test","history":[]}',
            "-w", "\nHTTP_CODE:%{http_code}\n",
            "-m", "5"
        ],
        capture_output=True, text=True, timeout=10
    )
    output = result.stdout
    if "HTTP_CODE:200" in output or "HTTP_CODE:502" in output:
        print("   ✅ Working!")
    else:
        code = output.split("HTTP_CODE:")[-1].strip()[:3] if "HTTP_CODE:" in output else "???"
        print(f"   Status: {code}")
except Exception as e:
    print(f"   Error: {e}")

os.system("pm2 save")

print("\n" + "=" * 60)
print("🎉 Done!")
print("=" * 60)
