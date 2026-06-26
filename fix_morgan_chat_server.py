#!/usr/bin/env python3
"""
Fix Morgan Chat - ensures PM2 runs Next.js server (not static export)
Pushed to: https://github.com/taqihas1/buildany-deploy/main/fix_morgan_chat_server.py
"""
import os, subprocess, json, re

BUILDANY_DIR = "/root/buildany"
os.chdir(BUILDANY_DIR)

print("=" * 60)
print("🔧 Morgan Chat Server Fix")
print("=" * 60)

# 1. Check PM2 config
print("\n1. Checking PM2 config...")
try:
    result = subprocess.run(
        ["pm2", "describe", "buildany"],
        capture_output=True, text=True, timeout=10
    )
    pm2_info = result.stdout
    
    # Check what command PM2 is running
    if "exec cwd" in pm2_info:
        # Extract the command
        cmd_match = re.search(r'exec cwd\s+│\s+(.+)', pm2_info)
        if cmd_match:
            print(f"   PM2 exec path: {cmd_match.group(1).strip()}")
    
    # Check if it's using node or npm
    if "node" in pm2_info:
        print("   ✅ PM2 running with node")
    elif "npm" in pm2_info:
        print("   ✅ PM2 running with npm")
    else:
        print("   ⚠️ PM2 config unclear")
        
except Exception as e:
    print(f"   ⚠️ Could not check PM2: {e}")

# 2. Check package.json scripts
print("\n2. Checking package.json...")
try:
    with open("package.json") as f:
        pkg = json.load(f)
    
    scripts = pkg.get("scripts", {})
    print(f"   Scripts: {list(scripts.keys())}")
    
    start_script = scripts.get("start", "")
    print(f"   Start script: {start_script}")
    
    if "next start" in start_script:
        print("   ✅ 'start' script uses 'next start' (server mode)")
    elif "serve" in start_script or "npx serve" in start_script:
        print("   ❌ 'start' script uses static server - API routes won't work!")
    else:
        print("   ⚠️ Unknown start script")
        
except Exception as e:
    print(f"   ❌ Error reading package.json: {e}")

# 3. Fix package.json if needed
print("\n3. Fixing package.json if needed...")
if "start" not in scripts or "next start" not in start_script:
    # Ensure we have a proper start script
    if "dev" in scripts:
        # We can use 'next dev' for development or 'next start' for production
        scripts["start"] = "next start"
        pkg["scripts"] = scripts
        with open("package.json", "w") as f:
            json.dump(pkg, f, indent=2)
        print("   ✅ Updated 'start' script to 'next start'")
    else:
        print("   ⚠️ Could not fix - no 'dev' or 'start' script found")
else:
    print("   ✅ Start script is correct")

# 4. Ensure next.config does NOT have output: 'export'
print("\n4. Checking next.config...")
config_files = ["next.config.ts", "next.config.js", "next.config.mjs"]
config_path = None
for cf in config_files:
    if os.path.exists(cf):
        config_path = cf
        break

if config_path:
    with open(config_path) as f:
        config = f.read()
    
    if "output:" in config and "export" in config:
        print(f"   ❌ {config_path} has output: 'export' - REMOVING")
        config = re.sub(r"output:\s*['\"]?export['\"]?\s*,?\s*\n", "\n", config)
        with open(config_path, "w") as f:
            f.write(config)
        print(f"   ✅ Removed output: 'export'")
    else:
        print(f"   ✅ {config_path} does not have output: 'export'")
else:
    print("   ⚠️ next.config not found")

# 5. Rebuild and restart PM2 with proper config
print("\n5. Rebuilding and restarting...")
print("   🔨 Building...")
build_result = os.system("npm run build 2>&1 | tail -30")

if build_result == 0:
    print("   ✅ Build successful!")
    
    # Check if there's a PM2 ecosystem file
    if os.path.exists("ecosystem.config.js"):
        print("   🔄 Restarting via PM2 ecosystem...")
        os.system("pm2 restart ecosystem.config.js --update-env")
    else:
        print("   🔄 Restarting PM2...")
        os.system("pm2 delete buildany 2>/dev/null; pm2 start 'npm start' --name buildany --update-env")
    
    print("   ✅ PM2 restarted!")
    
    # Wait a moment for the server to start
    print("   ⏳ Waiting for server to start...")
    os.system("sleep 3")
    
    # Test the API
    print("\n6. Testing Morgan chat API...")
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
        if "HTTP_CODE:200" in output or "HTTP_CODE:502" in output:
            print("   ✅ API route is responding!")
            # Extract the JSON part
            json_part = output.split("HTTP_CODE:")[0].strip()
            if json_part:
                print(f"   Response: {json_part[:100]}")
        elif "HTTP_CODE:404" in output:
            print("   ❌ Still 404 - API route not found")
            print(f"   Output: {output[:200]}")
        else:
            print(f"   ⚠️ Unexpected response: {output[:200]}")
    except Exception as e:
        print(f"   ❌ Error testing API: {e}")
else:
    print("   ❌ Build failed")

print("\n" + "=" * 60)
print("🎉 Done! Try chatting with Morgan now.")
print("=" * 60)
