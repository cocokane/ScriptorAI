# ScriptorAI

A "research paper IDE inside Chrome" - a Chrome extension with a local macOS companion app for managing, annotating, and semantically searching research papers.

## Features (V1)

- **Add to Scriptor**: Save online PDFs to your local library
- **Scriptor Bar** (Side Panel): Library browser with collection grouping
- **Reader Tab**: PDF viewer with annotation tools and heatmap overlay
- **Annotation Tools**: Highlight (10 colors), shapes, text, comments, pen
- **Semantic Search**: AI-powered search with relevance heatmap
- **LaTeXify**: Convert equation images to LaTeX code
- **Export**: Flattened PDF export with annotations, BibTeX citation

## Architecture

```
ScriptorAI/
├── extension/          # Chrome Extension (MV3)
│   ├── src/
│   │   ├── pages/
│   │   │   ├── sidepanel/   # Scriptor Bar UI
│   │   │   └── reader/      # PDF Reader with annotations
│   │   ├── utils/           # API client, utilities
│   │   └── types/           # TypeScript types
│   └── public/              # Static assets, manifest
│
├── local/              # Scriptor Local (macOS app)
│   └── scriptor_local/
│       ├── api/             # FastAPI routes
│       ├── models/          # SQLite database
│       └── services/        # Text extraction, embeddings, etc.
│
└── docs/               # Documentation
```

## Quick Start

### Prerequisites

- macOS 12+ (for Scriptor Local)
- Python 3.10+
- Node.js 18+
- Chrome browser

### 1. Set Up Scriptor Local

```bash
cd local

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the server
python run_server.py
```

The server will start on `http://127.0.0.1:52525`. Your auth token will be displayed in the terminal and saved to `~/.scriptor/config.json`.

### 2. Build the Chrome Extension

```bash
cd extension

# Install dependencies
npm install

# Build for development (with watch)
npm run dev

# Or build for production
npm run build
```

### 3. Load the Extension in Chrome

1. Open Chrome and go to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top right)
3. Click "Load unpacked"
4. Select the `extension/dist` folder
5. Pin the ScriptorAI extension for easy access

### 4. Pair Extension with Scriptor Local

1. Click the ScriptorAI extension icon to open the side panel
2. Copy the auth token from Scriptor Local terminal (or `~/.scriptor/config.json`)
3. Paste into the pairing input and click "Pair"
4. You should see "Connected" status

### 5. Add Your First Paper

1. Navigate to a PDF URL (e.g., arXiv paper)
2. Right-click → "Add to Scriptor" or use the side panel button
3. Open Scriptor Local and click "Run Batch" to index
4. Click the paper in your library to open in Reader

## Usage Guide

### Side Panel States

- **Normal browsing**: Shows library list only
- **On unsaved PDF**: Shows "Add to Scriptor" button
- **On saved paper**: Full tool panel + library

### Annotation Tools

| Tool | Description |
|------|-------------|
| Select | Select and move annotations |
| Highlight | Text highlight (10 colors) |
| Rectangle | Draw rectangle shapes |
| Text | Add text annotations |
| Pen | Freehand drawing |
| Comment | Sticky note comments |
| LaTeX | Capture region → LaTeX |

### Semantic Search

1. Ensure paper is indexed (run batch processing)
2. Enter query in search bar
3. Press Enter or click Search
4. Heatmap overlay shows relevance intensity
5. Hover over highlighted regions for details

### Keyboard Shortcuts

- `Cmd+Shift+S` (Mac) / `Ctrl+Shift+S` (Win): Toggle Scriptor Bar

## Scriptor Local API

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check (no auth) |
| `/api/status` | GET | Detailed status |
| `/api/pair` | POST | Verify pairing |
| `/api/papers/add` | POST | Add new paper |
| `/api/papers/list` | GET | List all papers |
| `/api/papers/:id` | GET | Get paper details |
| `/api/papers/:id/pdf` | GET | Download PDF |
| `/api/annotations/save` | POST | Save annotation |
| `/api/annotations/:paper_id` | GET | Get annotations |
| `/api/search/semantic` | POST | Semantic search |
| `/api/batch/run` | POST | Run batch jobs |
| `/api/latexify` | POST | Convert to LaTeX |
| `/api/export/pdf` | POST | Export annotated PDF |
| `/api/bibtex/:paper_id` | GET | Get BibTeX citation |

### Authentication

All endpoints (except `/health`) require Bearer token:
```
Authorization: Bearer <your-token>
```

## Configuration

Scriptor Local config is stored at `~/.scriptor/config.json`:

```json
{
  "storage_dir": "~/.scriptor/storage",
  "auth_token": "<generated-token>",
  "server_port": 52525,
  "gemini_api_key": "",
  "embedding_model": "all-MiniLM-L6-v2"
}
```

### Storage Directories

- `PDFs/` - Downloaded PDF files
- `Exports/` - Exported annotated PDFs
- `Models/` - AI model cache
- `DB/` - SQLite database

## Enabling LaTeX Conversion

### Option 1: pix2tex (Local, Free)

```bash
pip install pix2tex
```

### Option 2: Gemini API (Cloud)

1. Get API key from https://makersuite.google.com/app/apikey
2. Add to config or via API:
```bash
curl -X POST http://127.0.0.1:52525/api/config/update \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"gemini_api_key": "your-key"}'
```

## Security Notes

- **Localhost only**: Server binds to 127.0.0.1 only
- **Token auth**: All API requests require valid token
- **No remote access**: Extension cannot be accessed externally
- **Data local**: All data stored on your machine

## Batch Processing

Papers are indexed on-demand via batch processing:

1. "Add to Scriptor" queues: EXTRACT_TEXT, EXTRACT_DOI, EMBED
2. Processing happens when you click "Run Batch"
3. This keeps models unloaded until needed (battery-friendly)

## BibTeX / DOI

We use safe, approved methods for citation retrieval:

1. **DOI extraction**: Regex scan of PDF text
2. **DOI → BibTeX**: Content negotiation via doi.org
3. **Manual input**: Parse pasted citation text

**Note**: We do NOT scrape Google Scholar to avoid ToS issues.

## Troubleshooting

### "Scriptor Local not running"

- Ensure the server is started: `python run_server.py`
- Check the port isn't in use: `lsof -i :52525`

### "Not paired"

- Copy token from server terminal
- Or check `~/.scriptor/config.json` for `auth_token`

### "Semantic search disabled"

- Paper needs batch processing first
- Click "Run Batch" in Scriptor Local

### PDF not rendering

- Check browser console for errors
- Ensure PDF.js worker is in dist folder

### Annotation not saving

- Check server is running
- Check browser console for API errors

## Development

### Extension Development

```bash
cd extension
npm run dev  # Watch mode
```

### Local Development

```bash
cd local
source venv/bin/activate
python run_server.py
```

### Running Menu Bar App (Optional)

```bash
python run_menubar.py
```

---

# Scriptor.ai Roadmap

## Phase 1: Heatmap based AI PDF Annotation (V1 - Current)
**Core Features**
- **Drag and drop PDFs**:
  Upload research papers or drag-and-drop readable PDFs for analysis.
- **Commenting and Highlighting**:
  Annotate sections with highlighting or comments.
- **AI highlight Heatmaps**:
  AI highlights sections by topic using preset color palettes (e.g., blues, reds, greens). Relevance intensity scales from light (low) to dark (high).
- **DOI-to-Paper**:
  Enter a DOI to auto-fetch open-access PDFs with preserved formatting.

**Example Workflow**
1. Upload a CRISPR research paper.
2. Search for `off-target effects` (assigned to **blue** palette).
3. Dark blue highlights appear on pages discussing error rates.
4. Hover over a dense section to see relevance score.

---

## Phase 2: Structured Knowledge Assembly
**Core Features**
  - **PDF-to-Text**:
    Convert PDFs to searchable text.
- **Drag-and-Drop Guides**:
  Organize highlights/images into study guides. Rearrange blocks to match your narrative flow.
- **Auto-Citation**:
  Exported sections include original paper citations. For a particular section snippet, if there is a citation, it will be picked up and added automatically (e.g., *"Source: Zhang et al. 2023, p.12"*).
- **Multi-Format Export**:
  Save as Markdown (for notes) or LaTeX-ready PDF (for academic reuse).

**Example Workflow**
1. Select 5 highlights from a quantum computing paper.
2. Drag a qubit diagram into position 3.
3. Export as PDF with headings: *"Problem → Methods → Results"*.

---

## Phase 3: Review Paper Synthesis
**Core Features**
- **Multi-Paper Compilation**:
  Select 10-50 papers from your library. Extract key claims/figures by theme (e.g., *"error correction methods"*).
- **AI-Powered Narrative**:
  Auto-generate a review paper with logical flow. Original text is preserved; AI adds transitions like *"Building on X, Y demonstrates..."*.
- **Conflict Detection**:
  Flag contradictory findings (e.g., *"Paper A claims 95% accuracy vs Paper B's 82%"*).

**Example Workflow**
1. Choose 20 papers on *"mRNA vaccine stability"*.
2. Compile sections tagged `lyophilization` and `temperature response`.
3. Generate PDF with:
   - Section 1: *"Lyophilization Advances (2020-2023)"*
   - Section 2: *"Contested Optimal Storage Temperatures"*

---

## License

MIT License

## Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Submit pull request

---

Built with FastAPI, React, PDF.js, and sentence-transformers.
