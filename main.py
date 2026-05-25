from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional
import httpx
import json
import secrets
from config import OLLAMA_BASE_URL, DEFAULT_MODEL, API_KEY

app = FastAPI(title="Gemma API Wrapper", version="1.0.0")

UNPROTECTED_PATHS = {"/", "/health", "/docs", "/openapi.json", "/redoc"}


@app.middleware("http")
async def require_api_key(request: Request, call_next):
    if not API_KEY or request.url.path in UNPROTECTED_PATHS:
        return await call_next(request)
    key = request.headers.get("X-API-Key", "")
    if not secrets.compare_digest(key, API_KEY):
        return JSONResponse(status_code=401, content={"detail": "Invalid or missing API key"})
    return await call_next(request)


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    model: Optional[str] = DEFAULT_MODEL
    system: Optional[str] = None
    stream: Optional[bool] = False
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None


class ChatConversationRequest(BaseModel):
    messages: list[ChatMessage]
    model: Optional[str] = DEFAULT_MODEL
    system: Optional[str] = None
    stream: Optional[bool] = False
    temperature: Optional[float] = 0.7


class GenerateRequest(BaseModel):
    prompt: str
    model: Optional[str] = DEFAULT_MODEL
    stream: Optional[bool] = False
    temperature: Optional[float] = 0.7


@app.get("/")
def root():
    return {"status": "ok", "service": "Gemma API Wrapper", "ollama": OLLAMA_BASE_URL}


@app.get("/models")
async def list_models():
    """Lista los modelos disponibles en Ollama."""
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=10)
            resp.raise_for_status()
            data = resp.json()
            models = [m["name"] for m in data.get("models", [])]
            return {"models": models}
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="No se puede conectar a Ollama. ¿Está corriendo en localhost:11434?")


@app.get("/health")
async def health():
    """Verifica si Ollama está disponible."""
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
            resp.raise_for_status()
            return {"status": "healthy", "ollama": "reachable"}
        except Exception as e:
            return {"status": "unhealthy", "ollama": "unreachable", "error": str(e)}


@app.post("/chat")
async def chat(req: ChatRequest):
    """
    Endpoint simple: envía un mensaje y recibe respuesta de Gemma.
    Soporta streaming opcional.
    """
    messages = []
    if req.system:
        messages.append({"role": "system", "content": req.system})
    messages.append({"role": "user", "content": req.message})

    payload = {
        "model": req.model,
        "messages": messages,
        "stream": req.stream,
        "options": {"temperature": req.temperature},
    }
    if req.max_tokens:
        payload["options"]["num_predict"] = req.max_tokens

    if req.stream:
        return StreamingResponse(
            _stream_chat(payload),
            media_type="text/event-stream",
        )

    async with httpx.AsyncClient(timeout=120) as client:
        try:
            resp = await client.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return {
                "model": req.model,
                "message": data["message"]["content"],
                "done": data.get("done", True),
                "eval_count": data.get("eval_count"),
                "eval_duration": data.get("eval_duration"),
            }
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="No se puede conectar a Ollama")
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


@app.post("/chat/conversation")
async def chat_conversation(req: ChatConversationRequest):
    """
    Endpoint para conversaciones multi-turno con historial de mensajes.
    """
    messages = []
    if req.system:
        messages.append({"role": "system", "content": req.system})
    messages.extend([{"role": m.role, "content": m.content} for m in req.messages])

    payload = {
        "model": req.model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": req.temperature},
    }

    async with httpx.AsyncClient(timeout=120) as client:
        try:
            resp = await client.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return {
                "model": req.model,
                "message": data["message"]["content"],
                "role": "assistant",
            }
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="No se puede conectar a Ollama")
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


@app.post("/generate")
async def generate(req: GenerateRequest):
    """
    Endpoint de generación de texto raw (sin formato de chat).
    """
    payload = {
        "model": req.model,
        "prompt": req.prompt,
        "stream": req.stream,
        "options": {"temperature": req.temperature},
    }

    if req.stream:
        return StreamingResponse(
            _stream_generate(payload),
            media_type="text/event-stream",
        )

    async with httpx.AsyncClient(timeout=120) as client:
        try:
            resp = await client.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return {
                "model": req.model,
                "response": data["response"],
                "done": data.get("done", True),
            }
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="No se puede conectar a Ollama")
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


async def _stream_chat(payload: dict):
    """Genera SSE desde el stream de Ollama /api/chat."""
    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream("POST", f"{OLLAMA_BASE_URL}/api/chat", json=payload) as resp:
            async for line in resp.aiter_lines():
                if line:
                    try:
                        chunk = json.loads(line)
                        token = chunk.get("message", {}).get("content", "")
                        done = chunk.get("done", False)
                        yield f"data: {json.dumps({'token': token, 'done': done})}\n\n"
                        if done:
                            break
                    except json.JSONDecodeError:
                        continue


async def _stream_generate(payload: dict):
    """Genera SSE desde el stream de Ollama /api/generate."""
    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream("POST", f"{OLLAMA_BASE_URL}/api/generate", json=payload) as resp:
            async for line in resp.aiter_lines():
                if line:
                    try:
                        chunk = json.loads(line)
                        token = chunk.get("response", "")
                        done = chunk.get("done", False)
                        yield f"data: {json.dumps({'token': token, 'done': done})}\n\n"
                        if done:
                            break
                    except json.JSONDecodeError:
                        continue
