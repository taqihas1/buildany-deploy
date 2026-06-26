#!/usr/bin/env python3
"""
Fix: Morgan chat route exists in source but 404s - rebuild required
Pushed to: https://github.com/taqihas1/buildany-deploy/main/fix_rebuild_morgan_chat.py
"""
import os, subprocess, time

BUILDANY_DIR = "/root/buildany"
os.chdir(BUILDANY_DIR)

print("=" * 60)
print("🔧 Rebuild Morgan Chat Route")
print("=" * 60)

# 1. Check source file
print("\n1. Checking source route...")
if os.path.exists("src/app/api/morgan-chat/route.ts"):
    print("   ✅ src/app/api/morgan-chat/route.ts exists")
    with open("src/app/api/morgan-chat/route.ts") as f:
        content = f.read()
    if "export async function POST" in content:
        print("   ✅ Has POST handler")
    else:
        print("   ❌ Missing POST handler!")
else:
    print("   ❌ Route file missing!")
    exit(1)

# 2. Check build output
print("\n2. Checking build output...")
if os.path.exists(".next/server/app/api/morgan-chat/route.js"):
    print("   ✅ Build output exists")
    # Check modification time
    src_mtime = os.path.getmtime("src/app/api/morgan-chat/route.ts")
    build_mtime = os.path.getmtime(".next/server/app/api/morgan-chat/route.js")
    if build_mtime < src_mtime:
        print(f"   ⚠️ Build is OLDER than source (build: {build_mtime}, src: {src_mtime})")
        print("   Need to rebuild!")
    else:
        print("   Build is up to date")
else:
    print("   ❌ Build output missing! Need to rebuild!")

# 3. Check route manifest
print("\n3. Checking route manifest...")
manifest_path = ".next/server/app-paths-manifest.json"
if os.path.exists(manifest_path):
    import json
    with open(manifest_path) as f:
        manifest = json.load(f)
    if "/api/morgan-chat" in manifest:
        print("   ✅ /api/morgan-chat in route manifest")
    else:
        print("   ❌ /api/morgan-chat NOT in route manifest!")
        print(f"   API routes found: {[k for k in manifest.keys() if '/api/' in k]}")
else:
    print("   ⚠️ No manifest found")

# 4. Rebuild
print("\n4. Rebuilding...")
print("   Removing old build...")
os.system("rm -rf .next")
print("   Building...")
build = os.system("npm run build 2>&1 | tail -30")
if build != 0:
    print("   ⚠️ Build may have had issues")
else:
    print("   ✅ Build complete")

# 5. Check if route is in manifest after rebuild
print("\n5. Checking manifest after rebuild...")
if os.path.exists(".next/server/app-paths-manifest.json"):
    import json
    with open(".next/server/app-paths-manifest.json") as f:
        manifest = json.load(f)
    if "/api/morgan-chat" in manifest:
        print("   ✅ /api/morgan-chat is now in route manifest!")
    else:
        print("   ❌ Still not in route manifest")
        print(f"   Available routes: {sorted([k for k in manifest.keys() if k.startswith('/api/')])}")
else:
    print("   ❌ No manifest found after build!")

# 6. Restart PM2
print("\n6. Restarting PM2...")
os.system("pm2 restart buildany")
time.sleep(5)

# 7. Check PM2 status
print("\n7. PM2 status:")
os.system("pm2 status buildany 2>/dev/null")

# 8. Test API
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
    elif "HTTP_CODE:404" in output:
        print("   ❌ Still 404")
    elif "HTTP_CODE:500" in output:
        print("   ❌ 500 error")
    else:
        code = output.split("HTTP_CODE:")[-1].strip()[:3] if "HTTP_CODE:" in output else "???"
        print(f"   Status: {code}")
except Exception as e:
    print(f"   Error: {e}")

os.system("pm2 save")

print("\n" + "=" * 60)
print("🎉 Done!")
print("=" * 60)
