"""Small REST interface around the same agent used by the CLI."""

import os
from functools import lru_cache
from threading import Lock

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from pathlib import Path

from agent import Agent, OllamaAgent
from store import Store


app = FastAPI(title="Empório da Música - atendimento", version="0.1.0")
WEB_DIR = Path(__file__).resolve().parent / "web"
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
sessions = {}
session_lock = Lock()


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")
    message: str = Field(min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    session_id: str
    answer: str


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(WEB_DIR / "index.html")


@app.get("/style.css", include_in_schema=False)
def stylesheet():
    return FileResponse(WEB_DIR / "style.css", media_type="text/css")


@app.get("/app.js", include_in_schema=False)
def browser_script():
    return FileResponse(WEB_DIR / "app.js", media_type="text/javascript")


@lru_cache(maxsize=1)
def get_store() -> Store:
    path = os.getenv("DATA_DIR", "/data")
    return Store(path)


@app.get("/health")
def health():
    try:
        get_store()
        return {"status": "ok"}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/mode")
def mode():
    selected = os.getenv("AGENT_MODE", "ollama")
    model = (os.getenv("OLLAMA_MODEL", "gpt-oss:20b") if selected == "ollama"
             else os.getenv("OPENAI_MODEL", "gpt-5.4-mini") if selected == "openai" else None)
    return {"mode": selected, "model": model}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    try:
        with session_lock:
            if request.session_id not in sessions:
                if len(sessions) >= 100:
                    raise HTTPException(status_code=503, detail="Session capacity reached")
                store = get_store()
                mode = os.getenv("AGENT_MODE", "ollama")
                if mode == "openai":
                    if not os.getenv("OPENAI_API_KEY"):
                        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is required")
                    agent = Agent(store, os.getenv("OPENAI_MODEL", "gpt-5.4-mini"))
                elif mode == "ollama":
                    agent = OllamaAgent(store, os.getenv("OLLAMA_MODEL", "gpt-oss:20b"),
                                         os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11435/v1"))
                else:
                    raise HTTPException(status_code=503, detail="Unsupported AGENT_MODE")
                sessions[request.session_id] = agent
            agent = sessions[request.session_id]
        answer = agent.ask(request.message)
        return ChatResponse(session_id=request.session_id, answer=answer)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Agent unavailable: {type(exc).__name__}") from exc

