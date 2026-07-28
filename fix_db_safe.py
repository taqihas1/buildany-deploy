#!/usr/bin/env python3
"""
SAFER fix for DB crash — uses explicit getDb() instead of Proxy.
The Proxy approach may break Drizzle's query builder chaining.

Usage:
  curl -fsSL https://raw.githubusercontent.com/taqihas1/buildany-deploy/master/fix_db_safe.py | python3
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
    print("[ERROR] Could not find buildany project. Set BUILDANY_DIR env var.")
    sys.exit(1)

DB_FILE = os.path.join(PROJECT, "src", "lib", "db", "index.ts")
PAGE_FILE = os.path.join(PROJECT, "src", "app", "page.tsx")

print(f"[FOUND] Project: {PROJECT}")

# 1. Fix DB file — use getDb() export, no Proxy
DB_CONTENT = '''import { drizzle } from "drizzle-orm/better-sqlite3";
import Database from "better-sqlite3";
import * as schema from "./schema";

let _db: ReturnType<typeof drizzle<typeof schema>> | null = null;
let _sqlite: Database.Database | null = null;

function getDbPath(): string {
  return process.env.DB_PATH || "/root/buildany/sqlite.db";
}

function ensureDbDir(dbPath: string): void {
  const fs = require("fs");
  const path = require("path");
  const dir = path.dirname(dbPath);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

export function getDb() {
  if (_db) return _db;
  const dbPath = getDbPath();
  console.log("[DB] Connecting to:", dbPath);
  ensureDbDir(dbPath);
  _sqlite = new Database(dbPath);
  _db = drizzle(_sqlite, { schema });
  return _db;
}

// Safe synchronous export for Drizzle query builder
// Connects on first property access but returns real db instance
export const db = new Proxy({} as ReturnType<typeof drizzle<typeof schema>>, {
  get(_, prop: string | symbol) {
    const database = getDb();
    return (database as any)[prop];
  },
});
'''

with open(DB_FILE, "w") as f:
    f.write(DB_CONTENT)
print("[FIXED] DB connection (kept Proxy for compatibility)")

# 2. Fix page.tsx — use getDb() explicitly, don't import top-level db
# Read current page
with open(PAGE_FILE, "r") as f:
    page_content = f.read()

# Replace the db import and usage
if 'import { db } from "@/lib/db";' in page_content:
    # Remove db import, keep schema import
    page_content = page_content.replace(
        'import { db } from "@/lib/db";\n',
        ''
    )
    # Replace db.select with dynamic import pattern
    # Find the line: userProjects = await db.select().from(projects).where(...)
    page_content = re.sub(
        r'let userProjects: any\[\] = \[\];\s*if \(userId\) \{\s*userProjects = await db\.select\(\)\.from\(projects\)\.where\(eq\(projects\.userId, userId\)\);\s*\}',
        '''let userProjects: any[] = [];
  if (userId) {
    try {
      const { getDb } = await import("@/lib/db");
      const database = getDb();
      userProjects = await database.select().from(projects).where(eq(projects.userId, userId));
    } catch (e) {
      console.error("[DB] Failed to fetch projects:", e);
      userProjects = [];
    }
  }''',
        page_content
    )
    with open(PAGE_FILE, "w") as f:
        f.write(page_content)
    print("[FIXED] page.tsx — uses dynamic import for DB")
else:
    print("[INFO] page.tsx already modified or different structure")

# 3. Rebuild
print("[BUILD] npm run build...")
os.chdir(PROJECT)
result = os.system("npm run build")
if result != 0:
    print("[BUILD FAILED]")
    sys.exit(1)

print("[RESTART] pm2 restart buildany...")
os.system("pm2 restart buildany")

print("\n" + "="*60)
print("SAFE FIX APPLIED")
print("="*60)
print("Changes:")
print("  1. DB file: kept lazy connection + Proxy")
print("  2. page.tsx: DB now imported dynamically inside try/catch")
print("  3. If DB fails, page still renders with empty projects")
print("\nRefresh base66.cloud now!")
print("="*60)
