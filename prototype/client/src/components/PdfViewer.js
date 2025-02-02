import React, { useState, useEffect } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import HeatmapOverlay from './HeatmapOverlay';

pdfjs.GlobalWorkerOptions.workerSrc = 
  `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`;

function PdfViewer({ pdfPath, searchResults }) {
  const [numPages, setNumPages] = useState(null);

  const onDocumentLoadSuccess = (pdf) => {
    setNumPages(pdf.numPages);
  };

  return (
    <div>
      <Document
        file={pdfPath}
        onLoadSuccess={onDocumentLoadSuccess}
      >
        {Array.from(new Array(numPages), (el, index) => (
          <div key={`page_${index + 1}`} style={{ position: 'relative' }}>
            <Page pageNumber={index + 1} width={600} />
            {/* 
              HeatmapOverlay is an absolutely positioned canvas overlay 
              that we place over the PDF page
            */}
            <HeatmapOverlay 
              pageIndex={index} 
              searchResults={searchResults} 
              pageWidth={600} 
            />
          </div>
        ))}
      </Document>
    </div>
  );
}

export default PdfViewer;
