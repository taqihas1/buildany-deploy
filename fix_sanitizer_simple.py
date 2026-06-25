#!/usr/bin/env python3
"""
Simple fix - just rewrite the sanitizer function cleanly
"""
import os

BUILDANY_DIR = "/root/buildany"
os.chdir(BUILDANY_DIR)

print("🔧 Fixing sanitizer...")

# Read file
with open("src/app/api/morgan-generate/route.ts") as f:
    lines = f.readlines()

# Find sanitizeGeneratedFiles function and replace it
output = []
i = 0
while i < len(lines):
    line = lines[i]
    if "function sanitizeGeneratedFiles" in line:
        # Skip until end of function
        brace_count = 0
        started = False
        while i < len(lines):
            if "{" in lines[i]:
                brace_count += lines[i].count("{")
                started = True
            if "}" in lines[i]:
                brace_count -= lines[i].count("}")
            i += 1
            if started and brace_count <= 0:
                break
        
        # Insert new function
        output.append("function sanitizeGeneratedFiles(projectDir: string) {\n")
        output.append("  try {\n")
        output.append("    const fs = require('fs');\n")
        output.append("    const path = require('path');\n")
        output.append("    function walkDir(dir, callback) {\n")
        output.append("      if (!fs.existsSync(dir)) return;\n")
        output.append("      const entries = fs.readdirSync(dir, { withFileTypes: true });\n")
        output.append("      for (const entry of entries) {\n")
        output.append("        const fullPath = path.join(dir, entry.name);\n")
        output.append("        if (entry.isDirectory() && entry.name !== 'node_modules') {\n")
        output.append("          walkDir(fullPath, callback);\n")
        output.append("        } else if (entry.isFile() && /\\.(tsx?|jsx?)$/.test(entry.name)) {\n")
        output.append("          callback(fullPath);\n")
        output.append("        }\n")
        output.append("      }\n")
        output.append("    }\n")
        output.append("    const srcDir = path.join(projectDir, 'src');\n")
        output.append("    walkDir(srcDir, (fp) => {\n")
        output.append("      if (fp.includes('_document')) return;\n")
        output.append("      let code = fs.readFileSync(fp, 'utf8');\n")
        output.append("      if (!code.includes('next/document')) return;\n")
        output.append("      console.log('[Sanitize] Fixing: ' + fp);\n")
        output.append("      code = code.replace(/import\\s*\\{[^}]*\\}\\s*from\\s*[' + \"\" + '']next/document[' + \"\" + ''];?\\s*\\n?/gi, '');\n")
        output.append("      code = code.replace(/import\\s+\\w+\\s+from\\s*[' + \"\" + '']next/document[' + \"\" + ''];?\\s*\\n?/gi, '');\n")
        output.append("      code = code.replace(/<Html([^>]*)>/gi, '<div$1>');\n")
        output.append("      code = code.replace(/<\\/Html>/gi, '</div>');\n")
        output.append("      code = code.replace(/<Main([^>]*)>/gi, '<main$1>');\n")
        output.append("      code = code.replace(/<\\/Main>/gi, '</main>');\n")
        output.append("      code = code.replace(/<NextScript\\s*\\/>/gi, '');\n")
        output.append("      fs.writeFileSync(fp, code);\n")
        output.append("    });\n")
        output.append("  } catch (e) {\n")
        output.append("    console.error('[Sanitize] Error:', e);\n")
        output.append("  }\n")
        output.append("}\n")
    else:
        output.append(line)
        i += 1

with open("src/app/api/morgan-generate/route.ts", "w") as f:
    f.writelines(output)

print("✅ Sanitizer fixed!")

# Commit and build
os.system("git add src/app/api/morgan-generate/route.ts")
os.system("git commit -m 'fix: pure Node.js sanitizer'")

print("\n🔨 Building...")
build_result = os.system("npm run build")

if build_result == 0:
    print("\n✅ BUILD SUCCESS!")
    os.system("pm2 restart buildany")
    print("🚀 BuildAny restarted!")
else:
    print("\n❌ BUILD FAILED")
    exit(1)
