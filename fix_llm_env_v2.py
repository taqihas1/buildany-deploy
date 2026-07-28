#!/usr/bin/env python3
"""
Fix llm-router.ts to use process.env as PRIMARY source, DB as fallback only.
ENV always wins over database.

Usage:
  curl -fsSL https://raw.githubusercontent.com/taqihas1/buildany-deploy/master/fix_llm_env_v2.py | python3
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
backup = ROUTER_FILE + ".env-v2-backup"
if not os.path.exists(backup):
    shutil.copy2(ROUTER_FILE, backup)
    print(f"[BACKUP] {backup}")

# Read current file
with open(ROUTER_FILE, "r") as f:
    content = f.read()

# Check if already fixed
if "Load from process.env FIRST" in content:
    print("[OK] File already has correct priority. No changes needed.")
else:
    # Replace the loadConfigs method
    old_pattern = "  async loadConfigs() {"
    if old_pattern not in content:
        print("[ERROR] Could not find loadConfigs method.")
        sys.exit(1)

    # Find the end of loadConfigs (next method or closing brace)
    start = content.find("  async loadConfigs() {")
    if start == -1:
        print("[ERROR] Could not find loadConfigs.")
        sys.exit(1)

    # Find the closing brace of loadConfigs (the one that ends the method)
    # Look for the next method at same indentation level
    rest = content[start:]
    brace_count = 0
    end_offset = 0
    found_first = False
    for i, ch in enumerate(rest):
        if ch == '{':
            brace_count += 1
            found_first = True
        elif ch == '}':
            brace_count -= 1
            if found_first and brace_count == 0:
                end_offset = i + 1
                break

    if end_offset == 0:
        print("[ERROR] Could not find end of loadConfigs.")
        sys.exit(1)

    new_method = '''  async loadConfigs() {
    // ─── 1. Load from process.env FIRST (source of truth) ───
    if (process.env.DEEPSEEK_API_KEY) {
      this.configs.set("deepseek", {
        baseUrl: "https://api.deepseek.com/v1",
        model: "deepseek-chat",
        apiKey: process.env.DEEPSEEK_API_KEY,
      });
    }
    if (process.env.KIMI_API_KEY) {
      this.configs.set("kimi", {
        baseUrl: "https://api.moonshot.cn/v1",
        model: "moonshot-v1-8k",
        apiKey: process.env.KIMI_API_KEY,
      });
    }
    if (process.env.OPENAI_API_KEY) {
      this.configs.set("openai", {
        baseUrl: "https://api.openai.com/v1",
        model: "gpt-4o",
        apiKey: process.env.OPENAI_API_KEY,
      });
    }
    if (process.env.GEMMA_API_KEY) {
      this.configs.set("gemma", {
        baseUrl: "http://localhost:1234/v1",
        model: "gemma-4-e2b",
        apiKey: process.env.GEMMA_API_KEY,
      });
    }

    // ─── 2. Only if .env is empty, fall back to DB ───
    if (this.configs.size === 0) {
      console.log('[LLM Router] No API keys in .env, falling back to database...');
      const keys = await db
        .select()
        .from(apiKeys)
        .where(eq(apiKeys.isActive, true));

      for (const key of keys) {
        const provider = key.provider as LLMProvider;
        if (provider === "deepseek") {
          this.configs.set(provider, {
            baseUrl: "https://api.deepseek.com/v1",
            model: "deepseek-chat",
            apiKey: key.keyValue,
          });
        } else if (provider === "kimi") {
          this.configs.set(provider, {
            baseUrl: "https://api.moonshot.cn/v1",
            model: "moonshot-v1-8k",
            apiKey: key.keyValue,
          });
        } else if (provider === "openai") {
          this.configs.set(provider, {
            baseUrl: "https://api.openai.com/v1",
            model: "gpt-4o",
            apiKey: key.keyValue,
          });
        } else if (provider === "gemma") {
          this.configs.set(provider, {
            baseUrl: "http://localhost:1234/v1",
            model: "gemma-4-e2b",
            apiKey: key.keyValue || "not-needed",
          });
        }
      }
    }
  }'''

    content = content[:start] + new_method + content[start + end_offset:]

    with open(ROUTER_FILE, "w") as f:
        f.write(content)

    print("[FIXED] llm-router.ts updated — .env is now PRIMARY, DB is fallback")

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
print("DONE! ENV takes priority over database.")
print("Kelly will now use DEEPSEEK_API_KEY from .env first.")
print("="*60)
