#!/usr/bin/env python3
"""
Fix code parser to handle various LLM output formats.
Also updates system prompt to be more explicit about file format.

Usage:
  curl -fsSL https://raw.githubusercontent.com/taqihas1/buildany-deploy/master/fix_parser.py | python3
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
backup = ROUTER_FILE + ".parser-backup"
if not os.path.exists(backup):
    shutil.copy2(ROUTER_FILE, backup)
    print(f"[BACKUP] {backup}")

# Read current file
with open(ROUTER_FILE, "r") as f:
    content = f.read()

# Replace parseGeneratedCode function
old_func_start = "export function parseGeneratedCode(content: string): ParsedFile[] {"
if old_func_start not in content:
    print("[ERROR] Could not find parseGeneratedCode function.")
    sys.exit(1)

# Find the function boundaries
start = content.find(old_func_start)
rest = content[start:]

# Find the next export function (end of current function)
end_marker = "export function getSystemPromptForType"
end_pos = rest.find(end_marker)
if end_pos == -1:
    print("[ERROR] Could not find end of parseGeneratedCode.")
    sys.exit(1)

new_func = '''export function parseGeneratedCode(content: string): ParsedFile[] {
  const files: ParsedFile[] = [];
  
  // ─── Strategy 1: ```language:path format ───
  const formatWithPath = /```(?:(\\w+):)?([^\\n]+)\\n([\\s\\S]*?)```/g;
  let match;
  while ((match = formatWithPath.exec(content)) !== null) {
    const language = match[1] || "html";
    const path = match[2].trim();
    const fileContent = match[3].trim();
    // Skip if path looks like a language name only (e.g., just "json", "html")
    const looksLikePath = path.includes('.') || path.includes('/') || path.startsWith('src/');
    if (looksLikePath && fileContent && !files.find(f => f.path === path)) {
      files.push({ path, content: fileContent, language });
    }
  }
  
  // ─── Strategy 2: Look for "File: path" or "// path" markers ───
  if (files.length === 0) {
    const fileMarkerPattern = /(?:^|\\n)(?:File:|file:|\\/\\/|#)\\s*([\\w\\/\\-.]+\\.(?:html|css|js|tsx|jsx|ts|json|md|py))\\s*(?:\\n|$)/gi;
    let markerMatch;
    const markers: {path: string, index: number}[] = [];
    while ((markerMatch = fileMarkerPattern.exec(content)) !== null) {
      markers.push({path: markerMatch[1], index: markerMatch.index});
    }
    
    for (let i = 0; i < markers.length; i++) {
      const start = markers[i].index + markers[i].path.length + 10; // rough offset
      const end = i < markers.length - 1 ? markers[i + 1].index : content.length;
      const fileContent = content.slice(start, end).trim();
      // Strip leading code block markers if present
      const cleanContent = fileContent.replace(/^```\\w*\\n?/, '').replace(/\\n?```$/, '').trim();
      if (cleanContent && !files.find(f => f.path === markers[i].path)) {
        files.push({ 
          path: markers[i].path, 
          content: cleanContent, 
          language: markers[i].path.split('.').pop() || 'html'
        });
      }
    }
  }
  
  // ─── Strategy 3: Parse markdown code blocks without paths ───
  if (files.length === 0) {
    const codeBlockPattern = /```(\\w+)?\\n([\\s\\S]*?)```/g;
    let blockIndex = 0;
    while ((match = codeBlockPattern.exec(content)) !== null) {
      const lang = match[1] || 'html';
      const code = match[2].trim();
      // Try to detect if this is HTML/JS/React
      let path: string;
      if (code.includes('<!DOCTYPE html>') || code.includes('<html')) {
        path = 'index.html';
      } else if (lang === 'css') {
        path = 'styles.css';
      } else if (lang === 'js' || lang === 'javascript') {
        path = 'app.js';
      } else if (lang === 'tsx' || lang === 'ts') {
        path = 'app.tsx';
      } else {
        path = `file${blockIndex}.${lang}`;
      }
      if (code && !files.find(f => f.path === path)) {
        files.push({ path, content: code, language: lang });
      }
      blockIndex++;
    }
  }
  
  // ─── Strategy 4: If content looks like HTML but no blocks found ───
  if (files.length === 0 && (content.includes('<!DOCTYPE html>') || content.includes('<html'))) {
    files.push({ path: 'index.html', content, language: 'html' });
  }
  
  // ─── Strategy 5: If content looks like JSON (schema/data) ───
  if (files.length === 0 && content.trim().startsWith('{')) {
    try {
      JSON.parse(content);
      files.push({ path: 'data.json', content, language: 'json' });
    } catch {
      // Not valid JSON
    }
  }
  
  return files;
}
'''

content = content[:start] + new_func + content[start + end_pos:]

# Also update system prompt
old_prompt = 'Output format: Return code as markdown code blocks with file paths:'
new_prompt = '''OUTPUT FORMAT - VERY IMPORTANT:
You MUST output files using markdown code blocks with the file path in the format:

```html:index.html
<!-- HTML content here -->
```

```css:styles.css
/* CSS content here */
```

```js:app.js
// JavaScript content here
```

Each file MUST start with ```language:filepath and end with ```.
Provide COMPLETE, runnable files. Never use "..." or "// rest of code" placeholders.'''

if old_prompt in content:
    content = content.replace(old_prompt, new_prompt)
    print("[FIXED] Updated system prompt for explicit file format")
else:
    print("[WARN] Could not find old prompt text, prompt may already be updated")

with open(ROUTER_FILE, "w") as f:
    f.write(content)

print("[FIXED] parseGeneratedCode updated with multiple parsing strategies")

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
print("DONE! Parser now handles multiple LLM output formats.")
print("Try building a new project!")
print("="*60)
