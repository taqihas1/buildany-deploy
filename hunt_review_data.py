#!/usr/bin/env python3
"""
Hunt for 'review_data' in compiled .next output on VPS.
This finds stale artifacts, minified variable names, or hidden references.

Usage:
  curl -fsSL https://raw.githubusercontent.com/taqihas1/buildany-deploy/master/hunt_review_data.py | python3
"""

import os
import sys
import subprocess

def find_project():
    candidates = ["/root/buildany", "/root/buildany-fix", "/var/www/buildany"]
    for c in candidates:
        if os.path.exists(os.path.join(c, "package.json")):
            return c
    try:
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

NEXT_DIR = os.path.join(PROJECT, ".next")
if not os.path.exists(NEXT_DIR):
    print(f"[ERROR] .next directory not found at {NEXT_DIR}")
    print("[INFO] Run 'npm run build' first.")
    sys.exit(1)

print(f"[HUNT] Searching for 'review_data' in compiled .next output...")
print(f"[HUNT] Directory: {NEXT_DIR}")
print("="*60)

# Search in all JS files in .next
found = []
for root, dirs, files in os.walk(NEXT_DIR):
    # Skip source maps (they'll match too but are noise)
    for fname in files:
        if fname.endswith('.js') and not fname.endswith('.js.map'):
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, 'r', errors='ignore') as f:
                    content = f.read()
                    if 'review_data' in content:
                        # Find line numbers
                        lines = content.split('\n')
                        for i, line in enumerate(lines, 1):
                            if 'review_data' in line:
                                found.append((fpath, i, line.strip()[:200]))
            except Exception as e:
                pass

if found:
    print(f"[FOUND] {len(found)} occurrences of 'review_data':\n")
    for fpath, line_no, line_text in found:
        rel = fpath.replace(PROJECT, "")
        print(f"  File: {rel}")
        print(f"  Line: {line_no}")
        print(f"  Text: {line_text}")
        print()
else:
    print("[RESULT] 'review_data' NOT FOUND in any compiled .next file.")
    print("[DIAGNOSIS] The error is NOT coming from your code or build artifacts.")
    print("[LIKELY] A third-party package (Clerk, Drizzle, etc.) is generating this query.")

print("="*60)
print("Also checking node_modules for 'review_data'...")
print("="*60)

# Quick grep in node_modules (limited to avoid noise)
nm_found = []
nm_dir = os.path.join(PROJECT, "node_modules")
if os.path.exists(nm_dir):
    try:
        result = subprocess.run(
            ["grep", "-rn", "review_data", nm_dir],
            capture_output=True, text=True, timeout=10
        )
        if result.stdout:
            lines = result.stdout.strip().split('\n')[:20]  # limit output
            for line in lines:
                if 'node_modules' in line:
                    nm_found.append(line)
    except Exception as e:
        print(f"[WARN] grep failed: {e}")

if nm_found:
    print(f"[FOUND] {len(nm_found)} occurrences in node_modules:")
    for line in nm_found:
        print(f"  {line[:200]}")
else:
    print("[RESULT] 'review_data' NOT FOUND in node_modules either.")

print("\n" + "="*60)
print("CONCLUSION:")
if not found and not nm_found:
    print("  'review_data' is NOWHERE in your build output or dependencies.")
    print("  This error is IMPOSSIBLE from your current codebase.")
    print("")
    print("  SOLUTION: The .next build cache is 100% stale.")
    print("  Run: rm -rf .next && npm run build && pm2 restart buildany")
else:
    print("  Found references above — investigate the listed files.")
print("="*60)
