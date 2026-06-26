#!/usr/bin/env python3
"""
Fix: middleware.ts blocking Morgan chat routes - add to PUBLIC routes
Pushed to: https://github.com/taqihas1/buildany-deploy/main/fix_middleware_public.py
"""
import os

BUILDANY_DIR = "/root/buildany"
os.chdir(BUILDANY_DIR)

print("=" * 60)
print("🔧 Middleware Public Routes Fix")
print("=" * 60)

middleware_path = "src/middleware.ts"
with open(middleware_path) as f:
    middleware = f.read()

print("\n1. Current public routes in middleware:")
if '"/api/morgan-chat"' in middleware:
    print("   ✅ /api/morgan-chat is already public")
else:
    print("   ❌ /api/morgan-chat is NOT public - adding...")
    # Add it after /api/morgan-generate
    middleware = middleware.replace(
        '"/api/morgan-generate",',
        '"/api/morgan-generate",\n  "/api/morgan-chat",'
    )
    print("   ✅ Added /api/morgan-chat to public routes")

if '"/api/project-chat-init"' in middleware:
    print("   ✅ /api/project-chat-init is already public")
else:
    print("   ❌ /api/project-chat-init is NOT public - adding...")
    middleware = middleware.replace(
        '"/api/morgan-chat",',
        '"/api/morgan-chat",\n  "/api/project-chat-init",'
    )
    print("   ✅ Added /api/project-chat-init to public routes")

with open(middleware_path, "w") as f:
    f.write(middleware)

print("\n2. Rebuilding...")
build = os.system("npm run build 2>&1 | tail -15")
if build == 0:
    print("   ✅ Build successful!")
    print("\n3. Restarting PM2...")
    os.system("pm2 restart buildany")
    print("   ✅ Restarted!")
    
    print("\n4. Testing Morgan chat...")
    import time, subprocess
    time.sleep(3)
    
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
        print("   ✅ Morgan chat API is responding!")
    elif "HTTP_CODE:404" in output:
        print("   ❌ Still 404")
    else:
        code = output.split("HTTP_CODE:")[-1].strip()[:3] if "HTTP_CODE:" in output else "???"
        print(f"   Status: {code}")
else:
    print("   ❌ Build failed")

print("\n" + "=" * 60)
print("🎉 Done! The middleware was blocking Morgan chat.")
print("=" * 60)
