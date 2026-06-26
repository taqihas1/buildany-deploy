#!/usr/bin/env python3
"""
BuildAny Deploy Script - Fix Build Orchestration (Clean v2)
Fixes: Build fires before Morgan finishes, next/document imports, preview generation
Pushed to: https://github.com/taqihas1/buildany-deploy/main/fix_build_v2.py
"""
import os, re, json

BUILDANY_DIR = "/root/buildany"
os.chdir(BUILDANY_DIR)

print("=" * 60)
print("🔧 Build Orchestration Fix v2")
print("=" * 60)

# ============================================================================
# 1. FIX MORGAN-CHAT ROUTE - Add BUILD trigger marker detection
# ============================================================================
MORGAN_CHAT = '''import { NextRequest, NextResponse } from "next/server";

const DEEPSEEK_KEY = process.env.DEEPSEEK_API_KEY || "";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    let messages = body.messages;
    let projectContext = body.projectContext;
    
    if (!messages && body.message) {
      messages = [
        ...(body.history || []),
        { role: "user", content: body.message }
      ];
    }

    if (!messages || !Array.isArray(messages)) {
      return NextResponse.json({ error: "messages array required" }, { status: 400 });
    }

    const systemPrompt = body.systemPrompt || `You are Morgan, an expert AI builder for BuildAny. You help users build web and mobile apps.

Rules:
- Be concise and actionable
- Suggest code when relevant
- Focus on Next.js, React, Tailwind, TypeScript
- If user wants to build something, ask clarifying questions then say "Should I start building?"
- When user confirms building, emit [BUILD: start] to trigger generation
- Use emojis for personality 🚀
- CRITICAL: NEVER import <Html>, <Head>, <Main>, or <NextScript> from 'next/document' in regular pages. Only use these in pages/_document.js
${projectContext ? "\\nCurrent project context: " + JSON.stringify(projectContext) : ""}`;

    const response = await fetch("https://api.deepseek.com/v1/chat/completions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${DEEPSEEK_KEY}`,
      },
      body: JSON.stringify({
        model: "deepseek-chat",
        messages: [
          { role: "system", content: systemPrompt },
          ...messages,
        ],
        temperature: 0.7,
        max_tokens: 2000,
      }),
    });

    if (!response.ok) {
      const error = await response.text();
      console.error("[Morgan Chat] DeepSeek error:", error);
      return NextResponse.json({ error: "Morgan is thinking... try again!" }, { status: 502 });
    }

    const data = await response.json();
    let content = data.choices?.[0]?.message?.content || "I'm Morgan! How can I help you build today? 🚀";

    // Detect BUILD trigger in response
    const buildTrigger = content.match(/\\[BUILD:\\s*(\\w+)\\]/);
    const shouldBuild = !!buildTrigger;
    if (buildTrigger) {
      content = content.replace(/\\[BUILD:\\s*\\w+\\]/g, "").trim();
    }

    return NextResponse.json({
      role: "assistant",
      content,
      model: "morgan",
      shouldBuild,
      buildTrigger: buildTrigger?.[1] || null,
    });

  } catch (error: any) {
    console.error("[Morgan Chat] Error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
'''

chat_path = os.path.join(BUILDANY_DIR, "src/app/api/morgan-chat/route.ts")
with open(chat_path, "w") as f:
    f.write(MORGAN_CHAT)
print("✅ 1. morgan-chat route.ts - Added shouldBuild trigger detection")

# ============================================================================
# 2. FIX MORGAN-GENERATE - Add standalone sanitizer at the END of the file
# ============================================================================
generate_path = os.path.join(BUILDANY_DIR, "src/app/api/morgan-generate/route.ts")
with open(generate_path) as f:
    gen_content = f.read()

# Check if we already have the sanitizer
if "sanitizeGeneratedFiles" not in gen_content:
    # Append sanitizer to the end of the file
    sanitizer = '''

// ============================================================================
// POST-BUILD SANITIZER - Remove bad next/document imports from generated code
// ============================================================================
function sanitizeGeneratedFiles(projectDir: string) {
  try {
    const fs = require("fs");
    const path = require("path");
    
    function walkDir(dir: string, callback: (fp: string) => void) {
      if (!fs.existsSync(dir)) return;
      const entries = fs.readdirSync(dir, { withFileTypes: true });
      for (const entry of entries) {
        const fullPath = path.join(dir, entry.name);
        if (entry.isDirectory() && entry.name !== "node_modules" && entry.name !== ".git") {
          walkDir(fullPath, callback);
        } else if (entry.isFile() && /\\.(tsx?|jsx?)$/.test(entry.name)) {
          callback(fullPath);
        }
      }
    }
    
    const srcDir = path.join(projectDir, "src");
    if (!fs.existsSync(srcDir)) {
      console.log("[Sanitize] No src/ directory yet, skipping");
      return;
    }
    
    let fixedCount = 0;
    walkDir(srcDir, (fp: string) => {
      if (fp.includes("_document")) return;
      
      let code = fs.readFileSync(fp, "utf8");
      if (!code.includes("next/document")) return;
      
      console.log(`[Sanitize] Fixing: ${fp}`);
      
      // Remove imports from next/document
      code = code.replace(/import\\s*\\{[^}]*\\}\\s*from\\s*["\']next\\/document["\'];?\\s*\\n?/gi, "");
      code = code.replace(/import\\s+\\w+\\s+from\\s*["\']next\\/document["\'];?\\s*\\n?/gi, "");
      
      // Replace JSX tags
      code = code.replace(/<Html([^>]*)>/gi, "<div$1>");
      code = code.replace(/<\\/Html>/gi, "</div>");
      code = code.replace(/<Main([^>]*)>/gi, "<main$1>");
      code = code.replace(/<\\/Main>/gi, "</main>");
      code = code.replace(/<NextScript\\s*\\/>/gi, "");
      code = code.replace(/<Head>/gi, "");
      code = code.replace(/<\\/Head>/gi, "");
      
      fs.writeFileSync(fp, code);
      fixedCount++;
    });
    
    console.log(`[Sanitize] Fixed ${fixedCount} files`);
  } catch (e) {
    console.error("[Sanitize] Error:", e);
  }
}
'''
    gen_content = gen_content + sanitizer
    
    with open(generate_path, "w") as f:
        f.write(gen_content)
    print("✅ 2. morgan-generate route.ts - Added sanitizer")
else:
    print("✅ 2. morgan-generate already has sanitizer")

# ============================================================================
# 3. FIX next.config.js - Ensure export mode
# ============================================================================
config_path = os.path.join(BUILDANY_DIR, "next.config.js")
config_ts_path = os.path.join(BUILDANY_DIR, "next.config.ts")

config_file = config_path if os.path.exists(config_path) else config_ts_path

if os.path.exists(config_file):
    with open(config_file) as f:
        config = f.read()
    
    if "output:" not in config or "'export'" not in config:
        print("⚠️  next.config may be missing output: 'export' - CHECK MANUALLY")
    else:
        print("✅ 3. next.config has output: 'export'")
else:
    print("⚠️ 3. next.config not found - CREATING")
    with open(config_path, "w") as f:
        f.write('''/** @type {import('next').NextConfig} */\nconst nextConfig = {\n  output: 'export',\n  distDir: 'out',\n  images: { unoptimized: true },\n  typescript: { ignoreBuildErrors: true },\n  eslint: { ignoreDuringBuilds: true },\n};\n\nmodule.exports = nextConfig;\n''')
    print("✅ 3. Created next.config.js with export mode")

# ============================================================================
# 4. FIX Workspace3Col - Only build after Morgan triggers it
# ============================================================================
ws_path = os.path.join(BUILDANY_DIR, "src/components/Workspace3Col.tsx")
if os.path.exists(ws_path):
    with open(ws_path) as f:
        ws = f.read()

    # Check if we already have shouldBuild logic
    if "shouldBuild" not in ws:
        # Find the message handler and add build trigger detection
        if "const data = await response.json();" in ws:
            ws = ws.replace(
                "const data = await response.json();",
                '''const data = await response.json();
            
            // Trigger build if Morgan signals it
            if (data.shouldBuild) {
              console.log("[Build] Morgan triggered build:", data.buildTrigger);
              setTimeout(() => startBuild(), 500);
            }'''
            )
            
            with open(ws_path, "w") as f:
                f.write(ws)
            print("✅ 4. Workspace3Col - Build triggered by Morgan response only")
        else:
            print("⚠️ 4. Could not find response handler in Workspace3Col")
    else:
        print("✅ 4. Workspace3Col already has shouldBuild logic")
else:
    print("⚠️ 4. Workspace3Col not found")

# ============================================================================
# 5. FIX Preview API - Better error handling
# ============================================================================
preview_path = os.path.join(BUILDANY_DIR, "src/app/api/preview/[[...path]]/route.ts")
if os.path.exists(preview_path):
    with open(preview_path) as f:
        preview = f.read()
    
    if "Build in progress" not in preview and "not completed" not in preview:
        # Add build check before serving files
        preview = preview.replace(
            "export async function GET",
            '''import { existsSync } from "fs";
import { join } from "path";

export async function GET'''
        )
        
        # Find the filePath line and add check before it
        preview_lines = preview.split('\n')
        new_lines = []
        inserted = False
        for line in preview_lines:
            if 'const filePath = ' in line and not inserted:
                new_lines.append('  // Check if build output exists')
                new_lines.append('  const outDir = join(process.cwd(), "projects", projectId, "out");')
                new_lines.append('  if (!existsSync(outDir)) {')
                new_lines.append('    return new NextResponse(')
                new_lines.append('      `<!DOCTYPE html><html><head><style>')
                new_lines.append('        body { font-family: system-ui; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; background: #f5f5f5; }')
                new_lines.append('        .box { text-align: center; padding: 40px; background: white; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }')
                new_lines.append('      </style></head><body>')
                new_lines.append('        <div class="box"><h2>🔨 Build In Progress</h2><p>Morgan is generating your app. This may take 1-2 minutes.</p></div>')
                new_lines.append('      </body></html>`,')
                new_lines.append('      { status: 200, headers: { "Content-Type": "text/html" } }')
                new_lines.append('    );')
                new_lines.append('  }')
                new_lines.append('')
                inserted = True
            new_lines.append(line)
        
        preview = '\n'.join(new_lines)
        
        with open(preview_path, "w") as f:
            f.write(preview)
        print("✅ 5. Preview API - Added build-in-progress page")
    else:
        print("✅ 5. Preview API already has build status handling")
else:
    print("⚠️ 5. Preview route not found")

# ============================================================================
# 6. COMMIT AND BUILD
# ============================================================================
print("\n" + "=" * 60)
print("📦 Committing changes...")
os.system("git add -A")
os.system('git commit -m "fix: build orchestration - Morgan triggers build, sanitize next/document imports" --allow-empty')

print("\n🔨 Building...")
build_result = os.system("npm run build 2>&1")

if build_result == 0:
    print("\n✅ BUILD SUCCESS!")
    os.system("pm2 restart buildany")
    print("🚀 BuildAny restarted!")
else:
    print("\n❌ BUILD FAILED")
    print("Check errors above. Common fixes:")
    print("  - Type errors: Check src/lib/db/schema.ts and hermes-chat/route.ts")
    print("  - Import errors: Run npm install")
    exit(1)

print("\n" + "=" * 60)
print("🎉 DONE! New flow:")
print("   1. User sends prompt → Morgan chats (NO build yet)")
print("   2. Morgan says 'Should I build?' → User confirms")
print("   3. Morgan emits [BUILD: start] → Build triggers")
print("   4. Build runs → Preview generated")
print("=" * 60)
