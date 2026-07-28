#!/usr/bin/env python3
"""
Nuclear option: Strip homepage to absolute minimum to isolate the crash.
Replaces page.tsx with a div that does ZERO imports.

Usage:
  curl -fsSL https://raw.githubusercontent.com/taqihas1/buildany-deploy/master/nuclear_homepage.py | python3
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

PAGE = os.path.join(PROJECT, "src", "app", "page.tsx")
BACKUP = os.path.join(PROJECT, "src", "app", "page.tsx.nuclear-backup")

if not os.path.exists(PAGE):
    print(f"[ERROR] page.tsx not found at {PAGE}")
    sys.exit(1)

# Backup if not already
if not os.path.exists(BACKUP):
    shutil.copy2(PAGE, BACKUP)
    print(f"[BACKUP] Saved to {BACKUP}")

# Nuclear minimal page — zero imports, zero DB, zero auth
MINIMAL = '''export default function Home() {
  return (
    <html>
      <body>
        <div style={{ padding: 40, fontFamily: 'system-ui' }}>
          <h1>BuildAny — NUCLEAR MODE</h1>
          <p style={{ color: 'green' }}>✓ If you see this, the crash is NOT in Next.js core.</p>
          <p>The error is in one of these:</p>
          <ul>
            <li>layout.tsx</li>
            <li>middleware.ts</li>
            <li>A third-party package (Clerk, etc.)</li>
            <li>Stale .next build cache</li>
          </ul>
          <p>Try: <code>rm -rf .next && npm run build && pm2 restart buildany</code></p>
        </div>
      </body>
    </html>
  );
}
'''

with open(PAGE, "w") as f:
    f.write(MINIMAL)
print("[NUCLEAR] page.tsx replaced with absolute minimum")

# Also clear .next
next_dir = os.path.join(PROJECT, ".next")
if os.path.exists(next_dir):
    shutil.rmtree(next_dir)
    print("[CLEAN] Deleted .next cache")

# Rebuild
print("[BUILD] npm run build...")
os.chdir(PROJECT)
result = os.system("npm run build")
if result != 0:
    print("[BUILD FAILED]")
    sys.exit(1)

print("[RESTART] pm2 restart buildany...")
os.system("pm2 restart buildany")

print("\n" + "="*60)
print("NUCLEAR MODE ACTIVE")
print("="*60)
print("Refresh base66.cloud now.")
print("")
print("If you STILL see the error → the crash is in:")
print("  - layout.tsx (still loads even with minimal page)")
print("  - middleware.ts (runs before every request)")
print("  - A node_modules package")
print("")
print("If the page loads fine → the crash was in page.tsx imports.")
print("Restore with: cp " + BACKUP + " " + PAGE)
print("="*60)
