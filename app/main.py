"""FastAPI entry point for the Embr → Foundry chat sample."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .agent import get_agent

load_dotenv()

app = FastAPI(title="Embr × Foundry chat sample")

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None


class ChatResponse(BaseModel):
    reply: str


_threads: dict[str, list[dict[str, str]]] = {}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    try:
        agent = get_agent()
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    thread_id = req.thread_id or "default"
    history = _threads.setdefault(thread_id, [])
    history.append({"role": "user", "content": req.message})

    conversation = "\n".join(f"{m['role']}: {m['content']}" for m in history[-20:])
    try:
        result = await agent.run(conversation)
    except Exception as exc:  # noqa: BLE001 — surface model errors to the UI
        # Roll back the user message so retry isn't polluted by a failed turn.
        history.pop()
        raise HTTPException(
            status_code=502,
            detail=f"Model call failed: {exc}",
        ) from exc
    reply = str(result)

    history.append({"role": "assistant", "content": reply})
    return ChatResponse(reply=reply)


@app.get("/api/config")
async def config() -> dict[str, object]:
    return {
        "model": os.environ.get("AZURE_OPENAI_MODEL", "gpt-4o-mini"),
        "endpoint_configured": bool(os.environ.get("AZURE_OPENAI_ENDPOINT")),
    }
