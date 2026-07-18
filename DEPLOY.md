# FactLens — Railway Deployment Guide

## Architecture

```
Chrome Extension  ──── WebSocket ────►  FastAPI Backend (Railway)
                                              │
                                     ┌────── Groq LLM ──────┐
                                     │                       │
                               Claim Extractor     Verdict Generator
                                     │                       │
                               Evidence Hunter  ◄── ChromaDB (Volume)
                                     │
                                  Tavily Search
```

---

## Step 1 — Push to GitHub

```bash
cd /Users/nakshatrasharma/Desktop/FactLens

# Initialize git
git init
git add .
git commit -m "Initial FactLens commit"

# Push to GitHub (create a new repo first at github.com)
git remote add origin https://github.com/YOUR_USERNAME/factlens.git
git push -u origin main
```

---

## Step 2 — Deploy on Railway

### 2a — Create a new project
1. Go to **[railway.app](https://railway.app)** → New Project
2. Click **"Deploy from GitHub repo"**
3. Select your `factlens` repo
4. Railway auto-detects your `Dockerfile` ✅

### 2b — Add a Persistent Volume (for ChromaDB)
1. In your Railway project, click **"Add Service" → "Volume"**
2. Mount path: `/app/chroma_data`
3. Size: 1 GB (free tier)

> **Why:** ChromaDB stores vector embeddings on disk. Without a volume, data resets on every deploy.

### 2c — Set Environment Variables
In your Railway service → **Variables**, add:

| Variable | Value |
|:---|:---|
| `GROQ_API_KEY` | `your_groq_api_key_here` |
| `TAVILY_API_KEY` | `your_tavily_api_key_here` |
| `ENVIRONMENT` | `production` |
| `CHROMA_PERSIST_DIR` | `/app/chroma_data` |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` |

Railway injects `PORT` automatically — no need to set it.

### 2d — Deploy
Click **"Deploy"** — Railway builds your Dockerfile and starts the server.

Your backend URL will be something like:
```
https://factlens-production-xxxx.up.railway.app
```

---

## Step 3 — Update the Chrome Extension

After Railway gives you the URL:

1. Open the FactLens extension popup (click the icon in Chrome)
2. Click **🚂 Railway** button
3. Enter your Railway URL:
   ```
   wss://factlens-production-xxxx.up.railway.app/ws/factcheck
   ```
   > Note: Use `wss://` (secure WebSocket) for HTTPS Railway URLs
4. Click **Save Settings**
5. The status dot should turn green: ✓ Backend connected

---

## Step 4 — Load the Extension in Chrome

1. Open `chrome://extensions`
2. Enable **Developer Mode** (top-right toggle)
3. Click **Load unpacked**
4. Select the `extension/` folder from this repo
5. Open **Google Meet** and start a meeting
6. Enable captions: **More options → Turn on captions**
7. The FactLens panel will appear in the bottom-right

---

## Verify Deployment

Test your backend health check:
```bash
curl https://factlens-production-xxxx.up.railway.app/health
# Expected: {"status":"healthy","active_sessions":0,...}
```

Test fact-check endpoint:
```bash
curl -X POST https://factlens-production-xxxx.up.railway.app/factcheck \
  -H "Content-Type: application/json" \
  -d '{"text": "The Earth is the largest planet in our solar system."}'
```

---

## Local Development

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy env vars
cp .env.example .env
# Edit .env with your actual API keys

# Run server
python main.py
# Server starts at http://localhost:8000
```

---

## Troubleshooting

| Issue | Fix |
|:---|:---|
| Extension shows "Backend not reachable" | Check backend is deployed and URL uses `wss://` not `ws://` |
| CORS errors in browser console | Add extension ID to `CORS_ORIGINS` env var in Railway |
| ChromaDB errors | Ensure volume is mounted at `/app/chroma_data` |
| Slow first request | Normal — sentence-transformer model loads on first use |
| `PORT` binding error | Railway auto-sets `PORT` — don't set it manually |

---

## File Structure

```
FactLens/
├── Dockerfile              # Production container
├── railway.toml            # Railway deploy config
├── .gitignore
├── backend/
│   ├── main.py             # FastAPI server
│   ├── config.py           # Environment config
│   ├── models.py           # Pydantic schemas
│   ├── agency.py           # Agency Swarm definition
│   ├── requirements.txt
│   ├── .env.example
│   ├── orchestrator/
│   ├── claim_extractor/
│   ├── evidence_hunter/
│   └── verdict_generator/
└── extension/
    ├── manifest.json
    ├── content.js
    ├── background.js
    ├── popup.html
    ├── popup.js
    └── styles.css
```
