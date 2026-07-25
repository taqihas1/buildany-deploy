#!/usr/bin/env python3
"""
Write Kelly Unified Architecture files directly to /root/buildany/
This bypasses git entirely — writes files from embedded content.
"""

import os

BUILDANY_DIR = "/root/buildany"

# ============================================================
# FILE 1: src/app/api/kelly/route.ts
# ============================================================
KELLY_ROUTE = r'''import { NextRequest, NextResponse } from "next/server";
import { executeTool, KELLY_TOOLS } from "@/lib/kelly-tools";
import { buildSystemPrompt } from "@/lib/kelly-system";

const HERMES_API_URL = process.env.HERMES_API_URL || "http://127.0.0.1:8642";
const HERMES_API_KEY = process.env.HERMES_API_KEY || "";
const DEEPSEEK_API_KEY = process.env.DEEPSEEK_API_KEY || "";
const DEEPSEEK_BASE_URL = process.env.DEEPSEEK_BASE_URL || "https://api.deepseek.com/v1";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { message, projectId, history = [], stream = false } = body;
    if (!message) {
      return NextResponse.json({ error: "Message required" }, { status: 400 });
    }
    const systemPrompt = await buildSystemPrompt({ projectId });
    const messages = [
      { role: "system" as const, content: systemPrompt },
      ...history,
      { role: "user", content: message },
    ];
    const llmResponse = await callLLM(messages, stream);
    if (stream) {
      return new Response("Streaming not yet implemented", { status: 501 });
    }
    const choice = llmResponse.choices?.[0];
    const assistantMessage = choice?.message;
    if (assistantMessage?.tool_calls && assistantMessage.tool_calls.length > 0) {
      const toolResults = await Promise.all(
        assistantMessage.tool_calls.map(async (tc: any) => {
          try {
            const args = JSON.parse(tc.function.arguments);
            const result = await executeTool(tc.function.name, args);
            return { tool_call_id: tc.id, role: "tool" as const, content: JSON.stringify(result) };
          } catch (err: any) {
            return { tool_call_id: tc.id, role: "tool" as const, content: JSON.stringify({ error: err.message }) };
          }
        })
      );
      const followUpMessages = [...messages, assistantMessage, ...toolResults];
      const finalResponse = await callLLM(followUpMessages, false);
      const finalContent = finalResponse.choices?.[0]?.message?.content || "Done.";
      return NextResponse.json({
        reply: finalContent,
        toolCalls: assistantMessage.tool_calls.map((tc: any) => ({
          name: tc.function.name,
          arguments: JSON.parse(tc.function.arguments),
        })),
        toolResults: toolResults.map((tr: any) => ({ tool: tr.tool_call_id, result: JSON.parse(tr.content) })),
        projectId,
      });
    }
    return NextResponse.json({ reply: assistantMessage?.content || "No response.", projectId });
  } catch (e: any) {
    console.error("[Kelly] Error:", e);
    return NextResponse.json({ error: "Kelly processing failed", details: e.message }, { status: 500 });
  }
}

async function callLLM(messages: any[], stream: boolean): Promise<any> {
  const useHermes = HERMES_API_KEY && HERMES_API_URL;
  const url = useHermes ? `${HERMES_API_URL}/v1/chat/completions` : `${DEEPSEEK_BASE_URL}/chat/completions`;
  const authHeader = useHermes ? `Bearer ${HERMES_API_KEY}` : `Bearer ${DEEPSEEK_API_KEY}`;
  const res = await fetch(url, {
    method: "POST",
    headers: { Authorization: authHeader, "Content-Type": "application/json" },
    body: JSON.stringify({
      model: "deepseek-chat",
      messages,
      tools: KELLY_TOOLS,
      tool_choice: "auto",
      temperature: 0.7,
      stream,
    }),
  });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`LLM error ${res.status}: ${errorText}`);
  }
  if (stream) return res;
  return await res.json();
}

export async function GET() {
  return NextResponse.json({
    status: "ok",
    agent: "kelly",
    version: "2.0",
    architecture: "unified",
    tools: KELLY_TOOLS.map((t) => ({ name: t.function.name, description: t.function.description })),
  });
}
'''

# ============================================================
# FILE 2: src/lib/kelly-tools.ts  (truncated — key tools only)
# ============================================================
KELLY_TOOLS = r'''import { exec } from "child_process";
import { promisify } from "util";
import fs from "fs/promises";
import path from "path";

const execAsync = promisify(exec);
const PROJECTS_DIR = process.env.PROJECTS_DIR || "/root/buildany/projects";
const DEEPSEEK_API_KEY = process.env.DEEPSEEK_API_KEY || "";
const DEEPSEEK_BASE_URL = process.env.DEEPSEEK_BASE_URL || "https://api.deepseek.com/v1";
const GITHUB_TOKEN = process.env.GITHUB_TOKEN || "";
const CLOUDFLARE_API_TOKEN = process.env.CLOUDFLARE_API_TOKEN || "";
const CF_ACCOUNT_ID = process.env.CF_ACCOUNT_ID || "";

export interface ToolResult {
  success: boolean;
  data?: any;
  error?: string;
}

export const KELLY_TOOLS = [
  {
    type: "function" as const,
    function: {
      name: "create_project",
      description: "Create a new app project. Returns project ID.",
      parameters: {
        type: "object",
        properties: {
          name: { type: "string", description: "Project name" },
          prompt: { type: "string", description: "User's app description" },
          platform: { type: "string", enum: ["web", "mobile", "both"], description: "Target platform" },
        },
        required: ["name", "prompt", "platform"],
      },
    },
  },
  {
    type: "function" as const,
    function: {
      name: "generate_code",
      description: "Generate code files for a project using AI. Writes files to disk.",
      parameters: {
        type: "object",
        properties: {
          projectId: { type: "string", description: "Project ID" },
          filePath: { type: "string", description: "Relative file path to create (e.g. src/App.tsx)" },
          prompt: { type: "string", description: "What code to generate" },
          language: { type: "string", description: "TypeScript, TSX, etc." },
        },
        required: ["projectId", "filePath", "prompt"],
      },
    },
  },
  {
    type: "function" as const,
    function: {
      name: "build_project",
      description: "Run npm install + build for a project. Returns build output.",
      parameters: {
        type: "object",
        properties: {
          projectId: { type: "string", description: "Project ID" },
        },
        required: ["projectId"],
      },
    },
  },
  {
    type: "function" as const,
    function: {
      name: "security_audit",
      description: "Run security audit on a project. Returns findings.",
      parameters: {
        type: "object",
        properties: {
          projectId: { type: "string", description: "Project ID" },
        },
        required: ["projectId"],
      },
    },
  },
  {
    type: "function" as const,
    function: {
      name: "code_cleanup",
      description: "Clean up dead code, unused imports, formatting in a project.",
      parameters: {
        type: "object",
        properties: {
          projectId: { type: "string", description: "Project ID" },
        },
        required: ["projectId"],
      },
    },
  },
  {
    type: "function" as const,
    function: {
      name: "git_checkpoint",
      description: "Create a git checkpoint (commit) for a project.",
      parameters: {
        type: "object",
        properties: {
          projectId: { type: "string", description: "Project ID" },
          message: { type: "string", description: "Commit message" },
        },
        required: ["projectId", "message"],
      },
    },
  },
  {
    type: "function" as const,
    function: {
      name: "git_revert",
      description: "Revert a project to a previous git checkpoint.",
      parameters: {
        type: "object",
        properties: {
          projectId: { type: "string", description: "Project ID" },
          commitHash: { type: "string", description: "Commit hash to revert to" },
        },
        required: ["projectId", "commitHash"],
      },
    },
  },
  {
    type: "function" as const,
    function: {
      name: "list_project_files",
      description: "List all files in a project directory.",
      parameters: {
        type: "object",
        properties: {
          projectId: { type: "string", description: "Project ID" },
        },
        required: ["projectId"],
      },
    },
  },
  {
    type: "function" as const,
    function: {
      name: "read_file",
      description: "Read a file from a project.",
      parameters: {
        type: "object",
        properties: {
          projectId: { type: "string", description: "Project ID" },
          filePath: { type: "string", description: "Relative file path" },
        },
        required: ["projectId", "filePath"],
      },
    },
  },
  {
    type: "function" as const,
    function: {
      name: "write_file",
      description: "Write content to a file in a project. Creates dirs if needed.",
      parameters: {
        type: "object",
        properties: {
          projectId: { type: "string", description: "Project ID" },
          filePath: { type: "string", description: "Relative file path" },
          content: { type: "string", description: "File content" },
        },
        required: ["projectId", "filePath", "content"],
      },
    },
  },
  {
    type: "function" as const,
    function: {
      name: "memory_read",
      description: "Read from BuildAny memory (OKF/MEMORY.md).",
      parameters: {
        type: "object",
        properties: {
          key: { type: "string", description: "Memory key or path" },
        },
        required: ["key"],
      },
    },
  },
  {
    type: "function" as const,
    function: {
      name: "memory_write",
      description: "Write to BuildAny memory (OKF/MEMORY.md).",
      parameters: {
        type: "object",
        properties: {
          key: { type: "string", description: "Memory key" },
          content: { type: "string", description: "Content to store" },
        },
        required: ["key", "content"],
      },
    },
  },
  {
    type: "function" as const,
    function: {
      name: "github_push",
      description: "Push project code to GitHub. Creates repo if needed.",
      parameters: {
        type: "object",
        properties: {
          projectId: { type: "string", description: "Project ID" },
          repoName: { type: "string", description: "GitHub repo name" },
          commitMessage: { type: "string", description: "Commit message" },
        },
        required: ["projectId", "repoName", "commitMessage"],
      },
    },
  },
  {
    type: "function" as const,
    function: {
      name: "cloudflare_deploy",
      description: "Deploy project to Cloudflare Pages.",
      parameters: {
        type: "object",
        properties: {
          projectId: { type: "string", description: "Project ID" },
          projectName: { type: "string", description: "Cloudflare project name" },
        },
        required: ["projectId", "projectName"],
      },
    },
  },
  {
    type: "function" as const,
    function: {
      name: "cloudflare_purge_cache",
      description: "Purge Cloudflare cache for a domain.",
      parameters: {
        type: "object",
        properties: {
          zoneId: { type: "string", description: "Cloudflare zone ID" },
        },
        required: ["zoneId"],
      },
    },
  },
];

export async function executeTool(name: string, args: any): Promise<ToolResult> {
  try {
    switch (name) {
      case "create_project":
        return await toolCreateProject(args);
      case "generate_code":
        return await toolGenerateCode(args);
      case "build_project":
        return await toolBuildProject(args);
      case "security_audit":
        return await toolSecurityAudit(args);
      case "code_cleanup":
        return await toolCodeCleanup(args);
      case "git_checkpoint":
        return await toolGitCheckpoint(args);
      case "git_revert":
        return await toolGitRevert(args);
      case "list_project_files":
        return await toolListFiles(args);
      case "read_file":
        return await toolReadFile(args);
      case "write_file":
        return await toolWriteFile(args);
      case "memory_read":
        return await toolMemoryRead(args);
      case "memory_write":
        return await toolMemoryWrite(args);
      case "github_push":
        return await toolGitHubPush(args);
      case "cloudflare_deploy":
        return await toolCloudflareDeploy(args);
      case "cloudflare_purge_cache":
        return await toolCloudflarePurge(args);
      default:
        return { success: false, error: `Unknown tool: ${name}` };
    }
  } catch (e: any) {
    return { success: false, error: e.message };
  }
}

/* ─── TOOL IMPLEMENTATIONS ─── */

async function toolCreateProject(args: any): Promise<ToolResult> {
  const id = args.name.toLowerCase().replace(/[^a-z0-9]/g, "-") + "-" + Date.now();
  const dir = path.join(PROJECTS_DIR, id);
  await fs.mkdir(dir, { recursive: true });
  await fs.writeFile(path.join(dir, "README.md"), `# ${args.name}\n\n${args.prompt}\n`);
  return { success: true, data: { projectId: id, path: dir } };
}

async function toolGenerateCode(args: any): Promise<ToolResult> {
  if (!DEEPSEEK_API_KEY) return { success: false, error: "DEEPSEEK_API_KEY not set" };
  const projectDir = path.join(PROJECTS_DIR, args.projectId);
  const fullPath = path.join(projectDir, args.filePath);
  await fs.mkdir(path.dirname(fullPath), { recursive: true });

  const prompt = `Generate ${args.language || "TypeScript"} code for: ${args.prompt}\n\nRules:\n- NO imports from next/document (no Html, Head, Main, NextScript)\n- Use standard JSX for App Router pages\n- Return ONLY the code, no markdown fences\n- Include \"use client\" or \"use server\" directives as needed`;

  const res = await fetch(`${DEEPSEEK_BASE_URL}/chat/completions`, {
    method: "POST",
    headers: { Authorization: `Bearer ${DEEPSEEK_API_KEY}`, "Content-Type": "application/json" },
    body: JSON.stringify({ model: "deepseek-chat", messages: [{ role: "user", content: prompt }], temperature: 0.2 }),
  });
  if (!res.ok) return { success: false, error: `DeepSeek error: ${res.status}` };
  const data = await res.json();
  let code = data.choices?.[0]?.message?.content || "";
  code = code.replace(/\`\`\`[a-z]*\n?/g, "").replace(/\`\`\`$/g, "").trim();
  await fs.writeFile(fullPath, code, "utf-8");
  return { success: true, data: { filePath: args.filePath, bytes: code.length } };
}

async function toolBuildProject(args: any): Promise<ToolResult> {
  const projectDir = path.join(PROJECTS_DIR, args.projectId);
  try {
    const { stdout, stderr } = await execAsync("npm install && npm run build", { cwd: projectDir, timeout: 120000 });
    return { success: true, data: { stdout, stderr } };
  } catch (e: any) {
    return { success: false, error: e.stderr || e.message };
  }
}

async function toolSecurityAudit(args: any): Promise<ToolResult> {
  const projectDir = path.join(PROJECTS_DIR, args.projectId);
  const findings: string[] = [];
  try {
    const files = await listAllFiles(projectDir);
    for (const f of files) {
      const content = await fs.readFile(f, "utf-8");
      if (/api[_-]?key|password|secret|token/i.test(content) && !/process\.env/i.test(content)) {
        findings.push(`Possible hardcoded secret in ${path.relative(projectDir, f)}`);
      }
      if (/eval\s*\(|Function\s*\(/i.test(content)) {
        findings.push(`Dangerous eval/Function in ${path.relative(projectDir, f)}`);
      }
    }
    return { success: true, data: { findings, passed: findings.length === 0 } };
  } catch (e: any) {
    return { success: false, error: e.message };
  }
}

async function toolCodeCleanup(args: any): Promise<ToolResult> {
  const projectDir = path.join(PROJECTS_DIR, args.projectId);
  try {
    await execAsync("npx prettier --write .", { cwd: projectDir, timeout: 60000 });
    return { success: true, data: { message: "Prettier formatting applied" } };
  } catch (e: any) {
    return { success: false, error: e.message };
  }
}

async function toolGitCheckpoint(args: any): Promise<ToolResult> {
  const projectDir = path.join(PROJECTS_DIR, args.projectId);
  try {
    await execAsync(`git add -A && git commit -m "${args.message.replace(/"/g, '\\"')}"`, { cwd: projectDir });
    const { stdout } = await execAsync("git rev-parse HEAD", { cwd: projectDir });
    return { success: true, data: { commitHash: stdout.trim() } };
  } catch (e: any) {
    return { success: false, error: e.message };
  }
}

async function toolGitRevert(args: any): Promise<ToolResult> {
  const projectDir = path.join(PROJECTS_DIR, args.projectId);
  try {
    await execAsync(`git reset --hard ${args.commitHash}`, { cwd: projectDir });
    return { success: true, data: { revertedTo: args.commitHash } };
  } catch (e: any) {
    return { success: false, error: e.message };
  }
}

async function toolListFiles(args: any): Promise<ToolResult> {
  const projectDir = path.join(PROJECTS_DIR, args.projectId);
  try {
    const files = await listAllFiles(projectDir);
    return { success: true, data: { files: files.map((f) => path.relative(projectDir, f)) } };
  } catch (e: any) {
    return { success: false, error: e.message };
  }
}

async function toolReadFile(args: any): Promise<ToolResult> {
  const projectDir = path.join(PROJECTS_DIR, args.projectId);
  const fullPath = path.join(projectDir, args.filePath);
  if (!fullPath.startsWith(projectDir)) return { success: false, error: "Path traversal blocked" };
  try {
    const content = await fs.readFile(fullPath, "utf-8");
    return { success: true, data: { content } };
  } catch (e: any) {
    return { success: false, error: e.message };
  }
}

async function toolWriteFile(args: any): Promise<ToolResult> {
  const projectDir = path.join(PROJECTS_DIR, args.projectId);
  const fullPath = path.join(projectDir, args.filePath);
  if (!fullPath.startsWith(projectDir)) return { success: false, error: "Path traversal blocked" };
  await fs.mkdir(path.dirname(fullPath), { recursive: true });
  await fs.writeFile(fullPath, args.content, "utf-8");
  return { success: true, data: { filePath: args.filePath, bytes: args.content.length } };
}

async function toolMemoryRead(args: any): Promise<ToolResult> {
  const memPath = path.join(BUILDANY_DIR, "memory", `${args.key}.md`);
  try {
    const content = await fs.readFile(memPath, "utf-8");
    return { success: true, data: { key: args.key, content } };
  } catch {
    return { success: false, error: `Memory key '${args.key}' not found` };
  }
}

async function toolMemoryWrite(args: any): Promise<ToolResult> {
  const memDir = path.join(BUILDANY_DIR, "memory");
  await fs.mkdir(memDir, { recursive: true });
  const memPath = path.join(memDir, `${args.key}.md`);
  await fs.writeFile(memPath, args.content, "utf-8");
  return { success: true, data: { key: args.key, saved: true } };
}

async function toolGitHubPush(args: any): Promise<ToolResult> {
  if (!GITHUB_TOKEN) return { success: false, error: "GITHUB_TOKEN not set" };
  const projectDir = path.join(PROJECTS_DIR, args.projectId);
  try {
    const remoteUrl = `https://${GITHUB_TOKEN}@github.com/taqihas1/${args.repoName}.git`;
    const initCheck = await execAsync("git rev-parse --git-dir", { cwd: projectDir }).catch(() => null);
    if (!initCheck) await execAsync("git init && git branch -m main", { cwd: projectDir });
    await execAsync(`git remote add origin ${remoteUrl} 2>/dev/null || git remote set-url origin ${remoteUrl}`, { cwd: projectDir });
    await execAsync("git add -A", { cwd: projectDir });
    await execAsync(`git commit -m "${args.commitMessage.replace(/"/g, '\\"')}" 2>/dev/null || true`, { cwd: projectDir });
    await execAsync("git push -u origin main --force", { cwd: projectDir });
    return { success: true, data: { repo: `https://github.com/taqihas1/${args.repoName}`, pushed: true } };
  } catch (e: any) {
    return { success: false, error: e.stderr || e.message };
  }
}

async function toolCloudflareDeploy(args: any): Promise<ToolResult> {
  if (!CLOUDFLARE_API_TOKEN) return { success: false, error: "CLOUDFLARE_API_TOKEN not set" };
  const projectDir = path.join(PROJECTS_DIR, args.projectId);
  try {
    const distDir = path.join(projectDir, "dist");
    const zipPath = path.join(projectDir, "deploy.zip");
    await execAsync(`zip -r ${zipPath} dist/`, { cwd: projectDir });
    const res = await fetch(`https://api.cloudflare.com/client/v4/accounts/${CF_ACCOUNT_ID}/pages/projects/${args.projectName}/deployments`, {
      method: "POST",
      headers: { Authorization: `Bearer ${CLOUDFLARE_API_TOKEN}`, "Content-Type": "application/json" },
      body: JSON.stringify({ branch: "main" }),
    });
    const data = await res.json();
    if (!data.success) return { success: false, error: JSON.stringify(data.errors) };
    return { success: true, data: { deploymentId: data.result.id, url: data.result.url } };
  } catch (e: any) {
    return { success: false, error: e.message };
  }
}

async function toolCloudflarePurge(args: any): Promise<ToolResult> {
  if (!CLOUDFLARE_API_TOKEN) return { success: false, error: "CLOUDFLARE_API_TOKEN not set" };
  try {
    const res = await fetch(`https://api.cloudflare.com/client/v4/zones/${args.zoneId}/purge_cache`, {
      method: "POST",
      headers: { Authorization: `Bearer ${CLOUDFLARE_API_TOKEN}`, "Content-Type": "application/json" },
      body: JSON.stringify({ purge_everything: true }),
    });
    const data = await res.json();
    if (!data.success) return { success: false, error: JSON.stringify(data.errors) };
    return { success: true, data: { purged: true } };
  } catch (e: any) {
    return { success: false, error: e.message };
  }
}

/* ─── HELPERS ─── */

async function listAllFiles(dir: string): Promise<string[]> {
  const files: string[] = [];
  const entries = await fs.readdir(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory() && entry.name !== "node_modules" && entry.name !== ".git") {
      files.push(...(await listAllFiles(fullPath)));
    } else if (entry.isFile()) {
      files.push(fullPath);
    }
  }
  return files;
}
'''

# ============================================================
# FILE 3: src/lib/kelly-system.ts
# ============================================================
KELLY_SYSTEM = r'''import fs from "fs/promises";
import path from "path";

const BUILDANY_DIR = process.cwd();

export async function buildSystemPrompt(ctx: { projectId?: string }): Promise<string> {
  const skills = await loadSkills();
  const memory = await loadMemory(ctx.projectId);

  return `You are Kelly — the BuildAny AI agent.

Your job: Help users build apps. You have direct access to tools.
Think step by step. Ask clarifying questions when needed.
When you're confident, call tools to get things done.

## Available Tools
You can call these functions:
- create_project — start a new app project
- generate_code — write code files using AI
- build_project — run npm install + build
- security_audit — scan for secrets and vulnerabilities
- code_cleanup — format and clean code
- git_checkpoint — save progress with git
- git_revert — roll back to a previous save
- list_project_files — see all files in a project
- read_file — read any file
- write_file — write any file
- memory_read / memory_write — persistent knowledge storage
- github_push — push code to GitHub
- cloudflare_deploy — deploy to Cloudflare Pages
- cloudflare_purge_cache — clear CDN cache

## Decision Rules
1. If user asks to build something → create_project → generate_code → build_project
2. If build fails → read_file (the error file) → generate_code (fix) → build_project
3. If user asks to deploy → github_push → cloudflare_deploy
4. If user asks to revert → git_revert
5. Always checkpoint before major changes

## Stack Defaults (when not specified)
- Web: Next.js 14+ (App Router), TypeScript, Tailwind, shadcn/ui
- Mobile: Expo SDK 54+, React Native, TypeScript
- Both: Shared TypeScript types, REST API

## Code Generation Rules
- NO imports from next/document in App Router pages
- Use standard JSX: <div>, <head> from next/head
- Include proper "use client" / "use server" directives
- Use TypeScript with proper types
- Follow the existing codebase patterns

## Loaded Skills
${skills.join("\n")}

## Project Context
${memory}
`;
}

async function loadSkills(): Promise<string[]> {
  const skillsDir = path.join(BUILDANY_DIR, "skills");
  const skills: string[] = [];
  try {
    const files = await fs.readdir(skillsDir);
    for (const file of files.filter((f) => f.endsWith(".md"))) {
      const content = await fs.readFile(path.join(skillsDir, file), "utf-8");
      skills.push(`### ${file}\n${content.slice(0, 500)}...`);
    }
  } catch {
    skills.push("(no skills loaded)");
  }
  return skills;
}

async function loadMemory(projectId?: string): Promise<string> {
  const lines: string[] = [];
  if (projectId) {
    lines.push(`Current Project: ${projectId}`);
    const memFile = path.join(BUILDANY_DIR, "memory", `${projectId}.md`);
    try {
      const content = await fs.readFile(memFile, "utf-8");
      lines.push(`Project Memory:\n${content.slice(0, 1000)}`);
    } catch {
      lines.push("(no project memory yet)");
    }
  }
  return lines.join("\n");
}
'''

# ============================================================
# FILE 4: src/app/api/github-tool/route.ts
# ============================================================
GITHUB_TOOL = r'''import { NextRequest, NextResponse } from "next/server";

const GITHUB_TOKEN = process.env.GITHUB_TOKEN || "";

async function githubApi(path: string, opts: RequestInit = {}) {
  const res = await fetch(`https://api.github.com${path}`, {
    ...opts,
    headers: {
      Authorization: `Bearer ${GITHUB_TOKEN}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      ...(opts.headers || {}),
    },
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(JSON.stringify(data));
  return data;
}

export async function POST(req: NextRequest) {
  try {
    const { action, ...args } = await req.json();
    let result: any;

    switch (action) {
      case "create_repo": {
        result = await githubApi("/user/repos", {
          method: "POST",
          body: JSON.stringify({ name: args.name, private: args.private ?? false, description: args.description || "" }),
        });
        break;
      }
      case "push_changes": {
        result = await githubApi(`/repos/${args.owner}/${args.repo}/git/refs/heads/main`, { method: "GET" });
        break;
      }
      case "create_pull_request": {
        result = await githubApi(`/repos/${args.owner}/${args.repo}/pulls`, {
          method: "POST",
          body: JSON.stringify({ title: args.title, head: args.head, base: args.base || "main", body: args.body || "" }),
        });
        break;
      }
      case "get_repo_files": {
        result = await githubApi(`/repos/${args.owner}/${args.repo}/contents/${args.path || ""}`);
        break;
      }
      case "get_file_content": {
        const data = await githubApi(`/repos/${args.owner}/${args.repo}/contents/${args.path}`);
        result = { content: Buffer.from(data.content, "base64").toString("utf-8"), sha: data.sha };
        break;
      }
      case "update_file": {
        const current = await githubApi(`/repos/${args.owner}/${args.repo}/contents/${args.path}`);
        result = await githubApi(`/repos/${args.owner}/${args.repo}/contents/${args.path}`, {
          method: "PUT",
          body: JSON.stringify({ message: args.message, content: Buffer.from(args.content).toString("base64"), sha: current.sha }),
        });
        break;
      }
      case "check_workflows": {
        result = await githubApi(`/repos/${args.owner}/${args.repo}/actions/runs`);
        break;
      }
      default:
        return NextResponse.json({ error: `Unknown action: ${action}` }, { status: 400 });
    }

    return NextResponse.json({ success: true, data: result });
  } catch (e: any) {
    return NextResponse.json({ success: false, error: e.message }, { status: 500 });
  }
}

export async function GET() {
  return NextResponse.json({ status: "ok", connector: "github", actions: ["create_repo", "push_changes", "create_pull_request", "get_repo_files", "get_file_content", "update_file", "check_workflows"] });
}
'''

# ============================================================
# FILE 5: src/app/api/cloudflare-tool/route.ts
# ============================================================
CLOUDFLARE_TOOL = r'''import { NextRequest, NextResponse } from "next/server";

const CF_TOKEN = process.env.CLOUDFLARE_API_TOKEN || "";
const CF_ACCOUNT_ID = process.env.CF_ACCOUNT_ID || "";

async function cfApi(path: string, opts: RequestInit = {}) {
  const res = await fetch(`https://api.cloudflare.com/client/v4${path}`, {
    ...opts,
    headers: { Authorization: `Bearer ${CF_TOKEN}`, "Content-Type": "application/json", ...(opts.headers || {}) },
  });
  const data = await res.json().catch(() => ({}));
  if (!data.success) throw new Error(JSON.stringify(data.errors || data.messages || ["CF API error"]));
  return data.result;
}

export async function POST(req: NextRequest) {
  try {
    const { action, ...args } = await req.json();
    let result: any;

    switch (action) {
      case "deploy_pages": {
        result = await cfApi(`/accounts/${CF_ACCOUNT_ID}/pages/projects/${args.projectName}/deployments`, {
          method: "POST",
          body: JSON.stringify({ branch: args.branch || "main" }),
        });
        break;
      }
      case "get_deployment_status": {
        result = await cfApi(`/accounts/${CF_ACCOUNT_ID}/pages/projects/${args.projectName}/deployments/${args.deploymentId}`);
        break;
      }
      case "purge_cache": {
        result = await cfApi(`/zones/${args.zoneId}/purge_cache`, { method: "POST", body: JSON.stringify({ purge_everything: true }) });
        break;
      }
      case "list_dns_records": {
        result = await cfApi(`/zones/${args.zoneId}/dns_records`);
        break;
      }
      case "create_dns_record": {
        result = await cfApi(`/zones/${args.zoneId}/dns_records`, {
          method: "POST",
          body: JSON.stringify({ type: args.type, name: args.name, content: args.content, ttl: args.ttl || 1 }),
        });
        break;
      }
      case "get_analytics": {
        result = await cfApi(`/zones/${args.zoneId}/analytics/dashboard`);
        break;
      }
      case "list_zones": {
        result = await cfApi("/zones");
        break;
      }
      default:
        return NextResponse.json({ error: `Unknown action: ${action}` }, { status: 400 });
    }

    return NextResponse.json({ success: true, data: result });
  } catch (e: any) {
    return NextResponse.json({ success: false, error: e.message }, { status: 500 });
  }
}

export async function GET() {
  return NextResponse.json({ status: "ok", connector: "cloudflare", actions: ["deploy_pages", "get_deployment_status", "purge_cache", "list_dns_records", "create_dns_record", "get_analytics", "list_zones"] });
}
'''

# ============================================================
# FILE 6: src/app/kelly-test/page.tsx
# ============================================================
KELLY_TEST_PAGE = r'''"use client";

import { useState } from "react";

export default function KellyTestPage() {
  const [message, setMessage] = useState("");
  const [response, setResponse] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const sendMessage = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/kelly", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
      });
      const data = await res.json();
      setResponse(data);
    } catch (e: any) {
      setResponse({ error: e.message });
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-white p-8">
      <h1 className="text-3xl font-bold mb-6">🧠 Kelly Unified Test</h1>
      <div className="flex gap-2 mb-4">
        <input
          className="flex-1 px-4 py-2 rounded bg-slate-800 border border-slate-700"
          placeholder="Say something to Kelly..."
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && sendMessage()}
        />
        <button
          onClick={sendMessage}
          disabled={loading}
          className="px-6 py-2 rounded bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50"
        >
          {loading ? "..." : "Send"}
        </button>
      </div>
      {response && (
        <pre className="bg-slate-900 p-4 rounded text-sm overflow-auto max-h-96">
          {JSON.stringify(response, null, 2)}
        </pre>
      )}
    </div>
  );
}
'''

# ============================================================
# WRITE ALL FILES
# ============================================================

def write_file(rel_path: str, content: str):
    full = os.path.join(BUILDANY_DIR, rel_path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[OK] {rel_path} ({len(content)} bytes)")

if __name__ == "__main__":
    write_file("src/app/api/kelly/route.ts", KELLY_ROUTE)
    write_file("src/lib/kelly-tools.ts", KELLY_TOOLS)
    write_file("src/lib/kelly-system.ts", KELLY_SYSTEM)
    write_file("src/app/api/github-tool/route.ts", GITHUB_TOOL)
    write_file("src/app/api/cloudflare-tool/route.ts", CLOUDFLARE_TOOL)
    write_file("src/app/kelly-test/page.tsx", KELLY_TEST_PAGE)
    print("\n✅ All Kelly files written. Now run: rm -rf .next && npm run build && pm2 restart buildany")
