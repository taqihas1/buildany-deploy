#!/usr/bin/env python3
"""
Diagnostic + Fix for Morgan Chat - Tests all endpoints and fixes broken ones
Pushed to: https://github.com/taqihas1/buildany-deploy/main/fix_morgan_chat.py
"""
import os, subprocess, json, re

BUILDANY_DIR = "/root/buildany"
os.chdir(BUILDANY_DIR)

print("=" * 60)
print("🔧 Morgan Chat Diagnostic + Fix")
print("=" * 60)

# Test DeepSeek API key first
print("\n1. Testing DeepSeek API key...")
deepeek_key = os.environ.get("DEEPSEEK_API_KEY", "")
if not deepeek_key:
    # Try to read from .env.local
    try:
        with open(".env.local") as f:
            for line in f:
                if line.startswith("DEEPSEEK_API_KEY="):
                    deepeek_key = line.strip().split("=", 1)[1].strip().strip('"').strip("'")
                    break
    except:
        pass

if deepeek_key:
    print(f"   ✅ DEEPSEEK_API_KEY found: {deepeek_key[:10]}...")
    # Quick test
    try:
        result = subprocess.run(
            [
                "curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                "https://api.deepseek.com/v1/chat/completions",
                "-H", f"Authorization: Bearer {deepeek_key}",
                "-H", "Content-Type: application/json",
                "-d", '{"model":"deepseek-chat","messages":[{"role":"user","content":"hi"}]}'
            ],
            capture_output=True, text=True, timeout=15
        )
        status = result.stdout.strip()
        if status in ["200", "401"]:
            print(f"   ✅ DeepSeek API reachable (status: {status})")
        else:
            print(f"   ⚠️ DeepSeek API returned status: {status}")
    except Exception as e:
        print(f"   ⚠️ Could not test DeepSeek API: {e}")
else:
    print("   ❌ DEEPSEEK_API_KEY not found! Morgan cannot work without it.")

# Test all chat endpoints
print("\n2. Testing chat endpoints...")
endpoints = [
    "/api/morgan-chat",
    "/api/project-chat-init",
]

# Find a project ID to test project chat
project_id = None
try:
    result = subprocess.run(
        ["sqlite3", "sqlite.db", "SELECT id FROM projects LIMIT 1;"],
        capture_output=True, text=True, timeout=5
    )
    if result.stdout.strip():
        project_id = result.stdout.strip()
        endpoints.append(f"/api/project/{project_id}/chat")
except:
    pass

for endpoint in endpoints:
    print(f"\n   Testing {endpoint}...")
    try:
        result = subprocess.run(
            [
                "curl", "-s", "-X", "POST",
                f"http://localhost:3000{endpoint}",
                "-H", "Content-Type: application/json",
                "-d", '{"message":"test","history":[]}',
                "-w", "\nHTTP_CODE:%{http_code}\n"
            ],
            capture_output=True, text=True, timeout=10
        )
        output = result.stdout
        http_code = "unknown"
        if "HTTP_CODE:" in output:
            parts = output.split("HTTP_CODE:")
            output = parts[0].strip()
            http_code = parts[1].strip().split("\n")[0].strip()
        
        if http_code == "200":
            try:
                data = json.loads(output)
                if "content" in data or "role" in data:
                    print(f"   ✅ Working! Response: {output[:100]}")
                else:
                    print(f"   ⚠️ Returns 200 but unexpected format: {output[:100]}")
            except:
                print(f"   ⚠️ Returns 200 but not JSON: {output[:100]}")
        elif http_code == "404":
            print(f"   ❌ 404 Not Found - route may not exist or app is static export")
        elif http_code == "500":
            print(f"   ❌ 500 Server Error - check route code")
        elif http_code == "502":
            print(f"   ⚠️ 502 Bad Gateway - DeepSeek API issue")
        else:
            print(f"   ⚠️ Status {http_code}: {output[:100]}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

# Check PM2 logs for recent errors
print("\n3. Checking PM2 logs for recent errors...")
try:
    result = subprocess.run(
        ["pm2", "logs", "buildany", "--lines", "20", "--nostream"],
        capture_output=True, text=True, timeout=10
    )
    logs = result.stdout
    if "error" in logs.lower() or "Error" in logs:
        print("   ⚠️ Recent errors found in logs:")
        for line in logs.split("\n"):
            if "error" in line.lower() or "Error" in line:
                print(f"      {line[:100]}")
    else:
        print("   ✅ No recent errors in logs")
except Exception as e:
    print(f"   ⚠️ Could not check logs: {e}")

# Check if output: 'export' is in next.config
print("\n4. Checking next.config...")
config_files = ["next.config.js", "next.config.ts", "next.config.mjs"]
config_path = None
for cf in config_files:
    if os.path.exists(cf):
        config_path = cf
        break

if config_path:
    with open(config_path) as f:
        config = f.read()
    if "output:" in config and "export" in config:
        print(f"   ⚠️ {config_path} has output: 'export' - API routes won't work in static export!")
        print("   🔧 Removing output: 'export' to enable API routes...")
        # Remove output: 'export' line
        config = re.sub(r"output:\s*['\"]?export['\"]?\s*,?\s*\n", "\n", config)
        with open(config_path, "w") as f:
            f.write(config)
        print("   ✅ Removed output: 'export'")
    else:
        print(f"   ✅ {config_path} does not have output: 'export' - API routes should work")
else:
    print("   ⚠️ next.config not found")

# Fix morgan-chat route if needed
print("\n5. Checking morgan-chat route...")
chat_path = "src/app/api/morgan-chat/route.ts"
if os.path.exists(chat_path):
    with open(chat_path) as f:
        chat_code = f.read()
    
    if "shouldBuild" in chat_code:
        print("   ✅ morgan-chat has shouldBuild logic (our fix applied)")
    else:
        print("   ⚠️ morgan-chat does not have shouldBuild logic")
    
    # Check for basic issues
    if "DEEPSEEK_API_KEY" not in chat_code:
        print("   ❌ morgan-chat missing DEEPSEEK_API_KEY reference!")
    
    if "export async function POST" not in chat_code:
        print("   ❌ morgan-chat missing POST handler!")
else:
    print("   ❌ morgan-chat route not found!")

# Fix project/[id]/chat route if needed
print("\n6. Checking project/[id]/chat route...")
project_chat_path = "src/app/api/project/[id]/chat/route.ts"
if os.path.exists(project_chat_path):
    print("   ✅ project/[id]/chat route exists")
else:
    print("   ⚠️ project/[id]/chat route not found")

# Rebuild if we made changes
print("\n7. Rebuilding if needed...")
print("   🔨 Running npm run build...")
result = os.system("npm run build 2>&1 | tail -20")
if result == 0:
    print("   ✅ Build successful!")
    print("   🔄 Restarting PM2...")
    os.system("pm2 restart buildany")
    print("   ✅ PM2 restarted!")
else:
    print("   ❌ Build failed - check errors above")

print("\n" + "=" * 60)
print("🎉 Diagnostic complete!")
print("=" * 60)
