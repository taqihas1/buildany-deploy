# BuildAny VPS Setup Guide
## Unified Kelly Architecture + GitHub + Cloudflare Connectors

### ⚡ Quick Start (Copy-paste ready)

```bash
# 1. SSH to your VPS
ssh root@your-vps-ip

# 2. Set environment variables (DO THIS FIRST)
export GITHUB_TOKEN=ghp_your_new_token_here
export CLOUDFLARE_API_TOKEN=your_cloudflare_token_here
export DEEPSEEK_API_KEY=sk_your_new_deepseek_key_here
export CF_ACCOUNT_ID=your_cloudflare_account_id

# 3. Download and run deploy script
cd /root
curl -sL https://raw.githubusercontent.com/taqihas1/buildany-deploy/main/deploy_kelly_v2.py -o deploy_kelly_v2.py
python3 deploy_kelly_v2.py

# 4. Verify it's running
curl http://127.0.0.1:3000/api/kelly
# Should return: {"status":"ok"} or similar
```

---

### 🔑 Step 1: Get Your Tokens

#### GitHub Token
1. Go to https://github.com/settings/tokens
2. Click **Generate new token (classic)**
3. Select scopes: ✅ `repo`, ✅ `workflow`
4. Generate and **COPY immediately** (you won't see it again)
5. **NEVER paste this in chat** — save directly on VPS

#### Cloudflare API Token
1. Go to https://dash.cloudflare.com/profile/api-tokens
2. Click **Create Token**
3. Use template: **Edit zone DNS**
4. Or custom token with:
   - Zone:Read
   - DNS:Edit
   - Page Rules:Edit
   - Cache Purge:Edit
5. Copy token (save on VPS only)

#### DeepSeek API Key
1. Go to https://platform.deepseek.com/
2. Create new API key
3. Copy and save on VPS only

#### Cloudflare Account ID
1. Go to https://dash.cloudflare.com/
2. Any domain → right sidebar shows **Account ID**
3. Copy it

---

### 🚀 Step 2: Deploy

```bash
# SSH to VPS
ssh root@your-vps-ip

# Create persistent env file
sudo tee /etc/buildany.env << 'EOF'
GITHUB_TOKEN=ghp_xxx
CLOUDFLARE_API_TOKEN=xxx
DEEPSEEK_API_KEY=sk-xxx
CF_ACCOUNT_ID=xxx
EOF
sudo chmod 600 /etc/buildany.env

# Source it
source /etc/buildany.env

# Run deploy
cd /root
curl -sL https://raw.githubusercontent.com/taqihas1/buildany-deploy/main/deploy_kelly_v2.py | python3 -
```

---

### ✅ Step 3: Verify

```bash
# Test Kelly endpoint
curl -X POST http://127.0.0.1:3000/api/kelly \
  -H "Content-Type: application/json" \
  -d '{"message": "hello kelly"}'

# Test GitHub tool
curl -X POST http://127.0.0.1:3000/api/github-tool \
  -H "Content-Type: application/json" \
  -d '{"action": "list_repos"}'

# Test Cloudflare tool
curl -X POST http://127.0.0.1:3000/api/cloudflare-tool \
  -H "Content-Type: application/json" \
  -d '{"action": "list_zones"}'
```

---

### 🧪 Step 4: Test via Browser

Open: `http://your-vps-ip:3000/kelly-test`

This page lets you:
- Send messages to Kelly
- Test individual tools
- See raw JSON responses

---

### 🔒 Security Checklist

| Check | Status |
|-------|--------|
| `.env.local` created with real tokens | ⬜ |
| `.env.local` is in `.gitignore` | ✅ (already configured) |
| Old exposed tokens deleted from GitHub | ⬜ |
| Tokens never shared in chat/email | ⬜ |
| VPS firewall allows only necessary ports | ⬜ |
| PM2 running with `--name buildany` | ⬜ |

---

### 🛠️ Troubleshooting

#### "GITHUB_TOKEN not configured"
```bash
# Check it's set
env | grep GITHUB

# If empty, re-export:
export GITHUB_TOKEN=ghp_xxx

# For persistence, add to ~/.bashrc:
echo 'export GITHUB_TOKEN=ghp_xxx' >> ~/.bashrc
```

#### "Build failed"
```bash
# Clear and rebuild
cd /root/buildany
rm -rf .next node_modules/.cache
npm install
npm run build
pm2 restart buildany
```

#### "Port 3000 already in use"
```bash
# Find what's using it
lsof -i :3000

# Kill it
kill -9 $(lsof -t -i:3000)

# Or use different port
PORT=3001 npm start
```

#### "Cloudflare deploy failed"
- Verify `CF_ACCOUNT_ID` is set
- Check token has `Cloudflare Pages:Edit` permission
- Verify project name exists in Cloudflare Pages

---

### 📁 File Structure After Deploy

```
/root/buildany/
├── src/
│   ├── app/
│   │   ├── api/
│   │   │   ├── kelly/              ← NEW: Unified endpoint
│   │   │   │   └── route.ts
│   │   │   ├── github-tool/        ← NEW: GitHub connector
│   │   │   │   └── route.ts
│   │   │   ├── cloudflare-tool/    ← NEW: Cloudflare connector
│   │   │   │   └── route.ts
│   │   │   ├── orchestrate/        ← DEPRECATED
│   │   │   ├── hermes-chat/        ← DEPRECATED
│   │   │   └── ...
│   │   └── kelly-test/             ← NEW: Test page
│   │       └── page.tsx
│   └── lib/
│       ├── kelly-tools.ts          ← NEW: 15 tools
│       └── kelly-system.ts         ← NEW: Prompt builder
├── .env.local                      ← NEW: Your secrets
├── .env                            ← NEW: Backup of secrets
└── ...
```

---

### 🎯 What's Different Now

**Before:**
- Kelly plans → Morgan generates (broken handoffs)
- Manual GitHub pushes
- Manual Cloudflare deploys
- Exposed tokens in code

**After:**
- Kelly does everything (15 tools)
- One API call: `create → generate → build → push → deploy`
- All tokens in `.env.local` (never committed)
- Full autonomy

---

**Date:** 2026-07-25
**Version:** Kelly Unified v2
**Questions?** The test page at `/kelly-test` will show you everything.
