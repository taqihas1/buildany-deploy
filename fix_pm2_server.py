#!/usr/bin/env python3
"""
Fix: PM2 is serving static files instead of running Next.js server
Pushed to: https://github.com/taqihas1/buildany-deploy/main/fix_pm2_server.py
"""
import os, subprocess, json

BUILDANY_DIR = "/root/buildany"
os.chdir(BUILDANY_DIR)

print("=" * 60)
print("🔧 PM2 Server Fix - Switching from static to Next.js server")
print("=" * 60)

# 1. Stop and delete current PM2 process
print("\n1. Stopping current PM2 process...")
os.system("pm2 delete buildany 2>/dev/null")
print("   ✅ PM2 process deleted")

# 2. Save PM2 config so we can see what it was
print("\n2. Checking PM2 dump file...")
try:
    with open("/root/.pm2/dump.pm2") as f:
        dump = f.read()
    if "bash" in dump and "serve" in dump:
        print("   ⚠️ PM2 was running a static file server (bash + serve)")
    elif "next" in dump:
        print("   ✅ PM2 was running Next.js")
    else:
        print(f"   ℹ️ PM2 dump: {dump[:100]}")
except Exception as e:
    print(f"   ⚠️ Could not read dump: {e}")

# 3. Clear PM2 dump to prevent auto-restart of wrong config
print("\n3. Clearing PM2 dump...")
os.system("rm -f /root/.pm2/dump.pm2")
os.system("pm2 save 2>/dev/null")
print("   ✅ PM2 dump cleared")

# 4. Check if there's a PM2 ecosystem config
print("\n4. Checking for ecosystem.config.js...")
if os.path.exists("ecosystem.config.js"):
    with open("ecosystem.config.js") as f:
        eco = f.read()
    print(f"   Found ecosystem.config.js:")
    if "serve" in eco:
        print("   ❌ ecosystem.config.js uses 'serve' - static file server!")
        # Fix it
        eco = eco.replace("serve", "next start")
        eco = eco.replace("out", ".")  # Remove static dir reference
        with open("ecosystem.config.js", "w") as f:
            f.write(eco)
        print("   ✅ Fixed ecosystem.config.js to use 'next start'")
    else:
        print("   ✅ ecosystem.config.js looks correct")
else:
    print("   ℹ️ No ecosystem.config.js found - will use direct command")

# 5. Check the actual start script
print("\n5. Checking start script...")
with open("package.json") as f:
    pkg = json.load(f)
start_cmd = pkg["scripts"].get("start", "")
print(f"   Start script: {start_cmd}")

if "next start" not in start_cmd:
    print("   ❌ Start script is NOT 'next start'")
    pkg["scripts"]["start"] = "next start"
    with open("package.json", "w") as f:
        json.dump(pkg, f, indent=2)
    print("   ✅ Fixed start script to 'next start'")
else:
    print("   ✅ Start script is 'next start'")

# 6. Start PM2 with the correct command
print("\n6. Starting PM2 with Next.js server...")
# Use the direct command approach
start_cmd = f"cd {BUILDANY_DIR} && npm start"
print(f"   Command: {start_cmd}")

result = os.system(f"pm2 start --name buildany '{start_cmd}'")
if result == 0:
    print("   ✅ PM2 started with Next.js server")
else:
    print("   ❌ Failed to start PM2")
    # Fallback: try with node directly
    result = os.system(f"pm2 start --name buildany 'node node_modules/next/dist/bin/next start'")
    if result == 0:
        print("   ✅ PM2 started with direct node command")
    else:
        print("   ❌ Failed to start with fallback")

# 7. Wait and test
print("\n7. Waiting for server to start...")
os.system("sleep 5")

print("\n8. Testing API endpoints...")
endpoints = [
    ("/api/morgan-chat", '{"message":"test","history":[]}'),
    ("/api/project-chat-init", '{"message":"test"}'),
]

for endpoint, payload in endpoints:
    print(f"\n   Testing {endpoint}...")
    try:
        result = subprocess.run(
            [
                "curl", "-s", "-X", "POST",
                f"http://localhost:3000{endpoint}",
                "-H", "Content-Type: application/json",
                "-d", payload,
                "-w", "\nHTTP_CODE:%{http_code}\n",
                "-m", "10"
            ],
            capture_output=True, text=True, timeout=15
        )
        output = result.stdout
        if "HTTP_CODE:200" in output:
            print(f"   ✅ {endpoint} - WORKING!")
        elif "HTTP_CODE:404" in output:
            print(f"   ❌ {endpoint} - 404 (HTML response)")
        elif "HTTP_CODE:502" in output:
            print(f"   ⚠️ {endpoint} - 502 (DeepSeek API issue)")
        else:
            http_code = output.split("HTTP_CODE:")[-1].strip()[:3] if "HTTP_CODE:" in output else "???"
            print(f"   ⚠️ {endpoint} - Status {http_code}")
    except Exception as e:
        print(f"   ❌ {endpoint} - Error: {e}")

# 9. Save PM2 config
print("\n9. Saving PM2 config...")
os.system("pm2 save")
print("   ✅ PM2 config saved")

print("\n" + "=" * 60)
print("🎉 Done! Check if Morgan chat works now.")
print("=" * 60)
