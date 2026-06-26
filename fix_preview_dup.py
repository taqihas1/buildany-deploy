#!/usr/bin/env python3
"""Fix duplicate outDir and imports in preview route"""
import os, re

BUILDANY_DIR = "/root/buildany"
preview_path = os.path.join(BUILDANY_DIR, "src/app/api/preview/[[...path]]/route.ts")

with open(preview_path) as f:
    content = f.read()

# Count occurrences
outdir_count = content.count("const outDir")
exists_count = content.count("existsSync")
join_count = content.count("from \"path\"")

print(f"Found: {outdir_count} outDir, {exists_count} existsSync, {join_count} path imports")

if outdir_count > 1:
    # Remove the inserted block (the one with "Check if build output exists")
    # Match from "// Check if build output exists" to "  }"
    pattern = r'\n  // Check if build output exists\n  const outDir = join\(process\.cwd\(\), "projects", projectId, "out"\);\n  if \(!existsSync\(outDir\)\) \{[\s\S]*?\n  \}\n'
    content = re.sub(pattern, '\n', content, count=1)
    print("✅ Removed duplicate outDir block")

if exists_count > 1 and "import { existsSync } from \"fs\";" in content:
    # Remove the duplicate import we added
    content = content.replace(
        'import { existsSync } from "fs";\n',
        '',
        1
    )
    print("✅ Removed duplicate existsSync import")

if join_count > 1 and "import { join } from \"path\";" in content:
    # Remove the duplicate import we added
    content = content.replace(
        'import { join } from "path";\n',
        '',
        1
    )
    print("✅ Removed duplicate join import")

with open(preview_path, "w") as f:
    f.write(content)

print("\n🔨 Rebuilding...")
result = os.system("cd %s && npm run build 2>&1" % BUILDANY_DIR)

if result == 0:
    print("\n✅ BUILD SUCCESS!")
    os.system("pm2 restart buildany")
else:
    print("\n❌ Build failed - check errors above")
