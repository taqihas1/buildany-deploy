#!/usr/bin/env python3
"""
Make Morgan magical: propose + build on yes, no questions
"""
import os, subprocess

BUILDANY_DIR = "/root/buildany"
MORGAN_CHAT = os.path.join(BUILDANY_DIR, "src/app/api/morgan-chat/route.ts")
MORGAN_GENERATE = os.path.join(BUILDANY_DIR, "src/app/api/morgan-generate/route.ts")

print("=" * 60)
print("✨ Making Morgan MAGICAL - Propose + Build on Yes")
print("=" * 60)

# 1. Update Morgan chat system prompt
print("\n1. Updating Morgan chat system prompt...")

with open(MORGAN_CHAT) as f:
    content = f.read()

old_system = """const systemPrompt = body.systemPrompt || `You are Morgan, an expert AI builder for BuildAny. You help users build web and mobile apps.

Rules:
- Be concise and actionable
- Suggest code when relevant
- Focus on Next.js, React, Tailwind, TypeScript
- If user wants to build something, suggest they click the Build button
- Use emojis for personality 🚀
- CRITICAL: NEVER import <Html>, <Head>, <Main>, or <NextScript> from 'next/document' in regular pages. Only use these in pages/_document.js
${projectContext ? "\nCurrent project context: " + projectContext : ""}`;"""

new_system = """const systemPrompt = body.systemPrompt || `You are Morgan, an expert AI builder for BuildAny. You build apps instantly.

YOUR FLOW (MANDATORY):
1. User asks to build something → YOU PROPOSE a complete plan immediately with smart defaults. DO NOT ask questions.
2. Ask: "Should I start building? 🚀"
3. User says yes → Respond with ONLY: [BUILD: {"appType": "web"}] and a brief "Let's build! 🚀"
4. User says no or wants changes → Adjust and re-propose

SMART DEFAULTS (use these unless user specifies otherwise):
- Web apps: Next.js 14 + App Router + TypeScript + Tailwind CSS + Prisma + SQLite + NextAuth
- Mobile apps: Expo + React Native + TypeScript + NativeWind
- Data source: TheMealDB (free), OpenWeatherMap (free), or custom SQLite
- Auth: NextAuth.js with Google/GitHub OAuth
- Design: Clean, modern, responsive
- Image storage: Cloudinary (free tier) or local storage

RULES:
- Be concise, warm, and actionable
- Use emojis for personality 🚀
- NEVER ask what tech stack they want — YOU DECIDE based on best practices
- NEVER ask about data sources — YOU pick the best free option
- NEVER ask about design preferences — YOU choose a clean modern look
- NEVER import <Html>, <Head>, <Main>, <NextScript> from 'next/document' in pages
- If user says "yes", "build", "let's go", "go ahead", "start building" → IMMEDIATELY emit [BUILD: {"appType": "web"}] then build
${projectContext ? "\nCurrent project context: " + projectContext : ""}`;"""

if old_system in content:
    content = content.replace(old_system, new_system)
    print("   ✅ System prompt updated")
else:
    # Try a simpler replacement
    if "You are Morgan, an expert AI builder" in content:
        # Find the system prompt section and replace it
        import re
        pattern = r'const systemPrompt = body\.systemPrompt \|\| `[^`]+`;'
        content = re.sub(pattern, new_system, content, flags=re.DOTALL)
        print("   ✅ System prompt updated (regex)")
    else:
        print("   ⚠️ Could not find system prompt - checking...")

with open(MORGAN_CHAT, "w") as f:
    f.write(content)

# 2. Fix file path parsing in morgan-generate
print("\n2. Fixing file path parsing...")

with open(MORGAN_GENERATE) as f:
    gen = f.read()

# Fix /* */ in file paths
old_parse = "const filePath = match[1].trim().replace(/^\\/\\//, \"\").trim();"
new_parse = """let filePath = match[1].trim();
      // Strip leading // comment markers
      filePath = filePath.replace(/^\\/\\/\\s*/, "");
      // Strip leading /* comment markers
      filePath = filePath.replace(/^\\/\\*\\s*/, "");
      // Strip trailing */ comment markers
      filePath = filePath.replace(/\\s*\\*\\/$/, "");
      filePath = filePath.trim();"""

if old_parse in gen:
    gen = gen.replace(old_parse, new_parse)
    print("   ✅ File path parsing fixed")
else:
    print("   ⚠️ File path pattern not found - may already be fixed")

with open(MORGAN_GENERATE, "w") as f:
    f.write(gen)

# 3. Commit and build
print("\n3. Committing changes...")
os.chdir(BUILDANY_DIR)

result = subprocess.run(["git", "add", "-A"], capture_output=True, text=True)
result = subprocess.run(["git", "commit", "-m", "feat: Morgan proposes + builds on yes, magical flow ✨"], capture_output=True, text=True)
print(f"   {result.stdout.strip()}")

print("\n4. Building...")
result = subprocess.run(["npm", "run", "build"], capture_output=True, text=True)

if result.returncode == 0:
    print("\n✅ BUILD SUCCESS!")
    
    # Restart PM2
    subprocess.run(["pm2", "restart", "buildany"], capture_output=True)
    print("🚀 BuildAny restarted!")
    
    print("\n" + "=" * 60)
    print("✨ MORGAN IS NOW MAGICAL!")
    print("=" * 60)
    print("\nNew flow:")
    print("1. User: 'Build a recipe app'")
    print("2. Morgan: 'I'll build a recipe app with Next.js 14, Tailwind, TheMealDB API, auth, and favorites. Should I start building? 🚀'")
    print("3. User: 'Yes'")
    print("4. Morgan: '[BUILD: {\"appType\": \"web\"}] Let's build! 🚀'")
    print("5. BUILD STARTS IMMEDIATELY!")
    print("\nNo questions. No back-and-forth. Just MAGIC! ✨")
else:
    print("\n❌ BUILD FAILED")
    print(result.stdout[-1000:])
    print(result.stderr[-500:])
    exit(1)
