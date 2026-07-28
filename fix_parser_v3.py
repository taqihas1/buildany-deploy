#!/usr/bin/env python3
"""
Parser v3 - Handles the ACTUAL LLM output format:
- Code blocks with path comments inside: ```tsx \n // app/page.tsx \n code...
- Also handles: ```tsx:app/page.tsx format
- Upsert files (REPLACE on duplicate) instead of INSERT

Usage:
  curl -fsSL https://raw.githubusercontent.com/taqihas1/buildany-deploy/master/fix_parser_v3.py | python3
"""

import os
import sys
import shutil

def find_project():
    candidates = ["/root/buildany", "/root/buildany-fix", "/var/www/buildany"]
    for c in candidates:
        if os.path.exists(os.path.join(c, "package.json")):
            return c
    try:
        import subprocess
        r = subprocess.run(["pm2", "describe", "buildany"], capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            for line in r.stdout.split("\n"):
                if "exec cwd" in line.lower():
                    parts = [p.strip() for p in line.split("│")]
                    if len(parts) >= 3 and os.path.exists(parts[2]):
                        return parts[2]
    except:
        pass
    return None

PROJECT = find_project()
if not PROJECT:
    print("[ERROR] Could not find buildany project.")
    sys.exit(1)

ROUTER_FILE = os.path.join(PROJECT, "src", "lib", "llm-router.ts")
if not os.path.exists(ROUTER_FILE):
    print(f"[ERROR] llm-router.ts not found at {ROUTER_FILE}")
    sys.exit(1)

# Backup
backup = ROUTER_FILE + ".parser3-backup"
if not os.path.exists(backup):
    shutil.copy2(ROUTER_FILE, backup)
    print(f"[BACKUP] {backup}")

# Read current file
with open(ROUTER_FILE, "r") as f:
    content = f.read()

# Find parseGeneratedCode function
func_start = content.find("export function parseGeneratedCode(content: string): ParsedFile[] {")
if func_start == -1:
    print("[ERROR] Could not find parseGeneratedCode function.")
    sys.exit(1)

# Find end of function
next_markers = ["export function getSystemPromptForType", "export class LLMRouter"]
func_end = -1
for m in next_markers:
    pos = content.find(m, func_start + 1)
    if pos != -1 and (func_end == -1 or pos < func_end):
        func_end = pos

if func_end == -1:
    print("[ERROR] Could not find end of function.")
    sys.exit(1)

new_parser = '''export function parseGeneratedCode(content: string): ParsedFile[] {
  console.log("[Parser] Input length:", content.length);
  console.log("[Parser] First 300 chars:", content.substring(0, 300).replace(/\\n/g, " "));
  
  const files: ParsedFile[] = [];
  
  // ─── Strategy 0: JSON wrapper ───
  const trimmed = content.trim();
  if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
    try {
      const parsed = JSON.parse(trimmed);
      if (parsed && typeof parsed === 'object') {
        const inner = parsed.files || parsed.code || parsed.content || parsed.source || parsed.html;
        if (typeof inner === 'string') content = inner;
        else if (Array.isArray(parsed.files)) {
          for (const f of parsed.files) {
            if (f.path && f.content) {
              files.push({ path: f.path, content: f.content, language: f.language || f.path.split('.').pop() || 'html' });
            }
          }
          if (files.length > 0) {
            console.log("[Parser] Extracted", files.length, "files from JSON");
            return files;
          }
        }
      }
    } catch (e) { /* not JSON */ }
  }
  
  // ─── Strategy 1: Split by code blocks and parse each ───
  // Pattern: ```lang or ```lang:path followed by content ending with ```
  const blockRegex = /```(?:(\\w+)(?::([^\\n]+))?)?\\n([\\s\\S]*?)(?:\\n)?```/g;
  let match;
  let blockCount = 0;
  
  while ((match = blockRegex.exec(content)) !== null) {
    blockCount++;
    const lang = match[1] || 'text';
    const pathFromFence = match[2] ? match[2].trim() : null;
    let blockContent = match[3];
    
    // Skip bash/sh/shell blocks (setup commands)
    if (lang === 'bash' || lang === 'sh' || lang === 'shell') {
      console.log("[Parser] Skipping bash block #", blockCount);
      continue;
    }
    
    let path = pathFromFence;
    let codeStartLine = 0;
    
    // If no path in fence, look for path comment in first 3 lines
    if (!path) {
      const lines = blockContent.split('\\n');
      for (let i = 0; i < Math.min(3, lines.length); i++) {
        const line = lines[i].trim();
        // Match: // app/page.tsx, // app/page.tsx (complete), # app/page.tsx, /* app/page.tsx */
        const commentMatch = line.match(/^(?:\\/\\/|#|\\/\\*)\\s*([\\w\\/\\-.]+\\.(?:html|css|js|tsx|jsx|ts|json|md|py))(?:\\s*\\*\\/)?(?:\\s*\\(complete\\))?/i);
        if (commentMatch) {
          path = commentMatch[1];
          codeStartLine = i + 1;
          console.log("[Parser] Found path in comment:", path);
          break;
        }
      }
    }
    
    // Auto-assign path if still not found
    if (!path) {
      const code = blockContent.toLowerCase();
      if (code.includes('<!doctype html>') || code.includes('<html')) {
        path = 'index.html';
      } else if (lang === 'css') {
        path = 'styles.css';
      } else if (lang === 'js' || lang === 'javascript') {
        path = 'app.js';
      } else if (lang === 'tsx' || lang === 'ts') {
        path = 'app.tsx';
      } else if (lang === 'jsx') {
        path = 'app.jsx';
      } else {
        path = `file${blockCount}.${lang}`;
      }
      console.log("[Parser] Auto-assigned path:", path);
    }
    
    // Extract code (skip path comment lines if found)
    const allLines = blockContent.split('\\n');
    const code = allLines.slice(codeStartLine).join('\\n').trim();
    
    if (code && !files.find(f => f.path === path)) {
      files.push({ path, content: code, language: lang });
      console.log("[Parser] Added file:", path, "(" + code.length, "chars)");
    }
  }
  
  // ─── Strategy 2: Raw HTML (no code blocks) ───
  if (files.length === 0 && (content.includes('<!DOCTYPE html>') || content.includes('<html'))) {
    files.push({ path: 'index.html', content, language: 'html' });
  }
  
  console.log("[Parser] Total files extracted:", files.length);
  return files;
}

'''

content = content[:func_start] + new_parser + content[func_end:]

# Also fix the save function to use upsert instead of insert
# Find the file saving code
save_pattern = 'await db.insert(projectFiles).values(fileRecords);'
if save_pattern in content:
    # Replace with upsert using onConflictDoUpdate or delete+insert
    content = content.replace(
        save_pattern,
        '''// Delete existing files first to avoid UNIQUE constraint
      await db.delete(projectFiles).where(eq(projectFiles.projectId, projectId));
      // Then insert new files
      await db.insert(projectFiles).values(fileRecords);'''
    )
    print("[FIXED] Changed file save to delete+insert (avoids UNIQUE constraint)")

with open(ROUTER_FILE, "w") as f:
    f.write(content)

print("[FIXED] Updated parseGeneratedCode to handle comment-paths inside code blocks")

# Rebuild and restart
print("[BUILD] npm run build...")
os.chdir(PROJECT)
result = os.system("npm run build")
if result != 0:
    print("[BUILD FAILED]")
    sys.exit(1)

print("[RESTART] pm2 restart buildany...")
os.system("pm2 restart buildany")

print("\n" + "="*60)
print("DONE! Parser v3 handles actual LLM output format.")
print("Watch logs: tail -f ~/.pm2/logs/buildany-out.log | grep Parser")
print("="*60)
