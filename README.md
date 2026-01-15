<div align="center">

# OBookLLM - Open Source NotebookLLM

![Open Source](https://forthebadge.com/api/badges/generate?primaryLabel=OPEN+SOURCE&secondaryLabel=LOVE&secondaryIcon=heart&secondaryIconColor=%23D14836&primaryBGColor=%23555555&secondaryBGColor=%23ffffff&secondaryTextColor=%23555555)
![Version](https://forthebadge.com/api/badges/generate?primaryLabel=VERSION&secondaryLabel=0.3.4&primaryBGColor=%23555555&secondaryBGColor=%23ffffff&secondaryTextColor=%23555555)

</div>


OBookLLM is a powerful, self-hosted, offline-capable alternative to NotebookLLM. It allows you to upload documents (PDF, Docx, Text, Markdown), audio files, and even YouTube URLs to create interactive "notebooks." You can then chat with your sources using advanced RAG (Retrieval-Augmented Generation) powered by local LLMs (Ollama) or cloud providers (OpenAI, Anthropic, Gemini).

## Features

-   **Multi-Modal Ingestion**: Support for PDF, DOCX, TXT, MD, JSON, CSV, Excel, XML, YAML, HTML, and Source Code.
-   **Audio Transcription**: Built-in GPU-accelerated transcription for Audio files (MP3, WAV, etc.) and automatic YouTube video processing using `faster-whisper`.
-   **OCR Capabilities**: Automatically extracts text from scanned PDFs and Images using Tesseract.
-   **Interactive Chat**: Context-aware chat with your documents using RAG.
-   **Source Citations**: Responses include citations linking back to the exact segment in the source text or audio transcript.
-   **Podcast Generation**: (Coming Soon) Generate conversational audio summaries of your notebooks.
-   **Local First**: Designed to run 100% locally with Ollama and Docker, ensuring privacy.
-   **Flexible AI Providers**: Switch between Ollama, OpenAI, Anthropic, and Google Gemini for chat and embeddings.

## Tech Stack

-   **Frontend**: SvelteKit, TailwindCSS, TypeScript (Bun runtime).
-   **Backend**: FastAPI, Python 3.10.
-   **AI/ML**:
    -   **LLM Orchestration**: LangChain.
    -   **Vector DB**: ChromaDB.
    -   **Transcription**: Faster Whisper (CTranslate2).
    -   **Local Inference**: Ollama.
-   **Infrastructure**: Docker & Docker Compose.

## Hardware Requirements

Since OBookLLM processes audio and LLMs locally, hardware requirements depend on usage:

-   **Minimum**:
    -   **CPU**: Valid AVX2 support (Modern Intel/AMD CPUs)
    -   **RAM**: 8GB (Running small quantized models, e.g., Llama 3 8B q4_0)
    -   **GPU**: None (CPU-only inference is slower but functional)
    -   **Storage**: 10GB free space

-   **Recommended (For best performance)**:
    -   **RAM**: 16GB+
    -   **GPU**: NVIDIA GPU with 8GB+ VRAM (for fast Whisper transcription & LLM inference)
    -   **Storage**: SSD

## Quick Start (Docker)

The easiest way to run OBookLLM is with Docker Compose. This starts the Frontend, Backend, Database, Vector DB, and Ollama services.

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/yourusername/OBookLLM.git
    cd OBookLLM
    ```

2.  **Run with Docker Compose**:
    ```bash
    # Ensure you have NVIDIA Container Toolkit installed if you want GPU support
    docker-compose up --build -d
    ```

3.  **Access the App**:
    -   **Frontend**: [http://localhost:3000](http://localhost:3000)

## Table of Contents

-   [Frontend Documentation](./frontend/README.md)
-   [Backend Documentation](./backend/README.md)
-   [Hardware Requirements](#hardware-requirements)
-   [Manual Installation](#manual-installation)
-   [Configuration](#configuration)
-   [Roadmap](#roadmap)

## Roadmap

-   [x] Basic RAG (PDF, Text, Markdown)
-   [x] Audio Transcription (Faster Whisper)
-   [x] YouTube Integration
-   [x] OCR Support (Tesseract)
-   [x] Docker support
-   [ ] Podcast Generation (Conversational Audio)
-   [ ] Web Search Agent (Search Integration)

## Manual Installation

### Backend

1.  Navigate to `backend/`:
    ```bash
    cd backend
    ```
2.  Create virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate
    ```
3.  Install dependencies:
    ```bash
    # Requires system deps: ffmpeg, tesseract-ocr, poppler-utils
    pip install -r requirements.txt
    ```
4.  Run Server:
    ```bash
    python -m src.main
    ```

### Frontend

1.  Navigate to `frontend/`:
    ```bash
    cd frontend
    ```
2.  Install dependencies:
    ```bash
    bun install
    ```
3.  Run Dev Server:
    ```bash
    bun run dev
    ```

## Configuration

### Backend `.env`
Create a `.env` file in the `backend/` directory:
```env
MONGODB_URI=mongodb://localhost:27017
CHROMA_HOST=localhost
CHROMA_PORT=8000
OLLAMA_HOST=http://localhost:11434
```

### Frontend `.env`
Create a `.env` file in the `frontend/` directory:
```env
AUTH_SECRET=your-secure-secret-key-here
AUTH_URL=http://localhost:3000
MONGODB_URI=mongodb://localhost:27017
PUBLIC_BACKEND_URL=http://localhost:8008
PORT=3000
```

> **Note**: For production deployments, ensure `AUTH_SECRET` is a secure random string. You can generate one with: `openssl rand -base64 32`

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
