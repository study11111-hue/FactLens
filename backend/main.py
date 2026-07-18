"""
FactLens — FastAPI Backend Server
Real-time fact-checking API with WebSocket support for Chrome extension.
"""

# ── Pydantic Monkeypatch ────────────────────────────────
try:
    from openai.types.responses.response_usage import InputTokensDetails
    original_init = InputTokensDetails.__init__
    def patched_init(self, *args, **kwargs):
        kwargs.setdefault('cache_write_tokens', 0)
        kwargs.setdefault('cached_tokens', 0)
        original_init(self, *args, **kwargs)
    InputTokensDetails.__init__ = patched_init
except ImportError:
    pass

import asyncio
import json
import os
import uuid
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import SERVER_HOST, SERVER_PORT, CORS_ORIGINS, GROQ_API_KEY, TAVILY_API_KEY
from models import (
    VerdictCategory,
    FactCheckResult,
    Verdict,
)


# ── Session Store ─────────────────────────────────────────

sessions: dict[str, dict] = {}


def get_session(session_id: str) -> dict:
    """Get or create a session."""
    if session_id not in sessions:
        sessions[session_id] = {
            "id": session_id,
            "created_at": datetime.now().isoformat(),
            "claims_checked": 0,
            "verdicts": [],
            "transcript_chunks": [],
        }
    return sessions[session_id]


# ── Fact-Check Pipeline (Direct — no Agency Swarm overhead) ──

async def run_fact_check_pipeline(
    transcript: str,
    speaker: str,
    session_id: str,
) -> list[dict]:
    """
    Run the fact-checking pipeline directly using Groq + Tavily + ChromaDB.
    This provides a fast, direct pipeline without Agency Swarm orchestration
    overhead, while still using the same tools under the hood.
    """
    from claim_extractor.tools.extract_claims import ExtractClaims
    from evidence_hunter.tools.web_search import WebSearch
    from evidence_hunter.tools.store_evidence import StoreEvidence
    from evidence_hunter.tools.retrieve_evidence import RetrieveEvidence
    from verdict_generator.tools.generate_verdict import GenerateVerdict

    verdicts = []

    # Step 1: Extract claims
    extractor = ExtractClaims(transcript_text=transcript, speaker=speaker)
    claims_json = await asyncio.to_thread(extractor.run)

    try:
        claims = json.loads(claims_json)
        if isinstance(claims, dict):
            claims = claims.get("claims", [])
    except (json.JSONDecodeError, TypeError):
        claims = []

    if not claims:
        return []

    # Step 2-4: For each claim, search → store → retrieve → verdict
    for claim_data in claims:
        claim_text = claim_data.get("claim_text", "")
        claim_speaker = claim_data.get("speaker", speaker)

        if not claim_text:
            continue

        try:
            # Step 2: Web search
            searcher = WebSearch(query=claim_text, max_results=5)
            search_results = await asyncio.to_thread(searcher.run)

            # Step 3: Store evidence in ChromaDB
            storer = StoreEvidence(
                search_results_json=search_results,
                session_id=session_id,
            )
            await asyncio.to_thread(storer.run)

            # Step 4: Retrieve relevant evidence
            retriever = RetrieveEvidence(
                claim_text=claim_text,
                session_id=session_id,
                top_k=5,
            )
            evidence_json = await asyncio.to_thread(retriever.run)

            # Step 5: Generate verdict
            generator = GenerateVerdict(
                claim_text=claim_text,
                evidence_json=evidence_json,
                speaker=claim_speaker,
            )
            verdict_json = await asyncio.to_thread(generator.run)

            try:
                verdict_data = json.loads(verdict_json)
                verdicts.append(verdict_data)
            except (json.JSONDecodeError, TypeError):
                verdicts.append({
                    "claim_text": claim_text,
                    "verdict": "UNVERIFIED",
                    "confidence": 0.0,
                    "explanation": "Error processing verdict",
                    "sources": [],
                    "speaker": claim_speaker,
                })

        except Exception as e:
            verdicts.append({
                "claim_text": claim_text,
                "verdict": "UNVERIFIED",
                "confidence": 0.0,
                "explanation": f"Pipeline error: {str(e)}",
                "sources": [],
                "speaker": claim_speaker,
            })

    return verdicts


# ── App Lifecycle ─────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    print("🔍 FactLens backend starting...")
    print(f"   Groq API Key: {'✅ Set' if GROQ_API_KEY else '❌ Missing'}")
    print(f"   Tavily API Key: {'✅ Set' if TAVILY_API_KEY else '❌ Missing'}")

    # Pre-load the embedding model in background
    async def preload():
        try:
            from evidence_hunter.tools.store_evidence import _get_embedding_model
            await asyncio.to_thread(_get_embedding_model)
            print("   Embedding model: ✅ Loaded")
        except Exception as e:
            print(f"   Embedding model: ⚠️ Will load on first use ({e})")

    asyncio.create_task(preload())
    print("🚀 FactLens ready! WebSocket at ws://localhost:8000/ws/factcheck")

    yield

    print("👋 FactLens shutting down...")


# ── FastAPI App ───────────────────────────────────────────

app = FastAPI(
    title="FactLens",
    description="Real-time Google Meet fact-checking AI powered by multi-agent swarm",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for Chrome extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Chrome extensions need wildcard
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── REST Endpoints ────────────────────────────────────────

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "FactLens",
        "groq_configured": bool(GROQ_API_KEY),
        "tavily_configured": bool(TAVILY_API_KEY),
        "active_sessions": len(sessions),
    }


@app.get("/api/sessions")
async def list_sessions():
    """List all active sessions."""
    return {
        "sessions": [
            {
                "id": s["id"],
                "created_at": s["created_at"],
                "claims_checked": s["claims_checked"],
            }
            for s in sessions.values()
        ]
    }


@app.get("/api/session/{session_id}/history")
async def session_history(session_id: str):
    """Get fact-check history for a session."""
    session = sessions.get(session_id)
    if not session:
        return JSONResponse(
            status_code=404,
            content={"error": "Session not found"},
        )
    return {
        "session_id": session_id,
        "created_at": session["created_at"],
        "claims_checked": session["claims_checked"],
        "verdicts": session["verdicts"],
    }


@app.post("/api/factcheck")
async def factcheck_rest(payload: dict):
    """
    REST endpoint for fact-checking (alternative to WebSocket).
    Accepts {"text": "...", "speaker": "...", "session_id": "..."}
    """
    text = payload.get("text", "")
    speaker = payload.get("speaker", "Unknown")
    session_id = payload.get("session_id", str(uuid.uuid4())[:8])

    if not text:
        return JSONResponse(
            status_code=400,
            content={"error": "No text provided"},
        )

    session = get_session(session_id)
    session["transcript_chunks"].append(text)

    verdicts = await run_fact_check_pipeline(text, speaker, session_id)

    session["claims_checked"] += len(verdicts)
    session["verdicts"].extend(verdicts)

    return {
        "session_id": session_id,
        "verdicts": verdicts,
        "claims_found": len(verdicts),
    }


# ── WebSocket Endpoint ───────────────────────────────────

@app.websocket("/ws/factcheck")
async def websocket_factcheck(websocket: WebSocket):
    """
    WebSocket endpoint for real-time fact-checking.
    Chrome extension connects here and sends transcript chunks.
    """
    await websocket.accept()
    session_id = str(uuid.uuid4())[:8]
    session = get_session(session_id)

    print(f"🔌 New WebSocket connection: session={session_id}")

    # Send session ID to client
    await websocket.send_json({
        "type": "status",
        "data": {
            "message": "Connected to FactLens",
            "session_id": session_id,
        },
    })

    try:
        while True:
            # Receive message from Chrome extension
            raw = await websocket.receive_text()

            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "data": {"message": "Invalid JSON"},
                })
                continue

            msg_type = message.get("type", "")

            # Handle ping/pong
            if msg_type == "ping":
                await websocket.send_json({"type": "pong", "data": {}})
                continue

            # Handle transcript messages
            if msg_type == "transcript":
                text = message.get("text", "")
                speaker = message.get("speaker", "Unknown")

                if not text or len(text.strip()) < 10:
                    continue

                session["transcript_chunks"].append(text)

                # Send "checking" status
                await websocket.send_json({
                    "type": "status",
                    "data": {
                        "message": "Analyzing transcript for claims...",
                        "processing": True,
                    },
                })

                # Run fact-check pipeline
                try:
                    verdicts = await run_fact_check_pipeline(
                        text, speaker, session_id
                    )

                    if verdicts:
                        session["claims_checked"] += len(verdicts)
                        session["verdicts"].extend(verdicts)

                        await websocket.send_json({
                            "type": "verdict",
                            "data": {
                                "verdicts": verdicts,
                                "session_id": session_id,
                            },
                        })
                    else:
                        await websocket.send_json({
                            "type": "status",
                            "data": {
                                "message": "No verifiable claims found in this segment",
                                "processing": False,
                            },
                        })

                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "data": {"message": f"Pipeline error: {str(e)}"},
                    })

    except WebSocketDisconnect:
        print(f"🔌 WebSocket disconnected: session={session_id}")
    except Exception as e:
        print(f"❌ WebSocket error: {e}")


# ── Run Server ────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    is_production = os.getenv("ENVIRONMENT", "development") == "production"

    uvicorn.run(
        "main:app",
        host=SERVER_HOST,
        port=SERVER_PORT,
        reload=not is_production,  # No hot-reload in production
        log_level="info",
    )
