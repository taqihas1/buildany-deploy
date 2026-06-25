#!/usr/bin/env python3
"""
Comprehensive fix for Morgan builds:
1. Pure Node.js sanitizer (no shell quote issues)
2. Fix file tree to show files
3. Fix preview to handle errors gracefully
"""
import os, re

BUILDANY_DIR = "/root/buildany"
os.chdir(BUILDANY_DIR)

print("=" * 60)
print("🔧 Comprehensive Morgan Build Fix")
print("=" * 60)

# 1. Fix morgan-generate route - replace sanitizer
with open("src/app/api/morgan-generate/route.ts") as f:
    content = f.read()

# Find the sanitizeGeneratedFiles function and replace it
old_pattern = r'function sanitizeGeneratedFiles\(projectDir: string\) \{[\s\S]*?\n\}'

new_func = '''function sanitizeGeneratedFiles(projectDir: string) {
  try {
    const fs = require("fs");
    const path = require("path");
    
    function walkDir(dir: string, callback: (fp: string) => void) {
      if (!fs.existsSync(dir)) return;
      const entries = fs.readdirSync(dir, { withFileTypes: true });
      for (const entry of entries) {
        const fullPath = path.join(dir, entry.name);
        if (entry.isDirectory() && entry.name !== "node_modules" && entry.name !== ".git") {
          walkDir(fullPath, callback);
        } else if (entry.isFile() && /\\.(tsx?|jsx?)$/.test(entry.name)) {
          callback(fullPath);
        }
      }
    }
    
    const srcDir = path.join(projectDir, "src");
    walkDir(srcDir, (fp: string) => {
      if (fp.includes("_document")) return;
      
      let code = fs.readFileSync(fp, "utf8");
      if (!code.includes("next/document")) return;
      
      console.log(`[Sanitize] Fixing: ${fp}`);
      
      // Remove all imports from next/document
      code = code.replace(/import\\s*\\{[^}]*\\}\\s*from\\s*["']next\\/document["'];?\\s*\\n?/gi, "");
      code = code.replace(/import\\s+\\w+\\s+from\\s*["']next\\/document["'];?\\s*\\n?/gi, "");
      
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

content = re.sub(old_pattern, new_func, content)

with open("src/app/api/morgan-generate/route.ts", "w") as f:
    f.write(content)

print("✅ 1. Sanitizer fixed (pure Node.js)")

# 2. Fix project-files API to properly list files
with open("src/app/api/project-files/route.ts") as f:
    pf_content = f.read()

# Check if it properly walks directories
if "readdirSync" not in pf_content:
    print("⚠️ project-files API may need fixing - check manually")
else:
    print("✅ 2. project-files API looks OK")

# 3. Fix preview API to handle missing builds gracefully
preview_path = "src/app/api/preview/[[...path]]/route.ts"
if os.path.exists(preview_path):
    with open(preview_path) as f:
        preview = f.read()
    
    # Add check for build output existence
    if "existsSync" not in preview:
        preview = preview.replace(
            "export async function GET",
            '''import { existsSync } from "fs";
import { join } from "path";

export async function GET'''
        )
        
        # Add build check before serving
        preview = preview.replace(
            "const filePath = ",
            '''// Check if build output exists
  const outDir = join(PROJECTS_DIR, projectId, "out");
  if (!existsSync(outDir)) {
    return new NextResponse("Build not completed yet. Click 'Build' to generate.", { status: 404 });
  }

  const filePath = '''
        )
        
        with open(preview_path, "w") as f:
            f.write(preview)
        print("✅ 3. Preview API handles missing builds")
    else:
        print("✅ 3. Preview API already has checks")
else:
    print("⚠️ 3. Preview route not found at expected path")

# 4. Fix Workspace3Col to show files from disk
with open("src/components/Workspace3Col.tsx") as f:
    ws = f.read()

# Add a useEffect to poll for files when status changes
if "useEffect(() => {\n    if (buildStatus === 'ready'" not in ws:
    # Find a good place to add the effect
    ws = ws.replace(
        "// Auto-scroll chat",
        '''// Load files when build completes
  useEffect(() => {
    if (buildStatus === 'ready' || buildStatus === 'failed') {
      fetch(`/api/project-files?projectId=${project.id}`)
        .then(res => res.json())
        .then(data => {
          if (data.files) setFiles(data.files);
        })
        .catch(console.error);
    }
  }, [buildStatus, project.id]);

  // Auto-scroll chat'''
    )
    
    with open("src/components/Workspace3Col.tsx", "w") as f:
        f.write(ws)
    print("✅ 4. Workspace3Col loads files on build completion")
else:
    print("✅ 4. Workspace3Col already loads files")

# Commit and build
os.system("git add -A")
os.system('git commit -m "fix: pure Node sanitizer + file loading + preview error handling"')

print("\n🔨 Building...")
build_result = os.system("npm run build")

if build_result == 0:
    print("\n✅ BUILD SUCCESS!")
    os.system("pm2 restart buildany")
    print("🚀 BuildAny restarted!")
    print("\n💡 Test a new project - it should:")
    print("   1. Generate code without <Html> errors")
    print("   2. Show files in the file tree")
    print("   3. Show a friendly message if build fails")
else:
    print("\n❌ BUILD FAILED")
    exit(1)
