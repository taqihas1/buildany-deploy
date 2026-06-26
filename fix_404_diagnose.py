#!/usr/bin/env python3
"""
Fix: Diagnose why morgan-chat 404s - check route manifest and test other routes
Pushed to: https://github.com/taqihas1/buildany-deploy/main/fix_404_diagnose.py
"""
import os, subprocess, json

BUILDANY_DIR = "/root/buildany"
os.chdir(BUILDANY_DIR)

print("=" * 60)
print("🔧 404 Diagnose - Why is /api/morgan-chat not found?")
print("=" * 60)

# 1. Check app-paths-manifest.json
print("\n1. Checking app-paths-manifest.json...")
manifest_path = ".next/server/app-paths-manifest.json"
if os.path.exists(manifest_path):
    with open(manifest_path) as f:
        manifest = json.load(f)
    
    morgan_keys = [k for k in manifest.keys() if "morgan-chat" in k]
    print(f"   Morgan-chat keys: {morgan_keys}")
    
    all_api = [k for k in manifest.keys() if k.startswith("/api/")]
    print(f"   All API routes ({len(all_api)}):")
    for route in sorted(all_api):
        print(f"     {route}")
else:
    print("   ❌ No app-paths-manifest.json found!")

# 2. Check if it's a Pages Router vs App Router issue
print("\n2. Checking route structure...")
if os.path.exists("src/app/api/morgan-chat"):
    if os.path.isdir("src/app/api/morgan-chat"):
        print("   ✅ src/app/api/morgan-chat is a directory (App Router)")
        files = os.listdir("src/app/api/morgan-chat")
        print(f"   Contents: {files}")
    elif os.path.isfile("src/app/api/morgan-chat"):
        print("   ⚠️ src/app/api/morgan-chat is a FILE (weird)")

if os.path.exists("src/pages/api/morgan-chat"):
    print("   ⚠️ src/pages/api/morgan-chat exists (Pages Router conflict!)")

if os.path.exists("src/app/api/morgan-chat.ts"):
    print("   ⚠️ src/app/api/morgan-chat.ts exists (file conflict!)")

# 3. Test other API routes
print("\n3. Testing other API routes...")
routes_to_test = [
    "/api/diag",
    "/api/hermes-chat",
    "/api/morgan-generate",
    "/api/build",
    "/api/morgan-chat",
]

for route in routes_to_test:
    try:
        result = subprocess.run(
            [
                "curl", "-s", "-X", "POST",
                f"http://localhost:3000{route}",
                "-H", "Content-Type: application/json",
                "-d", '{"test":"test"}',
                "-w", "\nHTTP:%{http_code}\n",
                "-m", "3"
            ],
            capture_output=True, text=True, timeout=10
        )
        output = result.stdout
        if "HTTP:" in output:
            code = output.split("HTTP:")[-1].strip()[:3]
            body_preview = output.split("HTTP:")[0].strip()[:50]
            print(f"   {route}: HTTP {code} - {body_preview}")
        else:
            print(f"   {route}: No response")
    except Exception as e:
        print(f"   {route}: Error - {e}")

# 4. Check if the route.js file exists in build and is valid
print("\n4. Checking build output...")
route_build = ".next/server/app/api/morgan-chat/route.js"
if os.path.exists(route_build):
    print(f"   ✅ {route_build} exists")
    size = os.path.getsize(route_build)
    print(f"   Size: {size} bytes")
    with open(route_build) as f:
        content = f.read()
    if "POST" in content:
        print("   ✅ Contains POST handler")
    else:
        print("   ❌ No POST handler in build output!")
else:
    print(f"   ❌ {route_build} NOT found")

# 5. Check if there's a middleware intercepting
print("\n5. Checking middleware config...")
if os.path.exists("src/middleware.ts"):
    with open("src/middleware.ts") as f:
        mw = f.read()
    if "/api/morgan-chat" in mw:
        print("   ✅ /api/morgan-chat mentioned in middleware")
    else:
        print("   ⚠️ /api/morgan-chat NOT in middleware (may be blocked by Clerk)")
    
    if "isPublicRoute" in mw and "/api/morgan-chat" in mw:
        print("   ✅ Should be in public routes")
    elif "isPublicRoute" in mw:
        print("   ⚠️ Public routes exist but morgan-chat may not be listed")

# 6. Try a GET request to the route (in case POST handler is missing)
print("\n6. Testing GET request to morgan-chat...")
try:
    result = subprocess.run(
        ["curl", "-s", "http://localhost:3000/api/morgan-chat", "-w", "\nHTTP:%{http_code}\n", "-m", "3"],
        capture_output=True, text=True, timeout=10
    )
    output = result.stdout
    if "HTTP:" in output:
        code = output.split("HTTP:")[-1].strip()[:3]
        print(f"   GET /api/morgan-chat: HTTP {code}")
    else:
        print(f"   GET: No response")
except Exception as e:
    print(f"   GET: Error - {e}")

# 7. Check if the route file is TypeScript or JavaScript
print("\n7. Checking route file type...")
route_ts = "src/app/api/morgan-chat/route.ts"
route_js = "src/app/api/morgan-chat/route.js"
if os.path.exists(route_ts):
    print(f"   ✅ {route_ts} exists")
elif os.path.exists(route_js):
    print(f"   ✅ {route_js} exists (JS, not TS)")
else:
    print(f"   ❌ No route file found!")

print("\n" + "=" * 60)
print("🎉 Diagnostic complete!")
print("=" * 60)
