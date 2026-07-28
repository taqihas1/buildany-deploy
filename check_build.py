#!/usr/bin/env python3
"""
Check PM2 logs for the most recent build to see parser status.

Usage:
  curl -fsSL https://raw.githubusercontent.com/taqihas1/buildany-deploy/master/check_build.py | python3
"""

import subprocess
import re

def run(cmd, timeout=10):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout + r.stderr
    except Exception as e:
        return f"[ERROR] {e}"

print("="*70)
print("BUILD LOG CHECKER")
print("="*70)

# Get logs
logs = run("cat ~/.pm2/logs/buildany-out.log | tail -100", timeout=10)

# Filter for build-related lines
build_lines = []
for line in logs.split('\n'):
    if any(k in line for k in ['[Build]', '[Kelly]', 'parsedFiles', 'contentLength', 'Failed', 'error', 'saved', 'files']):
        build_lines.append(line)

if build_lines:
    print("\n[RECENT BUILD ACTIVITY]:")
    for line in build_lines[-30:]:  # Last 30 relevant lines
        print(f"  {line}")
else:
    print("\n[NO BUILD ACTIVITY FOUND]")

# Check for specific error patterns
print("\n" + "="*70)
print("ERROR ANALYSIS:")
print("="*70)

if "parsedFiles: 0" in logs:
    print("❌ Parser extracted 0 files — LLM output format not recognized")
elif "parsedFiles: 1" in logs and "firstFile: 'json'" in logs:
    print("⚠️  Parser extracted only 1 file named 'json' — not actual source files")
elif "parsedFiles" in logs:
    # Extract parsedFiles count
    match = re.search(r'parsedFiles: (\d+)', logs)
    if match:
        print(f"✅ Parser extracted {match.group(1)} files")
else:
    print("ℹ️  No parser output found in recent logs")

if "API error (401)" in logs:
    print("❌ API key still invalid!")
elif "success: true" in logs and "hasContent: true" in logs:
    print("✅ LLM generation succeeded")

if "No preview file found" in logs:
    print("❌ Preview generation failed — no HTML output")

if "Build completed but out/index.html not found" in logs:
    print("❌ Build output missing — next build failed")

print("\n" + "="*70)
print("NEXT STEPS:")
print("="*70)
print("If parser shows 0 or 1 files:")
print("  1. The LLM output format doesn't match parser expectations")
print("  2. Check what format the LLM is using in the chat output")
print("  3. May need to adjust system prompt or parser")
print("")
print("If files are parsed but not showing in UI:")
print("  1. Check if files are saved to project_files table")
print("  2. Run: curl -fsSL .../diag_project.py | python3")
print("="*70)
