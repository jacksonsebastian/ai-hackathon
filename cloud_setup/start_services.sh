#!/bin/bash
# ============================================================
# AI Interviewer – Cloud GPU Service Startup Script
# ============================================================
# Run this on your Jupyter Cloud GPU environment.
# Starts all 4 services:
#   1. vLLM (DeepSeek-R1)   → port 8000
#   2. Model Server (Whisper + Kokoro + BGE-M3) → port 8001
# ============================================================

set -e

echo "============================================"
echo "  AI Interviewer – Starting Cloud Services"
echo "============================================"
echo ""

# ── 1. Start vLLM for DeepSeek-R1 ────────────────────────────
echo "[1/2] Starting vLLM server with DeepSeek-R1..."
echo "      Model: deepseek-ai/DeepSeek-R1"
echo "      Port:  8000"
echo ""

nohup python -m vllm.entrypoints.openai.api_server \
    --model deepseek-ai/DeepSeek-R1 \
    --host 0.0.0.0 \
    --port 8000 \
    --gpu-memory-utilization 0.85 \
    --max-model-len 8192 \
    --dtype auto \
    --trust-remote-code \
    > logs/vllm.log 2>&1 &

VLLM_PID=$!
echo "      vLLM PID: $VLLM_PID"
echo ""

# ── 2. Start Model Server (Whisper + Kokoro + BGE-M3) ────────
echo "[2/2] Starting Model Server (Whisper V3 + Kokoro TTS + BGE-M3)..."
echo "      Port:  8001"
echo ""

# Wait for vLLM to start loading before starting model server
sleep 5

nohup python model_server.py \
    > logs/model_server.log 2>&1 &

MODEL_PID=$!
echo "      Model Server PID: $MODEL_PID"
echo ""

# ── Wait for services to be ready ─────────────────────────────
echo "Waiting for services to become ready..."
echo ""

# Wait for model server (faster to start)
for i in $(seq 1 60); do
    if curl -s http://localhost:8001/health > /dev/null 2>&1; then
        echo "[✓] Model Server is ready on port 8001"
        break
    fi
    sleep 2
done

# Wait for vLLM (takes longer to load model)
echo "Waiting for vLLM to load DeepSeek-R1 (this may take several minutes)..."
for i in $(seq 1 120); do
    if curl -s http://localhost:8000/v1/models > /dev/null 2>&1; then
        echo "[✓] vLLM (DeepSeek-R1) is ready on port 8000"
        break
    fi
    sleep 5
done

echo ""
echo "============================================"
echo "  All Services Started!"
echo "============================================"
echo ""
echo "  DeepSeek-R1 (vLLM):     http://0.0.0.0:8000/v1"
echo "  Whisper V3:              http://0.0.0.0:8001/transcribe"
echo "  Kokoro TTS:              http://0.0.0.0:8001/synthesize"
echo "  BGE-M3 Embeddings:      http://0.0.0.0:8001/embed"
echo "  Health Check:            http://0.0.0.0:8001/health"
echo "  Model Status:            http://0.0.0.0:8001/status"
echo ""
echo "  Logs:"
echo "    vLLM:         logs/vllm.log"
echo "    Model Server: logs/model_server.log"
echo ""
echo "  To connect from local Streamlit, update .env:"
echo "    VLLM_BASE_URL=http://<CLOUD_IP>:8000/v1"
echo "    WHISPER_API_URL=http://<CLOUD_IP>:8001"
echo "    KOKORO_API_URL=http://<CLOUD_IP>:8001"
echo "    EMBEDDING_API_URL=http://<CLOUD_IP>:8001"
echo ""
echo "============================================"
