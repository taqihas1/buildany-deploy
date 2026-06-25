#!/usr/bin/env python3
"""
Fix: Auto-send + Morgan code generation completeness
1. Auto-send prompt from URL without requiring user to say "hi" first
2. Morgan generates ALL components inline (no broken imports)
"""
import os, subprocess

# Fix 1: Workspace3Col auto-send
WORKSPACE_FILE = "/root/buildany/src/components/Workspace3Col.tsx"
with open(WORKSPACE_FILE, 'r') as f:
    content = f.read()

old_auto_send = '''  // Auto-send prompt from URL on first load (chat-first flow)
  useEffect(() => {
    if (promptFromUrl && !autoSentRef.current && chatMessages.length > 0) {
      autoSentRef.current = true;
      // Check if the prompt is already in chat messages (from DB)
      const hasPrompt = chatMessages.some(m => m.role === 'user' && m.content === promptFromUrl);
      if (!hasPrompt) {
        sendMessageToMorgan(promptFromUrl);
      }
    }
  }, [promptFromUrl, chatMessages]);'''

new_auto_send = '''  // Auto-send prompt from URL on first load (chat-first flow)
  useEffect(() => {
    if (promptFromUrl && !autoSentRef.current) {
      autoSentRef.current = true;
      // Small delay to ensure component is fully mounted
      const timer = setTimeout(() => {
        // Check if the prompt is already in chat messages (from DB)
        const hasPrompt = chatMessages.some(m => m.role === 'user' && m.content === promptFromUrl);
        if (!hasPrompt) {
          sendMessageToMorgan(promptFromUrl);
        }
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [promptFromUrl]);'''

if old_auto_send in content:
    content = content.replace(old_auto_send, new_auto_send)
    print("✅ Fixed auto-send (removed chatMessages.length > 0 guard)")
else:
    print("⚠️ Auto-send already fixed or different format")

with open(WORKSPACE_FILE, 'w') as f:
    f.write(content)

# Fix 2: Morgan system prompt - generate all components inline
MORGAN_CHAT = "/root/buildany/src/app/api/morgan-chat/route.ts"
morgan_content = '''import { NextRequest, NextResponse } from "next/server";

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

    const systemPrompt = body.systemPrompt || `You are Morgan, an expert AI builder for BuildAny. You build apps instantly.

YOUR FLOW (MANDATORY):
1. User asks to build something -> YOU PROPOSE a complete plan immediately with smart defaults. DO NOT ask questions.
2. Ask: "Should I start building? 🚀"
3. User says yes -> Respond with ONLY: [BUILD: {\\"appType\\": \\"web\\"}] and a brief "Let\\'s build! 🚀"
4. User says no or wants changes -> Adjust and re-propose

SMART DEFAULTS:
- Web apps: Next.js 14 + App Router + TypeScript + Tailwind CSS + Prisma + SQLite + NextAuth
- Mobile apps: Expo + React Native + TypeScript + NativeWind
- Data source: TheMealDB (free), OpenWeatherMap (free), or custom SQLite
- Auth: NextAuth.js with Google/GitHub OAuth
- Design: Clean, modern, responsive
- Image storage: Cloudinary (free tier) or local storage

CODE GENERATION RULES (CRITICAL):
- Generate ALL components inline in each page file. DO NOT create import statements for components you don\\'t also generate.
- NEVER use @/components/ imports unless you also generate those component files
- NEVER import <Html>, <Head>, <Main>, <NextScript> from \\'next/document\\' in pages
- Each page must be self-contained with all its JSX inline
- If you need a shared component, define it in the same file or generate it as a separate file
- ALWAYS generate a complete working app — no missing files, no broken imports

RULES:
- Be concise, warm, and actionable
- Use emojis for personality 🚀
- NEVER ask what tech stack they want — YOU DECIDE based on best practices
- NEVER ask about data sources — YOU pick the best free option
- NEVER ask about design preferences — YOU choose a clean modern look
- If user says "yes", "build", "let\\'s go", "go ahead", "start building" -> IMMEDIATELY emit [BUILD: {\\"appType\\": \\"web\\"}] then build
` + (projectContext ? "\\nCurrent project context: " + projectContext : "");

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
    const content = data.choices?.[0]?.message?.content || "I\\'m Morgan! How can I help you build today? 🚀";

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

with open(MORGAN_CHAT, 'w') as f:
    f.write(morgan_content)
print("✅ Updated Morgan system prompt (inline components rule)")

# Build
print("Building...")
os.chdir("/root/buildany")
result = subprocess.run(["npm", "run", "build"], capture_output=True, text=True)
print(result.stdout[-1500:] if len(result.stdout) > 1500 else result.stdout)
if result.returncode != 0:
    print("STDERR:", result.stderr[-500:] if len(result.stderr) > 500 else result.stderr)
    print("❌ Build failed")
else:
    print("✅ Build successful!")
    subprocess.run(["pm2", "restart", "buildany"], capture_output=True)
    print("✅ Restarted buildany")
