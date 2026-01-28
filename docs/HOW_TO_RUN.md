# ScriptorAI - How to Run Guide

This guide walks you through setting up, running, and using ScriptorAI.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Running Scriptor Local](#running-scriptor-local)
4. [Installing the Chrome Extension](#installing-the-chrome-extension)
5. [Pairing Extension with Local App](#pairing-extension-with-local-app)
6. [Using ScriptorAI](#using-scriptorai)
7. [Features Overview](#features-overview)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before you begin, ensure you have:

- **macOS 12+** (for Scriptor Local)
- **Python 3.10+** ([Download](https://www.python.org/downloads/))
- **Node.js 18+** ([Download](https://nodejs.org/))
- **Google Chrome** browser
- **Git** (for cloning the repo)

Verify installations:
```bash
python3 --version   # Should be 3.10+
node --version      # Should be 18+
npm --version       # Should be 9+
```

---

## Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/cocokane/ScriptorAI.git
cd ScriptorAI
```

### Step 2: Set Up Scriptor Local (Backend)

```bash
# Navigate to local directory
cd local

# Create Python virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

**Note**: First run will download the embedding model (~90MB). This happens automatically.

### Step 3: Build the Chrome Extension

```bash
# Navigate to extension directory
cd ../extension

# Install Node.js dependencies
npm install

# Build for production
npm run build

# Or for development with auto-rebuild
npm run dev
```

This creates a `dist/` folder with the built extension.

---

## Running Scriptor Local

### Option 1: Development Server (Recommended for Testing)

```bash
cd local
source venv/bin/activate  # If not already activated
python run_server.py
```

You'll see output like:
```
Starting Scriptor Local server...
INFO:     Uvicorn running on http://127.0.0.1:52525
```

**Keep this terminal open while using ScriptorAI.**

### Option 2: Menu Bar App (macOS)

```bash
cd local
source venv/bin/activate
python run_menubar.py
```

This adds a menu bar icon with controls for:
- Start/Stop Server
- Show/Copy Token
- Open Storage Folder
- Open API Docs

### Finding Your Auth Token

The token is automatically generated on first run. Find it in:

1. **Terminal output** when starting the server
2. **Config file**: `~/.scriptor/config.json`
3. **Menu bar app**: Click "Show Token" or "Copy Token"

---

## Installing the Chrome Extension

1. Open Chrome and navigate to:
   ```
   chrome://extensions/
   ```

2. Enable **Developer mode** (toggle in top-right corner)

3. Click **"Load unpacked"**

4. Select the `extension/dist` folder from the project

5. The ScriptorAI icon should appear in your toolbar

6. **Pin the extension** for easy access:
   - Click the puzzle piece icon in Chrome toolbar
   - Click the pin icon next to ScriptorAI

---

## Pairing Extension with Local App

1. **Start Scriptor Local** (see above)

2. **Open the Scriptor Bar**:
   - Click the ScriptorAI extension icon, OR
   - Use keyboard shortcut: `Cmd+Shift+S` (Mac) / `Ctrl+Shift+S` (Windows)

3. You'll see "Not paired" status

4. **Get your token**:
   ```bash
   cat ~/.scriptor/config.json | grep auth_token
   ```
   Or copy from the terminal output when starting the server.

5. **Paste the token** in the extension and click "Pair"

6. You should see "Connected" status

---

## Using ScriptorAI

### Adding Papers

**Method 1: Context Menu**
1. Navigate to any PDF URL (e.g., arXiv paper)
2. Right-click on the page
3. Select "Add to Scriptor"

**Method 2: Side Panel**
1. Open a PDF in Chrome
2. Open the Scriptor Bar
3. Click "+ Add to Scriptor"

### Processing Papers (Batch Mode)

After adding papers, they need to be indexed for semantic search:

1. Papers show "pending" status initially
2. **Run batch processing**:
   - In terminal: The batch runs when you call the API
   - Or use the API directly:
     ```bash
     curl -X POST http://127.0.0.1:52525/api/batch/run \
       -H "Authorization: Bearer YOUR_TOKEN"
     ```
3. Wait for processing to complete
4. Papers will show "Ready" status when done

### Reading & Annotating Papers

1. Click any paper in the library to open it
2. Use the annotation tools:
   - **Select**: Click to select/move annotations
   - **Highlight**: Draw over text to highlight
   - **Rectangle**: Draw rectangular shapes
   - **Text**: Add text annotations
   - **Pen**: Freehand drawing
   - **Comment**: Add sticky note comments
   - **LaTeX**: Capture equations as LaTeX

### Semantic Search

1. Open a paper that's been processed ("Ready" status)
2. Enter a search query in the search box
3. Press Enter or click Search
4. The PDF shows a **heatmap overlay**:
   - Darker blue = higher relevance
   - Hover to see relevance score and text

### Viewing Highlights Collection

1. In the Scriptor Bar, click "Highlights" tab
2. See all highlights across all papers
3. Click to expand and see context
4. Click "Jump to highlight" to navigate

### Exporting

- **Export PDF**: Creates a flattened PDF with annotations burned in
- **BibTeX**: Copies citation to clipboard (if DOI found)
- **DOI Link**: Opens the paper's DOI page

### LaTeX Capture

1. Select the LaTeX tool (∑)
2. Draw a rectangle around an equation
3. The equation is converted to LaTeX
4. Copy to clipboard

**Requirements**:
- Install pix2tex: `pip install pix2tex`
- OR configure Gemini API key in settings

---

## Features Overview

| Feature | Description | Status |
|---------|-------------|--------|
| PDF Library | Store and organize papers | ✅ Ready |
| Collections | Group papers by topic | ✅ Ready |
| Highlights | 10-color highlighting | ✅ Ready |
| Annotations | Shapes, text, comments | ✅ Ready |
| Semantic Search | AI-powered text search | ✅ Ready |
| Heatmap | Visual relevance overlay | ✅ Ready |
| LaTeX Capture | Equation to LaTeX | ✅ Ready |
| PDF Export | Flattened with annotations | ✅ Ready |
| BibTeX | DOI-based citation | ✅ Ready |
| Highlights View | Cross-paper highlight browser | ✅ Ready |

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Cmd/Ctrl+Shift+S` | Toggle Scriptor Bar |

---

## API Reference

The local server exposes these endpoints at `http://127.0.0.1:52525/api/`:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check (no auth) |
| `/status` | GET | Detailed status |
| `/pair` | POST | Verify pairing |
| `/papers/add` | POST | Add paper from URL |
| `/papers/list` | GET | List all papers |
| `/papers/{id}` | GET | Get paper details |
| `/papers/{id}/pdf` | GET | Download PDF |
| `/annotations/save` | POST | Save annotation |
| `/annotations/{paper_id}` | GET | Get annotations |
| `/search/semantic` | POST | Semantic search |
| `/batch/run` | POST | Run batch jobs |
| `/latexify` | POST | Convert to LaTeX |
| `/export/pdf` | POST | Export annotated PDF |
| `/bibtex/{paper_id}` | GET | Get BibTeX |

Interactive API docs: http://127.0.0.1:52525/docs

---

## Troubleshooting

### "Scriptor Local not running"

**Cause**: The backend server isn't running.

**Solution**:
```bash
cd local
source venv/bin/activate
python run_server.py
```

### "Not paired" / Invalid Token

**Cause**: Token mismatch between extension and server.

**Solution**:
1. Get fresh token: `cat ~/.scriptor/config.json | grep auth_token`
2. Re-enter in extension pairing dialog

### "Semantic search disabled"

**Cause**: Paper hasn't been indexed yet.

**Solution**:
1. Run batch processing:
   ```bash
   curl -X POST http://127.0.0.1:52525/api/batch/run \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```
2. Wait for "Ready" status

### PDF not loading

**Cause**: PDF.js worker not found.

**Solution**:
1. Rebuild extension: `npm run build`
2. Reload extension in Chrome

### Extension not appearing

**Solution**:
1. Check `chrome://extensions/` for errors
2. Ensure `dist/` folder exists
3. Try "Load unpacked" again

### Port already in use

**Cause**: Another process using port 52525.

**Solution**:
```bash
# Find process using port
lsof -i :52525

# Kill it (replace PID)
kill -9 <PID>

# Or change port in ~/.scriptor/config.json
```

### Embedding model download fails

**Solution**:
```bash
# Pre-download the model
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

---

## Development Tips

### Watch Mode (Extension)

```bash
cd extension
npm run dev
```

Changes auto-rebuild. Reload extension in Chrome to apply.

### View API Logs

The terminal running `run_server.py` shows all API requests.

### Reset Everything

```bash
# Delete all data and config
rm -rf ~/.scriptor

# Next run will create fresh config
```

### Testing API Manually

```bash
# Health check
curl http://127.0.0.1:52525/api/health

# List papers (with auth)
curl http://127.0.0.1:52525/api/papers/list \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Getting Help

- **Issues**: https://github.com/cocokane/ScriptorAI/issues
- **Documentation**: See `/docs` folder
- **API Docs**: http://127.0.0.1:52525/docs (when server running)
