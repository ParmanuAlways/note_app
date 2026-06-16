# AI Notes & Scheduler

A single-user web app that turns captured work information (scanned letters,
typed/voice notes) into a confirmed, searchable internal calendar — running
**entirely offline on an air-gapped network**. All AI runs locally. No data
ever leaves the host.

Full spec: [`AI-Notes-Scheduler-Requirements-v1.md`](./AI-Notes-Scheduler-Requirements-v1.md).

## Stack

| Layer | Tech |
|---|---|
| Backend | FastAPI (Python 3.12) |
| Frontend | React + Vite + FullCalendar |
| Auth | Keycloak (auth only, v1) |
| Database | PostgreSQL + pgvector |
| Doc extraction | Qwen2.5-VL via vLLM (OpenAI-compatible) |
| Voice | WhisperLive (faster-whisper, streaming) |
| Embeddings | bge-m3 via vLLM |

The model layer is **swappable by config** (`.env`) — no model name is
hardcoded anywhere (NFR-7). Swap a model/hardware = edit `.env`, restart.

## Layout

```
backend/    FastAPI app — app/inference is the swappable model layer
frontend/   React + FullCalendar client
docker-compose.yml   full stack
.env.example         all config incl. inference endpoints
```

## Develop (on the internet PC)

```bash
# backend
cd backend && python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8011

# frontend
cd frontend && npm install && npm run dev
```

The app runs in **degraded mode** with no models/DB present: health, status,
calendar, and (Phase 1+) manual entry all work without a GPU (NFR-9).

## Build & export to the air-gapped host

The whole point: build with internet, run without it, minimum hassle.

### 1. Build images and gather model weights (internet PC)

```bash
cp .env.example .env            # adjust passwords/timezone
docker compose build            # builds backend + frontend images

# Pull the model service images
docker pull pgvector/pgvector:pg16
docker pull quay.io/keycloak/keycloak:26.0
docker pull vllm/vllm-openai:v0.6.6
docker pull ghcr.io/collabora/whisperlive-gpu:latest

# Pre-download model weights into ./models (so HF_HUB_OFFLINE works air-gapped)
#   - Qwen2.5-VL-7B-Instruct   (~15GB fp16, or an AWQ quant ~6GB)
#   - bge-m3                    (~2GB)
#   - whisper large-v3-turbo    (~1.5GB)
# e.g. with huggingface-cli download <repo> --local-dir ./models/<repo>
```

### 2. Package

```bash
docker save \
  note_app-backend note_app-frontend \
  pgvector/pgvector:pg16 quay.io/keycloak/keycloak:26.0 \
  vllm/vllm-openai:v0.6.6 ghcr.io/collabora/whisperlive-gpu:latest \
  | gzip > app-images.tar.gz

tar czf models.tar.gz ./models
# Transfer app-images.tar.gz, models.tar.gz, docker-compose.yml, .env to media.
```

### 3. Load and run (air-gapped host)

> Prerequisite: the host has **Docker** + **nvidia-container-toolkit**
> installed (GPU passthrough). If it does not, switch to the native-install
> fallback (pip wheel bundle + prebuilt `frontend/dist`).

```bash
docker load < app-images.tar.gz
tar xzf models.tar.gz
docker compose up -d
# App at http://<host>/   ·   Keycloak at http://<host>:8080/
```

## Air-gap guarantees (NFR-3 / AC-21)

- Model services run with `HF_HUB_OFFLINE=1` — no runtime downloads.
- Frontend bundles all assets (fonts, FullCalendar) at build — **no CDN**.
- Compose uses an internal-only network; only ports 80 + 8080 are published.
- Verify: run with the host's network cable out, confirm full function, and
  monitor for zero outbound connections.

## Build phases

- [x] **Phase 0** — Foundation: structure, inference layer, schema, status, shell
- [ ] **Phase 1** — Non-AI backbone (upload, manual entry, calendar, trash, audit)
- [ ] **Phase 2** — AI document extraction + confirm screen
- [ ] **Phase 3** — Voice transcription (streaming)
- [ ] **Phase 4** — Search & linking
- [ ] **Phase 5** — Polish & verify
