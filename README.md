# 🔍 FactLens — Real-Time Google Meet Fact-Checking AI

**A multi-agent AI swarm that fact-checks Google Meet conversations in real-time.**

Built on [Agency Swarm](https://github.com/VRSEN/agency-swarm) (powering [OpenSwarm](https://github.com/VRSEN/OpenSwarm)), FactLens uses 4 specialized agents coordinated by an orchestrator to extract claims, search the web, and deliver instant verdicts — all powered by Groq's free API.

---

## 🏗️ Architecture

```
Google Meet → Chrome Extension → WebSocket → FastAPI Backend → Agent Swarm → Verdicts
                    ↑                                              │
                    └──────── Overlay Panel ←──────────────────────┘
```

### The Agent Swarm

| Agent | Role | Tools |
|:---|:---|:---|
| 🤖 **Orchestrator** | Routes tasks, coordinates pipeline | Handoffs |
| 🔍 **Claim Extractor** | Identifies verifiable claims from transcript | `ExtractClaims` |
| 🌐 **Evidence Hunter** | Searches web, stores/retrieves evidence via RAG | `WebSearch`, `StoreEvidence`, `RetrieveEvidence` |
| ⚖️ **Verdict Generator** | Evaluates claims against evidence | `RetrieveEvidence`, `GenerateVerdict` |

### Tech Stack

- **LLM**: Groq (Llama 3.3 70B) — free tier, ultra-fast inference
- **Web Search**: Tavily AI — optimized for RAG/fact-checking
- **Vector DB**: ChromaDB — local, no external service needed
- **Embeddings**: all-MiniLM-L6-v2 — runs locally on CPU
- **Backend**: FastAPI + WebSocket
- **Extension**: Chrome Manifest V3

---

## 🚀 Quick Start (< 5 minutes)

### Prerequisites

- Python 3.10+
- Google Chrome
- Free API keys:
  - [Groq](https://console.groq.com/keys) (no credit card required)
  - [Tavily AI](https://tavily.com) (1,000 free credits/month)

### 1. Clone & Setup Backend

```bash
cd FactLens/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env with your Groq and Tavily API keys
```

### 2. Start the Backend

```bash
cd backend
python main.py
```

You should see:
```
🔍 FactLens backend starting...
   Groq API Key: ✅ Set
   Tavily API Key: ✅ Set
🚀 FactLens ready! WebSocket at ws://localhost:8000/ws/factcheck
```

### 3. Load the Chrome Extension

1. Open Chrome → `chrome://extensions/`
2. Enable **Developer mode** (top-right toggle)
3. Click **Load unpacked** → Select the `extension/` folder
4. The FactLens icon should appear in your extensions bar

### 4. Use It!

1. Join a Google Meet call
2. **Turn on captions** (CC button at the bottom of Meet)
3. The FactLens panel will appear in the bottom-right corner
4. As people speak, claims are automatically detected and fact-checked!

---

## 🔧 How It Works

### Pipeline Flow

1. **Caption Capture**: Chrome extension uses `MutationObserver` to watch Google Meet's caption DOM
2. **Transcript Buffering**: Captions are debounced (3s) to form complete sentences
3. **Claim Extraction**: Groq LLM identifies verifiable factual claims
4. **Web Search**: Tavily AI searches for evidence related to each claim
5. **RAG Storage**: Evidence is chunked, embedded, and stored in ChromaDB
6. **Evidence Retrieval**: Semantic search finds the most relevant evidence
7. **Verdict Generation**: Groq LLM evaluates claims against evidence
8. **Display**: Results appear in the overlay panel with verdict badges

### Verdict Categories

- ✅ **TRUE** — Supported by multiple reliable sources
- ❌ **FALSE** — Contradicts evidence from reliable sources
- ⚠️ **MISLEADING** — Contains partial truths, out-of-context, or outdated info
- ❓ **UNVERIFIED** — Insufficient evidence to determine

---

## 📁 Project Structure

```
FactLens/
├── extension/                     # Chrome Extension
│   ├── manifest.json
│   ├── content.js                 # Caption capture + overlay UI
│   ├── background.js              # Service worker
│   ├── popup.html + popup.js      # Extension popup
│   └── styles.css                 # Glassmorphism overlay styles
│
├── backend/                       # FastAPI + Agency Swarm
│   ├── main.py                    # WebSocket server
│   ├── agency.py                  # Agency definition
│   ├── agency_manifesto.md        # Shared agent instructions
│   ├── config.py                  # Environment config
│   ├── models.py                  # Pydantic schemas
│   │
│   ├── orchestrator/              # 🤖 Orchestrator Agent
│   ├── claim_extractor/           # 🔍 Claim Extractor + tools
│   ├── evidence_hunter/           # 🌐 Evidence Hunter + tools
│   └── verdict_generator/         # ⚖️ Verdict Generator + tools
│
├── README.md
└── .env.example
```

---

## 🔌 API Reference

### REST Endpoints

| Method | Path | Description |
|:---|:---|:---|
| `GET` | `/health` | Health check |
| `GET` | `/api/sessions` | List active sessions |
| `GET` | `/api/session/{id}/history` | Get session fact-check history |
| `POST` | `/api/factcheck` | Submit text for fact-checking |

### WebSocket

Connect to `ws://localhost:8000/ws/factcheck`

**Send** (transcript):
```json
{
  "type": "transcript",
  "text": "The Eiffel Tower is 330 meters tall",
  "speaker": "John",
  "session_id": "abc123"
}
```

**Receive** (verdict):
```json
{
  "type": "verdict",
  "data": {
    "verdicts": [{
      "claim_text": "The Eiffel Tower is 330 meters tall",
      "verdict": "TRUE",
      "confidence": 0.92,
      "explanation": "The Eiffel Tower's height is 330 metres including its antenna, confirmed by multiple sources.",
      "sources": ["https://..."]
    }]
  }
}
```

---

## 🏆 Built For

OpenSwarm Hackathon — Powered by [Agency Swarm](https://github.com/VRSEN/agency-swarm) + [Groq](https://groq.com)

---

## 📄 License

MIT
