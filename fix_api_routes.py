#!/usr/bin/env python3
"""
Fix: API routes returning 404 - check middleware and build output
Pushed to: https://github.com/taqihas1/buildany-deploy/main/fix_api_routes.py
"""
import os, subprocess, json, re

BUILDANY_DIR = "/root/buildany"
os.chdir(BUILDANY_DIR)

print("=" * 60)
print("🔧 API Routes 404 Fix")
print("=" * 60)

# 1. Check middleware.ts
print("\n1. Checking middleware.ts...")
middleware_path = "src/middleware.ts"
if os.path.exists(middleware_path):
    with open(middleware_path) as f:
        middleware = f.read()
    
    # Check if there's a matcher that excludes API routes
    if "matcher" in middleware:
        print("   ⚠️ Middleware has matcher config")
        # Find the matcher pattern
        match = re.search(r'matcher:\s*\[(.*?)\]', middleware, re.DOTALL)
        if match:
            print(f"   Matcher: {match.group(1)[:100]}")
    
    # Check if API routes are protected
    if "/api/" in middleware and ("redirect" in middleware or "rewrite" in middleware):
        print("   ⚠️ Middleware may be intercepting API routes")
    
    # Check if there's a PUBLIC_API_ROUTES or similar
    if "PUBLIC_API_ROUTES" in middleware:
        print("   ✅ Found PUBLIC_API_ROUTES - checking if morgan-chat is included...")
        # Extract the array
        match = re.search(r'PUBLIC_API_ROUTES\s*=\s*\[(.*?)\]', middleware, re.DOTALL)
        if match:
            routes = match.group(1)
            if "/api/morgan-chat" in routes:
                print("   ✅ /api/morgan-chat is in PUBLIC_API_ROUTES")
            else:
                print("   ❌ /api/morgan-chat NOT in PUBLIC_API_ROUTES - ADDING")
                # Add the route
                routes = routes.rstrip()
                if routes.endswith(","):
                    routes = routes + '\n  "/api/morgan-chat",'
                else:
                    routes = routes + ',\n  "/api/morgan-chat",'
                middleware = middleware.replace(match.group(1), routes)
                with open(middleware_path, "w") as f:
                    f.write(middleware)
                print("   ✅ Added /api/morgan-chat to PUBLIC_API_ROUTES")
    else:
        print("   ℹ️ No PUBLIC_API_ROUTES found in middleware")
else:
    print("   ℹ️ No middleware.ts found")

# 2. Check if the API route files actually exist
print("\n2. Checking API route files...")
api_routes = [
    "src/app/api/morgan-chat/route.ts",
    "src/app/api/project-chat-init/route.ts",
]

for route in api_routes:
    if os.path.exists(route):
        print(f"   ✅ {route} exists")
        # Check if it has a POST handler
        with open(route) as f:
            content = f.read()
        if "export async function POST" in content:
            print(f"   ✅ {route} has POST handler")
        else:
            print(f"   ❌ {route} missing POST handler!")
    else:
        print(f"   ❌ {route} NOT FOUND!")

# 3. Check if build output includes API routes
print("\n3. Checking build output...")
build_dir = ".next"
if os.path.exists(build_dir):
    # Check server files
    server_dir = os.path.join(build_dir, "server", "app", "api")
    if os.path.exists(server_dir):
        print(f"   ✅ Server build directory exists: {server_dir}")
        # Check if morgan-chat is there
        morgan_chat_build = os.path.join(server_dir, "morgan-chat")
        if os.path.exists(morgan_chat_build):
            print(f"   ✅ morgan-chat build exists")
        else:
            print(f"   ❌ morgan-chat build NOT FOUND")
    else:
        print(f"   ⚠️ Server build directory not found: {server_dir}")
else:
    print(f"   ❌ Build directory not found: {build_dir}")

# 4. Check if there's a standalone build
print("\n4. Checking for standalone build...")
standalone_dir = os.path.join(build_dir, "standalone")
if os.path.exists(standalone_dir):
    print(f"   ✅ Standalone build exists")
else:
    print(f"   ℹ️ No standalone build")

# 5. Check if we're using output: 'standalone'
print("\n5. Checking next.config for standalone output...")
config_files = ["next.config.ts", "next.config.js", "next.config.mjs"]
config_path = None
for cf in config_files:
    if os.path.exists(cf):
        config_path = cf
        break

if config_path:
    with open(config_path) as f:
        config = f.read()
    
    if "standalone" in config:
        print(f"   ⚠️ next.config has standalone output - this may conflict with server mode")
    else:
        print(f"   ✅ next.config does not have standalone output")
else:
    print(f"   ⚠️ next.config not found")

# 6. Try starting the server directly and testing
print("\n6. Testing server directly...")
print("   Stopping PM2 temporarily...")
os.system("pm2 stop buildany 2>/dev/null")

print("   Starting Next.js dev server on port 3000...")
# Start in background and test
server_proc = subprocess.Popen(
    ["npm", "run", "dev"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    cwd=BUILDANY_DIR
)

# Wait for server to start
import time
time.sleep(5)

# Test the API
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
        print("   ✅ Dev server API works!")
    elif "HTTP_CODE:404" in output:
        print("   ❌ Dev server also returns 404 - route is broken")
    else:
        http_code = output.split("HTTP_CODE:")[-1].strip()[:3] if "HTTP_CODE:" in output else "???"
        print(f"   ⚠️ Dev server status: {http_code}")
except Exception as e:
    print(f"   ❌ Error testing dev server: {e}")
finally:
    # Kill the dev server
    server_proc.terminate()
    try:
        server_proc.wait(timeout=5)
    except:
        server_proc.kill()

# 7. Restart PM2
print("\n7. Restarting PM2...")
os.system("pm2 start buildany 2>/dev/null || pm2 start 'npm start' --name buildany")
os.system("sleep 3")

# 8. Final test
print("\n8. Final test...")
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
        print("   ✅ API route is working!")
    elif "HTTP_CODE:404" in output:
        print("   ❌ Still 404 - need to investigate middleware further")
    else:
        http_code = output.split("HTTP_CODE:")[-1].strip()[:3] if "HTTP_CODE:" in output else "???"
        print(f"   ⚠️ Status: {http_code}")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "=" * 60)
print("🎉 Done!")
print("=" * 60)
