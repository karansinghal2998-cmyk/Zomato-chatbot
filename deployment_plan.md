# 🚀 Deployment Plan — Zomato AI Restaurant Recommendation System

> **Backend**: [Railway](https://railway.app) — FastAPI + Uvicorn  
> **Frontend**: [Vercel](https://vercel.com) — Static HTML/CSS/JS  
> **Repository**: `https://github.com/karansinghal2998-cmyk/Zomato-chatbot.git`

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        USER BROWSER                          │
│                                                             │
│   Visits: https://zomato-ai.vercel.app                      │
└──────────────────────┬──────────────────────────────────────┘
                       │ loads HTML/CSS/JS static files
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    VERCEL (Frontend)                         │
│   src/frontend/templates/index.html                          │
│   src/frontend/static/style.css                              │
│   src/frontend/static/app.js                                 │
│                                                             │
│   All API calls → POST https://zomato-api.railway.app/...   │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTPS API calls
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                   RAILWAY (Backend)                          │
│   FastAPI + Uvicorn on port $PORT                            │
│   POST /api/v1/recommend                                     │
│   GET  /api/v1/locations                                     │
│   GET  /api/v1/health                                        │
│                         │                                    │
│      ┌──────────────────┴──────────────────┐                │
│      │  Groq LLM API (external)            │                │
│      │  HuggingFace REST API (external)    │                │
│      └─────────────────────────────────────┘                │
└─────────────────────────────────────────────────────────────┘
```

---

## Pre-Deployment Checklist

- [ ] Groq API key obtained from [console.groq.com](https://console.groq.com)
- [ ] GitHub repo pushed with all latest code
- [ ] Railway account created at [railway.app](https://railway.app)
- [ ] Vercel account created at [vercel.com](https://vercel.com)

---

## Phase 1 — Backend Deployment on Railway

### Step 1 · Prepare Railway Config Files

Three files are required in the project root:

#### `Procfile` (tells Railway how to start the server)
```
web: uvicorn src.api.server:app --host 0.0.0.0 --port $PORT
```

#### `railway.json` (Railway project config)
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "uvicorn src.api.server:app --host 0.0.0.0 --port $PORT",
    "healthcheckPath": "/api/v1/health",
    "healthcheckTimeout": 60,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 3
  }
}
```

#### `runtime.txt` (pin Python version)
```
python-3.11.x
```

---

### Step 2 · Set Railway Environment Variables

In the Railway dashboard -> your project -> **Variables**, add:

| Variable | Value | Required |
|---|---|---|
| `GROQ_API_KEY` | `gsk_xxxxxxxxxxxxxxxx` | Yes |
| `GROQ_LLM_MODEL` | `llama-3.3-70b-versatile` | Yes |
| `GROQ_FALLBACK_MODEL` | `llama-3.1-8b-instant` | Yes |
| `HUGGINGFACE_DATASET_ID` | `ManikaSaini/zomato-restaurant-recommendation` | Yes |
| `MAX_CANDIDATES_POOL` | `10` | Optional |
| `PORT` | (Railway sets this automatically) | Auto |

Never commit `.env` to GitHub. Railway reads env vars from its dashboard.

---

### Step 3 · Deploy Backend on Railway

**Option A — GitHub Auto-Deploy (Recommended)**
1. Go to [railway.app](https://railway.app) -> **New Project** -> **Deploy from GitHub repo**
2. Select `karansinghal2998-cmyk/Zomato-chatbot`
3. Railway auto-detects Python and runs `pip install -r requirements.txt`
4. Set start command: `uvicorn src.api.server:app --host 0.0.0.0 --port $PORT`
5. Add environment variables (Step 2 above)
6. Click **Deploy** — Railway assigns a public URL like `https://zomato-chatbot-production.up.railway.app`

**Option B — Railway CLI**
```bash
# Install CLI
npm install -g @railway/cli

# Login
railway login

# Link to project
railway link

# Deploy
railway up
```

---

### Step 4 · Verify Backend is Live

```bash
# Health check
curl https://YOUR-RAILWAY-URL.up.railway.app/api/v1/health

# Expected response:
# {
#   "status": "healthy",
#   "model": "llama-3.3-70b-versatile",
#   "dataset": "ManikaSaini/zomato-restaurant-recommendation",
#   "total_restaurants_indexed": 5000
# }

# Locations endpoint
curl https://YOUR-RAILWAY-URL.up.railway.app/api/v1/locations
```

---

## Phase 2 — Frontend Deployment on Vercel

### Step 1 · Separate the Frontend

The frontend is a static site (index.html + style.css + app.js).
For Vercel, it lives in a `frontend/` folder at the project root:

```
frontend/             <- Vercel root
  index.html          <- copy from src/frontend/templates/index.html
  style.css           <- copy from src/frontend/static/style.css
  app.js              <- copy from src/frontend/static/app.js
  vercel.json         <- Vercel routing config
```

#### `frontend/vercel.json`
```json
{
  "version": 2,
  "builds": [
    { "src": "index.html", "use": "@vercel/static" }
  ],
  "routes": [
    { "src": "/(.*)", "dest": "/$1" }
  ]
}
```

---

### Step 2 · Update `app.js` — Point to Railway Backend

The `app.js` currently uses relative API paths (`/api/v1/...`).
On Vercel, it must call the Railway backend URL directly.

Add at the top of `app.js`:
```javascript
const API_BASE_URL = "https://YOUR-RAILWAY-URL.up.railway.app";

// Then all fetch calls must prefix with API_BASE_URL:
// fetch(`${API_BASE_URL}/api/v1/recommend`, ...)
// fetch(`${API_BASE_URL}/api/v1/locations`)
```

You must also update `server.py` CORS to allow the Vercel domain:
```python
allow_origins=["https://YOUR-PROJECT.vercel.app", "http://localhost:3000"]
```

---

### Step 3 · Deploy Frontend on Vercel

**Option A — Vercel Dashboard (Recommended)**
1. Go to [vercel.com](https://vercel.com) -> **Add New Project**
2. Import from GitHub: `karansinghal2998-cmyk/Zomato-chatbot`
3. Set **Root Directory** to `frontend/`
4. Framework preset: **Other** (static site)
5. No build command needed
6. Click **Deploy** -> Vercel assigns `https://zomato-chatbot.vercel.app`

**Option B — Vercel CLI**
```bash
# Install CLI
npm install -g vercel

# From the frontend/ directory
cd frontend
vercel --prod
```

---

## Phase 3 — CORS + API URL Updates Post-Deployment

Once both are live, update these two files with the real URLs:

### 1. `src/api/server.py` — Restrict CORS to Vercel domain
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://zomato-chatbot.vercel.app",
        "http://localhost:3000",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

### 2. `frontend/app.js` — Use live Railway URL
```javascript
const API_BASE_URL = "https://zomato-chatbot-production.up.railway.app";
```

---

## Phase 4 — CI/CD Auto-Deploy

| Trigger | Action |
|---|---|
| Push to `main` branch | Railway auto-redeploys backend |
| Push to `main` branch | Vercel auto-redeploys frontend |
| Daily cron (05:00 UTC) | GitHub Actions refreshes dataset from HuggingFace |

Enable auto-deploy in Railway:
Railway Dashboard -> Settings -> Enable **Auto Deploy on Push to `main`**

---

## Files to Create Before Deploying

The following files need to be created in the repo before pushing:

| File | Purpose | Status |
|---|---|---|
| `Procfile` | Railway start command | To Create |
| `railway.json` | Railway project config | To Create |
| `runtime.txt` | Pin Python 3.11 | To Create |
| `frontend/index.html` | Static copy for Vercel | To Create |
| `frontend/style.css` | Static copy for Vercel | To Create |
| `frontend/app.js` | Static copy with Railway URL | To Create |
| `frontend/vercel.json` | Vercel routing config | To Create |

---

## Final Public URLs After Deployment

| Service | URL |
|---|---|
| Railway Backend | `https://zomato-chatbot-production.up.railway.app` |
| Vercel Frontend | `https://zomato-chatbot.vercel.app` |
| API Docs (Swagger) | `https://zomato-chatbot-production.up.railway.app/docs` |
| Health Check | `https://zomato-chatbot-production.up.railway.app/api/v1/health` |

---

## Estimated Monthly Costs

| Service | Plan | Estimated Cost |
|---|---|---|
| Railway | Hobby ($5 credit/month free) | Free for low traffic |
| Vercel | Hobby (free tier) | Free |
| Groq API | Free tier (rate limited) | Free |
| HuggingFace Datasets Server | Free | Free |

Railway Hobby gives $5/month free credit.
FastAPI + Uvicorn for low-traffic typically costs ~$2-3/month, staying within the free tier.

---

## Rollback Strategy

### Railway Rollback
```bash
# List past deployments
railway deployments

# Roll back to a specific deployment
railway rollback <deployment-id>
```

### Vercel Rollback
Vercel Dashboard -> **Deployments** -> click any previous deployment -> **Promote to Production**

---

## Monitoring

| Tool | What to Watch |
|---|---|
| Railway Logs | Uvicorn access logs, LLM errors, dataset load time |
| Railway Metrics | CPU / memory usage, average response time |
| Vercel Analytics | Page views, geography, Core Web Vitals |
| UptimeRobot (free) | Ping `/api/v1/health` every 5 min for uptime alerts |
