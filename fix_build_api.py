#!/usr/bin/env python3
"""
Fix build API to read files from DB and write to disk before building.

Usage:
  curl -fsSL https://raw.githubusercontent.com/taqihas1/buildany-deploy/master/fix_build_api.py | python3
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

BUILD_FILE = os.path.join(PROJECT, "src", "app", "api", "build", "route.ts")
if not os.path.exists(BUILD_FILE):
    print(f"[ERROR] build/route.ts not found at {BUILD_FILE}")
    sys.exit(1)

# Backup
backup = BUILD_FILE + ".db-fix-backup"
if not os.path.exists(backup):
    shutil.copy2(BUILD_FILE, backup)
    print(f"[BACKUP] {backup}")

# Write the fixed build API
fixed_code = '''import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { projects, projectFiles } from "@/lib/db/schema";
import { eq } from "drizzle-orm";
import { spawn } from "child_process";
import fs from "fs/promises";
import path from "path";

const PROJECTS_DIR = "/data/projects";

// Build a project: fetch from DB → write to disk → npm install → next build
export async function POST(req: NextRequest) {
  try {
    const { projectId } = await req.json();
    if (!projectId) {
      return NextResponse.json({ error: "projectId required" }, { status: 400 });
    }

    const projectDir = path.join(PROJECTS_DIR, projectId);
    const outDir = path.join(projectDir, "out");

    // ─── Step 1: Fetch files from DB and write to disk ───
    console.log("[Build] Fetching files from DB for:", projectId);
    const files = await db.select().from(projectFiles)
      .where(eq(projectFiles.projectId, projectId));

    if (files.length === 0) {
      return NextResponse.json({ error: "No files found for this project" }, { status: 404 });
    }

    // Ensure project directory exists
    await fs.mkdir(projectDir, { recursive: true });

    // Write all files to disk
    for (const file of files) {
      const filePath = path.join(projectDir, file.path);
      await fs.mkdir(path.dirname(filePath), { recursive: true });
      await fs.writeFile(filePath, file.content || "", "utf-8");
    }
    console.log(`[Build] Wrote ${files.length} files to ${projectDir}`);

    // ─── Step 2: Ensure package.json exists ───
    const pkgPath = path.join(projectDir, "package.json");
    try {
      await fs.access(pkgPath);
    } catch {
      // Create minimal package.json
      const pkg = {
      name: "buildany-project-" + projectId.slice(0, 8),
        version: "0.1.0",
        private: true,
        scripts: {
          "dev": "next dev",
          "build": "next build",
          "start": "next start"
        },
        dependencies: {
          "next": "^15.0.0",
          "react": "^19.0.0",
          "react-dom": "^19.0.0"
        },
        devDependencies: {
          "typescript": "^5.0.0",
          "@types/node": "^20.0.0",
          "@types/react": "^19.0.0",
          "@types/react-dom": "^19.0.0"
        }
      };
      await fs.writeFile(pkgPath, JSON.stringify(pkg, null, 2), "utf-8");
      console.log("[Build] Created package.json");
    }

    // ─── Step 3: Ensure next.config.js exists ───
    const nextConfigPath = path.join(projectDir, "next.config.js");
    try {
      await fs.access(nextConfigPath);
    } catch {
      const nextConfig = `/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  distDir: 'out',
};
module.exports = nextConfig;`;
      await fs.writeFile(nextConfigPath, nextConfig, "utf-8");
      console.log("[Build] Created next.config.js");
    }

    // ─── Step 4: Ensure tsconfig.json exists ───
    const tsConfigPath = path.join(projectDir, "tsconfig.json");
    try {
      await fs.access(tsConfigPath);
    } catch {
      const tsConfig = {
        compilerOptions: {
          target: "ES2017",
          lib: ["dom", "dom.iterable", "esnext"],
          allowJs: true,
          skipLibCheck: true,
          strict: true,
          noEmit: true,
          esModuleInterop: true,
          module: "esnext",
          moduleResolution: "bundler",
          resolveJsonModule: true,
          isolatedModules: true,
          jsx: "preserve",
          incremental: true,
          plugins: [{ name: "next" }],
          paths: { "@/*": ["./*"] }
        },
        include: ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
        exclude: ["node_modules"]
      };
      await fs.writeFile(tsConfigPath, JSON.stringify(tsConfig, null, 2), "utf-8");
      console.log("[Build] Created tsconfig.json");
    }

    // ─── Step 5: Update status and build ───
    await db.update(projects)
      .set({ status: "building", updatedAt: new Date() })
      .where(eq(projects.id, projectId));

    // Run build in background
    buildProject(projectId, projectDir, outDir);

    return NextResponse.json({
      success: true,
      status: "building",
      message: "Build started with " + files.length + " files...",
    });

  } catch (error: any) {
    console.error("[Build] Error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

async function buildProject(projectId: string, projectDir: string, outDir: string) {
  try {
    console.log("[Build] Starting:", projectId);

    // Clean previous build
    try {
      await fs.rm(outDir, { recursive: true, force: true });
      await fs.rm(path.join(projectDir, ".next"), { recursive: true, force: true });
    } catch {}

    // npm install
    console.log("[Build] npm install...");
    await runCommand("npm", ["install"], projectDir, 120000);

    // next build with static export
    console.log("[Build] next build (static export)...");
    await runCommand("npx", ["next", "build", "--no-lint"], projectDir, 300000);

    // Verify output exists
    try {
      await fs.access(path.join(outDir, "index.html"));
      console.log("[Build] Output verified at:", outDir);
    } catch {
      throw new Error("Build completed but out/index.html not found. Check next.config.js has output: 'export'");
    }

    // Git checkpoint
    try {
      const { execSync } = await import("child_process");
      execSync("git add .", { cwd: projectDir, stdio: "ignore" });
      execSync('git commit -m "Build: static export"', { cwd: projectDir, stdio: "ignore" });
    } catch {}

    // Update status
    await db.update(projects)
      .set({ status: "ready", updatedAt: new Date() })
      .where(eq(projects.id, projectId));

    console.log("[Build] Complete:", projectId);

  } catch (error: any) {
    console.error("[Build] Failed:", error);
    await db.update(projects)
      .set({ status: "build_failed", updatedAt: new Date() })
      .where(eq(projects.id, projectId));
  }
}

// Helper: run command with spawn, collect output
function runCommand(cmd: string, args: string[], cwd: string, timeoutMs: number): Promise<void> {
  return new Promise((resolve, reject) => {
    const child = spawn(cmd, args, {
      cwd,
      shell: true,
      env: { ...process.env, NODE_ENV: "production" },
    });

    let stdout = "";
    let stderr = "";

    child.stdout?.on("data", (data) => {
      stdout += data.toString();
    });

    child.stderr?.on("data", (data) => {
      stderr += data.toString();
    });

    const timer = setTimeout(() => {
      child.kill("SIGTERM");
      reject(new Error(`Command timed out after ${timeoutMs}ms`));
    }, timeoutMs);

    child.on("close", (code) => {
      clearTimeout(timer);
      if (code !== 0) {
        console.error(`[Build] Command exited with code ${code}`);
        console.error("[Build] stdout:", stdout.slice(-500));
        console.error("[Build] stderr:", stderr.slice(-500));
      }
      // Resolve even on non-zero exit — Next.js may warn but still produce output
      resolve();
    });

    child.on("error", (err) => {
      clearTimeout(timer);
      reject(err);
    });
  });
}
'''

with open(BUILD_FILE, "w") as f:
    f.write(fixed_code)

print("[FIXED] build/route.ts updated to read files from DB before building")

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
print("DONE! Build API now reads files from DB and writes to disk.")
print("="*60)
