/**
 * Types for ScriptorAI Chrome Extension
 */

// Paper types
export interface Paper {
  id: string;
  title: string;
  authors?: string;
  year?: number;
  doi?: string;
  source_url?: string;
  local_pdf_path: string;
  added_at: string;
  indexed_at?: string;
  embeddings_ready: boolean;
  status: 'pending' | 'indexed' | 'needs_ocr' | 'error';
  collection: string;
  metadata?: Record<string, unknown>;
}

// Annotation types
export type AnnotationType = 'highlight' | 'rectangle' | 'ellipse' | 'text' | 'comment' | 'ink' | 'image';

export interface AnnotationGeometry {
  x: number;
  y: number;
  width?: number;
  height?: number;
  points?: Array<{ x: number; y: number }>;
}

export interface Annotation {
  id: string;
  paper_id: string;
  page: number;
  type: AnnotationType;
  geometry: AnnotationGeometry;
  color?: string;
  opacity?: number;
  text_content?: string;
  created_at: string;
  updated_at: string;
}

// Search result types
export interface SearchResult {
  id: string;
  page: number;
  bbox: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  text: string;
  score: number;
  normalized_score: number;
}

// Side panel state
export type PanelState =
  | 'no_pdf'        // Normal browsing, no PDF
  | 'unsaved_pdf'   // On a PDF that's not in library
  | 'saved_pdf';    // On a saved paper from library

// Extension storage
export interface ExtensionStorage {
  authToken?: string;
  serverUrl: string;
  activePaperId?: string;
  recentPapers: string[];
  collapsed: boolean;
}

// API response types
export interface HealthResponse {
  status: string;
  version: string;
  storage_dir: string;
}

export interface BatchStatus {
  pending: number;
  running: number;
  completed: number;
  failed: number;
  current_job?: {
    id: string;
    type: string;
    paper_id: string;
  };
}

export interface LatexifyResult {
  success: boolean;
  latex?: string;
  error?: string;
  method?: string;
  confidence?: number;
}

// Highlight colors
export const HIGHLIGHT_COLORS = [
  '#FFEB3B', // Yellow
  '#4CAF50', // Green
  '#2196F3', // Blue
  '#E91E63', // Pink
  '#FF9800', // Orange
  '#9C27B0', // Purple
  '#00BCD4', // Cyan
  '#F44336', // Red
  '#8BC34A', // Light Green
  '#607D8B', // Blue Grey
] as const;

export type HighlightColor = typeof HIGHLIGHT_COLORS[number];

// Annotation tool
export type AnnotationTool =
  | 'select'
  | 'highlight'
  | 'rectangle'
  | 'ellipse'
  | 'text'
  | 'comment'
  | 'pen'
  | 'image'
  | 'latexCapture';

// Message types for extension communication
export interface ExtensionMessage {
  type: string;
  payload?: unknown;
}

export interface AddPaperMessage extends ExtensionMessage {
  type: 'ADD_PAPER';
  payload: {
    url: string;
    title?: string;
  };
}

export interface OpenPaperMessage extends ExtensionMessage {
  type: 'OPEN_PAPER';
  payload: {
    paperId: string;
  };
}
