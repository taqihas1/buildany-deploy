#!/usr/bin/env python3
"""
Emergency diagnostic script for base66.cloud Server Component crash.
Temporarily replaces homepage with a minimal version to isolate the error.

Usage:
  curl -fsSL https://raw.githubusercontent.com/taqihas1/buildany-deploy/master/diag_homepage.py | python3
"""

import os
import sys
import shutil

# Find project dir
def find_project():
    candidates = ["/root/buildany", "/root/buildany-fix", "/var/www/buildany"]
    for c in candidates:
        if os.path.exists(os.path.join(c, "package.json")):
            return c
    # Check PM2
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
    print("[ERROR] Could not find buildany project. Set BUILDANY_DIR env var.")
    sys.exit(1)

PAGE = os.path.join(PROJECT, "src", "app", "page.tsx")
BACKUP = PAGE + ".original"

if not os.path.exists(PAGE):
    print(f"[ERROR] page.tsx not found at {PAGE}")
    sys.exit(1)

# Backup original if not already backed up
if not os.path.exists(BACKUP):
    shutil.copy2(PAGE, BACKUP)
    print(f"[BACKUP] Saved original to {BACKUP}")

# Minimal diagnostic page
MINIMAL_PAGE = '''export default function Home() {
  return (
    <main className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-4xl font-bold mb-4">BuildAny</h1>
        <p className="text-green-600">✓ Server Component renders OK</p>
        <p className="text-gray-500 text-sm mt-4">If you see this, the crash is in a component/import.</p>
      </div>
    </main>
  );
}
'''

with open(PAGE, "w") as f:
    f.write(MINIMAL_PAGE)
print("[DIAG] Replaced homepage with minimal version")

# Rebuild
print("[BUILD] Running npm run build...")
os.chdir(PROJECT)
result = os.system("npm run build")
if result != 0:
    print("[BUILD FAILED] npm run build returned error")
    sys.exit(1)

print("[RESTART] Restarting PM2...")
os.system("pm2 restart buildany")

print("\n" + "="*60)
print("DIAGNOSTIC MODE ACTIVE")
print("="*60)
print("Refresh base66.cloud now.")
print("")
print("If you see '✓ Server Component renders OK' → the crash is")
print("caused by one of these imports in the original page:")
print("  - @clerk/nextjs/server (auth)")
print("  - @/lib/db")
print("  - @/components/PromptBox")
print("  - @/components/DashboardHeader")
print("  - @/components/ProjectGrid")
print("  - @/components/KellyWelcomePanel")
print("")
print("To restore original page:")
print(f"  cp {BACKUP} {PAGE}")
print("  npm run build && pm2 restart buildany")
print("="*60)
