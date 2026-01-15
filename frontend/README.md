# OBookLLM Frontend

The modern, responsive web interface for OBookLLM, built with SvelteKit and TailwindCSS. It features a rich, application-like experience for managing notebooks and chatting with your data.

## Features

-   **Notebook Interface**: Clean, sidebar-based layout for switching between projects.
-   **Multi-Modal Viewer**:
    -   **PDFs**: Integrated PDF viewer.
    -   **Audio**: Custom audio player with interactive, synchronized transcript highlighting.
    -   **Code/Text**: Syntax-highlighted viewers for code and data files.
-   **Chat Experience**: Streaming chat interface with markdown support and distinctive source citations.
-   **Real-time Updates**: Optimistic UI updates and polling for processing status.
-   **Custom Server**: Node.js adapter with graceful shutdown and custom middleware support.
-   **Dark Mode**: Fully themed UI (currently dark-mode optimized).

## Tech Stack

-   **Framework**: SvelteKit (Svelte 5).
-   **Runtime**: Bun.
-   **Styling**: TailwindCSS (v4).
-   **Icons**: Iconify.

## Development

1.  **Install Dependencies**:
    ```bash
    bun install
    ```

2.  **Start Dev Server**:
    ```bash
    bun run dev
    ```

3.  **Build for Production**:
    ```bash
    bun run build
    ```

## Project Structure

-   `src/routes/`: SvelteKit File-based routing.
    -   `notebook/[id]/`: The main notebook view (chat + source panel).
    -   `(auth)/`: Login and Register pages.
-   `server/`: Custom Node.js server implementation (`server.ts`).
-   `src/lib/components/`: Reusable UI components.
    -   `SourceViewer.svelte`: Handles rendering of different file types.
    -   `AudioPlayer.svelte`: Custom audio controls.
    -   `ChatArea.svelte`: The main chat interface.
-   `src/lib/stores/`: Global state management.

## Environment Variables

The frontend relies on the backend URL, configurable via `.env` or Docker environment:

```env
PUBLIC_BACKEND_URL=http://localhost:8008
```
