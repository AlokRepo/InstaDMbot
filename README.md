# Instagram Auto-DM System 📩

A lightweight, zero-dependency Python system that automatically replies to Instagram comments with a direct message (DM) and/or a public comment reply. It supports keyword matching and universal catch-all fallback messages.

Inspired by [AniTrack](https://github.com/AlokRepo/AniTrack), this project offers two run configurations:
1. **Serverless Poller (GitHub Actions)**: Runs automatically on a cron schedule (every 15 minutes) to scan comments, reply, and push execution state back to your repository.
2. **Real-time Webhook Receiver**: Listens for instant Meta webhook events to reply to comments immediately.

A **premium glassmorphic local dashboard** is included to test credentials, configure reply rules, trigger manual scans, and view terminal logs.

---

## 🛠️ Step-by-Step Meta Setup Guide

To connect the bot to Instagram, you must obtain API credentials from Meta's Developer Portal.

### Step 1: Account Preparation
1. Ensure your Instagram account is a **Professional Account** (either **Business** or **Creator**). You can toggle this in the Instagram mobile app settings.
2. Create a **Facebook Page** and link your Instagram Professional account to it (Settings > Linked Accounts > Instagram).

### Step 2: Create a Meta Developer App
1. Go to the [Meta for Developers Portal](https://developers.facebook.com/) and register.
2. Click **Create App** and choose the **Other** or **Business** app type.
3. Select **Instagram Graph API** and **Messenger API** (or Set Up Messenger inside the app dashboard).

### Step 3: Get Your IDs
- **Facebook Page ID**: Open your Facebook Page > About > Page Transparency (or search Page Settings) to find the Page ID.
- **Instagram Business Account ID**: 
  - Go to the [Graph API Explorer](https://developers.facebook.com/tools/explorer/).
  - Run this GET query using your token: `me/accounts?fields=instagram_business_account{id,username}`
  - Copy the ID inside the `instagram_business_account` object.

### Step 4: Generate a Page Access Token
1. In the **Graph API Explorer**, select your App.
2. Add the following consolidated permissions in the **Permissions** panel (under the modern Instagram Business Login flow):
   - `instagram_business_basic` (Allows seeing profile data, metadata, and linked Page tools)
   - `instagram_business_manage_messages` (Crucial for managing, reading, and sending private DM replies)
   - `instagram_manage_comments` (Required to fetch comment text and post public comment replies)
3. Click **Generate Token**. Select the Facebook Page associated with your Instagram account.
4. Convert this token to a **Long-Lived Access Token** (valid for 60 days) or create a **System User Token** in your Meta Business Suite Developer settings (which does not expire).

---

## 💻 Local Dashboard Configuration

You can configure and test your bot using the built-in glassmorphic setup panel:

1. **Launch the Dashboard**:
   ```bash
   python auto_dm.py --dashboard
   ```
2. **Access the Interface**: Open your browser and navigate to `http://localhost:8000`.
3. **Configure Settings**:
   - Go to the **Credentials** tab and paste your Access Token, Instagram Business Account ID, and Facebook Page ID.
   - Click **Test Connection** to verify connection to Meta.
   - Click **Save Configuration** to write settings to `config.json` (this file is ignored by git to keep your tokens secure).
4. **Create Reply Rules**:
   - Switch to the **Reply Rules** tab.
   - Click **Add New Rule**.
   - You can set up keyword rules (e.g., matching "link" or "price") or edit the active **Universal Catch-All** rule which responds to any comment.
5. **Run Manual Scan**: Click **Run Manual Poll** in the sidebar to scan your recent comments immediately and check the **Terminal Logs** panel for results.

---

## 🚀 GitHub Actions Serverless Deployment (Polling Mode)

To run the bot in the cloud for free without hosting a server:

1. Go to your GitHub repository.
2. Navigate to **Settings > Secrets and Variables > Actions > New repository secret**.
3. Create the following three secrets:
   - `INSTAGRAM_ACCESS_TOKEN` (Paste your long-lived or system user Page access token)
   - `INSTAGRAM_BUSINESS_ACCOUNT_ID` (Paste your Instagram Business Account ID)
   - `FACEBOOK_PAGE_ID` (Paste your Facebook Page ID)
4. Enable GitHub Action permissions:
   - Navigate to **Settings > Actions > General > Workflow permissions**.
   - Select **Read and write permissions** (this allows the bot to commit the `sent_comments.json` cache back to the branch to persist state).
5. The workflow `.github/workflows/instagram_auto_dm.yml` is preconfigured to run every 15 minutes. You can also trigger it manually under the **Actions** tab by selecting **Instagram Auto-DM Poller** and clicking **Run workflow**.

---

## ⚡ Webhook Deployment (Real-Time Mode)

To respond to comments instantly:

1. Set up a secure HTTPS tunnel to your local machine (using tool like [ngrok](https://ngrok.com/)):
   ```bash
   ngrok http 8000
   ```
2. Start the webhook server:
   ```bash
   python auto_dm.py --webhook --port 8000
   ```
3. In the Meta Developer App panel, navigate to **Instagram Graph API > Webhooks**:
   - Set Callback URL to: `https://<your-ngrok-subdomain>.ngrok-free.app/webhook`
   - Set Verify Token to: The token configured in your dashboard (default: `my_secure_token`).
   - Subscribe to the `comments` webhook field.
4. Now, any comment made on your posts will trigger an immediate, real-time private DM reply from your bot!
