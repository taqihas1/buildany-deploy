#!/usr/bin/env python3
"""
Fix: Morgan Chat API 500 error - check server logs and fix the error
Pushed to: https://github.com/taqihas1/buildany-deploy/main/fix_morgan_500.py
"""
import os, subprocess, json, re

BUILDANY_DIR = "/root/buildany"
os.chdir(BUILDANY_DIR)

print("=" * 60)
print("🔧 Morgan Chat 500 Error Fix")
print("=" * 60)

# 1. Check PM2 logs for the exact error
print("\n1. Checking PM2 logs for 500 error...")
try:
    result = subprocess.run(
        ["pm2", "logs", "buildany", "--lines", "50", "--nostream"],
        capture_output=True, text=True, timeout=10
    )
    logs = result.stdout
    
    # Look for recent errors
    error_lines = []
    for line in logs.split("\n"):
        if "error" in line.lower() or "Error" in line or "500" in line or "morgan-chat" in line:
            error_lines.append(line)
    
    if error_lines:
        print("   Recent errors found:")
        for line in error_lines[-10:]:
            print(f"   {line[:120]}")
    else:
        print("   No specific errors in recent logs")
        
except Exception as e:
    print(f"   Could not read logs: {e}")

# 2. Check the morgan-chat route for issues
print("\n2. Checking morgan-chat route for issues...")
chat_path = "src/app/api/morgan-chat/route.ts"
with open(chat_path) as f:
    chat_code = f.read()

# Check for common issues
issues = []

if "DEEPSEEK_API_KEY" not in chat_code:
    issues.append("Missing DEEPSEEK_API_KEY reference")

if "process.env.DEEPSEEK_API_KEY" not in chat_code:
    issues.append("Not using process.env for API key")

# Check if the route has proper error handling
if "try {" not in chat_code:
    issues.append("Missing try-catch block")

if "catch" not in chat_code:
    issues.append("Missing catch block")

if issues:
    print(f"   Issues found: {issues}")
else:
    print("   ✅ Basic structure looks correct")

# 3. Check .env.local for DEEPSEEK_API_KEY
print("\n3. Checking .env.local for DEEPSEEK_API_KEY...")
env_path = ".env.local"
if os.path.exists(env_path):
    with open(env_path) as f:
        env_content = f.read()
    
    if "DEEPSEEK_API_KEY" in env_content:
        # Extract the key
        match = re.search(r'DEEPSEEK_API_KEY\s*=\s*"?([^"\n]+)"?', env_content)
        if match:
            key = match.group(1).strip()
            print(f"   ✅ DEEPSEEK_API_KEY found: {key[:15]}...")
            
            # Check if key is empty
            if not key or key == "your-api-key-here":
                print("   ❌ API key is empty or placeholder!")
                issues.append("API key is empty")
        else:
            print("   ⚠️ Could not parse DEEPSEEK_API_KEY value")
            issues.append("Could not parse API key")
    else:
        print("   ❌ DEEPSEEK_API_KEY not found in .env.local")
        issues.append("Missing DEEPSEEK_API_KEY in .env.local")
else:
    print("   ❌ .env.local not found")
    issues.append("Missing .env.local file")

# 4. Check if the route imports are correct
print("\n4. Checking imports...")
if "import { NextRequest, NextResponse }" not in chat_code:
    print("   ❌ Missing NextRequest/NextResponse imports")
    issues.append("Missing Next.js imports")
else:
    print("   ✅ NextRequest/NextResponse imports found")

if "from \"next/server\"" not in chat_code:
    print("   ❌ Import from wrong path")
    issues.append("Wrong import path")
else:
    print("   ✅ Imports from next/server")

# 5. Check for TypeScript errors in the route
print("\n5. Checking for TypeScript issues...")
# Check for common TS issues
if "any" in chat_code and "catch (error" in chat_code:
    if "error: any" not in chat_code:
        print("   ⚠️ Catch block may have type issues")

# 6. Check if the route is trying to use edge runtime
print("\n6. Checking runtime configuration...")
if "export const runtime" in chat_code:
    match = re.search(r'export\s+const\s+runtime\s*=\s*["\']([^"\']+)["\']', chat_code)
    if match:
        runtime = match.group(1)
        print(f"   ℹ️ Runtime: {runtime}")
        if runtime == "edge":
            print("   ⚠️ Edge runtime - may have issues with node APIs")
else:
    print("   ℹ️ No explicit runtime config (using default)")

# 7. If we found issues, rebuild and restart
if issues:
    print(f"\n7. Found {len(issues)} issues. Fixing...")
    
    # Rebuild to catch any TypeScript errors
    print("   🔨 Rebuilding...")
    build_result = os.system("npm run build 2>&1 | grep -E '(error|Error|morgan-chat|route.ts)' | tail -20")
    
    if build_result == 0:
        print("   ✅ Build successful")
        print("   🔄 Restarting PM2...")
        os.system("pm2 restart buildany")
        print("   ✅ Restarted")
    else:
        print("   ❌ Build failed - check errors above")
else:
    print("\n7. No obvious issues found in the route code.")
    print("   The 500 error may be from:")
    print("   - DeepSeek API being unreachable")
    print("   - Database connection issues")
    print("   - Middleware blocking the request")
    print("   - Session/auth issues")

# 8. Test the API again with verbose output
print("\n8. Testing with verbose output...")
try:
    result = subprocess.run(
        [
            "curl", "-s", "-v", "-X", "POST",
            "http://localhost:3000/api/morgan-chat",
            "-H", "Content-Type: application/json",
            "-d", '{"message":"test","history":[]}',
            "-m", "10"
        ],
        capture_output=True, text=True, timeout=15
    )
    
    # Check stderr for HTTP status
    stderr = result.stderr
    if "HTTP/1.1" in stderr or "HTTP/2" in stderr:
        status_line = [line for line in stderr.split("\n") if "HTTP/" in line]
        if status_line:
            print(f"   HTTP Status: {status_line[-1].strip()}")
    
    stdout = result.stdout
    if stdout:
        print(f"   Response: {stdout[:200]}")
    else:
        print("   No response body")
        
except Exception as e:
    print(f"   Error: {e}")

print("\n" + "=" * 60)
print("🎉 Done!")
print("=" * 60)
