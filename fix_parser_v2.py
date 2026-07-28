#!/usr/bin/env python3
"""
Comprehensive parser fix for llm-router.ts on VPS.
Handles JSON responses and multiple code block formats.

Usage:
  curl -fsSL https://raw.githubusercontent.com/taqihas1/buildany-deploy/master/fix_parser_v2.py | python3
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
backup = ROUTER_FILE + ".parser2-backup"
if not os.path.exists(backup):
    shutil.copy2(ROUTER_FILE, backup)
    print(f"[BACKUP] {backup}")

# Read current file
with open(ROUTER_FILE, "r") as f:
    content = f.read()

# Find and replace parseGeneratedCode function
# Look for the function signature
func_start = content.find("export function parseGeneratedCode(content: string): ParsedFile[] {")
if func_start == -1:
    print("[ERROR] Could not find parseGeneratedCode function.")
    sys.exit(1)

# Find the next function after parseGeneratedCode
next_func_markers = [
    "export function getSystemPromptForType",
    "export class LLMRouter",
    "export function generateCode"
]

func_end = -1
for marker in next_func_markers:
    pos = content.find(marker, func_start + 1)
    if pos != -1:
        if func_end == -1 or pos < func_end:
            func_end = pos

if func_end == -1:
    print("[ERROR] Could not find end of parseGeneratedCode function.")
    sys.exit(1)

# New parser function
new_parser = '''export function parseGeneratedCode(content: string): ParsedFile[] {
  console.log("[Parser] Input length:", content.length);
  console.log("[Parser] First 200 chars:", content.substring(0, 200));
  
  const files: ParsedFile[] = [];
  
  // ─── Strategy 0: Check if content is JSON wrapper ───
  const trimmed = content.trim();
  if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
    try {
      const parsed = JSON.parse(trimmed);
      // If it's an object with a "files" or "code" field, extract from there
      if (parsed && typeof parsed === 'object') {
        const codeContent = parsed.files || parsed.code || parsed.content || parsed.source || parsed.html || parsed.response;
        if (typeof codeContent === 'string') {
          console.log("[Parser] Found JSON wrapper, extracting inner content");
          content = codeContent;
        } else if (Array.isArray(parsed.files)) {
          // Array of file objects
          for (const file of parsed.files) {
            if (file.path && file.content) {
              files.push({
                path: file.path,
                content: file.content,
                language: file.language || file.path.split('.').pop() || 'html'
              });
            }
          }
          if (files.length > 0) {
            console.log("[Parser] Extracted", files.length, "files from JSON array");
            return files;
          }
        }
      }
    } catch (e) {
      // Not valid JSON, continue
    }
  }
  
  // ─── Strategy 1: ```language:path format (most specific) ───
  const formatWithPath = /\\`\\`\\`(?:(\\w+):)?([^\\n]+)\\n([\\s\\S]*?)\\`\\`\\`/g;
  let match;
  while ((match = formatWithPath.exec(content)) !== null) {
    const language = match[1] || "html";
    const path = match[2].trim();
    const fileContent = match[3].trim();
    // Skip if path looks like just a language name
    const looksLikePath = path.includes('.') || path.includes('/') || path.startsWith('src/');
    if (looksLikePath && fileContent && !files.find(f => f.path === path)) {
      files.push({ path, content: fileContent, language });
    }
  }
  
  // ─── Strategy 2: Look for "File: path" or path markers before code blocks ───
  if (files.length === 0) {
    const fileMarkerPattern = /(?:^|\\n)(?:File:|file:|#\\s*|\\/\\/\\s*)([\\w\\/\\-.]+\\.(?:html|css|js|tsx|jsx|ts|json|md|py))\\s*(?:\\n|$)/gi;
    let markerMatch;
    const markers: {path: string, index: number}[] = [];
    while ((markerMatch = fileMarkerPattern.exec(content)) !== null) {
      markers.push({path: markerMatch[1], index: markerMatch.index});
    }
    
    for (let i = 0; i < markers.length; i++) {
      const startIdx = markers[i].index + markers[i].path.length + 10;
      const endIdx = i < markers.length - 1 ? markers[i + 1].index : content.length;
      let fileContent = content.slice(startIdx, endIdx).trim();
      // Strip code block markers if present
      fileContent = fileContent.replace(/^\\`\\`\\`\\w*\\n?/, '').replace(/\\n?\\`\\`\\`$/, '').trim();
      if (fileContent && !files.find(f => f.path === markers[i].path)) {
        files.push({ 
          path: markers[i].path, 
          content: fileContent, 
          language: markers[i].path.split('.').pop() || 'html'
        });
      }
    }
  }
  
  // ─── Strategy 3: Parse markdown code blocks without explicit paths ───
  if (files.length === 0) {
    const codeBlockPattern = /\\`\\`\\`(\\w+)?\\n([\\s\\S]*?)\\`\\`\\`/g;
    let blockIndex = 0;
    while ((match = codeBlockPattern.exec(content)) !== null) {
      const lang = match[1] || 'html';
      const code = match[2].trim();
      
      // Skip if it's a setup/bash command block
      if (lang === 'bash' || lang === 'sh' || lang === 'shell') {
        continue;
      }
      
      let path: string;
      if (code.includes('<!DOCTYPE html>') || code.includes('<html')) {
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
        path = `file${blockIndex}.${lang}`;
      }
      
      if (code && !files.find(f => f.path === path)) {
        files.push({ path, content: code, language: lang });
      }
      blockIndex++;
    }
  }
  
  // ─── Strategy 4: If content looks like raw HTML ───
  if (files.length === 0 && (content.includes('<!DOCTYPE html>') || content.includes('<html'))) {
    files.push({ path: 'index.html', content, language: 'html' });
  }
  
  console.log("[Parser] Extracted", files.length, "files");
  if (files.length > 0) {
    console.log("[Parser] First file:", files[0].path, "(" + files[0].content.length, "chars)");
  }
  
  return files;
}

'''

# Replace the function
content = content[:func_start] + new_parser + content[func_end:]

with open(ROUTER_FILE, "w") as f:
    f.write(content)

print("[FIXED] Updated parseGeneratedCode with JSON handling and better logging")

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
print("DONE! Parser now handles JSON wrappers and multiple formats.")
print("Try building again and check logs with:")
print("  tail -f ~/.pm2/logs/buildany-out.log | grep -E 'Parser|parsedFiles|Build'")
print("="*60)
