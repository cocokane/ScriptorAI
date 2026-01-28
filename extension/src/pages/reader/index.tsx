import React from 'react';
import { createRoot } from 'react-dom/client';
import { Reader } from './Reader';
import '../../styles/reader.css';

const container = document.getElementById('root');
if (container) {
  const root = createRoot(container);
  root.render(<Reader />);
}
