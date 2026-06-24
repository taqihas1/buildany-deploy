#!/usr/bin/env python3
"""
Robust sanitizer for Morgan generated files
Handles ALL variations of next/document imports
"""
import os, re, sys

PROJECT_ID = sys.argv[1] if len(sys.argv) > 1 else None

if not PROJECT_ID:
    print("Usage: python3 robust_sanitizer.py <project-id>")
    exit(1)

PROJECT_DIR = f"/data/projects/{PROJECT_ID}"
if not os.path.exists(PROJECT_DIR):
    print(f"❌ Project not found: {PROJECT_DIR}")
    exit(1)

print(f"🔍 Scanning {PROJECT_DIR}...")

fixed_count = 0
for root, dirs, files in os.walk(os.path.join(PROJECT_DIR, "src")):
    for fname in files:
        if not fname.endswith((".tsx", ".ts", ".jsx", ".js")):
            continue
        
        fpath = os.path.join(root, fname)
        with open(fpath) as f:
            content = f.read()
        
        if "next/document" not in content:
            continue
        
        # Skip actual _document files
        if "_document" in fname:
            continue
        
        print(f"  🧹 Fixing: {fpath}")
        orig = content
        
        # Remove ALL imports from next/document (various formats)
        # Format 1: import { Html, Head } from 'next/document'
        content = re.sub(r'import\s*\{[^}]*\}\s*from\s*["\']next/document["\'];?\s*\n?', '', content, flags=re.I)
        # Format 2: import Document from 'next/document'
        content = re.sub(r'import\s+\w+\s+from\s*["\']next/document["\'];?\s*\n?', '', content, flags=re.I)
        # Format 3: import {Html} from "next/document"
        content = re.sub(r'import\s*\{\s*Html\s*\}\s*from\s*["\']next/document["\'];?\s*\n?', '', content, flags=re.I)
        # Format 4: import {Head} from "next/document"
        content = re.sub(r'import\s*\{\s*Head\s*\}\s*from\s*["\']next/document["\'];?\s*\n?', '', content, flags=re.I)
        # Format 5: import {Main} from "next/document"
        content = re.sub(r'import\s*\{\s*Main\s*\}\s*from\s*["\']next/document["\'];?\s*\n?', '', content, flags=re.I)
        # Format 6: import {NextScript} from "next/document"
        content = re.sub(r'import\s*\{\s*NextScript\s*\}\s*from\s*["\']next/document["\'];?\s*\n?', '', content, flags=re.I)
        
        # Replace tags with safe equivalents
        content = re.sub(r'<Html([^>]*)>', r'<div\1>', content, flags=re.I)
        content = re.sub(r'</Html>', '</div>', content, flags=re.I)
        content = re.sub(r'<Main([^>]*)>', r'<main\1>', content, flags=re.I)
        content = re.sub(r'</Main>', '</main>', content, flags=re.I)
        content = re.sub(r'<NextScript\s*/?>', '', content, flags=re.I)
        
        if content != orig:
            with open(fpath, "w") as f:
                f.write(content)
            fixed_count += 1

print(f"\n✅ Fixed {fixed_count} files")

# Now rebuild
print("\n🔨 Rebuilding project...")
os.chdir(PROJECT_DIR)
os.system("rm -rf .next out && npm run build")

print("\n✅ Done! Check if build succeeded.")
