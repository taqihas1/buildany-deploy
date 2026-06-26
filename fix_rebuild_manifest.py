#!/usr/bin/env python3
"""
Fix: Rebuild to regenerate route manifest for morgan-chat
Pushed to: https://github.com/taqihas1/buildany-deploy/main/fix_rebuild_manifest.py
"""
import os, subprocess, time

BUILDANY_DIR = "/root/buildany"
os.chdir(BUILDANY_DIR)

print("=" * 60)
print("🔧 Rebuild Route Manifest")
print("=" * 60)

# 1. Check if the route file exists in source
print("\n1. Checking source route...")
if os.path.exists("src/app/api/morgan-chat/route.ts"):
    print("   ✅ src/app/api/morgan-chat/route.ts exists")
    with open("src/app/api/morgan-chat/route.ts") as f:
        content = f.read()
    if "export async function POST" in content:
        print("   ✅ Has POST export")
    else:
        print("   ❌ Missing POST export!")
else:
    print("   ❌ Route file missing!")

# 2. Check build output
print("\n2. Checking build output...")
if os.path.exists(".next/server/app/api/morgan-chat/route.js"):
    print("   ✅ Build output exists")
else:
    print("   ❌ Build output missing!")

# 3. Check if .next/server/app/api/morgan-chat is a directory or file
route_path = ".next/server/app/api/morgan-chat"
if os.path.isdir(route_path):
    print("   ℹ️  morgan-chat is a directory (App Router format)")
    files = os.listdir(route_path)
    print(f"   Contents: {files}")
elif os.path.isfile(route_path + ".js"):
    print("   ℹ️  morgan-chat.js is a file (Pages Router format)")

# 4. Check the route manifest
print("\n3. Checking route manifest...")
manifest_path = ".next/server/app-paths-manifest.json"
if os.path.exists(manifest_path):
    with open(manifest_path) as f:
        manifest = f.read()
    if "/api/morgan-chat" in manifest:
        print("   ✅ /api/morgan-chat in route manifest")
    else:
        print("   ❌ /api/morgan-chat NOT in route manifest!")
        print(f"   Manifest snippet: {manifest[:500]}")
else:
    print("   ⚠️  No route manifest found")

# 5. Check if there are conflicting routes
print("\n4. Checking for route conflicts...")
if os.path.exists("src/app/api/morgan-chat"):
    if os.path.isdir("src/app/api/morgan-chat"):
        print("   ℹ️  src/app/api/morgan-chat is a directory")
        for f in os.listdir("src/app/api/morgan-chat"):
            print(f"   - {f}")
    elif os.path.isfile("src/app/api/morgan-chat"):
        print("   ⚠️  src/app/api/morgan-chat is a FILE (conflict!)")

if os.path.exists("src/app/api/morgan-chat.ts"):
    print("   ⚠️  src/app/api/morgan-chat.ts exists (conflict with directory!)")

# 6. Rebuild
print("\n5. Rebuilding...")
print("   Removing old build...")
os.system("rm -rf .next")
print("   Building...")
build = os.system("npm run build 2>&1 | tail -20")
if build == 0:
    print("   ✅ Build successful!")
    
    # Check if route is in manifest now
    if os.path.exists(".next/server/app-paths-manifest.json"):
        with open(".next/server/app-paths-manifest.json") as f:
            manifest = f.read()
        if "/api/morgan-chat" in manifest:
            print("   ✅ /api/morgan-chat is now in route manifest!")
        else:
            print("   ❌ Still not in route manifest")
            
    # 7. Restart PM2
    print("\n6. Restarting PM2...")
    os.system("pm2 restart buildany")
    time.sleep(5)
    
    # 8. Test
    print("\n7. Testing...")
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
            print("   ❌ Still 404")
        else:
            code = output.split("HTTP_CODE:")[-1].strip()[:3] if "HTTP_CODE:" in output else "???"
            print(f"   Status: {code}")
    except Exception as e:
        print(f"   Error: {e}")
else:
    print("   ❌ Build failed!")

os.system("pm2 save")

print("\n" + "=" * 60)
print("🎉 Done!")
print("=" * 60)
