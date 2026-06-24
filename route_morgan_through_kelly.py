#!/usr/bin/env python3
"""
Route Morgan Chat through Kelly (Hermes) so Morgan can use skills!
"""
import os

BUILDANY_DIR = "/root/buildany"
os.chdir(BUILDANY_DIR)

print("=" * 60)
print("🔗 Routing Morgan → Kelly (Skills Enabled)")
print("=" * 60)

NEW_ROUTE = '''import { NextRequest, NextResponse } from "next/server";

const KELLY_URL = process.env.HERMES_URL || "http://127.0.0.1:8642/v1/chat/completions";
const KELLY_KEY = process.env.HERMES_API_KEY || "";

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

    // Morgan system prompt with skill awareness
    const systemPrompt = body.systemPrompt || `You are Morgan, an expert AI builder for BuildAny. You help users build web and mobile apps.

You have access to 37+ skills through Kelly (Hermes Agent):
- code-review-and-quality: Review code for bugs and best practices
- planning-and-task-breakdown: Break projects into tasks
- test-driven-development: Write tests first
- debugging-and-error-recovery: Fix errors systematically
- frontend-ui-engineering: Build beautiful UIs
- performance-optimization: Speed up apps
- security-and-hardening: Secure applications
- And 30 more...

Rules:
- Be concise and actionable
- Suggest code when relevant
- Focus on Next.js, React, Tailwind, TypeScript
- If user wants to build something, ask clarifying questions then say "Should I start building?"
- When user confirms, emit [BUILD: {"appType": "web"}] to trigger generation
- Use emojis for personality 🚀
- CRITICAL: NEVER import <Html>, <Head>, <Main>, or <NextScript> from 'next/document' in regular pages. Only use these in pages/_document.js
${contextStr ? "\\nCurrent project context: " + contextStr : ""}`;

    console.log("[Morgan→Kelly] Routing to Hermes with", messages.length, "messages");

    // Call Kelly (Hermes) instead of DeepSeek directly
    const response = await fetch(KELLY_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${KELLY_KEY}`,
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
      console.error("[Morgan→Kelly] Hermes error:", error);
      // Fallback to direct DeepSeek if Kelly fails
      return fallbackToDeepSeek(messages, systemPrompt);
    }

    const data = await response.json();
    const content = data.choices?.[0]?.message?.content || "I'm Morgan! How can I help you build today? 🚀";
    
    console.log("[Morgan→Kelly] Response:", content.substring(0, 100));

    return NextResponse.json({
      role: "assistant",
      content,
      model: "morgan-kelly",
    });

  } catch (error: any) {
    console.error("[Morgan→Kelly] Error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

// Fallback to DeepSeek if Kelly is down
async function fallbackToDeepSeek(messages: any[], systemPrompt: string) {
  const DEEPSEEK_KEY = process.env.DEEPSEEK_API_KEY || "";
  
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

  const data = await response.json();
  const content = data.choices?.[0]?.message?.content || "I'm Morgan! How can I help you build today? 🚀";

  return NextResponse.json({
    role: "assistant",
    content,
    model: "morgan",
  });
}
'''

with open("src/app/api/morgan-chat/route.ts", "w") as f:
    f.write(NEW_ROUTE)

print("✅ Morgan now routes through Kelly (Hermes)!")
print("✅ Fallback to DeepSeek if Kelly is down")
print("✅ Morgan has access to 37+ skills")

# Commit and build
os.system("git add src/app/api/morgan-chat/route.ts")
os.system('git commit -m "feat: route Morgan through Kelly for skills access"')

print("\n🔨 Building...")
build_result = os.system("npm run build")

if build_result == 0:
    print("\n✅ BUILD SUCCESS!")
    os.system("pm2 restart buildany")
    print("🚀 BuildAny restarted!")
    print("\n🎯 Test Morgan chat now — it will use Kelly's skills!")
else:
    print("\n❌ BUILD FAILED")
    exit(1)
