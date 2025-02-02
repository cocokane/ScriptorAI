import React, { useState } from 'react';
import axios from 'axios';
import PdfViewer from './components/PdfViewer';
import './App.css';

function App() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [pdfPath, setPdfPath] = useState('');
  const [query, setQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);

  const handleFileChange = (e) => {
    setSelectedFile(e.target.files[0]);
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const response = await axios.post('http://localhost:5000/upload_pdf', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      setPdfPath(response.data.pdf_path);
    } catch (err) {
      console.error(err);
    }
  };

  const handleSearch = async () => {
    if (!pdfPath || !query) return;
    try {
      const response = await axios.post('http://localhost:5000/semantic_search', {
        pdf_path: pdfPath,
        query
      });
      setSearchResults(response.data.results);
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="App">
      <h1>Scriptor.ai MVP</h1>
      <div style={{ marginBottom: '1em' }}>
        <input type="file" onChange={handleFileChange} />
        <button onClick={handleUpload}>Upload PDF</button>
      </div>

      <div style={{ marginBottom: '1em' }}>
        <input
          type="text"
          placeholder="Enter search term"
          value={query}
          onChange={e => setQuery(e.target.value)}
        />
        <button onClick={handleSearch}>Semantic Search</button>
      </div>

      {pdfPath && (
        <PdfViewer pdfPath={pdfPath} searchResults={searchResults} />
      )}
    </div>
  );
}

export default App;
