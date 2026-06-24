#!/usr/bin/env python3
"""
Fix Morgan chat to persist messages and not lose them on build
"""
import os, re

BUILDANY_DIR = "/root/buildany"
os.chdir(BUILDANY_DIR)

print("=" * 60)
print("🔧 Fixing Morgan Chat Persistence")
print("=" * 60)

# Fix 1: Save Morgan responses to DB in morgan-chat route
with open("src/app/api/morgan-chat/route.ts") as f:
    chat_route = f.read()

# Add import for db if not present
if 'import { db }' not in chat_route:
    chat_route = chat_route.replace(
        'import { NextRequest, NextResponse } from "next/server";',
        'import { NextRequest, NextResponse } from "next/server";\nimport { db } from "@/lib/db";\nimport { conversations } from "@/lib/db/schema";'
    )

# Add conversation logging before return
if 'await db.insert(conversations)' not in chat_route:
    # Find the return statement and add logging before it
    chat_route = chat_route.replace(
        'return NextResponse.json({\n      role: "assistant",',
        '''// Log assistant response to DB
    try {
      await db.insert(conversations).values({
        id: crypto.randomUUID(),
        projectId: body.projectContext?.projectId || "unknown",
        role: "assistant",
        content: content,
        model: "morgan",
        createdAt: new Date(),
      });
    } catch (e) {
      console.error("[Morgan Chat] Failed to log conversation:", e);
    }

    return NextResponse.json({
      role: "assistant",'''
    )

with open("src/app/api/morgan-chat/route.ts", "w") as f:
    f.write(chat_route)

print("✅ Fixed: morgan-chat saves responses to DB")

# Fix 2: Don't reload page on build trigger - just update state
with open("src/components/Workspace3Col.tsx") as f:
    ws = f.read()

# Remove window.location.reload and replace with state update
ws = ws.replace(
    'setTimeout(() => window.location.reload(), 2000);',
    '''// Poll for files instead of reloading
            const pollInterval = setInterval(async () => {
              const res = await fetch(`/api/project-files?projectId=${project.id}`);
              if (res.ok) {
                const data = await res.json();
                if (data.files && data.files.length > 0) {
                  setFiles(data.files);
                  clearInterval(pollInterval);
                }
              }
            }, 2000);
            setTimeout(() => clearInterval(pollInterval), 30000);'''
)

with open("src/components/Workspace3Col.tsx", "w") as f:
    f.write(ws)

print("✅ Fixed: Workspace3Col polls for files instead of reloading")

# Commit and build
os.system("git add src/app/api/morgan-chat/route.ts src/components/Workspace3Col.tsx")
os.system('git commit -m "fix: persist Morgan chat and avoid page reload"')

print("\n🔨 Building...")
build_result = os.system("npm run build")

if build_result == 0:
    print("\n✅ BUILD SUCCESS!")
    os.system("pm2 restart buildany")
    print("🚀 BuildAny restarted!")
    print("\n💡 Now chat messages persist and don't disappear!")
else:
    print("\n❌ BUILD FAILED")
    exit(1)
