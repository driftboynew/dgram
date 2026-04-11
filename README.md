# Nokia 216 Telegram Client

A lightweight Telegram web client built specifically for the Nokia 216
running Opera Mini on 2G. Works like a proper Telegram client — login,
read chats, send messages — all in under 5KB of HTML per page.

---

## How It Works

```
Nokia 216          Your Server            Telegram
[Opera Mini] <──> [Flask + Telethon] <──> [API]
  240px HTML        Python server         MTProto
```

Your server does all the heavy Telegram work. The phone just gets
simple HTML pages it can load even on 2G.

---

## Step 1 — Get Your Telegram API Keys

1. Open https://my.telegram.org on a computer
2. Log in with your phone number
3. Click "API development tools"
4. Fill in the form (App title: "Nokia Client", Platform: Other)
5. You will get:
   - **API ID** (a number like `12345678`)
   - **API Hash** (a string like `abcdef1234567890abcdef1234567890`)

Keep these safe. Never share them publicly.

---

## Step 2 — Deploy to Railway (Free, Recommended)

Railway gives you a free server with a public URL. Perfect for this.

### 2a. Create a Railway account
Go to https://railway.app and sign up (free).

### 2b. Upload the project files
1. Go to https://github.com and create a free account
2. Create a new repository called `nokia-telegram`
3. Upload all these files to the repository:
   - `app.py`
   - `requirements.txt`
   - `railway.toml`
   - `Procfile`

### 2c. Deploy on Railway
1. On Railway, click "New Project"
2. Choose "Deploy from GitHub repo"
3. Select your `nokia-telegram` repo
4. Railway will detect Python and build it

### 2d. Set Environment Variables on Railway
In your Railway project, go to "Variables" and add:

```
API_ID       = your_api_id_number
API_HASH     = your_api_hash_string
SECRET_KEY   = any_random_long_string_like_this_one_abc123xyz
```

### 2e. Get your public URL
Railway gives you a URL like:
`https://nokia-telegram-production.up.railway.app`

---

## Step 3 — Use It On Your Nokia 216

1. Open Opera Mini on your Nokia 216
2. Type your Railway URL in the address bar
3. You will see the login page
4. Enter your Telegram phone number
5. Enter the OTP code Telegram sends you
6. Done! You can now read and send messages

---

## Running Locally (Optional / Testing on PC first)

If you have Python on your PC, you can test it locally:

```bash
# Install dependencies
pip install -r requirements.txt

# Set your keys (Linux/Mac)
export API_ID=12345678
export API_HASH=abcdef1234567890

# Or on Windows (Command Prompt)
set API_ID=12345678
set API_HASH=abcdef1234567890

# Run the server
python app.py
```

Then open http://localhost:5000 in your browser.

---

## Features

- Login with phone number + OTP
- Two-Factor Authentication (2FA) support
- Chat list showing your 20 most recent conversations
- Read messages (last 15 per chat, with "older" pagination)
- Send text messages
- Search your chats by name
- Logout

---

## Pages / URLs

| URL | What it does |
|-----|-------------|
| `/` | Home — redirects to chats or login |
| `/login` | Enter phone number |
| `/verify` | Enter OTP / 2FA password |
| `/chats` | Your chat list |
| `/chat/ID` | Messages in a chat |
| `/search` | Search chats by name |
| `/status` | Check if server is configured |
| `/logout` | Log out |

---

## Limitations

- Text messages only (no voice, no video, no sticker sending)
- Media received shows as `[media / sticker]`
- No notifications (refresh manually to see new messages)
- No group creation or contact management
- Single user only (your account)

---

## Security Notes

- Your Telegram session is saved on the server in `nokia_telegram.session`
- Only you should have access to your Railway project
- Do not share your Railway URL publicly — anyone with the URL can use it
- Change the SECRET_KEY environment variable to something random
- The server never stores your messages — it just fetches them live from Telegram

---

## Troubleshooting

**"API_ID / API_HASH not configured"**
→ Set the environment variables in Railway (Step 2d)

**"Chat not found"**
→ Go back to /chats and click the chat again. The cache resets on restart.

**Page loads but looks broken**
→ Make sure Opera Mini is not in "fit page" mode. 
  Go to Opera Mini Settings → Display → Column view OFF

**Login code never arrives**
→ Make sure you entered the full phone number with country code (e.g. +44...)

**Server crashes**
→ Check Railway logs. Usually means a Telethon version issue.
  Try pinning: `telethon==1.34.0` in requirements.txt

---

## File Structure

```
telegram-nokia/
├── app.py           Main application
├── requirements.txt Python dependencies  
├── railway.toml     Railway deployment config
├── Procfile         Process file for deployment
└── README.md        This file
```

---

Built for Nokia 216 (RM-1187) running Opera Mini on 2G.
Page sizes kept under 8KB. No JavaScript. No images. No external fonts.
