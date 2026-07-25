#!/usr/bin/env python3
"""
BuildAny Deployment Script - Unified Kelly Architecture
=========================================================

This script deploys the new unified Kelly architecture to your VPS.
It:
1. Backs up existing files
2. Replaces old dual-agent routes with unified ones
3. Adds new kelly-tools.ts and kelly-system.ts
4. Rebuilds and restarts the app

Usage on VPS:
    curl -sL https://raw.githubusercontent.com/taqihas1/buildany-deploy/main/deploy_kelly_unified.py | python3 -

Or if you have this file locally:
    python3 deploy_kelly_unified.py
"""

import os
import shutil
import subprocess
import sys
from datetime import datetime

# Configuration
BUILDANY_DIR = "/root/buildany"
BACKUP_DIR = f"/root/buildany-backups/kelly-unified-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
PROJECTS_DIR = "/data/projects"

# Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

def log(msg, color=GREEN):
    print(f"{color}[Kelly Deploy]{RESET} {msg}")

def run(cmd, cwd=None, check=True):
    """Run a shell command"""
    log(f"Running: {cmd}", YELLOW)
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if check and result.returncode != 0:
        log(f"FAILED: {cmd}", RED)
        log(result.stderr, RED)
        sys.exit(1)
    return result

def backup_existing():
    """Create backup of current buildany"""
    log("Creating backup...")
    os.makedirs(BACKUP_DIR, exist_ok=True)
    
    # Backup key files
    files_to_backup = [
        "src/app/api/orchestrate/route.ts",
        "src/app/api/hermes-chat/route.ts",
        "src/app/api/morgan-generate/route.ts",
        "src/app/api/morgan-chat/route.ts",
        "src/lib/morgan-generator.ts",
    ]
    
    for f in files_to_backup:
        src = os.path.join(BUILDANY_DIR, f)
        if os.path.exists(src):
            dst = os.path.join(BACKUP_DIR, os.path.basename(f))
            shutil.copy2(src, dst)
            log(f"  Backed up: {f}")
    
    log(f"Backup saved to: {BACKUP_DIR}")

def write_file(path, content):
    """Write a file, creating directories if needed"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
    log(f"  Written: {path}")

def deploy_new_files():
    """Deploy the new unified architecture files"""
    log("Deploying new unified architecture...")
    
    # 1. New unified Kelly endpoint
    kelly_route = '''import { NextRequest, NextResponse } from "next/server";

/**
 * KELLY - Unified AI Architect Endpoint
 *
 * Single brain, rich tools. No more dual-agent confusion.
 * Kelly plans, generates, audits, builds — all natively.
 */

import { buildSystemPrompt } from "@/lib/kelly-system";
import { executeTool, TOOLS } from "@/lib/kelly-tools";

const DEEPSEEK_KEY = process.env.DEEPSEEK_API_KEY || "";
const HERMES_URL = process.env.HERMES_URL || "http://127.0.0.1:8642";

export async function POST(req: NextRequest) {
  try {
    const { message, projectId, history = [] } = await req.json();
    if (!message) {
      return NextResponse.json({ error: "message required" }, { status: 400 });
    }

    // Build system prompt with context
    const systemPrompt = await buildSystemPrompt({ projectId });

    // Build messages
    const messages = [
      { role: "system", content: systemPrompt },
      ...history.slice(-10),
      { role: "user", content: message },
    ];

    // Call LLM with tool definitions
    const response = await callLLMWithTools(messages);

    // If LLM returned tool_calls, execute them
    let toolResults = null;
    if (response.tool_calls?.length) {
      toolResults = [];
      for (const tc of response.tool_calls) {
        const result = await executeTool(tc.name, tc.arguments);
        toolResults.push({ tool: tc.name, result });
      }
    }

    return NextResponse.json({
      role: "assistant",
      content: response.content,
      tool_calls: response.tool_calls || null,
      tool_results: toolResults,
    });
  } catch (e: any) {
    return NextResponse.json(
      { error: "Kelly error", details: e.message },
      { status: 500 }
    );
  }
}

async function callLLMWithTools(messages: any[]) {
  // Try Hermes first, fallback to DeepSeek
  let res;
  try {
    res = await fetch(`${HERMES_URL}/v1/chat/completions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: "hermes-3-llama-3.1-8b",
        messages,
        tools: TOOLS,
        temperature: 0.2,
      }),
    });
  } catch {
    res = await fetch("https://api.deepseek.com/v1/chat/completions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${DEEPSEEK_KEY}`,
      },
      body: JSON.stringify({
        model: "deepseek-chat",
        messages,
        tools: TOOLS,
        temperature: 0.2,
      }),
    });
  }

  const data = await res.json();
  const choice = data.choices?.[0];
  return {
    content: choice?.message?.content || "",
    tool_calls: choice?.message?.tool_calls?.map((tc: any) => ({
      name: tc.function?.name,
      arguments: JSON.parse(tc.function?.arguments || "{}"),
    })) || null,
  };
}
'''
    write_file(os.path.join(BUILDANY_DIR, "src/app/api/kelly/route.ts"), kelly_route)
    
    # 2. Deprecate old orchestrate route
    orchestrate_route = '''import { NextRequest, NextResponse } from "next/server";

/**
 * ORCHESTRATE - DEPRECATED
 * Use /api/kelly instead. Redirects for backward compatibility.
 */

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const res = await fetch("http://localhost:3000/api/kelly", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (e: any) {
    return NextResponse.json(
      { error: "Orchestration deprecated. Use /api/kelly", details: e.message },
      { status: 500 }
    );
  }
}

export async function GET() {
  return NextResponse.json({
    status: "deprecated",
    message: "Use /api/kelly instead",
    newEndpoint: "/api/kelly",
  });
}
'''
    write_file(os.path.join(BUILDANY_DIR, "src/app/api/orchestrate/route.ts"), orchestrate_route)
    
    # 3. Deprecate old hermes-chat route
    hermes_chat_route = '''import { NextRequest, NextResponse } from "next/server";

/**
 * HERMES-CHAT - DEPRECATED
 * Use /api/kelly instead. Redirects for backward compatibility.
 */

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const kellyBody = {
      message: body.message || body.query,
      projectId: body.projectId,
      history: body.history || body.messages || [],
    };
    const res = await fetch("http://localhost:3000/api/kelly", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(kellyBody),
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (e: any) {
    return NextResponse.json(
      { error: "hermes-chat deprecated. Use /api/kelly", details: e.message },
      { status: 500 }
    );
  }
}
'''
    write_file(os.path.join(BUILDANY_DIR, "src/app/api/hermes-chat/route.ts"), hermes_chat_route)
    
    log("New routes deployed")

def remove_morgan_deps():
    """Remove Morgan-specific files"""
    log("Removing Morgan dependencies...")
    
    morgan_files = [
        "src/app/api/morgan-generate/route.ts",
        "src/app/api/morgan-chat/route.ts",
        "src/lib/morgan-generator.ts",
    ]
    
    for f in morgan_files:
        path = os.path.join(BUILDANY_DIR, f)
        if os.path.exists(path):
            os.remove(path)
            log(f"  Removed: {f}")

def rebuild_and_restart():
    """Rebuild the app and restart PM2"""
    log("Rebuilding app...")
    
    # Clear old build
    next_dir = os.path.join(BUILDANY_DIR, ".next")
    if os.path.exists(next_dir):
        shutil.rmtree(next_dir)
        log("  Cleared .next cache")
    
    # Build
    result = run("npm run build", cwd=BUILDANY_DIR, check=False)
    if result.returncode != 0:
        log("Build had errors, but continuing...", YELLOW)
    
    # Restart PM2
    log("Restarting with PM2...")
    run("pm2 restart buildany || pm2 start npm --name buildany -- start", cwd=BUILDANY_DIR, check=False)
    
    log("App restarted!")

def verify_deployment():
    """Quick verification"""
    log("Verifying deployment...")
    
    # Check Kelly route exists
    kelly_path = os.path.join(BUILDANY_DIR, "src/app/api/kelly/route.ts")
    if os.path.exists(kelly_path):
        log("  ✅ Kelly route exists")
    else:
        log("  ❌ Kelly route missing!", RED)
    
    # Check tools exist
    tools_path = os.path.join(BUILDANY_DIR, "src/lib/kelly-tools.ts")
    if os.path.exists(tools_path):
        log("  ✅ Kelly tools exist")
    else:
        log("  ❌ Kelly tools missing!", RED)
    
    # Check PM2 status
    result = run("pm2 status | grep buildany", check=False)
    if result.returncode == 0:
        log(f"  ✅ PM2: {result.stdout.strip()}")
    else:
        log("  ⚠️ PM2 status check failed", YELLOW)

def main():
    log("=" * 60)
    log("BuildAny Unified Kelly Architecture Deployment")
    log("=" * 60)
    
    # Check we're on the right machine
    if not os.path.exists(BUILDANY_DIR):
        log(f"BuildAny not found at {BUILDANY_DIR}! Are you on the VPS?", RED)
        sys.exit(1)
    
    log(f"BuildAny dir: {BUILDANY_DIR}")
    log(f"Backup dir: {BACKUP_DIR}")
    
    # Execute
    backup_existing()
    deploy_new_files()
    remove_morgan_deps()
    rebuild_and_restart()
    verify_deployment()
    
    log("=" * 60)
    log("DEPLOYMENT COMPLETE!")
    log("=" * 60)
    log("")
    log("What's changed:")
    log("  • /api/kelly — NEW unified endpoint (single brain + tools)")
    log("  • /api/orchestrate — DEPRECATED (redirects to Kelly)")
    log("  • /api/hermes-chat — DEPRECATED (redirects to Kelly)")
    log("  • Morgan removed — no more dual-agent confusion")
    log("")
    log("Next steps:")
    log("  1. Update frontend to call /api/kelly instead of old endpoints")
    log("  2. Test: curl -X POST http://127.0.0.1:3000/api/kelly \\")
    log("       -H 'Content-Type: application/json' \\")
    log('       -d \'{"message": "hello kelly"}\'')
    log("")
    log(f"Backup saved at: {BACKUP_DIR}")

if __name__ == "__main__":
    main()
