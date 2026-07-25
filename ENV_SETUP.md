# How to Set Environment Variables on VPS (Securely)

## Option 1: Quick & Temporary (For Testing)

```bash
# SSH to your VPS
ssh root@your-vps-ip

# Export variables (they'll last until you logout)
export GITHUB_TOKEN=ghp_your_actual_token_here
export CLOUDFLARE_API_TOKEN=your_cloudflare_token_here
export DEEPSEEK_API_KEY=sk-your_deepseek_key_here
export CF_ACCOUNT_ID=your_cloudflare_account_id_here

# Verify they are set
env | grep -E "GITHUB|CLOUDFLARE|DEEPSEEK|CF_ACCOUNT"

# Run deploy
curl -sL https://raw.githubusercontent.com/taqihas1/buildany-deploy/main/deploy_kelly_v2.py | python3 -
```

**Problem:** These disappear when you logout. Not good for production.

---

## Option 2: Persistent (Recommended for Production)

### Step 1: Create a Secure Env File

```bash
# SSH to your VPS
ssh root@your-vps-ip

# Create the env file with sudo
cat > /root/buildany/.env.local << 'EOF'
# AI Models
DEEPSEEK_API_KEY=sk-your_actual_key_here
HERMES_URL=http://127.0.0.1:8642

# GitHub Integration
GITHUB_TOKEN=ghp-your_actual_token_here

# Cloudflare Integration
CLOUDFLARE_API_TOKEN=your_actual_cloudflare_token_here
CF_ACCOUNT_ID=your_actual_account_id_here

# BuildAny Settings
PROJECTS_DIR=/root/buildany/projects
BUILDANY_URL=https://base66.cloud
EOF

# Lock it down so only root can read it
chmod 600 /root/buildany/.env.local

# Verify it's secure
ls -la /root/buildany/.env.local
# Should show: -rw------- (only owner can read/write)
```

### Step 2: Verify .gitignore Includes It

```bash
cd /root/buildany

# Check if .gitignore exists
cat .gitignore | grep -E "\.env|\.env\.local"

# If not, add it
echo -e "\n# Secrets\n.env\n.env.local" >> .gitignore

# Verify
git check-ignore -v .env.local
# Should show: .gitignore:LINE:.env.local
```

### Step 3: Source It Automatically on Login

```bash
# Add to .bashrc so it's always available
cat >> ~/.bashrc << 'EOF'

# BuildAny Environment
if [ -f /root/buildany/.env.local ]; then
    export $(cat /root/buildany/.env.local | grep -v '^#' | xargs)
fi
EOF

# Apply immediately
source ~/.bashrc

# Test
env | grep GITHUB_TOKEN
# Should show: GITHUB_TOKEN=ghp_...
```

### Step 4: Test the Deploy

```bash
# Now run deploy - env vars are already loaded
curl -sL https://raw.githubusercontent.com/taqihas1/buildany-deploy/main/deploy_kelly_v2.py | python3 -
```

---

## Option 3: System-Wide (All Users)

```bash
# Create system-wide env file
sudo tee /etc/buildany.env << 'EOF'
DEEPSEEK_API_KEY=sk-your_key
GITHUB_TOKEN=ghp-your_token
CLOUDFLARE_API_TOKEN=your_token
CF_ACCOUNT_ID=your_account_id
EOF

sudo chmod 600 /etc/buildany.env

# Add to /etc/profile so all users get it
sudo tee -a /etc/profile << 'EOF'
if [ -f /etc/buildany.env ]; then
    export $(cat /etc/buildany.env | grep -v '^#' | xargs)
fi
EOF

# Apply
source /etc/profile
```

---

## Where to Get Each Value

| Variable | Where to Get | Example Format |
|----------|-------------|----------------|
| `GITHUB_TOKEN` | https://github.com/settings/tokens → Generate new (classic) → Scopes: repo, workflow | `ghp_xxxxxxxxxxxxxxxxxxxx` |
| `CLOUDFLARE_API_TOKEN` | https://dash.cloudflare.com/profile/api-tokens → Create Token | 40-char string |
| `CF_ACCOUNT_ID` | https://dash.cloudflare.com/ → Any domain → Right sidebar "Account ID" | 32-char hex |
| `DEEPSEEK_API_KEY` | https://platform.deepseek.com/ → API Keys | `sk-xxxxxxxx` |

---

## Quick Copy-Paste Template

```bash
# 1. SSH to VPS
ssh root@your-vps-ip

# 2. Fill in YOUR actual values below, then copy-paste the whole block:
cat > /root/buildany/.env.local << 'EOF'
DEEPSEEK_API_KEY=sk-YOUR_DEEPSEEK_KEY_HERE
GITHUB_TOKEN=ghp-YOUR_GITHUB_TOKEN_HERE
CLOUDFLARE_API_TOKEN=YOUR_CLOUDFLARE_TOKEN_HERE
CF_ACCOUNT_ID=YOUR_ACCOUNT_ID_HERE
PROJECTS_DIR=/root/buildany/projects
BUILDANY_URL=https://base66.cloud
EOF

# 3. Secure it
chmod 600 /root/buildany/.env.local

# 4. Add to .bashrc for persistence
cat >> ~/.bashrc << 'EOF'
if [ -f /root/buildany/.env.local ]; then
    export $(cat /root/buildany/.env.local | grep -v '^#' | xargs)
fi
EOF

# 5. Apply
source ~/.bashrc

# 6. Verify (should show masked values)
echo "GitHub: ${GITHUB_TOKEN:0:8}..."
echo "Cloudflare: ${CLOUDFLARE_API_TOKEN:0:8}..."
echo "DeepSeek: ${DEEPSEEK_API_KEY:0:8}..."

# 7. Deploy!
curl -sL https://raw.githubusercontent.com/taqihas1/buildany-deploy/main/deploy_kelly_v2.py | python3 -
```

---

## ⚠️ Security Checklist

- [ ] `.env.local` has `chmod 600` (only owner can read)
- [ ] `.env.local` is in `.gitignore` (never committed)
- [ ] Tokens were generated fresh (old exposed ones deleted)
- [ ] Tokens have minimum required scopes (not over-permissioned)
- [ ] No tokens were shared in chat/email/Slack

---

## 🆘 If You Mess Up

**Accidentally committed .env to GitHub?**
```bash
# 1. Delete token immediately (GitHub website)
# 2. Add to .gitignore
echo ".env*" >> .gitignore
# 3. Remove from git cache
git rm --cached .env .env.local
# 4. Commit
git add .gitignore
git commit -m "Remove env files from tracking"
git push
# 5. Generate new tokens
```
