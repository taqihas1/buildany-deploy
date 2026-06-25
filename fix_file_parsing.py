#!/usr/bin/env python3
"""
Fix file path parsing in morgan-generate - strip /* */ comment markers
"""
import os, re

BUILDANY_DIR = "/root/buildany"
MORGAN_ROUTE = os.path.join(BUILDANY_DIR, "src/app/api/morgan-generate/route.ts")

print("🔧 Fixing file path parsing...")

with open(MORGAN_ROUTE) as f:
    content = f.read()

# Find the file parsing section and fix it
old_code = '''    const fileRegex = /```(?:tsx?|jsx?|css|json|md|env)?\\s*\\n?(?:\\/\\/\\s*)?(.+?)\\n([\\s\\S]*?)```/g;
    const files: Record<string, string> = {};
    let match;
    while ((match = fileRegex.exec(generatedText)) !== null) {
      const filePath = match[1].trim().replace(/^\\/\\//, "").trim();
      const fileContent = match[2].trim();
      if (filePath && fileContent) {
        files[filePath] = fileContent;
      }
    }'''

new_code = '''    const fileRegex = /```(?:tsx?|jsx?|css|json|md|env)?\\s*\\n?(?:\\/\\/\\s*)?(.+?)\\n([\\s\\S]*?)```/g;
    const files: Record<string, string> = {};
    let match;
    while ((match = fileRegex.exec(generatedText)) !== null) {
      let filePath = match[1].trim();
      // Strip leading // comment markers
      filePath = filePath.replace(/^\\/\\/\\s*/, "");
      // Strip leading /* comment markers
      filePath = filePath.replace(/^\\/\\*\\s*/, "");
      // Strip trailing */ comment markers
      filePath = filePath.replace(/\\s*\\*\\/$/, "");
      filePath = filePath.trim();
      
      const fileContent = match[2].trim();
      if (filePath && fileContent) {
        files[filePath] = fileContent;
      }
    }'''

if old_code in content:
    content = content.replace(old_code, new_code)
    print("✅ Fixed file path parsing")
else:
    # Try regex replacement
    pattern = r'const filePath = match\[1\]\.trim\(\)\.replace\(/\^\\/\\//, ""\)\.trim\(\);'
    replacement = '''let filePath = match[1].trim();
      // Strip leading // comment markers
      filePath = filePath.replace(/^\\/\\/\\s*/, "");
      // Strip leading /* comment markers
      filePath = filePath.replace(/^\\/\\*\\s*/, "");
      // Strip trailing */ comment markers
      filePath = filePath.replace(/\\s*\\*\\/$/, "");
      filePath = filePath.trim();'''
    
    content = re.sub(pattern, replacement, content)
    print("✅ Fixed file path parsing (regex)")

with open(MORGAN_ROUTE, "w") as f:
    f.write(content)

# Also fix the build command to remove --no-lint if it exists
with open(MORGAN_ROUTE) as f:
    content = f.read()

if "--no-lint" in content:
    content = content.replace("--no-lint", "")
    print("✅ Removed --no-lint flag")
    with open(MORGAN_ROUTE, "w") as f:
        f.write(content)

# Commit and build
os.chdir(BUILDANY_DIR)
os.system("git add src/app/api/morgan-generate/route.ts")
os.system("git commit -m 'fix: strip /* */ from file paths in morgan-generate'")

print("\n🔨 Building...")
result = os.system("npm run build")

if result == 0:
    print("\n✅ BUILD SUCCESS!")
    os.system("pm2 restart buildany")
    print("🚀 BuildAny restarted!")
    print("\n💡 Test a new project - the file paths should be clean now!")
else:
    print("\n❌ BUILD FAILED")
    exit(1)
