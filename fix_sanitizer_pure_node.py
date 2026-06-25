#!/usr/bin/env python3
"""
Replace the broken shell-based sanitizer with a pure Node.js one
"""
import os, re

BUILDANY_DIR = "/root/buildany"
os.chdir(BUILDANY_DIR)

print("=" * 60)
print("🔧 Fixing Sanitizer (Shell → Pure Node.js)")
print("=" * 60)

# Read current route
with open("src/app/api/morgan-generate/route.ts") as f:
    content = f.read()

# Find and replace the sanitizeGeneratedFiles function
old_func = r'function sanitizeGeneratedFiles\(projectDir: string\) \{[\s\S]*?\n\}'

new_func = '''function sanitizeGeneratedFiles(projectDir: string) {
  try {
    const fs = require("fs");
    const path = require("path");
    
    function walkDir(dir: string, callback: (fp: string) => void) {
      const entries = fs.readdirSync(dir, { withFileTypes: true });
      for (const entry of entries) {
        const fullPath = path.join(dir, entry.name);
        if (entry.isDirectory() && entry.name !== "node_modules") {
          walkDir(fullPath, callback);
        } else if (entry.isFile() && /\\.(tsx?|jsx?)$/.test(entry.name)) {
          callback(fullPath);
        }
      }
    }
    
    const srcDir = path.join(projectDir, "src");
    if (!fs.existsSync(srcDir)) return;
    
    walkDir(srcDir, (fp: string) => {
      if (fp.includes("_document")) return; // Skip actual _document files
      
      let code = fs.readFileSync(fp, "utf8");
      if (!code.includes("next/document")) return;
      
      console.log(`[Sanitize] Fixing: ${fp}`);
      
      // Remove all import variations from next/document
      code = code.replace(/import\\s*\\{[^}]*\\}\\s*from\\s*["']next\/document["'];?\\s*\\n?/gi, "");
      code = code.replace(/import\\s+\\w+\\s+from\\s*["']next\/document["'];?\\s*\\n?/gi, "");
      
      // Replace JSX tags
      code = code.replace(/<Html([^>]*)>/gi, "<div$1>");
      code = code.replace(/<\\/Html>/gi, "</div>");
      code = code.replace(/<Main([^>]*)>/gi, "<main$1>");
      code = code.replace(/<\\/Main>/gi, "</main>");
      code = code.replace(/<NextScript\\s*\\/>/gi, "");
      
      fs.writeFileSync(fp, code);
    });
  } catch (e) {
    console.error("[Sanitize] Error:", e);
  }
}'''

# Replace the function
content = re.sub(old_func, new_func, content)

with open("src/app/api/morgan-generate/route.ts", "w") as f:
    f.write(content)

print("✅ Replaced sanitizer with pure Node.js version")

# Commit and build
os.system("git add src/app/api/morgan-generate/route.ts")
os.system('git commit -m "fix: replace shell sanitizer with pure Node.js"')

print("\n🔨 Building...")
build_result = os.system("npm run build")

if build_result == 0:
    print("\n✅ BUILD SUCCESS!")
    os.system("pm2 restart buildany")
    print("🚀 BuildAny restarted!")
    print("\n💡 Sanitizer now uses pure Node.js - no shell quote issues!")
else:
    print("\n❌ BUILD FAILED")
    exit(1)
