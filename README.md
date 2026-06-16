# AI Interviewer Agent Platform

AI-powered interview platform using multi-agent orchestration with real LLM inference.

## Architecture

```
LOCAL (Streamlit UI) ──── HTTP ────→ JUPYTER CLOUD GPU
├── Dashboard                       ├── vLLM :8000 (DeepSeek-R1)
├── Resume Upload                   └── FastAPI :8001
├── Interview Session                   ├── /transcribe (Whisper V3)
├── Results & Reports                   ├── /synthesize (Kokoro TTS)
└── Settings                            └── /embed (BGE-M3)
```

## Models

| Model | Task | Port |
|-------|------|------|
| DeepSeek-R1 | Resume analysis, technical interviews, evaluation, scoring | 8000 |
| Whisper Large V3 | Speech-to-text | 8001 |
| Kokoro TTS | AI interviewer voice | 8001 |
| BGE-M3 | Resume embeddings, RAG retrieval | 8001 |
| FAISS | Vector search | 8001 |

## Local Setup

```bash
pip install -r requirements.txt
# Edit .env with your cloud endpoint URLs
streamlit run app/main.py
```

## Cloud Setup

See `cloud_setup/` directory:
```bash
# On Jupyter Cloud GPU:
pip install -r cloud_setup/requirements_cloud.txt
python cloud_setup/model_server.py  # Whisper + Kokoro + BGE-M3
python -m vllm.entrypoints.openai.api_server --model deepseek-ai/DeepSeek-R1 --port 8000
```

## Configuration

Copy `.env.example` to `.env` and update cloud endpoint URLs.
