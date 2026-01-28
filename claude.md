# ScriptorAI - Project Context for Claude

## Project Overview

ScriptorAI is a "research paper IDE inside Chrome" consisting of:
1. **Chrome Extension (MV3)** - Side panel UI ("Scriptor Bar") + PDF Reader tab
2. **Scriptor Local** - macOS companion app (Python/FastAPI) for storage, AI processing, and exports

## Architecture

```
ScriptorAI/
├── extension/           # Chrome Extension (TypeScript + React)
│   ├── src/
│   │   ├── background.ts        # Service worker
│   │   ├── pages/
│   │   │   ├── sidepanel/       # Scriptor Bar React components
│   │   │   └── reader/          # PDF.js viewer with annotations
│   │   ├── utils/api.ts         # API client for Scriptor Local
│   │   ├── types/index.ts       # TypeScript type definitions
│   │   └── styles/              # CSS styles
│   ├── public/                  # Static assets, manifest.json
│   └── package.json
│
├── local/               # Scriptor Local (Python)
│   ├── scriptor_local/
│   │   ├── app.py               # FastAPI application
│   │   ├── config.py            # Configuration management
│   │   ├── api/routes.py        # API endpoints
│   │   ├── models/database.py   # SQLite schema and operations
│   │   └── services/
│   │       ├── text_extraction.py   # PyMuPDF text extraction
│   │       ├── embeddings.py        # Sentence-transformers embeddings
│   │       ├── batch_processor.py   # Job queue processing
│   │       ├── latexify.py          # Equation to LaTeX conversion
│   │       └── export.py            # PDF export, BibTeX
│   ├── run_server.py            # Dev server launcher
│   └── requirements.txt
│
└── docs/                # Documentation
```

## Key Technologies

### Extension
- **React 18** - UI components
- **TypeScript** - Type safety
- **PDF.js** - PDF rendering
- **Webpack** - Bundling
- **Chrome Extension Manifest V3** - Side panel, service worker

### Local Backend
- **FastAPI** - Async HTTP API
- **SQLite + aiosqlite** - Database
- **PyMuPDF (fitz)** - PDF processing
- **sentence-transformers** - Text embeddings
- **pix2tex** (optional) - LaTeX OCR
- **Gemini API** (optional) - LaTeX fallback

## Data Flow

1. User adds PDF via context menu or side panel
2. Extension sends URL to Scriptor Local `/api/papers/add`
3. Local downloads PDF, extracts metadata, stores in SQLite
4. Jobs queued: EXTRACT_TEXT → EMBED
5. User clicks "Run Batch" to process jobs
6. Embeddings computed with sentence-transformers
7. Semantic search queries embeddings, returns scored chunks
8. Reader renders heatmap overlay based on scores

## API Authentication

- Server binds to `127.0.0.1:52525` only (localhost)
- Token-based auth: `Authorization: Bearer <token>`
- Token generated on first run, stored in `~/.scriptor/config.json`
- Extension stores token in `chrome.storage.local`

## Database Schema

```sql
papers (id, title, authors, year, doi, source_url, local_pdf_path,
        added_at, indexed_at, embeddings_ready, status, collection)

annotations (id, paper_id, page, type, geometry, color, opacity,
             text_content, created_at, updated_at)

chunks (id, paper_id, page, bbox, text, chunk_index)

embeddings (chunk_id, vector)

jobs (id, paper_id, type, status, priority, error, created_at,
      started_at, finished_at)
```

## Side Panel States

- **no_pdf**: Normal browsing → shows library only
- **unsaved_pdf**: On PDF URL → shows "Add to Scriptor" button
- **saved_pdf**: In reader tab → shows tools + library

## Common Development Tasks

### Running the backend
```bash
cd local
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python run_server.py
```

### Building the extension
```bash
cd extension
npm install
npm run dev   # Watch mode
npm run build # Production
```

### Loading in Chrome
1. Go to `chrome://extensions/`
2. Enable Developer mode
3. Load unpacked → select `extension/dist`

## Important Constraints

1. **No Google Scholar scraping** - Use DOI content negotiation for BibTeX
2. **Localhost only** - Server never exposed externally
3. **Batch processing** - Heavy AI work only on user trigger
4. **Extension can't start processes** - Local app must run independently

## File Naming Conventions

- React components: PascalCase (`SidePanel.tsx`)
- Utilities: camelCase (`api.ts`)
- Python modules: snake_case (`batch_processor.py`)
- CSS: kebab-case in class names (`.paper-item`)

## Testing

- Backend: pytest with pytest-asyncio
- Extension: Jest for unit tests

## Environment Variables / Config

Config stored at `~/.scriptor/config.json`:
```json
{
  "storage_dir": "~/.scriptor/storage",
  "auth_token": "<generated>",
  "server_port": 52525,
  "gemini_api_key": "",
  "embedding_model": "all-MiniLM-L6-v2"
}
```

## Common Issues

1. **"Scriptor Local not running"** - Start with `python run_server.py`
2. **"Not paired"** - Copy token from config.json to extension
3. **Semantic search disabled** - Run batch processing first
4. **PDF not rendering** - Check PDF.js worker in dist folder
