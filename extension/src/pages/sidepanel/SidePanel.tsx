import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../../utils/api';
import type { Paper, Annotation, PanelState, AnnotationTool, HighlightColor } from '../../types';
import { HIGHLIGHT_COLORS } from '../../types';

// View modes for the library section
type LibraryView = 'papers' | 'highlights';

// Highlight with paper info for the collection view
interface HighlightWithContext {
  annotation: Annotation;
  paper: Paper;
  contextText?: string;
}

export function SidePanel() {
  // Connection state
  const [connected, setConnected] = useState(false);
  const [paired, setPaired] = useState(false);
  const [pairingToken, setPairingToken] = useState('');
  const [pairingError, setPairingError] = useState('');

  // UI state
  const [panelState, setPanelState] = useState<PanelState>('no_pdf');
  const [loading, setLoading] = useState(true);
  const [libraryView, setLibraryView] = useState<LibraryView>('papers');

  // Papers
  const [papers, setPapers] = useState<Paper[]>([]);
  const [activePaper, setActivePaper] = useState<Paper | null>(null);
  const [collections, setCollections] = useState<string[]>(['default']);
  const [activeCollection, setActiveCollection] = useState<string | null>(null);

  // Highlights collection
  const [allHighlights, setAllHighlights] = useState<HighlightWithContext[]>([]);
  const [loadingHighlights, setLoadingHighlights] = useState(false);
  const [expandedHighlight, setExpandedHighlight] = useState<string | null>(null);

  // Tools
  const [activeTool, setActiveTool] = useState<AnnotationTool>('select');
  const [activeColor, setActiveColor] = useState<HighlightColor>(HIGHLIGHT_COLORS[0]);

  // Search
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);

  // Current tab info
  const [currentTabUrl, setCurrentTabUrl] = useState<string>('');
  const [currentTabTitle, setCurrentTabTitle] = useState<string>('');

  // Initialize
  useEffect(() => {
    initializePanel();

    // Listen for updates
    chrome.runtime.onMessage.addListener((message) => {
      if (message.type === 'PAPERS_UPDATED') {
        loadPapers();
      }
    });
  }, []);

  async function initializePanel() {
    setLoading(true);
    try {
      await api.init();

      // Check connection
      try {
        await api.checkHealth();
        setConnected(true);

        // Check if paired
        if (api.isPaired()) {
          setPaired(true);
          await loadPapers();
        }
      } catch {
        setConnected(false);
      }

      // Get current tab info
      await updateTabInfo();

    } catch (error) {
      console.error('Init error:', error);
    } finally {
      setLoading(false);
    }
  }

  async function updateTabInfo() {
    try {
      const response = await chrome.runtime.sendMessage({ type: 'GET_CURRENT_TAB_INFO' });
      if (response) {
        setCurrentTabUrl(response.url || '');
        setCurrentTabTitle(response.title || '');

        // Determine panel state
        if (response.isPdf) {
          // Check if this PDF is in our library
          const urlPaperId = response.url?.match(/paperId=([^&]+)/)?.[1];
          if (urlPaperId) {
            setPanelState('saved_pdf');
            // Load the paper
            const paper = await api.getPaper(urlPaperId);
            setActivePaper(paper);
          } else {
            setPanelState('unsaved_pdf');
          }
        } else {
          setPanelState('no_pdf');
        }
      }
    } catch (error) {
      console.error('Tab info error:', error);
    }
  }

  async function loadPapers() {
    try {
      const { papers: fetchedPapers } = await api.listPapers(activeCollection || undefined);
      setPapers(fetchedPapers);

      // Extract unique collections
      const uniqueCollections = [...new Set(fetchedPapers.map(p => p.collection))];
      setCollections(['All', ...uniqueCollections]);
    } catch (error) {
      console.error('Load papers error:', error);
    }
  }

  async function loadAllHighlights() {
    setLoadingHighlights(true);
    try {
      const { papers: allPapers } = await api.listPapers();
      const highlightsWithContext: HighlightWithContext[] = [];

      // Load annotations for each paper
      for (const paper of allPapers) {
        try {
          const { annotations } = await api.getAnnotations(paper.id);

          // Filter only highlights
          const highlights = annotations.filter(a => a.type === 'highlight');

          for (const highlight of highlights) {
            highlightsWithContext.push({
              annotation: highlight,
              paper,
              contextText: highlight.text_content || undefined,
            });
          }
        } catch (e) {
          console.error(`Failed to load annotations for paper ${paper.id}:`, e);
        }
      }

      // Sort by most recent first
      highlightsWithContext.sort((a, b) =>
        new Date(b.annotation.updated_at).getTime() - new Date(a.annotation.updated_at).getTime()
      );

      setAllHighlights(highlightsWithContext);
    } catch (error) {
      console.error('Load highlights error:', error);
    } finally {
      setLoadingHighlights(false);
    }
  }

  function handleViewHighlights() {
    setLibraryView('highlights');
    loadAllHighlights();
  }

  function handleViewPapers() {
    setLibraryView('papers');
  }

  function handleHighlightClick(highlight: HighlightWithContext) {
    // Toggle expanded state
    if (expandedHighlight === highlight.annotation.id) {
      setExpandedHighlight(null);
    } else {
      setExpandedHighlight(highlight.annotation.id);
    }
  }

  function handleJumpToHighlight(highlight: HighlightWithContext) {
    // Open the paper in reader and scroll to the highlight
    chrome.runtime.sendMessage({
      type: 'OPEN_READER',
      payload: {
        paperId: highlight.paper.id,
        scrollTo: {
          page: highlight.annotation.page,
          bbox: highlight.annotation.geometry,
        }
      }
    });
  }

  async function handlePair() {
    if (!pairingToken.trim()) {
      setPairingError('Please enter a token');
      return;
    }

    try {
      const success = await api.pair(pairingToken.trim());
      if (success) {
        setPaired(true);
        setPairingError('');
        await loadPapers();
      } else {
        setPairingError('Invalid token. Please check and try again.');
      }
    } catch (error) {
      setPairingError('Failed to pair. Is Scriptor Local running?');
    }
  }

  async function handleAddPaper() {
    if (!currentTabUrl) return;

    try {
      setLoading(true);
      const result = await api.addPaper(currentTabUrl, currentTabTitle);
      await loadPapers();
      setPanelState('saved_pdf');
      setActivePaper(result as unknown as Paper);
    } catch (error) {
      alert(`Failed to add paper: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setLoading(false);
    }
  }

  async function handleOpenPaper(paper: Paper) {
    setActivePaper(paper);
    // Open in reader tab
    chrome.runtime.sendMessage({
      type: 'OPEN_READER',
      payload: { paperId: paper.id }
    });
  }

  async function handleSemanticSearch() {
    if (!activePaper || !searchQuery.trim()) return;

    if (!activePaper.embeddings_ready) {
      alert('Paper not ready for semantic search. Run batch processing first.');
      return;
    }

    setIsSearching(true);
    try {
      const results = await api.semanticSearch(activePaper.id, searchQuery);
      // Send results to reader tab
      chrome.runtime.sendMessage({
        type: 'SEARCH_RESULTS',
        payload: results
      });
    } catch (error) {
      alert(`Search failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsSearching(false);
    }
  }

  async function handleExportPdf() {
    if (!activePaper) return;

    try {
      const blob = await api.exportPdf(activePaper.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${activePaper.title}_annotated.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      alert(`Export failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  async function handleGetBibtex() {
    if (!activePaper) return;

    try {
      const result = await api.getBibtex(activePaper.id);
      if (result.bibtex) {
        await navigator.clipboard.writeText(result.bibtex);
        alert('BibTeX copied to clipboard!');
      } else {
        alert(result.message || 'No BibTeX available');
      }
    } catch (error) {
      alert(`Failed to get BibTeX: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  function handleToolSelect(tool: AnnotationTool) {
    setActiveTool(tool);
    // Notify reader tab
    chrome.runtime.sendMessage({
      type: 'SET_TOOL',
      payload: { tool, color: activeColor }
    });
  }

  function handleColorSelect(color: HighlightColor) {
    setActiveColor(color);
    chrome.runtime.sendMessage({
      type: 'SET_COLOR',
      payload: { color }
    });
  }

  // Loading state
  if (loading) {
    return (
      <div className="scriptor-bar">
        <div className="scriptor-header">
          <h1>Scriptor Bar</h1>
        </div>
        <div className="empty-state">
          <div className="loading-spinner"></div>
          <p style={{ marginTop: 12 }}>Loading...</p>
        </div>
      </div>
    );
  }

  // Not connected
  if (!connected) {
    return (
      <div className="scriptor-bar">
        <div className="scriptor-header">
          <h1>Scriptor Bar</h1>
        </div>
        <div className="connection-status error">
          <span className="status-dot"></span>
          Scriptor Local not running
        </div>
        <div className="pairing-section">
          <h2>Connection Required</h2>
          <p>Please start Scriptor Local on your Mac to use ScriptorAI.</p>
          <p style={{ fontSize: 12, color: '#999', marginTop: 16 }}>
            If you haven't installed it yet, follow the setup instructions in the documentation.
          </p>
          <button className="btn btn-secondary" onClick={initializePanel} style={{ marginTop: 16 }}>
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  // Not paired
  if (!paired) {
    return (
      <div className="scriptor-bar">
        <div className="scriptor-header">
          <h1>Scriptor Bar</h1>
        </div>
        <div className="connection-status">
          <span className="status-dot"></span>
          Not paired
        </div>
        <div className="pairing-section">
          <h2>Pair with Scriptor Local</h2>
          <p>Enter the token shown in the Scriptor Local app to connect.</p>
          <input
            type="text"
            placeholder="Paste your token here"
            value={pairingToken}
            onChange={(e) => setPairingToken(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handlePair()}
          />
          {pairingError && <p style={{ color: '#dc3545', fontSize: 12 }}>{pairingError}</p>}
          <button className="btn btn-primary" onClick={handlePair}>
            Pair
          </button>
        </div>
      </div>
    );
  }

  // Main panel
  return (
    <div className="scriptor-bar">
      <div className="scriptor-header">
        <h1>Scriptor Bar</h1>
        <div className="header-actions">
          <button className="icon-btn" onClick={loadPapers} title="Refresh">
            ↻
          </button>
        </div>
      </div>

      <div className="connection-status connected">
        <span className="status-dot"></span>
        Connected
      </div>

      {/* Unsaved PDF: Show Add to Scriptor */}
      {panelState === 'unsaved_pdf' && (
        <div className="add-paper-section">
          <button className="add-paper-btn" onClick={handleAddPaper} disabled={loading}>
            + Add to Scriptor
          </button>
        </div>
      )}

      {/* Saved PDF: Show Tools */}
      {panelState === 'saved_pdf' && activePaper && (
        <>
          <div className="tools-section">
            <div className="tools-header">
              Tools - {activePaper.title}
            </div>

            {/* Annotation Tools */}
            <div className="tool-group">
              <div className="tool-group-title">Annotate</div>
              <div className="tool-buttons">
                <button
                  className={`tool-btn ${activeTool === 'select' ? 'active' : ''}`}
                  onClick={() => handleToolSelect('select')}
                >
                  ↖ Select
                </button>
                <button
                  className={`tool-btn ${activeTool === 'highlight' ? 'active' : ''}`}
                  onClick={() => handleToolSelect('highlight')}
                >
                  ▬ Highlight
                </button>
                <button
                  className={`tool-btn ${activeTool === 'rectangle' ? 'active' : ''}`}
                  onClick={() => handleToolSelect('rectangle')}
                >
                  □ Rectangle
                </button>
                <button
                  className={`tool-btn ${activeTool === 'text' ? 'active' : ''}`}
                  onClick={() => handleToolSelect('text')}
                >
                  T Text
                </button>
                <button
                  className={`tool-btn ${activeTool === 'pen' ? 'active' : ''}`}
                  onClick={() => handleToolSelect('pen')}
                >
                  ✎ Pen
                </button>
                <button
                  className={`tool-btn ${activeTool === 'comment' ? 'active' : ''}`}
                  onClick={() => handleToolSelect('comment')}
                >
                  💬 Comment
                </button>
                <button
                  className={`tool-btn ${activeTool === 'latexCapture' ? 'active' : ''}`}
                  onClick={() => handleToolSelect('latexCapture')}
                >
                  ∑ LaTeX
                </button>
              </div>

              {/* Color Palette */}
              {(activeTool === 'highlight' || activeTool === 'pen' || activeTool === 'rectangle') && (
                <div className="color-palette">
                  {HIGHLIGHT_COLORS.map(color => (
                    <button
                      key={color}
                      className={`color-swatch ${activeColor === color ? 'selected' : ''}`}
                      style={{ backgroundColor: color }}
                      onClick={() => handleColorSelect(color)}
                    />
                  ))}
                </div>
              )}
            </div>

            {/* Export Tools */}
            <div className="tool-group">
              <div className="tool-group-title">Export</div>
              <div className="export-buttons">
                <button className="export-btn" onClick={handleExportPdf}>
                  Export PDF
                </button>
                <button className="export-btn" onClick={handleGetBibtex}>
                  BibTeX
                </button>
                {activePaper.doi && (
                  <button
                    className="export-btn"
                    onClick={() => window.open(`https://doi.org/${activePaper.doi}`, '_blank')}
                  >
                    DOI Link
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Semantic Search */}
          <div className="search-section">
            <div className="search-input-wrapper">
              <input
                type="text"
                className="search-input"
                placeholder="Semantic search..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSemanticSearch()}
              />
              <button
                className="search-btn"
                onClick={handleSemanticSearch}
                disabled={!activePaper?.embeddings_ready || isSearching}
              >
                {isSearching ? '...' : 'Search'}
              </button>
            </div>
            {!activePaper?.embeddings_ready && (
              <p style={{ fontSize: 11, color: '#999', marginTop: 4 }}>
                Run batch processing to enable semantic search
              </p>
            )}
          </div>
        </>
      )}

      {/* Search bar for non-saved views */}
      {panelState !== 'saved_pdf' && (
        <div className="search-section">
          <input
            type="text"
            className="search-input"
            placeholder="Search library..."
            onChange={(e) => {
              const query = e.target.value.toLowerCase();
              // Filter papers locally
              // This could be enhanced with proper search
            }}
          />
        </div>
      )}

      {/* Library Section */}
      <div className="library-section">
        <div className="library-header">
          <span>Library</span>
          <div className="library-view-toggle">
            <button
              className={`view-toggle-btn ${libraryView === 'papers' ? 'active' : ''}`}
              onClick={handleViewPapers}
              title="View Papers"
            >
              Papers
            </button>
            <button
              className={`view-toggle-btn ${libraryView === 'highlights' ? 'active' : ''}`}
              onClick={handleViewHighlights}
              title="View Highlights"
            >
              Highlights
            </button>
          </div>
        </div>

        {/* Papers View */}
        {libraryView === 'papers' && (
          <>
            {/* Collection Tabs */}
            {collections.length > 1 && (
              <div className="collection-tabs">
                {collections.map(col => (
                  <button
                    key={col}
                    className={`collection-tab ${(activeCollection === col || (col === 'All' && !activeCollection)) ? 'active' : ''}`}
                    onClick={() => {
                      setActiveCollection(col === 'All' ? null : col);
                      loadPapers();
                    }}
                  >
                    {col}
                  </button>
                ))}
              </div>
            )}

            {/* Paper List */}
            <div className="paper-list">
              {papers.length === 0 ? (
                <div className="empty-state">
                  <h3>No papers yet</h3>
                  <p>Add papers from PDFs you find online</p>
                </div>
              ) : (
                papers.map(paper => (
                  <div
                    key={paper.id}
                    className={`paper-item ${activePaper?.id === paper.id ? 'active' : ''}`}
                    onClick={() => handleOpenPaper(paper)}
                  >
                    <div className="paper-icon">PDF</div>
                    <div className="paper-info">
                      <div className="paper-title">{paper.title}</div>
                      <div className="paper-meta">
                        {paper.authors && <span>{paper.authors} • </span>}
                        {paper.year && <span>{paper.year}</span>}
                      </div>
                      <span className={`paper-status ${paper.embeddings_ready ? 'indexed' : 'pending'}`}>
                        {paper.embeddings_ready ? 'Ready' : paper.status}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </>
        )}

        {/* Highlights View */}
        {libraryView === 'highlights' && (
          <div className="highlights-list">
            {loadingHighlights ? (
              <div className="empty-state">
                <div className="loading-spinner"></div>
                <p style={{ marginTop: 12 }}>Loading highlights...</p>
              </div>
            ) : allHighlights.length === 0 ? (
              <div className="empty-state">
                <h3>No highlights yet</h3>
                <p>Highlight text in your papers to see them here</p>
              </div>
            ) : (
              allHighlights.map(highlight => (
                <div
                  key={highlight.annotation.id}
                  className={`highlight-item ${expandedHighlight === highlight.annotation.id ? 'expanded' : ''}`}
                  onClick={() => handleHighlightClick(highlight)}
                >
                  <div
                    className="highlight-color-bar"
                    style={{ backgroundColor: highlight.annotation.color || HIGHLIGHT_COLORS[0] }}
                  />
                  <div className="highlight-content">
                    <div className="highlight-paper-name">{highlight.paper.title}</div>
                    <div className="highlight-page">Page {highlight.annotation.page + 1}</div>

                    {/* Show context when expanded */}
                    {expandedHighlight === highlight.annotation.id && (
                      <div className="highlight-context">
                        {highlight.contextText ? (
                          <p className="context-text">{highlight.contextText}</p>
                        ) : (
                          <p className="context-text muted">No text content available</p>
                        )}
                        <button
                          className="jump-to-btn"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleJumpToHighlight(highlight);
                          }}
                        >
                          Jump to highlight
                        </button>
                      </div>
                    )}
                  </div>
                  <div className="highlight-meta">
                    {new Date(highlight.annotation.updated_at).toLocaleDateString()}
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}
