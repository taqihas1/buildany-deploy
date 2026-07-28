#!/usr/bin/env python3
"""
Fix for Server Component crash on base66.cloud (ERROR 688382577)
Applies lazy DB connection to prevent import-time SQLite crashes.

USAGE ON VPS:
  curl -fsSL https://raw.githubusercontent.com/taqihas1/buildany-deploy/main/fix_db_lazy.py | python3

Or download first:
  curl -fsSL https://raw.githubusercontent.com/taqihas1/buildany-deploy/main/fix_db_lazy.py -o fix_db_lazy.py
  python3 fix_db_lazy.py
"""

import os
import sys
import shutil

def find_buildany_dir():
    """Find the buildany project directory on the VPS."""
    # Common locations
    candidates = [
        "/root/buildany",
        "/root/buildany-fix",
        "/var/www/buildany",
        "/home/buildany",
        "/opt/buildany",
    ]
    
    # Also check PM2 for the actual path
    try:
        import subprocess
        result = subprocess.run(
            ["pm2", "describe", "buildany"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            for line in result.stdout.split("\n"):
                if "exec cwd" in line.lower() or "script" in line.lower():
                    # Extract path from PM2 output
                    parts = line.split("│")
                    if len(parts) >= 3:
                        path = parts[2].strip()
                        if path and os.path.exists(path):
                            candidates.insert(0, path)
    except Exception:
        pass
    
    # Check which candidate has the DB file
    for candidate in candidates:
        db_file = os.path.join(candidate, "src", "lib", "db", "index.ts")
        if os.path.exists(db_file):
            return candidate
    
    return None

def main():
    print("=" * 60)
    print("BuildAny DB Lazy Connection Fix")
    print("Fixes: Server Component crash (ERROR 688382577)")
    print("=" * 60)
    
    # Find project directory
    project_dir = find_buildany_dir()
    
    if not project_dir:
        print("\n[ERROR] Could not find buildany project directory automatically.")
        print("\nPlease set the path manually:")
        print("  BUILDANY_DIR=/path/to/buildany python3 fix_db_lazy.py")
        print("\nOr pass as argument:")
        print("  python3 fix_db_lazy.py /path/to/buildany")
        return 1
    
    # Allow override via env var or arg
    if len(sys.argv) > 1:
        project_dir = sys.argv[1]
    elif os.environ.get("BUILDANY_DIR"):
        project_dir = os.environ.get("BUILDANY_DIR")
    
    db_file = os.path.join(project_dir, "src", "lib", "db", "index.ts")
    
    if not os.path.exists(db_file):
        print(f"\n[ERROR] DB file not found: {db_file}")
        print(f"[HINT] Is {project_dir} the correct project directory?")
        return 1
    
    print(f"\n[FOUND] Project directory: {project_dir}")
    print(f"[FOUND] DB file: {db_file}")
    
    # Backup
    backup = db_file + ".backup." + str(int(os.path.getmtime(db_file)))
    shutil.copy2(db_file, backup)
    print(f"[BACKUP] Saved to: {backup}")
    
    # New lazy content
    new_content = '''import { drizzle } from "drizzle-orm/better-sqlite3";
import Database from "better-sqlite3";
import * as schema from "./schema";

// Lazy DB connection — only connects when first used
// Prevents Server Component crashes if DB file is missing at import time
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

// Backward-compatible export — still works for existing imports
// But prefer `getDb()` for new code to ensure lazy loading
export const db = new Proxy({} as ReturnType<typeof drizzle<typeof schema>>, {
  get(_, prop: string | symbol) {
    const database = getDb();
    return (database as any)[prop];
  },
});
'''
    
    # Apply fix
    with open(db_file, "w") as f:
        f.write(new_content)
    print(f"[FIXED] Applied lazy DB connection to: {db_file}")
    
    # Verify
    with open(db_file, "r") as f:
        content = f.read()
    if "Lazy DB connection" in content and "new Proxy" in content:
        print("[VERIFY] ✓ Fix verified in file")
    else:
        print("[VERIFY] ✗ Fix may not have applied correctly")
        return 1
    
    print("\n" + "=" * 60)
    print("NEXT STEPS:")
    print("=" * 60)
    print(f"1. cd {project_dir}")
    print("2. npm run build")
    print("3. pm2 restart buildany")
    print("\nThe fix will auto-create the DB directory if missing.")
    print("Your site should now load without ERROR 688382577!")
    print("=" * 60)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
