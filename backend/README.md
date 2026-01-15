# OBookLLM Backend

The backend service for OBookLLM, built with FastAPI and LangChain. It handles document ingestion, processing, audio transcription, vector embeddings, and RAG chat functionality.

## Features

-   **Universal Loader**: Automatically detects and processes a wide range of file formats.
-   **Audio Pipeline**: Uses `faster-whisper` for state-of-the-art speech-to-text transcription.
-   **RAG Engine**: Implements retrieval-augmented generation using ChromaDB and LangChain.
-   **Provider System**: Pluggable architecture for swapping LLM providers (Ollama, OpenAI, Anthropic, Gemini).
-   **Live Streaming**: Server-sent events (SSE) for real-time chat responses.

## Prerequisites

-   Python 3.10+
-   FFmpeg (for audio processing)
-   Tesseract OCR (for images/scanned PDFs)
-   Poppler Utils (for PDF conversion)
-   MongoDB
-   ChromaDB
-   Ollama (optional, for local inference)

## Setup

1.  **Install System Dependencies (Ubuntu/Debian)**:
    ```bash
    sudo apt-get install ffmpeg tesseract-ocr poppler-utils
    ```

2.  **Install Python Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the Server**:
    ```bash
    python -m src.main
    ```
    The API will be available at `http://localhost:8008`.

## API Documentation

Once running, visit `http://localhost:8008/docs` for the interactive Swagger UI.

**Key Endpoints:**

-   `GET /notebooks`: List all notebooks.
-   `POST /upload`: Upload a file to a notebook.
-   `POST /upload/url`: Process a URL (YouTube or Web).
-   `POST /chat`: Send a message to the RAG chat agent.
-   `DELETE /notebooks/{id}/sources/{name}`: Remove a source.

## Project Structure

-   `src/main.py`: Application entry point and API routes.
-   `src/rag.py`: Core RAG logic, embedding generation, and vector DB interaction.
-   `src/loaders.py`: Universal file parsing and transcription logic.
-   `src/providers/`: LLM provider interfaces.
-   `src/chains/`: LangChain definition and prompting strategies.
