/**
 * API client for Scriptor Local
 */

import type {
  Paper,
  Annotation,
  SearchResult,
  HealthResponse,
  BatchStatus,
  LatexifyResult,
} from '../types';

const DEFAULT_SERVER_URL = 'http://127.0.0.1:52525';

class ScriptorAPI {
  private serverUrl: string = DEFAULT_SERVER_URL;
  private authToken: string | null = null;

  async init(): Promise<void> {
    const storage = await chrome.storage.local.get(['serverUrl', 'authToken']);
    this.serverUrl = storage.serverUrl || DEFAULT_SERVER_URL;
    this.authToken = storage.authToken || null;
  }

  setToken(token: string): void {
    this.authToken = token;
    chrome.storage.local.set({ authToken: token });
  }

  setServerUrl(url: string): void {
    this.serverUrl = url;
    chrome.storage.local.set({ serverUrl: url });
  }

  private getHeaders(): HeadersInit {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };
    if (this.authToken) {
      headers['Authorization'] = `Bearer ${this.authToken}`;
    }
    return headers;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.serverUrl}/api${endpoint}`;

    const response = await fetch(url, {
      ...options,
      headers: {
        ...this.getHeaders(),
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  // Health & Connection
  async checkHealth(): Promise<HealthResponse> {
    try {
      const response = await fetch(`${this.serverUrl}/api/health`);
      return response.json();
    } catch {
      throw new Error('Scriptor Local not running');
    }
  }

  async pair(token: string): Promise<boolean> {
    this.setToken(token);
    try {
      await this.request('/pair', { method: 'POST' });
      return true;
    } catch {
      this.authToken = null;
      chrome.storage.local.remove('authToken');
      return false;
    }
  }

  isPaired(): boolean {
    return this.authToken !== null;
  }

  // Papers
  async addPaper(url: string, title?: string, collection?: string): Promise<Paper> {
    return this.request('/papers/add', {
      method: 'POST',
      body: JSON.stringify({ url, title, collection }),
    });
  }

  async listPapers(collection?: string): Promise<{ papers: Paper[] }> {
    const query = collection ? `?collection=${encodeURIComponent(collection)}` : '';
    return this.request(`/papers/list${query}`);
  }

  async getPaper(paperId: string): Promise<Paper> {
    return this.request(`/papers/${paperId}`);
  }

  async deletePaper(paperId: string): Promise<void> {
    await this.request(`/papers/${paperId}`, { method: 'DELETE' });
  }

  getPdfUrl(paperId: string): string {
    return `${this.serverUrl}/api/papers/${paperId}/pdf?token=${this.authToken}`;
  }

  // Annotations
  async saveAnnotation(annotation: Annotation): Promise<void> {
    await this.request('/annotations/save', {
      method: 'POST',
      body: JSON.stringify(annotation),
    });
  }

  async getAnnotations(paperId: string): Promise<{ annotations: Annotation[] }> {
    return this.request(`/annotations/${paperId}`);
  }

  async deleteAnnotation(annotationId: string): Promise<void> {
    await this.request(`/annotations/${annotationId}`, { method: 'DELETE' });
  }

  // Semantic Search
  async semanticSearch(
    paperId: string,
    query: string,
    topK: number = 50
  ): Promise<{ query: string; results: SearchResult[] }> {
    return this.request('/search/semantic', {
      method: 'POST',
      body: JSON.stringify({ paper_id: paperId, query, top_k: topK }),
    });
  }

  // Batch Processing
  async runBatch(): Promise<{ status: string; processed: number; failed: number }> {
    return this.request('/batch/run', { method: 'POST' });
  }

  async getBatchStatus(): Promise<BatchStatus> {
    return this.request('/batch/status');
  }

  // LaTeXify
  async latexify(
    paperId: string,
    page: number,
    bbox: { x: number; y: number; width: number; height: number }
  ): Promise<LatexifyResult> {
    return this.request('/latexify', {
      method: 'POST',
      body: JSON.stringify({ paper_id: paperId, page, bbox }),
    });
  }

  async getLatexifyStatus(): Promise<{ pix2tex_available: boolean; gemini_configured: boolean; ready: boolean }> {
    return this.request('/latexify/status');
  }

  // Export & BibTeX
  async exportPdf(paperId: string): Promise<Blob> {
    const url = `${this.serverUrl}/api/export/pdf`;
    const response = await fetch(url, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify({ paper_id: paperId }),
    });

    if (!response.ok) {
      throw new Error('Export failed');
    }

    return response.blob();
  }

  async getBibtex(paperId: string): Promise<{
    bibtex: string | null;
    doi: string | null;
    doi_link: string | null;
    source: string | null;
  }> {
    return this.request(`/bibtex/${paperId}`);
  }

  async parseCitation(citation: string): Promise<{ bibtex: string }> {
    return this.request('/bibtex/parse', {
      method: 'POST',
      body: JSON.stringify({ citation }),
    });
  }

  // Status
  async getStatus(): Promise<{
    connected: boolean;
    storage_dir: string;
    papers_count: number;
    batch_status: BatchStatus;
    latexify_status: { pix2tex_available: boolean; gemini_configured: boolean; ready: boolean };
  }> {
    return this.request('/status');
  }
}

// Export singleton instance
export const api = new ScriptorAPI();
