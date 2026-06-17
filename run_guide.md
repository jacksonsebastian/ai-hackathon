# AI Interviewer Platform - Step-by-Step Run Guide

This guide walks you through cloning the repository and setting up both the **Cloud GPU environment** (for running the AI models) and the **Local environment** (for running the Streamlit UI).

---

## Step 1: Clone the Repository

Open your terminal and clone the repository to your machine.

```bash
git clone https://github.com/jacksonsebastian/ai-hackathon.git
cd ai-hackathon
```

---

## Step 2: Setup the Cloud GPU Environment

The AI models (DeepSeek-R1, Whisper, Kokoro TTS, BGE-M3) must run on a GPU-enabled machine (like your Jupyter Cloud endpoint).

1. **Navigate to the cloud environment directory:**
   Ensure you are in the `ai-hackathon` folder on your cloud machine.

2. **Install Cloud Dependencies:**
   ```bash
   pip install -r cloud_setup/requirements_cloud.txt
   ```

3. **Start the Multi-Model API Server:**
   This server hosts Whisper (Speech-to-Text), Kokoro (Text-to-Speech), and BGE-M3 (Embeddings).
   ```bash
   python cloud_setup/model_server.py
   ```
   *This will start a FastAPI server on port 8001.*

4. **Start the DeepSeek-R1 LLM Server:**
   Open a **new terminal tab** on your cloud machine and start vLLM for the core language model:
   ```bash
   python -m vllm.entrypoints.openai.api_server --model deepseek-ai/DeepSeek-R1 --port 8000
   ```

---

## Step 3: Setup the Local User Interface

The Streamlit front-end runs locally (or on a thin client) and connects to the APIs hosted on your Cloud GPU.

1. **Navigate to the local environment directory:**
   Ensure you are in the `ai-hackathon` folder on your local machine.

2. **Install Local Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables:**
   ```bash
   cp .env.example .env
   ```
   Open the `.env` file and **update the endpoint URLs** to point to your running Jupyter Cloud servers.
   ```env
   # Example:
   VLLM_BASE_URL=http://<YOUR_CLOUD_IP>:8000/v1
   WHISPER_API_URL=http://<YOUR_CLOUD_IP>:8001
   KOKORO_API_URL=http://<YOUR_CLOUD_IP>:8001
   EMBEDDING_API_URL=http://<YOUR_CLOUD_IP>:8001
   ```

4. **Initialize the Database:**
   Before running the app for the first time, initialize the local SQLite database.
   ```bash
   python -c "from app.database.schema import init_db; init_db()"
   ```

5. **Start the Streamlit App:**
   ```bash
   streamlit run app/main.py
   ```

---

## Step 4: Final Verification

1. Open the local URL provided by Streamlit (usually `http://localhost:8501`) in your browser.
2. Navigate to the **Settings** page in the left sidebar.
3. Verify that the **Model Status** indicators show as green/connected.
4. If you wish to use the Video Proctoring feature, enable it here and click "Save Configuration".
5. Navigate to **Upload Resume** to begin your first interview session!
