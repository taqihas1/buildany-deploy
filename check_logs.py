#!/usr/bin/env python3
"""
Quick check: run PM2 logs and grep for Kelly/build activity.

Usage:
  curl -fsSL https://raw.githubusercontent.com/taqihas1/buildany-deploy/master/check_logs.py | python3
"""

import subprocess
import sys

def run(cmd, timeout=10):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout + r.stderr
    except Exception as e:
        return f"[ERROR] {e}"

print("="*60)
print("PM2 STATUS")
print("="*60)
print(run("pm2 status buildany", timeout=5))

print("\n" + "="*60)
print("LAST 30 LOG LINES (errors only)")
print("="*60)
logs = run("pm2 logs buildany --lines 30 --nostream 2>&1", timeout=10)
# Filter for relevant lines
for line in logs.split('\n'):
    if any(k in line for k in ['[Kelly]', '[Build]', 'error', 'Error', 'ERROR', 'API', 'Failed', 'success']):
        print(line)

print("\n" + "="*60)
print("CHECKING IF API KEY FIX IS APPLIED")
print("="*60)
# Check if the env fix is in the built code
buildany_dir = "/root/buildany"
router_file = f"{buildany_dir}/src/lib/llm-router.ts"
import os
if os.path.exists(router_file):
    with open(router_file) as f:
        content = f.read()
    if "Load from process.env FIRST" in content:
        print("✅ API key fix IS applied (env takes priority)")
    else:
        print("❌ API key fix NOT applied — run fix_llm_env_v2.py")
else:
    print(f"❌ File not found: {router_file}")

print("\n" + "="*60)
print("RECOMMENDATION:")
print("="*60)
print("If you see 'API error (401)' in logs above:")
print("  1. Run: curl -fsSL https://raw.githubusercontent.com/taqihas1/buildany-deploy/master/fix_llm_env_v2.py | python3")
print("")
print("If files exist but build fails:")
print("  1. Run: curl -fsSL https://raw.githubusercontent.com/taqihas1/buildany-deploy/master/fix_build_api.py | python3")
print("")
print("To see project data:")
print("  1. Run: curl -fsSL https://raw.githubusercontent.com/taqihas1/buildany-deploy/master/diag_project.py | python3")
print("="*60)
