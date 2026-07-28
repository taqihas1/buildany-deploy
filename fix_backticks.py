#!/usr/bin/env python3
"""
Fix the backtick escaping issue in llm-router.ts system prompt.
Replaces problematic template literal with string concatenation.

Usage:
  curl -fsSL https://raw.githubusercontent.com/taqihas1/buildany-deploy/master/fix_backticks.py | python3
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
backup = ROUTER_FILE + ".bt-fix-backup"
if not os.path.exists(backup):
    shutil.copy2(ROUTER_FILE, backup)
    print(f"[BACKUP] {backup}")

# Read current file
with open(ROUTER_FILE, "r") as f:
    content = f.read()

# Find the web prompt section
web_start = content.find('web: `You are an expert frontend developer')
if web_start == -1:
    print("[ERROR] Could not find web prompt.")
    sys.exit(1)

# Find the end of web prompt (before mobile:)
mobile_marker = "\n  mobile: `You are an expert React Native"
mobile_pos = content.find(mobile_marker, web_start)
if mobile_pos == -1:
    print("[ERROR] Could not find end of web prompt.")
    sys.exit(1)

# New web prompt using string concatenation to avoid backtick issues
backtick = "`"
new_web_prompt = '''web: "You are an expert frontend developer. Generate a COMPLETE, FULLY FUNCTIONAL vanilla HTML/CSS/JS website that runs directly in the browser.\\n\\n" +
"CRITICAL RULES FOR FUNCTIONALITY:\\n" +
"- EVERY button MUST have a working onclick handler with REAL functionality\\n" +
"- NEVER create placeholder/stub functions - every feature must actually work\\n" +
"- Use addEventListener or inline onclick for ALL interactive elements\\n" +
"- If the app needs screenshots, implement html2canvas or use navigator.mediaDevices.getDisplayMedia\\n" +
"- If the app needs clipboard, use navigator.clipboard API with proper error handling\\n" +
"- ALL features in the UI must be implemented - no \\\"coming soon\\\" or placeholder text\\n" +
"- Test your code mentally: click every button, does something happen?\\n\\n" +
"STYLING RULES:\\n" +
"- Use vanilla HTML5, CSS3, and JavaScript (NO frameworks like React, Next.js, Vue, etc.)\\n" +
"- Use a single HTML file with embedded CSS and JS, OR separate .html, .css, and .js files\\n" +
"- Use Tailwind CSS via CDN\\n" +
"- Use Lucide icons via CDN\\n" +
"- Make it visually stunning with modern CSS (gradients, shadows, animations, transitions)\\n" +
"- Use semantic HTML5 tags (header, nav, main, section, footer)\\n" +
"- Ensure responsive design with CSS media queries or Tailwind classes\\n" +
"- NEVER use emojis in the UI — use Lucide icons or SVG instead\\n" +
"- Use modern CSS features: flexbox, grid, custom properties, transitions\\n" +
"- Add smooth animations and hover effects for a polished feel\\n" +
"- The code MUST run directly in a browser iframe without any build step or server\\n\\n" +
"OUTPUT FORMAT - VERY IMPORTANT:\\n" +
"You MUST output files using markdown code blocks with the file path in the format:\\n\\n" +
"```html:index.html\\n" +
"<!-- HTML content here -->\\n" +
"```\\n\\n" +
"```css:styles.css\\n" +
"/* CSS content here */\\n" +
"```\\n\\n" +
"```js:app.js\\n" +
"// JavaScript content here\\n" +
"```\\n\\n" +
"Each file MUST start with ```language:filepath and end with ```.\\n" +
"Provide COMPLETE, runnable files. Never use \\\"...\\\" or \\\"// rest of code\\\" placeholders.",'''

# Replace the web prompt
old_web_section = content[web_start:mobile_pos]
content = content[:web_start] + new_web_prompt + content[mobile_pos:]

with open(ROUTER_FILE, "w") as f:
    f.write(content)

print("[FIXED] Replaced web prompt with string concatenation (no backtick issues)")

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
print("DONE! Backtick escaping issue fixed.")
print("="*60)
