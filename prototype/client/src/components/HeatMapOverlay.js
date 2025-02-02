import React, { useRef, useEffect } from 'react';

function HeatmapOverlay({ pageIndex, searchResults, pageWidth }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');

    // Clear previous drawings
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Filter results for this page
    const pageBlocks = searchResults.filter(r => r.page_index === pageIndex);

    // For demonstration: define a maxScore to scale intensities
    const maxScore = pageBlocks.length
      ? Math.max(...pageBlocks.map(b => b.score))
      : 1;

    // PDF coordinates are in points (72 DPI).
    // We'll do a naive scale factor based on your chosen pageWidth in react-pdf.
    // If the PDF is rendered at 72 DPI and we show it at 600px wide,
    // scale factor = 600 / actual PDF width in points.
    // For simplicity, let’s assume 612pt width (typical 8.5"x11" at 72 DPI).
    // Adjust as needed to match your real PDF width or use react-pdf's scale factor.
    const pdfPageWidthPts = 612;
    const scaleFactor = pageWidth / pdfPageWidthPts;

    pageBlocks.forEach(block => {
      const [x0, y0, x1, y1] = block.bbox;
      const score = block.score;
      const intensity = score / maxScore;

      // Convert PDF coordinates -> canvas coordinates
      const x = x0 * scaleFactor;
      const y = y0 * scaleFactor;
      const w = (x1 - x0) * scaleFactor;
      const h = (y1 - y0) * scaleFactor;

      // Choose color e.g., red with alpha ~ intensity
      ctx.fillStyle = `rgba(255, 0, 0, ${intensity * 0.5})`;
      ctx.fillRect(x, y, w, h);
    });
  }, [searchResults, pageIndex, pageWidth]);

  return (
    <canvas
      ref={canvasRef}
      width={pageWidth}
      height={800}  // naive fixed page height in px
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        pointerEvents: 'none'  // let clicks pass through
      }}
    />
  );
}

export default HeatmapOverlay;
