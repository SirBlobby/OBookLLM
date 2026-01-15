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

Create a `.env` file in the frontend root directory with the following variables:

```env
# Authentication (Auth.js)
AUTH_SECRET=your-secure-secret-key-here
AUTH_URL=http://localhost:3000

# Database
MONGODB_URI=mongodb://localhost:27017

# Backend API
PUBLIC_BACKEND_URL=http://localhost:8008

# Server
PORT=3000
```

| Variable | Description |
|----------|-------------|
| `AUTH_SECRET` | Secret key for signing JWT tokens. Generate with `openssl rand -base64 32` |
| `AUTH_URL` | Full URL where the frontend is hosted (used by Auth.js) |
| `MONGODB_URI` | MongoDB connection string for user authentication |
| `PUBLIC_BACKEND_URL` | URL to the backend API (exposed to client-side) |
| `PORT` | Port for the frontend server |

> **Note**: In Docker deployments, environment variables are set in `docker-compose.yml`.
