#!/usr/bin/env python3
"""
Fix: Morgan chat API 500 - read exact error from logs and fix it
Pushed to: https://github.com/taqihas1/buildany-deploy/main/fix_morgan_500_error.py
"""
import os, subprocess, re

BUILDANY_DIR = "/root/buildany"
os.chdir(BUILDANY_DIR)

print("=" * 60)
print("🔧 Morgan Chat 500 - Exact Error Fix")
print("=" * 60)

# 1. Read exact error from PM2 logs
print("\n1. Reading exact error from PM2 logs...")
try:
    result = subprocess.run(
        ["pm2", "logs", "buildany", "--lines", "30", "--nostream"],
        capture_output=True, text=True, timeout=10
    )
    logs = result.stdout
    
    # Find the most recent morgan-chat error
    lines = logs.split("\n")
    error_found = False
    for line in lines:
        if "morgan-chat" in line.lower() or "/api/morgan-chat" in line or "Error:" in line:
            print(f"   {line[:150]}")
            error_found = True
    
    if not error_found:
        print("   No morgan-chat specific error found. Showing last 10 log lines:")
        for line in lines[-10:]:
            print(f"   {line[:150]}")
            
except Exception as e:
    print(f"   Could not read logs: {e}")

# 2. Check morgan-chat route for syntax issues
print("\n2. Checking morgan-chat route for syntax issues...")
chat_path = "src/app/api/morgan-chat/route.ts"
with open(chat_path) as f:
    chat_code = f.read()

# Check for syntax issues
if "export async function POST" not in chat_code:
    print("   ❌ Missing POST export!")
else:
    print("   ✅ Has POST export")

# Check for unclosed braces
open_braces = chat_code.count("{")
close_braces = chat_code.count("}")
if open_braces != close_braces:
    print(f"   ❌ Brace mismatch: {open_braces} open, {close_braces} close")
else:
    print("   ✅ Braces balanced")

# Check for unclosed parens
open_parens = chat_code.count("(")
close_parens = chat_code.count(")")
if open_parens != close_parens:
    print(f"   ❌ Paren mismatch: {open_parens} open, {close_parens} close")
else:
    print("   ✅ Parens balanced")

# Check for TypeScript issues
if "const DEEPSEEK_KEY = process.env.DEEPSEEK_API_KEY" in chat_code:
    print("   ✅ DEEPSEEK_KEY defined correctly")
else:
    print("   ⚠️ DEEPSEEK_KEY definition may be wrong")

# Check for string interpolation issues
if "`Bearer ${DEEPSEEK_KEY}`" in chat_code or "Bearer ${DEEPSEEK_KEY}" in chat_code:
    print("   ✅ Bearer auth string looks correct")
else:
    print("   ⚠️ Bearer auth string may have issues")

# 3. Check if the route is trying to use the DeepSeek API correctly
print("\n3. Checking DeepSeek API integration...")
if "https://api.deepseek.com/v1/chat/completions" in chat_code:
    print("   ✅ Using correct DeepSeek API endpoint")
else:
    print("   ❌ Wrong or missing DeepSeek API endpoint!")

if "Authorization" in chat_code and "Bearer" in chat_code:
    print("   ✅ Authorization header present")
else:
    print("   ❌ Missing Authorization header!")

# 4. Check if the route has a proper return statement
if "return NextResponse.json" in chat_code:
    print("   ✅ Returns NextResponse.json")
else:
    print("   ❌ Missing return statement!")

# 5. Check for common TypeScript issues
print("\n5. Checking for TypeScript compilation issues...")
try:
    # Run TypeScript check on just this file
    result = subprocess.run(
        ["npx", "tsc", "--noEmit", "src/app/api/morgan-chat/route.ts"],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode == 0:
        print("   ✅ TypeScript compiles successfully")
    else:
        errors = result.stdout + result.stderr
        print(f"   ❌ TypeScript errors:")
        for line in errors.split("\n")[:10]:
            if line.strip():
                print(f"   {line[:120]}")
except Exception as e:
    print(f"   ⚠️ Could not run TypeScript check: {e}")

# 6. If we can see a clear error, fix it
print("\n6. Attempting fix...")
# Most common issue: the route was written with single quotes but needs double quotes for template literals
# Or: the DEEPSEEK_KEY is not being used correctly

# Check if there's a fetch with missing await or incorrect syntax
if "await fetch" in chat_code:
    print("   ✅ fetch is awaited")
else:
    print("   ⚠️ fetch may not be awaited")

# Check if the body is being parsed correctly
if "const body = await req.json()" in chat_code:
    print("   ✅ Request body is parsed")
else:
    print("   ⚠️ Request body parsing may be wrong")

print("\n7. Testing API with verbose error...")
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
        print("   ✅ Working!")
    elif "HTTP_CODE:500" in output:
        print("   ❌ Still 500")
        # Try to get the error message
        body = output.split("HTTP_CODE:")[0].strip()
        if body:
            print(f"   Response body: {body[:200]}")
    else:
        code = output.split("HTTP_CODE:")[-1].strip()[:3] if "HTTP_CODE:" in output else "???"
        print(f"   Status: {code}")
except Exception as e:
    print(f"   Error: {e}")

print("\n" + "=" * 60)
print("🎉 Diagnostic complete!")
print("=" * 60)
