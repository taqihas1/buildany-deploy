#!/usr/bin/env python3
"""
Fix: Auto-send prompt without requiring user to say "hi" first

Root cause: project-chat-init created the conversation in DB, so when
Workspace3Col loaded, hasPrompt was true and auto-send was skipped.
But Morgan never saw the prompt because it was only in DB, not sent to API.

Fix: 
1. Remove conversation creation from project-chat-init (client will send it)
2. Simplify auto-send to always fire when URL has prompt (no hasPrompt check)
"""
import os, subprocess

# Fix 1: project-chat-init - remove conversation creation
PROJECT_INIT = "/root/buildany/src/app/api/project-chat-init/route.ts"
with open(PROJECT_INIT, 'r') as f:
    content = f.read()

# Remove conversation import and creation
old_import = 'import { projects, conversations } from "@/lib/db/schema";'
new_import = 'import { projects } from "@/lib/db/schema";'
if old_import in content:
    content = content.replace(old_import, new_import)
    print("✅ Removed conversations import from project-chat-init")

old_conversation = '''    // 3. Log user prompt as conversation
    await db.insert(conversations).values({
      id: crypto.randomUUID(),
      projectId,
      role: "user",
      content: prompt,
      model: "user",
      createdAt: new Date(),
    });

    return NextResponse.json({'''

new_conversation = '''    // NOTE: We do NOT create the conversation here. The client will auto-send
    // the prompt to Morgan, which will create both the user message and the
    // assistant response in the DB. This ensures Morgan actually sees the prompt.

    return NextResponse.json({'''

if old_conversation in content:
    content = content.replace(old_conversation, new_conversation)
    print("✅ Removed conversation creation from project-chat-init")
else:
    print("⚠️ Conversation creation already removed or different format")

with open(PROJECT_INIT, 'w') as f:
    f.write(content)

# Fix 2: Workspace3Col - remove hasPrompt check
WORKSPACE = "/root/buildany/src/components/Workspace3Col.tsx"
with open(WORKSPACE, 'r') as f:
    content = f.read()

old_auto_send = '''  // Auto-send prompt from URL on first load (chat-first flow)
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

new_auto_send = '''  // Auto-send prompt from URL on first load (chat-first flow)
  useEffect(() => {
    if (promptFromUrl && !autoSentRef.current) {
      autoSentRef.current = true;
      // Small delay to ensure component is fully mounted
      const timer = setTimeout(() => {
        sendMessageToMorgan(promptFromUrl);
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [promptFromUrl]);'''

if old_auto_send in content:
    content = content.replace(old_auto_send, new_auto_send)
    print("✅ Removed hasPrompt check from auto-send")
else:
    print("⚠️ Auto-send already fixed or different format")

with open(WORKSPACE, 'w') as f:
    f.write(content)

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
