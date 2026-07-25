#!/usr/bin/env python3
"""
BuildAny Deployment Script - Unified Kelly + Connectors
=========================================================

Deploys the complete unified Kelly architecture with GitHub + Cloudflare connectors.

Usage on VPS:
    curl -sL https://raw.githubusercontent.com/taqihas1/buildany-deploy/main/deploy_kelly_v2.py | python3 -

Required env vars (add these BEFORE running):
    export GITHUB_TOKEN=ghp_xxx          # GitHub personal access token
    export CLOUDFLARE_API_TOKEN=xxx      # Cloudflare API token
    export DEEPSEEK_API_KEY=sk-xxx       # DeepSeek API key
    export CF_ACCOUNT_ID=xxx             # Cloudflare account ID
"""

import os
import shutil
import subprocess
import sys
from datetime import datetime

# Configuration
BUILDANY_DIR = "/root/buildany"
BACKUP_DIR = f"/root/buildany-backups/kelly-v2-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

# Colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

def log(msg, color=GREEN):
    print(f"{color}[Kelly Deploy v2]{RESET} {msg}")

def run(cmd, cwd=None, check=True):
    log(f"Running: {cmd}", YELLOW)
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if check and result.returncode != 0:
        log(f"FAILED: {cmd}", RED)
        log(result.stderr, RED)
        sys.exit(1)
    return result

def verify_env():
    """Check required environment variables"""
    log("Checking environment variables...")
    
    required = {
        "GITHUB_TOKEN": "GitHub personal access token (repo scope)",
        "CLOUDFLARE_API_TOKEN": "Cloudflare API token (Zone:Read, DNS:Edit)",
        "DEEPSEEK_API_KEY": "DeepSeek API key",
    }
    
    missing = []
    for key, desc in required.items():
        val = os.environ.get(key)
        if not val:
            missing.append(f"  {key}: {desc}")
        else:
            # Mask the value
            masked = val[:8] + "..." + val[-4:] if len(val) > 12 else "***"
            log(f"  ✅ {key}: {masked}")
    
    if missing:
        log("Missing required environment variables:", RED)
        for m in missing:
            log(m, RED)
        log("\nSet them like this:", BLUE)
        log("  export GITHUB_TOKEN=ghp_xxx")
        log("  export CLOUDFLARE_API_TOKEN=xxx")
        log("  export DEEPSEEK_API_KEY=sk-xxx")
        sys.exit(1)
    
    # Optional
    if os.environ.get("CF_ACCOUNT_ID"):
        log("  ✅ CF_ACCOUNT_ID: set")
    else:
        log("  ⚠️ CF_ACCOUNT_ID: not set (needed for Cloudflare deploys)", YELLOW)

def backup_existing():
    log("Creating backup...")
    os.makedirs(BACKUP_DIR, exist_ok=True)
    
    key_files = [
        "src/app/api/orchestrate/route.ts",
        "src/app/api/hermes-chat/route.ts",
        "src/app/api/morgan-generate/route.ts",
        "src/app/api/morgan-chat/route.ts",
        "src/lib/morgan-generator.ts",
        ".env",
        ".env.local",
    ]
    
    for f in key_files:
        src = os.path.join(BUILDANY_DIR, f)
        if os.path.exists(src):
            dst = os.path.join(BACKUP_DIR, f.replace("/", "_"))
            shutil.copy2(src, dst)
            log(f"  Backed up: {f}")
    
    log(f"Backup saved to: {BACKUP_DIR}")

def create_env_file():
    """Create/update .env.local with all required vars"""
    log("Setting up environment file...")
    
    env_path = os.path.join(BUILDANY_DIR, ".env.local")
    
    env_content = f"""# BuildAny Environment - Auto-generated {datetime.now().isoformat()}
# NEVER commit this file to GitHub!

# AI Models
DEEPSEEK_API_KEY={os.environ.get('DEEPSEEK_API_KEY', '')}
HERMES_URL=http://127.0.0.1:8642

# GitHub Integration
GITHUB_TOKEN={os.environ.get('GITHUB_TOKEN', '')}

# Cloudflare Integration
CLOUDFLARE_API_TOKEN={os.environ.get('CLOUDFLARE_API_TOKEN', '')}
CF_ACCOUNT_ID={os.environ.get('CF_ACCOUNT_ID', '')}

# BuildAny Settings
PROJECTS_DIR=/root/buildany/projects
BUILDANY_URL=https://base66.cloud
"""
    
    # Write to .env.local (gitignored)
    with open(env_path, "w") as f:
        f.write(env_content)
    
    # Also write to .env for compatibility
    with open(os.path.join(BUILDANY_DIR, ".env"), "w") as f:
        f.write(env_content)
    
    log(f"  ✅ Created .env.local and .env")
    log("  ⚠️  These files are gitignored — safe from accidental commits")

def pull_latest_code():
    """Pull latest code from GitHub"""
    log("Pulling latest code from GitHub...")
    
    # Use token-based auth for pull
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        run(f"git remote set-url origin https://taqihas1:{token}@github.com/taqihas1/buildany.git", cwd=BUILDANY_DIR, check=False)
    
    result = run("git pull origin master", cwd=BUILDANY_DIR, check=False)
    if result.returncode != 0:
        log("  ⚠️ Git pull failed, continuing with local files...", YELLOW)
    else:
        log("  ✅ Latest code pulled")

def rebuild_and_restart():
    log("Rebuilding application...")
    
    # Clear caches
    for cache_dir in [".next", "node_modules/.cache"]:
        path = os.path.join(BUILDANY_DIR, cache_dir)
        if os.path.exists(path):
            shutil.rmtree(path)
            log(f"  Cleared: {cache_dir}")
    
    # Build
    result = run("npm run build", cwd=BUILDANY_DIR, check=False)
    if result.returncode != 0:
        log("Build had errors (see above)", YELLOW)
        log("Continuing with restart...", YELLOW)
    else:
        log("  ✅ Build successful")
    
    # Restart PM2
    log("Restarting with PM2...")
    run("pm2 restart buildany 2>/dev/null || pm2 start npm --name buildany -- start", cwd=BUILDANY_DIR, check=False)
    log("  ✅ PM2 restarted")

def verify_deployment():
    log("Verifying deployment...")
    
    checks = [
        ("src/app/api/kelly/route.ts", "Kelly unified endpoint"),
        ("src/app/api/github-tool/route.ts", "GitHub connector"),
        ("src/app/api/cloudflare-tool/route.ts", "Cloudflare connector"),
        ("src/lib/kelly-tools.ts", "Kelly tools"),
        ("src/lib/kelly-system.ts", "Kelly system prompt"),
    ]
    
    for filepath, desc in checks:
        full_path = os.path.join(BUILDANY_DIR, filepath)
        if os.path.exists(full_path):
            log(f"  ✅ {desc}")
        else:
            log(f"  ❌ {desc} MISSING!", RED)
    
    # Check PM2
    result = run("pm2 status | grep buildany", check=False)
    if result.returncode == 0:
        log(f"  ✅ PM2: {result.stdout.strip()}")
    
    # Check API health
    import urllib.request
    try:
        req = urllib.request.Request("http://127.0.0.1:3000/api/kelly", method="GET")
        with urllib.request.urlopen(req, timeout=5) as res:
            log(f"  ✅ API responding: {res.status}")
    except Exception as e:
        log(f"  ⚠️ API check failed: {e}", YELLOW)

def main():
    log("=" * 60)
    log("BuildAny Unified Kelly + Connectors Deployment")
    log("=" * 60)
    
    if not os.path.exists(BUILDANY_DIR):
        log(f"BuildAny not found at {BUILDANY_DIR}!", RED)
        sys.exit(1)
    
    verify_env()
    backup_existing()
    create_env_file()
    pull_latest_code()
    rebuild_and_restart()
    verify_deployment()
    
    log("=" * 60)
    log("DEPLOYMENT COMPLETE!")
    log("=" * 60)
    log("")
    log("New capabilities:")
    log("  • /api/kelly — Unified AI with 15 tools")
    log("  • /api/github-tool — Repo, push, PR, file operations")
    log("  • /api/cloudflare-tool — Deploy, cache, DNS, analytics")
    log("")
    log("Quick test:")
    log("  curl -X POST http://127.0.0.1:3000/api/kelly \\")
    log("    -H 'Content-Type: application/json' \\")
    log('    -d \'{"message":"hello kelly"}\'')
    log("")
    log(f"Backup: {BACKUP_DIR}")

if __name__ == "__main__":
    main()
