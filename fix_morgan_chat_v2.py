#!/usr/bin/env python3
"""
Fix Morgan Chat - Properly handle projectContext and add better error handling
"""
import os, re

BUILDANY_DIR = "/root/buildany"
os.chdir(BUILDANY_DIR)

print("=" * 60)
print("🔧 Fixing Morgan Chat API")
print("=" * 60)

# Read current morgan-chat route
with open("src/app/api/morgan-chat/route.ts") as f:
    content = f.read()

# Fix: projectContext should be stringified if it's an object
# Also add better error handling
NEW_ROUTE = '''import { NextRequest, NextResponse } from "next/server";

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

    // Format projectContext for the prompt
    let contextStr = "";
    if (projectContext) {
      if (typeof projectContext === "string") {
        contextStr = projectContext;
      } else {
        contextStr = JSON.stringify(projectContext);
      }
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
${contextStr ? "\\nCurrent project context: " + contextStr : ""}`;

    console.log("[Morgan Chat] Calling DeepSeek with", messages.length, "messages");

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
    
    console.log("[Morgan Chat] Response:", content.substring(0, 100));

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

with open("src/app/api/morgan-chat/route.ts", "w") as f:
    f.write(NEW_ROUTE)

print("✅ Fixed morgan-chat/route.ts")

# Commit and build
os.system("git add src/app/api/morgan-chat/route.ts")
os.system('git commit -m "fix: morgan chat projectContext handling and logging"')

print("\n🔨 Building...")
build_result = os.system("npm run build")

if build_result == 0:
    print("\n✅ BUILD SUCCESS!")
    os.system("pm2 restart buildany")
    print("🚀 BuildAny restarted!")
    print("\n💡 Now test Morgan chat again. Check PM2 logs if still no response:")
    print("   pm2 logs buildany --lines 50")
else:
    print("\n❌ BUILD FAILED")
    exit(1)
