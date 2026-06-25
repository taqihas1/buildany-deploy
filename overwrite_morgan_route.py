#!/usr/bin/env python3
"""
Direct overwrite of morgan-generate/route.ts with clean sanitizer
"""
import os

BUILDANY_DIR = "/root/buildany"
MORGAN_ROUTE = os.path.join(BUILDANY_DIR, "src/app/api/morgan-generate/route.ts")

print("🔧 Writing clean morgan-generate/route.ts...")

# The COMPLETE clean file
CONTENT = '''import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { projects, projectFiles, conversations } from "@/lib/db/schema";
import { generateShortName } from "@/lib/project-name-generator";
import { eq } from "drizzle-orm";
import { execSync } from "child_process";
import fs from "fs/promises";
import path from "path";

const DEEPSEEK_KEY = process.env.DEEPSEEK_API_KEY || "";
const PROJECTS_DIR = "/data/projects";

function sanitizeGeneratedFiles(projectDir: string) {
  try {
    const nodeFs = require("fs");
    const nodePath = require("path");
    
    function walkDir(dir: string, callback: (fp: string) => void) {
      if (!nodeFs.existsSync(dir)) return;
      const entries = nodeFs.readdirSync(dir, { withFileTypes: true });
      for (const entry of entries) {
        const fullPath = nodePath.join(dir, entry.name);
        if (entry.isDirectory() && entry.name !== "node_modules" && entry.name !== ".git") {
          walkDir(fullPath, callback);
        } else if (entry.isFile() && /\\.(tsx?|jsx?)$/.test(entry.name)) {
          callback(fullPath);
        }
      }
    }
    
    const srcDir = nodePath.join(projectDir, "src");
    walkDir(srcDir, (fp: string) => {
      if (fp.includes("_document")) return;
      
      let code = nodeFs.readFileSync(fp, "utf8");
      if (!code.includes("next/document")) return;
      
      console.log("[Sanitize] Fixing: " + fp);
      
      code = code.replace(/import\\s*\\{[^}]*\\}\\s*from\\s*['"]next\\/document['"];?\\s*\\n?/gi, "");
      code = code.replace(/import\\s+\\w+\\s+from\\s*['"]next\\/document['"];?\\s*\\n?/gi, "");
      code = code.replace(/<Html([^>]*)>/gi, "<div$1>");
      code = code.replace(/<\\/Html>/gi, "</div>");
      code = code.replace(/<Main([^>]*)>/gi, "<main$1>");
      code = code.replace(/<\\/Main>/gi, "</main>");
      code = code.replace(/<NextScript\\s*\\/>/gi, "");
      
      nodeFs.writeFileSync(fp, code);
    });
  } catch (e) {
    console.error("[Sanitize] Error:", e);
  }
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { prompt, type = "web", appType, userId, projectId: existingProjectId } = body;
    const projectType = appType || type;

    if (!prompt?.trim()) {
      return NextResponse.json({ error: "Prompt is required" }, { status: 400 });
    }

    let projectId: string;
    let projectDir: string;
    let shortName: string;

    if (existingProjectId) {
      projectId = existingProjectId;
      const existing = await db.select().from(projects).where(eq(projects.id, projectId)).get();
      if (!existing) {
        return NextResponse.json({ error: "Project not found" }, { status: 404 });
      }
      shortName = existing.name;
      projectDir = path.join(PROJECTS_DIR, projectId);
      
      await db.update(projects)
        .set({ status: "creating", updatedAt: new Date() })
        .where(eq(projects.id, projectId));
    } else {
      projectId = crypto.randomUUID();
      shortName = generateShortName(prompt);

      await db.insert(projects).values({
        id: projectId,
        userId: userId || "guest-" + crypto.randomUUID(),
        name: shortName,
        description: prompt,
        type: projectType as "web" | "mobile" | "dashboard",
        status: "creating",
        createdAt: new Date(),
        updatedAt: new Date(),
      });

      projectDir = path.join(PROJECTS_DIR, projectId);
      await fs.mkdir(projectDir, { recursive: true });
      await fs.mkdir(path.join(projectDir, "src", "app"), { recursive: true });
      await fs.mkdir(path.join(projectDir, "src", "components"), { recursive: true });
      await fs.mkdir(path.join(projectDir, "src", "lib"), { recursive: true });

      try {
        execSync("git init", { cwd: projectDir, stdio: "ignore" });
        execSync('git config user.email "morgan@buildany.local"', { cwd: projectDir, stdio: "ignore" });
        execSync('git config user.name "Morgan"', { cwd: projectDir, stdio: "ignore" });
      } catch {
        // git optional
      }

      await db.insert(conversations).values({
        id: crypto.randomUUID(),
        projectId,
        role: "user",
        content: prompt,
        model: "user",
        createdAt: new Date(),
      });
    }

    const projectTypeForPrompt = projectType === "mobile" ? "React Native + Expo" : "Next.js 14 + App Router";

    const morganPrompt = `Build this app: "${prompt}"

Tech: ${projectTypeForPrompt}, TypeScript, Tailwind CSS.
Rules:
- Use the App Router (src/app).
- Keep components in src/components.
- Use client components ONLY when needed ('use client').
- Keep server components async when possible.
- Use Next.js built-in features: Image, Link, Script.
- Export default page components.
- CRITICAL: NEVER import <Html>, <Head>, <Main>, or <NextScript> from 'next/document' in any page. Only use these in pages/_document.js
- CRITICAL: NEVER create pages/_error.js or pages/_document.js or pages/500.js or pages/404.js
- Do NOT use <img>; always use next/image <Image>.
- CRITICAL: NEVER put <link rel="stylesheet" /> in JSX. Use next/head <Head> for global stylesheets OR import CSS modules. For Google Fonts, NEVER use <link> tags for fonts. Always use next/font.
- CRITICAL: NEVER call hooks like useState() directly in JSX (e.g., {useState(...)}). Hooks MUST be inside a function component, not in JSX expressions.
- Do NOT create empty route files. If a page is empty, add a simple React component.
- Use @/components and @/lib path aliases.
- Return ONLY the file paths and code blocks, no extra commentary.

Generate:
1. src/app/page.tsx
2. src/app/layout.tsx
3. src/components/Header.tsx
4. src/components/Hero.tsx
5. src/app/globals.css
6. next.config.js
7. package.json
8. tsconfig.json
9. src/app/about/page.tsx
10. src/app/contact/page.tsx
11. src/app/blog/page.tsx
12. src/app/blog/[slug]/page.tsx
13. src/app/api/hello/route.ts
14. README.md
15. .env.example`;

    const response = await fetch("https://api.deepseek.com/v1/chat/completions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${DEEPSEEK_KEY}`,
      },
      body: JSON.stringify({
        model: "deepseek-chat",
        messages: [{ role: "user", content: morganPrompt }],
        temperature: 0.7,
        max_tokens: 4000,
      }),
    });

    if (!response.ok) {
      throw new Error(`DeepSeek API error: ${response.status}`);
    }

    const data = await response.json();
    const generatedText = data.choices?.[0]?.message?.content || "";

    const fileRegex = /```(?:tsx?|jsx?|css|json|md|env)?\\s*\\n?(?:\\/\\/\\s*)?(.+?)\\n([\\s\\S]*?)```/g;
    const files: Record<string, string> = {};
    let match;
    while ((match = fileRegex.exec(generatedText)) !== null) {
      const filePath = match[1].trim().replace(/^\\/\\//, "").trim();
      const fileContent = match[2].trim();
      if (filePath && fileContent) {
        files[filePath] = fileContent;
      }
    }

    const writtenFiles: string[] = [];
    for (const [relativePath, content] of Object.entries(files)) {
      const safePath = path.join(projectDir, relativePath.replace(/^\\//, ""));
      await fs.mkdir(path.dirname(safePath), { recursive: true });
      const finalContent = relativePath.endsWith(".tsx") || relativePath.endsWith(".ts")
        ? "// @ts-nocheck\\n" + content
        : content;
      await fs.writeFile(safePath, finalContent);
      writtenFiles.push(relativePath);
    }

    if (writtenFiles.length === 0) {
      const fallbackPage = path.join(projectDir, "src", "app", "page.tsx");
      await fs.writeFile(fallbackPage, `// @ts-nocheck\\nexport default function Home() { return <div>Hello from ${shortName}</div>; }`);
      writtenFiles.push("src/app/page.tsx");
    }

    await writePackageJson(projectDir, projectType);
    await writeNextConfig(projectDir);
    await writeTsConfig(projectDir);
    await writeTailwindConfig(projectDir);

    sanitizeGeneratedFiles(projectDir);

    try {
      execSync("git add -A", { cwd: projectDir, stdio: "ignore" });
      execSync('git commit -m "Initial generation"', { cwd: projectDir, stdio: "ignore" });
    } catch {
      // git optional
    }

    await db.update(projects)
      .set({ status: "ready", updatedAt: new Date() })
      .where(eq(projects.id, projectId));

    for (const filePath of writtenFiles) {
      await db.insert(projectFiles).values({
        id: crypto.randomUUID(),
        projectId,
        path: filePath,
        content: files[filePath] || "",
      });
    }

    return NextResponse.json({
      success: true,
      projectId,
      projectName: shortName,
      files: writtenFiles,
    });

  } catch (error: any) {
    console.error("[Morgan Generate] Error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

async function writePackageJson(projectDir: string, type: string) {
  const isMobile = type === "mobile";
  const pkg = {
    name: "generated-app",
    version: "1.0.0",
    private: true,
    scripts: {
      dev: isMobile ? "expo start" : "next dev",
      build: isMobile ? "expo export:web" : "next build",
      start: isMobile ? "expo start" : "next start",
    },
    dependencies: isMobile
      ? { react: "^18", "react-native": "^0.73", expo: "~50.0.0" }
      : { next: "^15.0.0", react: "^19.0.0", "react-dom": "^19.0.0", tailwindcss: "^3.4.0", autoprefixer: "^10.4.0", postcss: "^8.4.0" },
    devDependencies: isMobile
      ? { "@types/react": "^18", typescript: "^5.3" }
      : { "@types/node": "^20", "@types/react": "^19", "@types/react-dom": "^19", typescript: "^5.3" },
  };
  await fs.writeFile(path.join(projectDir, "package.json"), JSON.stringify(pkg, null, 2));
}

async function writeNextConfig(projectDir: string) {
  const config = `
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  distDir: 'out',
  images: { unoptimized: true },
  typescript: { ignoreBuildErrors: true },
  eslint: { ignoreDuringBuilds: true },
};
module.exports = nextConfig;
`;
  await fs.writeFile(path.join(projectDir, "next.config.js"), config.trim());
}

async function writeTsConfig(projectDir: string) {
  const config = {
    compilerOptions: {
      lib: ["dom", "dom.iterable", "esnext"],
      allowJs: true,
      skipLibCheck: true,
      strict: false,
      noEmit: true,
      esModuleInterop: true,
      module: "esnext",
      moduleResolution: "bundler",
      resolveJsonModule: true,
      isolatedModules: true,
      jsx: "preserve",
      incremental: true,
      plugins: [{ name: "next" }],
      paths: { "@/*": ["./src/*"] },
    },
    include: ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
    exclude: ["node_modules"],
  };
  await fs.writeFile(path.join(projectDir, "tsconfig.json"), JSON.stringify(config, null, 2));
}

async function writeTailwindConfig(projectDir: string) {
  const config = `
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: { extend: {} },
  plugins: [],
};
`;
  await fs.writeFile(path.join(projectDir, "tailwind.config.js"), config.trim());
  await fs.writeFile(path.join(projectDir, "postcss.config.js"), `module.exports = { plugins: { tailwindcss: {}, autoprefixer: {} } };`);
}
'''

with open(MORGAN_ROUTE, "w") as f:
    f.write(CONTENT)

print(f"✅ Written: {MORGAN_ROUTE}")

# Commit and build
os.chdir(BUILDANY_DIR)
os.system("git add src/app/api/morgan-generate/route.ts")
os.system("git commit -m 'fix: overwrite with clean sanitizer'")

print("\n🔨 Building...")
result = os.system("npm run build")

if result == 0:
    print("\n✅ BUILD SUCCESS!")
    os.system("pm2 restart buildany")
    print("🚀 BuildAny restarted!")
else:
    print("\n❌ BUILD FAILED")
    exit(1)
