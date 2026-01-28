import React, { useState, useEffect, useRef, useCallback } from 'react';
import * as pdfjsLib from 'pdfjs-dist';
import { api } from '../../utils/api';
import type { Paper, Annotation, AnnotationTool, SearchResult, HighlightColor } from '../../types';
import { HIGHLIGHT_COLORS } from '../../types';
import { v4 as uuidv4 } from 'uuid';

// Set worker path
pdfjsLib.GlobalWorkerOptions.workerSrc = chrome.runtime.getURL('pdf.worker.min.mjs');

interface HeatmapItem extends SearchResult {
  color: string;
}

export function Reader() {
  // Paper state
  const [paper, setPaper] = useState<Paper | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // PDF state
  const [pdfDoc, setPdfDoc] = useState<pdfjsLib.PDFDocumentProxy | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [scale, setScale] = useState(1.2);

  // Annotation state
  const [annotations, setAnnotations] = useState<Annotation[]>([]);
  const [activeTool, setActiveTool] = useState<AnnotationTool>('select');
  const [activeColor, setActiveColor] = useState<HighlightColor>(HIGHLIGHT_COLORS[0]);
  const [isDrawing, setIsDrawing] = useState(false);
  const [drawStart, setDrawStart] = useState<{ x: number; y: number } | null>(null);
  const [currentPath, setCurrentPath] = useState<Array<{ x: number; y: number }>>([]);

  // Heatmap state
  const [heatmapResults, setHeatmapResults] = useState<HeatmapItem[]>([]);
  const [heatmapQuery, setHeatmapQuery] = useState<string>('');
  const [hoveredChunk, setHoveredChunk] = useState<HeatmapItem | null>(null);

  // LaTeX capture state
  const [isCapturing, setIsCapturing] = useState(false);
  const [captureRect, setCaptureRect] = useState<{ x: number; y: number; width: number; height: number } | null>(null);
  const [latexResult, setLatexResult] = useState<{ latex: string; method?: string } | null>(null);

  // Refs
  const containerRef = useRef<HTMLDivElement>(null);
  const pageRefs = useRef<Map<number, HTMLCanvasElement>>(new Map());

  // Get paper ID from URL
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const paperId = params.get('paperId');

    if (paperId) {
      loadPaper(paperId);
    } else {
      setError('No paper ID provided');
      setLoading(false);
    }

    // Listen for messages from side panel
    chrome.runtime.onMessage.addListener(handleMessage);
    return () => {
      chrome.runtime.onMessage.removeListener(handleMessage);
    };
  }, []);

  function handleMessage(message: { type: string; payload?: unknown }) {
    switch (message.type) {
      case 'SET_TOOL':
        const toolPayload = message.payload as { tool: AnnotationTool; color: HighlightColor };
        setActiveTool(toolPayload.tool);
        if (toolPayload.color) setActiveColor(toolPayload.color);
        if (toolPayload.tool === 'latexCapture') {
          setIsCapturing(true);
        }
        break;

      case 'SET_COLOR':
        const colorPayload = message.payload as { color: HighlightColor };
        setActiveColor(colorPayload.color);
        break;

      case 'SEARCH_RESULTS':
        const searchPayload = message.payload as { query: string; results: SearchResult[] };
        handleSearchResults(searchPayload);
        break;
    }
  }

  async function loadPaper(paperId: string) {
    try {
      await api.init();

      // Load paper metadata
      const paperData = await api.getPaper(paperId);
      setPaper(paperData);
      document.title = `${paperData.title} - Scriptor Reader`;

      // Load annotations
      const { annotations: ann } = await api.getAnnotations(paperId);
      setAnnotations(ann);

      // Load PDF
      const pdfUrl = api.getPdfUrl(paperId);
      const loadingTask = pdfjsLib.getDocument({
        url: pdfUrl,
        cMapUrl: chrome.runtime.getURL('cmaps/'),
        cMapPacked: true,
      });

      const pdf = await loadingTask.promise;
      setPdfDoc(pdf);
      setTotalPages(pdf.numPages);
      setLoading(false);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load paper');
      setLoading(false);
    }
  }

  // Render PDF pages
  useEffect(() => {
    if (!pdfDoc || !containerRef.current) return;

    renderVisiblePages();
  }, [pdfDoc, scale, currentPage]);

  async function renderVisiblePages() {
    if (!pdfDoc) return;

    // For simplicity, render all pages (could be optimized for large PDFs)
    for (let pageNum = 1; pageNum <= totalPages; pageNum++) {
      await renderPage(pageNum);
    }
  }

  async function renderPage(pageNum: number) {
    if (!pdfDoc) return;

    const page = await pdfDoc.getPage(pageNum);
    const viewport = page.getViewport({ scale });

    // Get or create canvas
    let canvas = pageRefs.current.get(pageNum);
    if (!canvas) {
      canvas = document.createElement('canvas');
      pageRefs.current.set(pageNum, canvas);
    }

    canvas.height = viewport.height;
    canvas.width = viewport.width;

    const context = canvas.getContext('2d');
    if (!context) return;

    await page.render({
      canvasContext: context,
      viewport,
    }).promise;
  }

  function handleSearchResults(payload: { query: string; results: SearchResult[] }) {
    setHeatmapQuery(payload.query);

    // Generate heatmap colors based on normalized scores
    const heatmapItems: HeatmapItem[] = payload.results.map(result => {
      // Color gradient from light blue to dark blue based on score
      const intensity = Math.floor(result.normalized_score * 255);
      const color = `rgba(33, 150, 243, ${0.2 + result.normalized_score * 0.6})`;

      return {
        ...result,
        color,
      };
    });

    setHeatmapResults(heatmapItems);
  }

  // Annotation handling
  function handleCanvasMouseDown(e: React.MouseEvent, pageNum: number) {
    if (activeTool === 'select') return;

    const rect = e.currentTarget.getBoundingClientRect();
    const x = (e.clientX - rect.left) / scale;
    const y = (e.clientY - rect.top) / scale;

    setIsDrawing(true);
    setDrawStart({ x, y });

    if (activeTool === 'pen') {
      setCurrentPath([{ x, y }]);
    }
  }

  function handleCanvasMouseMove(e: React.MouseEvent, pageNum: number) {
    if (!isDrawing || !drawStart) return;

    const rect = e.currentTarget.getBoundingClientRect();
    const x = (e.clientX - rect.left) / scale;
    const y = (e.clientY - rect.top) / scale;

    if (activeTool === 'pen') {
      setCurrentPath(prev => [...prev, { x, y }]);
    }
  }

  async function handleCanvasMouseUp(e: React.MouseEvent, pageNum: number) {
    if (!isDrawing || !drawStart) return;

    const rect = e.currentTarget.getBoundingClientRect();
    const x = (e.clientX - rect.left) / scale;
    const y = (e.clientY - rect.top) / scale;

    setIsDrawing(false);

    // Create annotation
    const annotation: Annotation = {
      id: uuidv4(),
      paper_id: paper!.id,
      page: pageNum - 1, // 0-indexed
      type: activeTool === 'pen' ? 'ink' : activeTool as Annotation['type'],
      geometry: activeTool === 'pen'
        ? { x: 0, y: 0, points: currentPath }
        : {
            x: Math.min(drawStart.x, x),
            y: Math.min(drawStart.y, y),
            width: Math.abs(x - drawStart.x),
            height: Math.abs(y - drawStart.y),
          },
      color: activeColor,
      opacity: activeTool === 'highlight' ? 0.4 : 1,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    // Add to state
    setAnnotations(prev => [...prev, annotation]);

    // Save to server (debounced in real implementation)
    try {
      await api.saveAnnotation(annotation);
    } catch (err) {
      console.error('Failed to save annotation:', err);
    }

    setDrawStart(null);
    setCurrentPath([]);
  }

  // LaTeX capture handling
  function handleCaptureStart(e: React.MouseEvent) {
    const rect = containerRef.current!.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    setDrawStart({ x, y });
  }

  function handleCaptureMove(e: React.MouseEvent) {
    if (!drawStart) return;

    const rect = containerRef.current!.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    setCaptureRect({
      x: Math.min(drawStart.x, x),
      y: Math.min(drawStart.y, y),
      width: Math.abs(x - drawStart.x),
      height: Math.abs(y - drawStart.y),
    });
  }

  async function handleCaptureEnd() {
    if (!captureRect || !paper) return;

    setIsCapturing(false);

    // Convert screen coordinates to PDF coordinates
    // This is simplified - would need proper coordinate transformation
    const pdfBbox = {
      x: captureRect.x / scale,
      y: captureRect.y / scale,
      width: captureRect.width / scale,
      height: captureRect.height / scale,
    };

    try {
      const result = await api.latexify(paper.id, currentPage - 1, pdfBbox);
      if (result.success && result.latex) {
        setLatexResult({ latex: result.latex, method: result.method });
      } else {
        alert(result.error || 'LaTeX conversion failed');
      }
    } catch (err) {
      alert(`LaTeX capture failed: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }

    setCaptureRect(null);
    setDrawStart(null);
    setActiveTool('select');
  }

  function copyLatex() {
    if (latexResult?.latex) {
      navigator.clipboard.writeText(latexResult.latex);
      setLatexResult(null);
    }
  }

  // Zoom controls
  function zoomIn() {
    setScale(prev => Math.min(prev + 0.2, 3));
  }

  function zoomOut() {
    setScale(prev => Math.max(prev - 0.2, 0.5));
  }

  // Page navigation
  function goToPage(page: number) {
    if (page >= 1 && page <= totalPages) {
      setCurrentPage(page);
      // Scroll to page
      const pageContainer = document.getElementById(`page-${page}`);
      pageContainer?.scrollIntoView({ behavior: 'smooth' });
    }
  }

  // Render annotation
  function renderAnnotation(ann: Annotation) {
    const style: React.CSSProperties = {
      left: ann.geometry.x * scale,
      top: ann.geometry.y * scale,
      width: (ann.geometry.width || 0) * scale,
      height: (ann.geometry.height || 0) * scale,
      backgroundColor: ann.type === 'highlight' ? ann.color : 'transparent',
      borderColor: ann.color,
      opacity: ann.opacity,
    };

    return (
      <div
        key={ann.id}
        className={`annotation ${ann.type}`}
        style={style}
        onClick={() => {
          if (activeTool === 'select') {
            // Could show annotation options
          }
        }}
      >
        {ann.type === 'text' && ann.text_content}
        {ann.type === 'comment' && '💬'}
      </div>
    );
  }

  // Render heatmap
  function renderHeatmap(pageNum: number) {
    const pageResults = heatmapResults.filter(r => r.page === pageNum - 1);

    return pageResults.map((result, idx) => (
      <div
        key={`heatmap-${idx}`}
        className="heatmap-rect"
        style={{
          left: result.bbox.x * scale,
          top: result.bbox.y * scale,
          width: result.bbox.width * scale,
          height: result.bbox.height * scale,
          backgroundColor: result.color,
        }}
        onMouseEnter={() => setHoveredChunk(result)}
        onMouseLeave={() => setHoveredChunk(null)}
      />
    ));
  }

  // Loading state
  if (loading) {
    return (
      <div className="reader-container">
        <div className="loading-overlay">
          <div className="loading-spinner-large"></div>
          <p style={{ marginTop: 16, color: '#666' }}>Loading paper...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="reader-container">
        <div className="error-state">
          <h2>Error Loading Paper</h2>
          <p>{error}</p>
          <button onClick={() => window.location.reload()}>Retry</button>
        </div>
      </div>
    );
  }

  return (
    <div className="reader-container">
      {/* Toolbar */}
      <div className="reader-toolbar">
        <div className="toolbar-left">
          <div className="paper-title-bar">{paper?.title}</div>
        </div>

        <div className="toolbar-center">
          <div className="page-nav">
            <button onClick={() => goToPage(currentPage - 1)} disabled={currentPage <= 1}>
              ←
            </button>
            <span className="page-indicator">
              {currentPage} / {totalPages}
            </span>
            <button onClick={() => goToPage(currentPage + 1)} disabled={currentPage >= totalPages}>
              →
            </button>
          </div>
        </div>

        <div className="toolbar-right">
          <div className="zoom-controls">
            <button onClick={zoomOut}>−</button>
            <span className="zoom-indicator">{Math.round(scale * 100)}%</span>
            <button onClick={zoomIn}>+</button>
          </div>
        </div>
      </div>

      {/* Heatmap Query Indicator */}
      {heatmapQuery && (
        <div style={{
          padding: '8px 16px',
          background: '#e3f2fd',
          color: '#1976D2',
          fontSize: 13,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <span>Showing heatmap for: "{heatmapQuery}"</span>
          <button
            onClick={() => {
              setHeatmapResults([]);
              setHeatmapQuery('');
            }}
            style={{
              background: 'none',
              border: 'none',
              color: '#1976D2',
              cursor: 'pointer'
            }}
          >
            Clear
          </button>
        </div>
      )}

      {/* PDF Viewer */}
      <div className="pdf-viewer" ref={containerRef}>
        {Array.from({ length: totalPages }, (_, i) => i + 1).map(pageNum => (
          <div
            key={pageNum}
            id={`page-${pageNum}`}
            className="pdf-page-container"
            style={{
              width: pageRefs.current.get(pageNum)?.width || 'auto',
              height: pageRefs.current.get(pageNum)?.height || 'auto',
            }}
          >
            <canvas
              ref={el => {
                if (el) {
                  pageRefs.current.set(pageNum, el);
                  renderPage(pageNum);
                }
              }}
              className="pdf-page-canvas"
            />

            {/* Annotation Layer */}
            <div
              className={`annotation-layer ${activeTool !== 'select' ? 'active' : ''} ${activeTool === 'pen' ? 'pen-mode' : ''}`}
              onMouseDown={(e) => handleCanvasMouseDown(e, pageNum)}
              onMouseMove={(e) => handleCanvasMouseMove(e, pageNum)}
              onMouseUp={(e) => handleCanvasMouseUp(e, pageNum)}
            >
              {/* Existing annotations for this page */}
              {annotations
                .filter(a => a.page === pageNum - 1)
                .map(renderAnnotation)}

              {/* Drawing preview */}
              {isDrawing && drawStart && activeTool !== 'pen' && (
                <div
                  className="temp-annotation"
                  style={{
                    left: drawStart.x * scale,
                    top: drawStart.y * scale,
                    width: 0,
                    height: 0,
                    borderColor: activeColor,
                  }}
                />
              )}
            </div>

            {/* Heatmap Layer */}
            {heatmapResults.length > 0 && (
              <div className="heatmap-layer">
                {renderHeatmap(pageNum)}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Heatmap Tooltip */}
      {hoveredChunk && (
        <div
          className="heatmap-tooltip"
          style={{
            left: hoveredChunk.bbox.x * scale + 10,
            top: hoveredChunk.bbox.y * scale - 40,
          }}
        >
          <div style={{ fontWeight: 500, marginBottom: 4 }}>
            Relevance: {Math.round(hoveredChunk.normalized_score * 100)}%
          </div>
          <div style={{ fontSize: 11, opacity: 0.9 }}>
            {hoveredChunk.text.substring(0, 150)}...
          </div>
        </div>
      )}

      {/* LaTeX Capture Overlay */}
      {isCapturing && (
        <div
          className="latex-capture-overlay"
          onMouseDown={handleCaptureStart}
          onMouseMove={handleCaptureMove}
          onMouseUp={handleCaptureEnd}
        >
          {captureRect && (
            <div
              className="latex-capture-rect"
              style={{
                left: captureRect.x,
                top: captureRect.y,
                width: captureRect.width,
                height: captureRect.height,
              }}
            />
          )}
        </div>
      )}

      {/* LaTeX Result Modal */}
      {latexResult && (
        <>
          <div className="latex-capture-overlay" onClick={() => setLatexResult(null)} />
          <div className="latex-modal">
            <h3>LaTeX Extracted</h3>
            {latexResult.method && (
              <p style={{ fontSize: 12, color: '#666', marginBottom: 8 }}>
                Method: {latexResult.method}
              </p>
            )}
            <div className="latex-preview">{latexResult.latex}</div>
            <div className="latex-actions">
              <button className="close-btn" onClick={() => setLatexResult(null)}>
                Close
              </button>
              <button className="copy-btn" onClick={copyLatex}>
                Copy to Clipboard
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
