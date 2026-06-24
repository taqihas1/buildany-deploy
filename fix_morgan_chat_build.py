#!/usr/bin/env python3
"""
BuildAny Deploy Script - Fix Morgan Chat Build Errors
Pushed to: https://github.com/taqihas1/buildany-deploy/main/fix_morgan_chat_build.py
"""
import os, re

BUILDANY_DIR = "/root/buildany"
os.chdir(BUILDANY_DIR)

print("=" * 60)
print("🔧 BuildAny Morgan Chat Fix")
print("=" * 60)

# 1. Fix morgan-chat/route.ts - write clean version
MORGAN_CHAT = '''import { NextRequest, NextResponse } from "next/server";

const DEEPSEEK_KEY = process.env.DEEPSEEK_API_KEY || "";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    let messages = body.messages;
    let projectContext = body.projectContext;
    
    // Support old format: { message, history, systemPrompt }
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
- When user confirms, emit [BUILD: {"appType": "web"}] to trigger generation
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
    const content = data.choices?.[0]?.message?.content || "I'm Morgan! How can I help you build today? 🚀";

    return NextResponse.json({
      role: "assistant",
      content,
      model: "morgan",
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
print(f"✅ Fixed: {chat_path}")

# 2. Check morgan-generate for duplicate imports
generate_path = os.path.join(BUILDANY_DIR, "src/app/api/morgan-generate/route.ts")
with open(generate_path) as f:
    gen_content = f.read()

# Count occurrences of key imports
if gen_content.count("import { execSync }") > 1:
    print(f"⚠️  Warning: {generate_path} has duplicate imports - may need manual fix")
else:
    print(f"✅ Checked: {generate_path} (no duplicate imports)")

# 3. Check Workspace3Col for import issues
workspace_path = os.path.join(BUILDANY_DIR, "src/components/Workspace3Col.tsx")
with open(workspace_path) as f:
    ws_content = f.read()

if ws_content.count("useSearchParams") > 1:
    print(f"⚠️  Warning: {workspace_path} may have duplicate useSearchParams")
else:
    print(f"✅ Checked: {workspace_path}")

# 4. Git add and commit
os.system("git add src/app/api/morgan-chat/route.ts")
os.system('git commit -m "fix: clean morgan-chat route.ts" --allow-empty')

# 5. Build
print("\n🔨 Building...")
build_result = os.system("npm run build")

if build_result == 0:
    print("\n✅ BUILD SUCCESS!")
    os.system("pm2 restart buildany")
    print("🚀 BuildAny restarted!")
else:
    print("\n❌ BUILD FAILED - check errors above")
    exit(1)
