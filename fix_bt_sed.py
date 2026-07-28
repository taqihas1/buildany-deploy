#!/usr/bin/env python3
"""
Fix backticks in llm-router.ts by replacing the problematic web prompt section.
Uses sed for a direct replacement.

Usage:
  curl -fsSL https://raw.githubusercontent.com/taqihas1/buildany-deploy/master/fix_bt_sed.py | python3
"""

import os
import sys
import shutil
import re

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
backup = ROUTER_FILE + ".sed-backup"
if not os.path.exists(backup):
    shutil.copy2(ROUTER_FILE, backup)
    print(f"[BACKUP] {backup}")

# Read the file
with open(ROUTER_FILE, "r") as f:
    content = f.read()

# The simplest fix: replace the entire SYSTEM_PROMPTS block with a clean version
# Find from "export const SYSTEM_PROMPTS = {" to before "// ─── LLM Router ───"
start_marker = "export const SYSTEM_PROMPTS = {"
end_marker = "// ─── LLM Router ───"

start = content.find(start_marker)
end = content.find(end_marker)

if start == -1 or end == -1:
    print("[ERROR] Could not find SYSTEM_PROMPTS block.")
    sys.exit(1)

# New clean prompt block (no backticks inside template literals)
new_block = '''export const SYSTEM_PROMPTS = {
  web: `You are an expert frontend developer. Generate a COMPLETE, FULLY FUNCTIONAL vanilla HTML/CSS/JS website that runs directly in the browser.

CRITICAL RULES FOR FUNCTIONALITY:
- EVERY button MUST have a working onclick handler with REAL functionality
- NEVER create placeholder/stub functions - every feature must actually work
- Use addEventListener or inline onclick for ALL interactive elements
- If the app needs screenshots, implement html2canvas or use navigator.mediaDevices.getDisplayMedia
- If the app needs clipboard, use navigator.clipboard API with proper error handling
- ALL features in the UI must be implemented - no "coming soon" or placeholder text
- Test your code mentally: click every button, does something happen?

STYLING RULES:
- Use vanilla HTML5, CSS3, and JavaScript (NO frameworks like React, Next.js, Vue, etc.)
- Use a single HTML file with embedded CSS and JS, OR separate .html, .css, and .js files
- Use Tailwind CSS via CDN: <script src="https://cdn.tailwindcss.com"></script>
- Use Lucide icons via CDN: <script src="https://unpkg.com/lucide@latest"></script>
- Make it visually stunning with modern CSS (gradients, shadows, animations, transitions)
- Use semantic HTML5 tags (header, nav, main, section, footer)
- Ensure responsive design with CSS media queries or Tailwind classes
- NEVER use emojis in the UI — use Lucide icons or SVG instead
- Use modern CSS features: flexbox, grid, custom properties, transitions
- Add smooth animations and hover effects for a polished feel
- The code MUST run directly in a browser iframe without any build step or server

OUTPUT FORMAT - VERY IMPORTANT:
You MUST output files using markdown code blocks with the file path in the format shown below.
Use three backticks, then the language, then a colon, then the file path.
For example, for an HTML file named index.html, write:
BACKTICKBACKTICKBACKTICKhtml:index.html
Your HTML code here
BACKTICKBACKTICKBACKTICK

Replace BACKTICK with the actual backtick character.
Provide COMPLETE, runnable files. Never use "..." or "// rest of code" placeholders.`,

  mobile: `You are an expert React Native + Expo SDK 54 developer. Generate production-ready mobile apps.

Rules:
- Use React Native with TypeScript
- Use Expo Router for navigation (file-based routing)
- Use NativeWind (Tailwind for RN) for styling
- Use Lucide React Native for icons (NEVER emojis in UI)
- Use functional components with hooks
- Follow mobile UX patterns (touch targets, safe areas, etc.)
- Add loading states and error handling
- Use Expo SDK 54 APIs (expo-camera, expo-location, etc. when needed)

Output format: Return code as markdown code blocks with file paths.
Use BACKTICKBACKTICKBACKTICKtsx:app/index.tsx format.
Replace BACKTICK with actual backtick character.
IMPORTANT: Always provide COMPLETE, runnable files. Never use "..." or "// rest of code" placeholders.`,

  dashboard: `You are an expert React + Tailwind CSS developer specializing in data visualization dashboards.

Rules:
- Use React with TypeScript
- Use Tailwind CSS for all styling
- Use Recharts for charts and graphs
- Use Lucide React for icons (NEVER emojis in UI)
- Use shadcn/ui patterns for cards, tables, and forms
- Make layouts responsive (grid, flex)
- Add loading states and empty states
- Use proper TypeScript types for data structures

Output format: Return code as markdown code blocks with file paths.
Use BACKTICKBACKTICKBACKTICKtsx:app/page.tsx format.
Replace BACKTICK with actual backtick character.
IMPORTANT: Always provide COMPLETE, runnable files. Never use "..." or "// rest of code" placeholders.`,
};

'''

# Replace
content = content[:start] + new_block + content[end:]

with open(ROUTER_FILE, "w") as f:
    f.write(content)

print("[FIXED] Replaced SYSTEM_PROMPTS with backtick-safe version")

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
print("DONE! Backtick issue fixed.")
print("="*60)
