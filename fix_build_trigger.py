#!/usr/bin/env python3
"""
Fix: BUILD trigger regex in Workspace3Col.tsx
The regex was too strict and didn't match Morgan's [BUILD: {"appType": "web"}] format
"""
import os, subprocess

FILE = "/root/buildany/src/components/Workspace3Col.tsx"

with open(FILE, 'r') as f:
    content = f.read()

# Fix the regex
old_regex = r'const buildMatch = responseText.match(/\[BUILD:\s*(\{[^\]]*\})\]/)'
new_regex = r'const buildMatch = responseText.match(/\[BUILD:\s*([^\]]+)\]/)'

if old_regex in content:
    content = content.replace(old_regex, new_regex)
    print("✅ Fixed BUILD trigger regex")
else:
    print("⚠️ Old regex not found, checking if already fixed...")
    if new_regex in content:
        print("✅ Regex already fixed")
    else:
        print("❌ Could not find regex pattern")

# Also fix the trim (add .trim() to handle whitespace)
old_parse = 'const buildConfig = JSON.parse(buildMatch[1])'
new_parse = 'const buildConfig = JSON.parse(buildMatch[1].trim())'

if old_parse in content:
    content = content.replace(old_parse, new_parse)
    print("✅ Added .trim() to BUILD config parsing")

with open(FILE, 'w') as f:
    f.write(content)

# Build
print("Building...")
os.chdir("/root/buildany")
result = subprocess.run(["npm", "run", "build"], capture_output=True, text=True)
print(result.stdout[-1500:] if len(result.stdout) > 1500 else result.stdout)
if result.returncode != 0:
    print("STDERR:", result.stderr[-500:] if len(result.stderr) > 500 else result.stderr)
    print("❌ Build failed")
else:
    print("✅ Build successful!")
    subprocess.run(["pm2", "restart", "buildany"], capture_output=True)
    print("✅ Restarted buildany")
