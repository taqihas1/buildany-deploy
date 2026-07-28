#!/usr/bin/env python3
"""
Fix llm-router.ts to fallback to process.env when DB has no API keys.

Usage:
  curl -fsSL https://raw.githubusercontent.com/taqihas1/buildany-deploy/master/fix_llm_env.py | python3
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
backup = ROUTER_FILE + ".env-fix-backup"
if not os.path.exists(backup):
    shutil.copy2(ROUTER_FILE, backup)
    print(f"[BACKUP] {backup}")

# Read current file
with open(ROUTER_FILE, "r") as f:
    content = f.read()

# Find and replace loadConfigs method
old_method = """  async loadConfigs() {
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
  }"""

new_method = """  async loadConfigs() {
    // ─── 1. Try loading from DB first ───
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

    // ─── 2. Fallback: load from process.env if no DB keys ───
    if (!this.configs.has("deepseek") && process.env.DEEPSEEK_API_KEY) {
      this.configs.set("deepseek", {
        baseUrl: "https://api.deepseek.com/v1",
        model: "deepseek-chat",
        apiKey: process.env.DEEPSEEK_API_KEY,
      });
    }
    if (!this.configs.has("kimi") && process.env.KIMI_API_KEY) {
      this.configs.set("kimi", {
        baseUrl: "https://api.moonshot.cn/v1",
        model: "moonshot-v1-8k",
        apiKey: process.env.KIMI_API_KEY,
      });
    }
    if (!this.configs.has("openai") && process.env.OPENAI_API_KEY) {
      this.configs.set("openai", {
        baseUrl: "https://api.openai.com/v1",
        model: "gpt-4o",
        apiKey: process.env.OPENAI_API_KEY,
      });
    }
  }"""

if old_method not in content:
    print("[WARN] Could not find exact old method. Checking if already fixed...")
    if "Fallback: load from process.env" in content:
        print("[OK] File already has the fallback. No changes needed.")
        sys.exit(0)
    else:
        print("[ERROR] Could not find the method to replace. Manual fix needed.")
        sys.exit(1)

content = content.replace(old_method, new_method)

with open(ROUTER_FILE, "w") as f:
    f.write(content)

print("[FIXED] llm-router.ts updated with process.env fallback")

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
print("DONE! Kelly will now use DEEPSEEK_API_KEY from .env")
print("="*60)
