# API Setup Guide - Module 09

This guide shows how to set up APIs for real (non-demo) examples.

**Quick Navigation:**
- [BlueSky Setup](#bluesky-setup) (5 minutes) ⭐ EASY
- [Gmail IMAP Setup](#gmail-imap-setup) (15 minutes) ⭐⭐⭐ HARD
- [Gmail SMTP Setup](#gmail-smtp-setup) (10 minutes) ⭐⭐ MEDIUM
- [Slack Webhook Setup](#slack-webhook-setup) (5 minutes) ⭐ EASY

---

## BlueSky Setup (5 minutes) ⭐ EASY

BlueSky is a decentralized social network with a simple, free API. Perfect for learning!

### Step 1: Create Account

1. Go to https://bsky.app
2. Click "Create Account"
3. Choose your handle (e.g., `yourname.bsky.social`)
4. Verify your email
5. Complete signup

**Cost:** Free forever
**Time:** 2 minutes

### Step 2: Generate App Password

1. Log in to BlueSky
2. Click your profile icon → **Settings**
3. Scroll down to **Privacy and Security**
4. Click **App Passwords**
5. Click **Add App Password**
6. Name it: `DisSysLab` (or any name you like)
7. Click **Create App Password**
8. **COPY THE PASSWORD** - you'll only see it once!

**Important:** This is NOT your main password. It's a special password just for apps.

### Step 3: Test Connection

Save this as `test_bluesky.py`:

```python
from components.sources.bluesky_source import BlueSkySource

# Replace with your credentials
source = BlueSkySource(
    handle="yourname.bsky.social",  # Your handle
    app_password="xxxx-xxxx-xxxx-xxxx"  # Your app password
)

# Test: Fetch one post
print("Testing BlueSky connection...")
post = source.run()
if post:
    print(f"✓ Success! Got post from @{post['author']}")
    print(f"  Text: {post['text'][:60]}...")
else:
    print("✗ No posts found (your timeline might be empty)")
```

Run it:
```bash
python3 test_bluesky.py
```

**Expected output:**
```
[BlueSkySource] Authenticated as yourname.bsky.social
[BlueSkySource] Fetching posts from timeline...
Testing BlueSky connection...
✓ Success! Got post from @someuser
  Text: Just posted about something interesting...
```

### Troubleshooting

**Problem:** `Authentication failed`

**Solution:** Check these:
1. Using your **app password**, not your main password
2. Handle format is correct: `yourname.bsky.social`
3. App password was copied correctly (no extra spaces)

**Problem:** `No posts found`

**Solution:** 
- Your timeline might be empty
- Follow some accounts first, then try again
- Or use `search_hashtag="#python"` to find posts

**Problem:** `Module not found: atproto`

**Solution:** Install the BlueSky library:
```bash
pip3 install atproto
```

### Example Usage

```python
from components.sources.bluesky_source import BlueSkySource

# Option 1: Get posts from your timeline
source = BlueSkySource(
    handle="yourname.bsky.social",
    app_password="xxxx-xxxx-xxxx-xxxx",
    max_posts=20
)

# Option 2: Search by hashtag
source = BlueSkySource(
    handle="yourname.bsky.social",
    app_password="xxxx-xxxx-xxxx-xxxx",
    search_hashtag="python",
    max_posts=50
)

# Option 3: Get posts from specific user
source = BlueSkySource(
    handle="yourname.bsky.social",
    app_password="xxxx-xxxx-xxxx-xxxx",
    search_author="someuser.bsky.social",
    max_posts=30
)
```

### Rate Limits

BlueSky is very generous:
- **Free tier:** ~3000 requests per 5 minutes
- **For our examples:** You'll never hit this limit
- **No daily limits**

### Security Notes

✅ **Do:**
- Use app passwords (not your main password)
- Revoke app passwords you're not using
- Keep passwords in environment variables (not in code)

❌ **Don't:**
- Share your app password
- Commit passwords to git
- Use your main BlueSky password in code

### Cost Summary

- **Account:** Free
- **API access:** Free
- **Rate limits:** Very generous
- **Perfect for learning!** ✅

---

## Managing Credentials (All Services)

**IMPORTANT: Never hardcode credentials in your code!**

### Option 1: Environment Variables (Recommended)

Environment variables keep credentials secure and separate from your code.

### Option 1: Shell Environment Variables (Recommended for Development)

Environment variables are stored in your shell and available to all programs you run.

#### **macOS/Linux (using zsh - RECOMMENDED):**

**1. Open your shell configuration file:**
```bash
nano ~/.zshrc
```

**2. Add your credentials at the end:**
```bash
# ============================================
# DisSysLab API Credentials
# ============================================
# IMPORTANT: Never commit these to git!

# BlueSky API
export BLUESKY_HANDLE='your.handle.bsky.social'
export BLUESKY_PASSWORD='xxxx-xxxx-xxxx-xxxx'

# Gmail Credentials (if using)
export GMAIL_EMAIL='your.email@gmail.com'
export GMAIL_APP_PASSWORD='abcdefghijklmnop'

# Slack Webhook (if using)
export SLACK_WEBHOOK_URL='https://hooks.slack.com/services/T07.../B08.../XXX...'
```

**3. Save and exit:**
- Press `Ctrl+O` (write out)
- Press `Enter` (confirm)
- Press `Ctrl+X` (exit)

**4. Reload your shell:**
```bash
source ~/.zshrc
```

**5. Verify it worked:**
```bash
echo $BLUESKY_HANDLE
# Should print: your.handle.bsky.social

echo $SLACK_WEBHOOK_URL
# Should print your webhook URL
```

**6. Test in Python:**
```bash
python3 -c "import os; print('BlueSky:', os.environ.get('BLUESKY_HANDLE'))"
# Should print: BlueSky: your.handle.bsky.social
```

✅ **Done!** Every new terminal will have these variables.

---

#### **macOS/Linux (using bash):**

Same steps, but use `~/.bashrc` or `~/.bash_profile` instead of `~/.zshrc`

```bash
nano ~/.bashrc
# Add same export commands as above
source ~/.bashrc
```

---

#### **Windows (PowerShell - RECOMMENDED):**

**1. Open PowerShell as Administrator:**
- Right-click Start Menu → "Windows PowerShell (Admin)"

**2. Set user environment variables (permanent):**
```powershell
# BlueSky
[System.Environment]::SetEnvironmentVariable('BLUESKY_HANDLE', 'your.handle.bsky.social', 'User')
[System.Environment]::SetEnvironmentVariable('BLUESKY_PASSWORD', 'xxxx-xxxx-xxxx-xxxx', 'User')

# Gmail (if using)
[System.Environment]::SetEnvironmentVariable('GMAIL_EMAIL', 'your.email@gmail.com', 'User')
[System.Environment]::SetEnvironmentVariable('GMAIL_APP_PASSWORD', 'abcdefghijklmnop', 'User')

# Slack Webhook (if using)
[System.Environment]::SetEnvironmentVariable('SLACK_WEBHOOK_URL', 'https://hooks.slack.com/services/...', 'User')
```

**3. Restart PowerShell** (close and reopen)

**4. Verify:**
```powershell
$env:BLUESKY_HANDLE
# Should print: your.handle.bsky.social
```

---

#### **Windows (Command Prompt):**

**1. Open Command Prompt as Administrator**

**2. Set environment variables (permanent):**
```cmd
setx BLUESKY_HANDLE "your.handle.bsky.social"
setx BLUESKY_PASSWORD "xxxx-xxxx-xxxx-xxxx"
setx GMAIL_EMAIL "your.email@gmail.com"
setx GMAIL_APP_PASSWORD "abcdefghijklmnop"
setx SLACK_WEBHOOK_URL "https://hooks.slack.com/services/..."
```

**3. Restart Command Prompt**

---

#### **Temporary Variables (Testing Only)**

Set for current terminal session only (disappears when you close terminal):

```bash
# macOS/Linux
export BLUESKY_HANDLE='your.handle.bsky.social'
export SLACK_WEBHOOK_URL='https://hooks.slack.com/...'

# Windows PowerShell
$env:BLUESKY_HANDLE = 'your.handle.bsky.social'
$env:SLACK_WEBHOOK_URL = 'https://hooks.slack.com/...'
```

**Use this for quick tests, but add to shell config for permanent setup.**

---

### Option 2: .env File (For Projects)

Good for project-specific credentials.

1. **Create `.env` file in your project directory:**
   ```bash
   cd ~/Documents/DisSysLab
   nano .env
   ```

2. **Add credentials:**
   ```
   BLUESKY_HANDLE=your.handle.bsky.social
   BLUESKY_PASSWORD=xxxx-xxxx-xxxx-xxxx
   GMAIL_EMAIL=your.email@gmail.com
   GMAIL_APP_PASSWORD=abcdefghijklmnop
   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
   ```

3. **Add `.env` to `.gitignore`:**
   ```bash
   echo ".env" >> .gitignore
   ```

4. **Install python-dotenv:**
   ```bash
   pip3 install python-dotenv
   ```

5. **Use in your code:**
   ```python
   from dotenv import load_dotenv
   import os
   
   # Load .env file
   load_dotenv()
   
   # Access credentials
   handle = os.environ.get("BLUESKY_HANDLE")
   password = os.environ.get("BLUESKY_PASSWORD")
   ```

### Option 3: Temporary (For Testing Only)

**WARNING: Only for quick tests. Never commit to git!**

```bash
# Set for current terminal session only
export BLUESKY_HANDLE='your.handle.bsky.social'
export BLUESKY_PASSWORD='xxxx-xxxx-xxxx-xxxx'

# Run your code
python3 your_script.py

# Variables disappear when you close the terminal
```

### Using Credentials in Your Code

```python
import os

# Always use environment variables
from components.sources.bluesky_source import BlueSkySource

source = BlueSkySource(
    handle=os.environ.get("BLUESKY_HANDLE"),
    app_password=os.environ.get("BLUESKY_PASSWORD")
)

# Never do this:
# source = BlueSkySource(
#     handle="hardcoded.bsky.social",  # ❌ BAD
#     app_password="xxxx-xxxx-xxxx"    # ❌ BAD
# )
```

### Security Checklist

✅ **Do:**
- Store credentials in environment variables or `.env` files
- Add `.env` to `.gitignore`
- Use different credentials for development vs production
- Revoke credentials you're not using
- Use app passwords (not main passwords)

❌ **Don't:**
- Hardcode credentials in your code
- Commit credentials to git
- Share credentials in Slack/Discord/email
- Use your main passwords for API access
- Leave credentials in screenshot or screen recordings

### Troubleshooting Credentials

**Problem:** "Credentials not found"

**Solution:**
```bash
# Check if set:
echo $BLUESKY_HANDLE

# If empty, they're not set. Follow steps above to set them.
```

**Problem:** "Authentication failed" but credentials are set

**Solution:**
```bash
# Check for extra spaces or quotes:
echo "$BLUESKY_HANDLE" | od -c

# Should show just your handle, no extra characters
```

**Problem:** Variables work in terminal but not in Python

**Solution:**
```bash
# Make sure you restarted terminal after editing ~/.zshrc

# Or reload it:
source ~/.zshrc

# Then verify in Python:
python3 -c "import os; print(os.environ.get('BLUESKY_HANDLE'))"
```

---

## Gmail IMAP Setup (15 minutes) ⭐⭐⭐ HARD

IMAP lets you read emails from Gmail (or any email provider).

### Prerequisites

- Gmail account
- **2-Factor Authentication enabled** (required for app passwords)

### Step 1: Enable IMAP

1. Open Gmail
2. Click **Settings** (gear icon) → **See all settings**
3. Click **Forwarding and POP/IMAP** tab
4. Under "IMAP access", select **Enable IMAP**
5. Click **Save Changes**

**Time:** 2 minutes

### Step 2: Enable 2-Factor Authentication

**If you already have 2FA enabled, skip to Step 3.**

1. Go to https://myaccount.google.com/security
2. Click **2-Step Verification**
3. Click **Get Started**
4. Follow the setup wizard:
   - Add your phone number
   - Verify with code
   - Turn on 2-step verification
5. **Test it:** Log out and log back in (should ask for code)

**Time:** 5 minutes

### Step 3: Generate App Password

1. Go to https://myaccount.google.com/apppasswords
   - Or: Google Account → Security → 2-Step Verification → App passwords
2. You may need to re-enter your password
3. Under "Select app", choose **Mail**
4. Under "Select device", choose **Other (Custom name)**
5. Enter name: `DisSysLab` or `Python Email Reader`
6. Click **Generate**
7. **COPY THE 16-CHARACTER PASSWORD**
   - It looks like: `abcd efgh ijkl mnop`
   - **You'll only see this once!**
   - Save it somewhere safe

**Time:** 3 minutes

### Step 4: Test Connection

Save this as `test_email.py`:

```python
from components.sources.email_source import EmailSource

# Replace with your credentials
source = EmailSource(
    imap_server="imap.gmail.com",
    email="your.email@gmail.com",
    password="abcdefghijklmnop",  # 16-char app password (no spaces!)
    folder="INBOX"
)

# Test: Read one email
print("Testing Gmail connection...")
email = source.run()
if email:
    print(f"✓ Success! Got email from {email['from_name']}")
    print(f"  Subject: {email['subject']}")
else:
    print("✓ Connected, but inbox is empty (no unread emails)")
```

Run it:
```bash
python3 test_email.py
```

**Expected output:**
```
[EmailSource] Connected to imap.gmail.com
[EmailSource] Reading from INBOX
Testing Gmail connection...
✓ Success! Got email from John Doe
  Subject: Meeting request
```

### Troubleshooting

**Problem:** `Authentication failed`

**Solution:** Check these:
1. Using **app password**, not your Gmail password
2. App password has **no spaces**: `abcdefghijklmnop` not `abcd efgh ijkl mnop`
3. 2-factor authentication is enabled
4. IMAP is enabled in Gmail settings

**Problem:** `IMAP not enabled`

**Solution:**
- Go to Gmail Settings → Forwarding and POP/IMAP
- Enable IMAP
- Save changes
- Wait 5 minutes, try again

**Problem:** `Can't generate app password`

**Solution:**
- Make sure 2-factor authentication is enabled first
- Visit https://myaccount.google.com/apppasswords directly
- If still doesn't work, you may need to enable "Less secure app access" (not recommended)

### Security Notes

⚠️ **Important:**
- App passwords give full access to your email
- Only use for personal projects
- Revoke app passwords you're not using
- Never share app passwords
- Never commit to git

### Example Usage

```python
from components.sources.email_source import EmailSource

# Read unread emails from inbox
source = EmailSource(
    imap_server="imap.gmail.com",
    email="your.email@gmail.com",
    password="your-app-password",
    folder="INBOX",
    filter_unread=True
)

# Read all emails (not just unread)
source = EmailSource(
    imap_server="imap.gmail.com",
    email="your.email@gmail.com",
    password="your-app-password",
    folder="INBOX",
    filter_unread=False
)

# Read from a label
source = EmailSource(
    imap_server="imap.gmail.com",
    email="your.email@gmail.com",
    password="your-app-password",
    folder="[Gmail]/Important"  # Gmail labels
)
```

### Works With Other Email Providers

**Outlook/Hotmail:**
```python
source = EmailSource(
    imap_server="outlook.office365.com",
    email="your.email@outlook.com",
    password="your-app-password"
)
```

**Yahoo Mail:**
```python
source = EmailSource(
    imap_server="imap.mail.yahoo.com",
    email="your.email@yahoo.com",
    password="your-app-password"
)
```

---

## Gmail SMTP Setup (10 minutes) ⭐⭐ MEDIUM

SMTP lets you send emails from Gmail.

**Good news:** You can use the **same app password** from IMAP setup!

### Step 1: Use Same App Password

If you already did IMAP setup, you're done! Use the same 16-character app password.

If not, follow [Gmail IMAP Setup Step 3](#step-3-generate-app-password) above.

### Step 2: Test Connection

Save this as `test_smtp.py`:

```python
from components.sinks.email_sender import EmailSender

# Replace with your credentials
sender = EmailSender(
    smtp_server="smtp.gmail.com",
    smtp_port=587,
    from_email="your.email@gmail.com",
    password="abcdefghijklmnop",  # Same app password as IMAP
    to_email="your.email@gmail.com"  # Send to yourself for testing
)

# Test: Send an email
print("Testing Gmail SMTP...")
sender.run({
    "subject": "Test from DisSysLab",
    "body": "If you're reading this, SMTP works!"
})
print("✓ Email sent! Check your inbox.")
```

Run it:
```bash
python3 test_smtp.py
```

**Check your inbox** - you should receive the test email!

### Troubleshooting

Same as IMAP - use the app password, not your Gmail password.

### Example Usage

```python
from components.sinks.email_sender import EmailSender

# Basic email
sender = EmailSender(
    smtp_server="smtp.gmail.com",
    smtp_port=587,
    from_email="your.email@gmail.com",
    password="your-app-password"
)

sender.run({
    "to": "recipient@example.com",
    "subject": "Alert: Server Down",
    "body": "The server is experiencing issues."
})

# HTML email
sender.run({
    "to": "recipient@example.com",
    "subject": "Daily Report",
    "body": "Plain text version",
    "html": "<h1>Daily Report</h1><p>Everything looks good!</p>"
})
```

---

## Slack Webhook Setup (10 minutes) ⭐ EASY

Webhooks let you send messages to Slack channels.

### Step 1: Create Incoming Webhook App

1. **Go to Slack API Apps page:**
   - Visit: https://api.slack.com/apps
   - Click **"Create New App"**

2. **Choose "From scratch":**
   - App Name: `DisSysLab` (or any name you like)
   - Pick your workspace: Select your workspace from dropdown
   - Click **"Create App"**

3. **You'll land on the "Basic Information" page:**
   - This is your app's main settings page
   - Look at the **LEFT SIDEBAR**

4. **Navigate to Incoming Webhooks:**
   - In the left sidebar, find the **"Features"** section
   - Click **"Incoming Webhooks"**
   - (If you don't see it, scroll down the left sidebar)

5. **Activate Incoming Webhooks:**
   - At the top of the page, toggle **"Activate Incoming Webhooks"** to **ON**
   - The toggle will turn green when activated

6. **Add Webhook to Your Workspace:**
   - Scroll down to "Webhook URLs for Your Workspace"
   - Click **"Add New Webhook to Workspace"** button
   - You'll be asked to authorize the app

7. **Choose a Channel:**
   - Select a channel from the dropdown (e.g., `#general`)
   - Or create a new channel like `#alerts` or `#monitoring`
   - Click **"Allow"**

8. **Copy the Webhook URL:**
   - You'll see a webhook URL appear
   - Format: `https://hooks.slack.com/services/T07CHK56K9U/B08.../XXX...`
   - Click the **"Copy"** button next to it
   - **DO NOT share this URL or commit it to git!**

**Time:** 5-10 minutes

### Important: The Webhook URL is a SECRET!

⚠️ **Treat the webhook URL like a password:**
- Anyone with this URL can post to your Slack channel
- Never commit it to git
- Never share it publicly
- If exposed, revoke it and create a new one

See the "Security: Protecting Your Secrets" section below for proper handling.

### Step 2: Test Connection

Save this as `test_slack.py`:

```python
from components.sinks.webhook_sink import Webhook

# Replace with your webhook URL
webhook = Webhook(
    url="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
)

# Test: Send a message
print("Testing Slack webhook...")
webhook.run({
    "text": "🎉 Hello from DisSysLab! Webhook works!"
})
print("✓ Message sent! Check your Slack channel.")
```

Run it:
```bash
python3 test_slack.py
```

**Check your Slack channel** - you should see the message!

### Example Usage

```python
from components.sinks.webhook_sink import Webhook

webhook = Webhook(
    url="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
)

# Simple message
webhook.run({
    "text": "Alert: CPU usage at 95%"
})

# Formatted message
webhook.run({
    "text": "🚨 *ALERT*\nServer: production-1\nCPU: 95%\nAction: Investigating"
})

# With username and icon
webhook.run({
    "text": "Daily report complete",
    "username": "ReportBot",
    "icon_emoji": ":chart_with_upwards_trend:"
})
```

### Slack Message Formatting

Use Slack's markdown-like formatting:

```python
{
    "text": """
*Bold text*
_Italic text_
~Strike through~
`Code`
```Code block```
> Quote
"""
}
```

### Troubleshooting

**Problem:** `Invalid webhook URL`

**Solution:**
- Make sure URL starts with `https://hooks.slack.com/services/`
- Copy the entire URL (they're very long)
- Check for extra spaces

**Problem:** `No response / timeout`

**Solution:**
- Check your internet connection
- Verify webhook is still active in Slack settings

---

## Security: Protecting Your Secrets

**CRITICAL: Never commit credentials to git!**

GitHub and other platforms actively scan for exposed secrets. If you accidentally commit a secret, it can be discovered and abused even after you delete it from the current code.

### What Are Secrets?

Secrets are sensitive credentials that grant access to services:
- API keys and passwords
- Webhook URLs
- Database connection strings
- Authentication tokens
- Email app passwords

### The Golden Rule

**❌ NEVER do this:**
```python
# BAD - Hardcoded secret in code
webhook = Webhook(url="https://hooks.slack.com/services/T07.../B08.../XXX...")
```

**✅ ALWAYS do this:**
```python
# GOOD - Secret from environment variable
import os
webhook = Webhook(url=os.environ.get("SLACK_WEBHOOK_URL"))
```

### If You Accidentally Commit a Secret

**Don't panic, but act quickly:**

#### 1. **Revoke the Secret Immediately**

For each type of secret:
- **BlueSky:** Delete the app password, create a new one
- **Gmail:** Revoke the app password, generate a new one
- **Slack Webhook:** Delete the webhook, create a new one

#### 2. **Remove from Git History**

The secret is still in your git history! Remove it:

**Option A: Remove specific file (recommended):**
```bash
cd ~/Documents/DisSysLab

# Remove the file from git history
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch path/to/file.py" \
  --prune-empty --tag-name-filter cat -- --all

# Force push (rewrites history)
git push origin --force --all
```

**Option B: If it's your most recent commit:**
```bash
# Remove file from last commit
git rm --cached path/to/file.py
git commit --amend --no-edit
git push --force
```

**Option C: Use BFG Repo Cleaner (easiest for large repos):**
```bash
# Install BFG
brew install bfg  # macOS
# or download from https://rtyley.github.io/bfg-repo-cleaner/

# Clean secrets
bfg --replace-text secrets.txt  # File with secrets to remove
git reflog expire --expire=now --all
git gc --prune=now --aggressive
git push --force
```

#### 3. **Add to .gitignore**

```bash
# Prevent future commits
echo "test_*.py" >> .gitignore
echo ".env" >> .gitignore
echo "credentials.json" >> .gitignore
git add .gitignore
git commit -m "Add sensitive files to gitignore"
git push
```

### Preventing Accidents

#### 1. **Use .gitignore Proactively**

Create `.gitignore` at the start:
```bash
# In your project root
cat > .gitignore << 'EOF'
# Secrets and credentials
.env
credentials.json
secrets.json
*_credentials.py
*_secrets.py

# Test files with hardcoded values
test_*.py
*_test.py

# Environment-specific
.venv/
__pycache__/
*.pyc

# OS files
.DS_Store
Thumbs.db
EOF
```

#### 2. **Use Pre-commit Hooks**

Install git-secrets to prevent commits:
```bash
# Install git-secrets
brew install git-secrets  # macOS
# or https://github.com/awslabs/git-secrets

# Set up for your repo
cd ~/Documents/DisSysLab
git secrets --install
git secrets --register-aws  # Scans for AWS keys
git secrets --add 'hooks\.slack\.com/services/[A-Z0-9/]+'  # Slack webhooks
git secrets --add '[a-z]{4}-[a-z]{4}-[a-z]{4}-[a-z]{4}'    # BlueSky app passwords
```

Now git will warn you before committing secrets!

#### 3. **Review Before Pushing**

Always check what you're committing:
```bash
# See what will be committed
git diff --cached

# Review file contents
git diff --cached path/to/file.py

# If you see secrets, unstage and fix
git reset HEAD path/to/file.py
```

### GitHub Secret Scanning

GitHub automatically scans commits for secrets. If detected, you'll see:

```
remote: —— Slack Incoming Webhook URL ————————————————
remote:        locations:
remote:          - commit: abc123...
remote:            path: test_webhook.py:6
remote:        
remote:        To push, remove secret from commit(s)
```

**This means:**
1. GitHub blocked your push (good!)
2. The secret is in your git history
3. Follow "Remove from Git History" steps above
4. Revoke the exposed secret
5. Create a new secret

---

## Managing Credentials (All Services)

**IMPORTANT: Never hardcode credentials in your code!**

Environment variables keep credentials secure and separate from your code.

### Option 1: Shell Environment Variables (Recommended for Development)

**In your terminal:**
```bash
# Add to ~/.bashrc or ~/.zshrc
export BLUESKY_HANDLE="yourname.bsky.social"
export BLUESKY_PASSWORD="xxxx-xxxx-xxxx-xxxx"
export GMAIL_EMAIL="your.email@gmail.com"
export GMAIL_APP_PASSWORD="abcdefghijklmnop"
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
```

**In your Python code:**
```python
import os

# BlueSky
source = BlueSkySource(
    handle=os.environ.get("BLUESKY_HANDLE"),
    app_password=os.environ.get("BLUESKY_PASSWORD")
)

# Gmail
source = EmailSource(
    email=os.environ.get("GMAIL_EMAIL"),
    password=os.environ.get("GMAIL_APP_PASSWORD"),
    imap_server="imap.gmail.com"
)

# Slack
webhook = Webhook(
    url=os.environ.get("SLACK_WEBHOOK_URL")
)
```

### Using .env File

Create `.env` file:
```
BLUESKY_HANDLE=yourname.bsky.social
BLUESKY_PASSWORD=xxxx-xxxx-xxxx-xxxx
GMAIL_EMAIL=your.email@gmail.com
GMAIL_APP_PASSWORD=abcdefghijklmnop
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

**Add to .gitignore:**
```
.env
```

Use with `python-dotenv`:
```bash
pip3 install python-dotenv
```

```python
from dotenv import load_dotenv
import os

load_dotenv()  # Load .env file

source = BlueSkySource(
    handle=os.environ.get("BLUESKY_HANDLE"),
    app_password=os.environ.get("BLUESKY_PASSWORD")
)
```

---

## Quick Reference

| Service | Setup Time | Difficulty | Cost | Rate Limits |
|---------|-----------|-----------|------|-------------|
| BlueSky | 5 min | ⭐ Easy | Free | Very generous |
| Gmail IMAP | 15 min | ⭐⭐⭐ Hard | Free | 500 emails/day |
| Gmail SMTP | 10 min | ⭐⭐ Medium | Free | 500 emails/day |
| Slack Webhook | 5 min | ⭐ Easy | Free | ~1 msg/second |

---

## Getting Help

**Having trouble?**

1. Check the troubleshooting section for your service
2. Verify credentials are correct (no typos, no extra spaces)
3. Make sure prerequisites are met (2FA, IMAP enabled, etc.)
4. Try the test scripts provided
5. Check service status pages:
   - BlueSky: https://status.bsky.app
   - Gmail: https://www.google.com/appsstatus
   - Slack: https://status.slack.com

**Still stuck?** Use the demo versions instead - they work offline and teach the same patterns!

---

**You're ready to build!** 🚀

Start with BlueSky (easiest) and work your way up.