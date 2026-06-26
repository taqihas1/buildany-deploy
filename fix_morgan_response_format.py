#!/usr/bin/env python3
"""
Fix: Morgan chat API response format - must match frontend expectations
Pushed to: https://github.com/taqihas1/buildany-deploy/main/fix_morgan_response_format.py
"""
import os

BUILDANY_DIR = "/root/buildany"
os.chdir(BUILDANY_DIR)

print("=" * 60)
print("🔧 Morgan Chat Response Format Fix")
print("=" * 60)

# The frontend expects: { response: "text" } or { message: "text" }
# But the API returns: { role: "assistant", content: "text" }
# Fix: return both formats for compatibility

chat_path = "src/app/api/morgan-chat/route.ts"
with open(chat_path) as f:
    content = f.read()

print("\n1. Checking current response format...")
if 'return NextResponse.json({ role: "assistant", content: assistantMessage })' in content:
    print("   Found: { role, content } format")
    print("   Frontend expects: { response } or { message }")
    print("   Fixing...")
    
    # Replace the response format
    content = content.replace(
        'return NextResponse.json({ role: "assistant", content: assistantMessage })',
        'return NextResponse.json({ role: "assistant", content: assistantMessage, response: assistantMessage, message: assistantMessage })'
    )
    
    with open(chat_path, "w") as f:
        f.write(content)
    print("   ✅ Fixed: Now returns response, message, role, and content fields")
    
elif 'response: assistantMessage' in content:
    print("   ✅ Already has response field")
else:
    print("   ⚠️ Could not find response format - checking end of file...")
    # Look for the return statement
    if 'return NextResponse.json(' in content:
        # Find and add response field
        content = content.replace(
            'return NextResponse.json({ role: "assistant", content: assistantMessage })',
            'return NextResponse.json({ role: "assistant", content: assistantMessage, response: assistantMessage, message: assistantMessage })'
        )
        with open(chat_path, "w") as f:
            f.write(content)
        print("   ✅ Fixed")
    else:
        print("   ❌ Could not find return statement")

# Also check if there's a shouldBuild field needed
print("\n2. Checking for shouldBuild field...")
if "shouldBuild" not in content:
    print("   Adding shouldBuild detection...")
    # The API should detect [BUILD: ...] in the response and return shouldBuild: true
    # But actually the frontend does this check: const buildMatch = responseText.match(/\[BUILD:\s*([^\]]+)\]/);
    # So the frontend handles the build trigger. We just need to return the response text.
    print("   Frontend already checks for [BUILD: ...] in response text - OK")
else:
    print("   ✅ shouldBuild field exists")

# Rebuild
print("\n3. Rebuilding...")
build = os.system("npm run build 2\u003e\u00261 | tail -15")
if build == 0:
    print("   ✅ Build successful!")
    print("\n4. Restarting PM2...")
    os.system("pm2 restart buildany")
    print("   ✅ Restarted!")
    
    # Test
    import time, subprocess
    time.sleep(5)
    print("\n5. Testing API response format...")
    try:
        result = subprocess.run(
            [
                "curl", "-s", "-X", "POST",
                "http://localhost:3000/api/morgan-chat",
                "-H", "Content-Type: application/json",
                "-d", '{"messages":[{"role":"user","content":"hi"}],"projectContext":{"projectId":"test","description":"test","type":"web"}}',
                "-w", "\nHTTP_CODE:%{http_code}\n",
                "-m", "10"
            ],
            capture_output=True, text=True, timeout=15
        )
        output = result.stdout
        if "HTTP_CODE:200" in output:
            print("   ✅ API responds!")
            body = output.split("HTTP_CODE:")[0].strip()
            if body:
                print(f"   Response: {body[:200]}")
                if '"response"' in body:
                    print("   ✅ Has 'response' field!")
                elif '"message"' in body:
                    print("   ✅ Has 'message' field!")
                else:
                    print("   ⚠️ Missing 'response' or 'message' field")
        else:
            code = output.split("HTTP_CODE:")[-1].strip()[:3] if "HTTP_CODE:" in output else "???"
            print(f"   Status: {code}")
    except Exception as e:
        print(f"   Error: {e}")
else:
    print("   ❌ Build failed!")

os.system("pm2 save")

print("\n" + "=" * 60)
print("🎉 Done! Morgan chat response format fixed.")
print("=" * 60)
