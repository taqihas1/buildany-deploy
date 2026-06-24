#!/usr/bin/env python3
import subprocess, re

def run(cmd, cwd="/root/buildany"):
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    return result.stdout.strip(), result.stderr.strip(), result.returncode

# Check which files have conflicts
stdout, _, _ = run("git diff --name-only --diff-filter=U")
conflicted = stdout.split('\n') if stdout else []

print(f"Conflicted files: {conflicted}")

for f in conflicted:
    if not f:
        continue
    fpath = f"/root/buildany/{f}"
    print(f"\n=== {f} ===")
    
    with open(fpath) as fh:
        content = fh.read()
    
    # Take the NEW version (from origin/main) - between ======= and >>>>>>>
    resolved = re.sub(
        r'<<<<<<<.*?\n(.*?)=======(.*?)>>>>>>>.*?\n',
        r'\2',
        content,
        flags=re.DOTALL
    )
    
    # Clean any remaining markers
    resolved = re.sub(r'<<<<<<<.*?\n', '', resolved)
    resolved = re.sub(r'=======(.*?)>>>>>>>.*?\n', r'\1', resolved, flags=re.DOTALL)
    resolved = re.sub(r'>>>>>>>.*?\n', '', resolved)
    
    with open(fpath, 'w') as fh:
        fh.write(resolved)
    
    run(f"git add {f}")
    print(f"  ✅ Resolved: {f}")

# Commit the merge
run('git commit -m "Merge: resolved conflicts with new chat-first flow"')

print("\n✅ All conflicts resolved! Now building...")
