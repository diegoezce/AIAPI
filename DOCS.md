# Gemma API Wrapper — Documentación

API wrapper construida con FastAPI para exponer un modelo Gemma corriendo localmente en Ollama, accesible desde internet via Cloudflare Tunnel.

---

## Stack

| Componente | Tecnología |
|------------|------------|
| LLM | Gemma (via Ollama) |
| API | FastAPI + Uvicorn |
| Túnel público | Cloudflare Tunnel |
| Lenguaje | Python 3.11+ |

---

## Arquitectura

```
Internet
   │
   ▼
Cloudflare Tunnel (HTTPS)
   │  https://xxx.trycloudflare.com
   ▼
FastAPI (localhost:8000)
   │
   ▼
Ollama (localhost:11434)
   │
   ▼
Gemma (modelo local)
```

El modelo corre completamente en la miniPC. Cloudflare actúa como proxy HTTPS sin necesidad de abrir puertos en el router ni tener IP pública fija.

---

## Instalación

### 1. Requisitos

- Python 3.11+
- [Ollama](https://ollama.com) instalado y corriendo
- Modelo descargado: `ollama pull gemma3:4b`
- [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/) (`cloudflared`)

### 2. Dependencias Python

```powershell
pip install -r requirements.txt
```

### 3. Configuración

Copia `.env.example` y define las variables de entorno:

```powershell
$env:OLLAMA_BASE_URL = "http://localhost:11434"
$env:DEFAULT_MODEL   = "gemma3:4b"
$env:API_KEY         = "tu-clave-secreta"   # dejar vacío para deshabilitar auth
$env:API_PORT        = "8000"
```

---

## Arranque

### 1. Iniciar Ollama

```powershell
ollama serve
```

### 2. Iniciar la API

```powershell
python run.py
```

La API queda disponible en `http://localhost:8000`.  
Documentación interactiva (Swagger): `http://localhost:8000/docs`

### 3. Exponer a internet con Cloudflare Tunnel

```powershell
cloudflared tunnel --url http://localhost:8000
```

Cloudflare genera una URL pública temporal:

```
https://xxxx-xxxx-xxxx.trycloudflare.com
```

> Esta URL cambia cada vez que se reinicia `cloudflared`. Para una URL fija, configurar un dominio propio en Cloudflare Zero Trust.

---

## Endpoints

### `GET /health`
Verifica si Ollama está disponible. No requiere autenticación.

```bash
curl https://tu-url.trycloudflare.com/health
```

### `GET /models`
Lista los modelos instalados en Ollama.

```bash
curl https://tu-url.trycloudflare.com/models \
  -H "X-API-Key: tu-clave-secreta"
```

### `POST /chat`
Mensaje simple con respuesta de Gemma.

**Body:**
```json
{
  "message": "I cannot log into the app",
  "model": "gemma3:4b",
  "system": "Instrucción de sistema opcional",
  "stream": false,
  "temperature": 0.7
}
```

**Respuesta:**
```json
{
  "model": "gemma3:4b",
  "message": "...",
  "done": true,
  "eval_count": 42,
  "eval_duration": 871571800
}
```

### `POST /chat/conversation`
Conversación multi-turno con historial de mensajes.

**Body:**
```json
{
  "messages": [
    {"role": "user", "content": "Hola, me llamo Diego"},
    {"role": "assistant", "content": "Hola Diego!"},
    {"role": "user", "content": "¿Cómo me llamo?"}
  ],
  "model": "gemma3:4b"
}
```

### `POST /generate`
Generación de texto raw sin formato de chat.

**Body:**
```json
{
  "prompt": "Escribe un poema sobre Python",
  "model": "gemma3:4b",
  "stream": false
}
```

---

## Autenticación

Todos los endpoints excepto `/health`, `/docs` y `/` requieren el header `X-API-Key`.

```bash
curl -X POST https://tu-url.trycloudflare.com/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: tu-clave-secreta" \
  -d '{"message": "Hola"}'
```

Si la variable de entorno `API_KEY` está vacía, la autenticación queda deshabilitada.

---

## Ejemplo: clasificador de mensajes

```bash
curl -X POST https://tu-url.trycloudflare.com/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: tu-clave-secreta" \
  -d '{
    "system": "Classify the user message. Reply with ONLY this JSON, nothing else: {\"category\":\"X\"} where X is one of: appointment, billing, technical, other. No markdown, no explanation.",
    "message": "I cannot log into the app",
    "model": "gemma3:1b"
  }'
```

**Respuesta esperada:**
```json
{"category": "technical"}
```

---

## Modelos disponibles

| Modelo | RAM requerida | Velocidad | Calidad |
|--------|--------------|-----------|---------|
| gemma3:1b | ~1.5 GB | Muy rápido | Básica |
| gemma3:4b | ~4 GB | Rápido | Buena |
| gemma3:12b | ~8 GB | Medio | Alta |
| gemma4 | ~10 GB+ | Lento | Muy alta |

Para tareas simples como clasificación, `gemma3:1b` o `gemma3:4b` son suficientes.

---

## Estructura del proyecto

```
AIAPI/
├── main.py          # API principal, endpoints y middleware de auth
├── config.py        # Configuración via variables de entorno
├── run.py           # Script de arranque
├── requirements.txt # Dependencias Python
├── .env.example     # Plantilla de variables de entorno
├── DOCS.md          # Esta documentación
└── techdebt.md      # Registro de deuda técnica
```
