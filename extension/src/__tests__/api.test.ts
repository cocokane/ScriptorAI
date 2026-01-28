/**
 * Tests for API client
 */
import { api } from '../utils/api';

describe('ScriptorAPI', () => {
  const mockFetch = global.fetch as jest.Mock;

  beforeEach(() => {
    mockFetch.mockClear();
    // Reset API state
    (chrome.storage.local.get as jest.Mock).mockResolvedValue({
      serverUrl: 'http://127.0.0.1:52525',
      authToken: 'test-token',
    });
  });

  describe('checkHealth', () => {
    it('should return health status when server is running', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          status: 'ok',
          version: '1.0.0',
          storage_dir: '/test/storage',
        }),
      });

      const health = await api.checkHealth();

      expect(health.status).toBe('ok');
      expect(health.version).toBe('1.0.0');
    });

    it('should throw when server is not running', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      await expect(api.checkHealth()).rejects.toThrow('Scriptor Local not running');
    });
  });

  describe('pair', () => {
    it('should return true for valid token', async () => {
      await api.init();

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ paired: true }),
      });

      const result = await api.pair('valid-token');

      expect(result).toBe(true);
      expect(chrome.storage.local.set).toHaveBeenCalledWith({ authToken: 'valid-token' });
    });

    it('should return false for invalid token', async () => {
      await api.init();

      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({ detail: 'Invalid token' }),
      });

      const result = await api.pair('invalid-token');

      expect(result).toBe(false);
    });
  });

  describe('listPapers', () => {
    it('should return papers list', async () => {
      await api.init();
      api.setToken('test-token');

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          papers: [
            { id: '1', title: 'Paper 1', status: 'indexed' },
            { id: '2', title: 'Paper 2', status: 'pending' },
          ],
        }),
      });

      const result = await api.listPapers();

      expect(result.papers).toHaveLength(2);
      expect(result.papers[0].title).toBe('Paper 1');
    });

    it('should include collection filter in query', async () => {
      await api.init();
      api.setToken('test-token');

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ papers: [] }),
      });

      await api.listPapers('research');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('collection=research'),
        expect.any(Object)
      );
    });
  });

  describe('addPaper', () => {
    it('should add paper from URL', async () => {
      await api.init();
      api.setToken('test-token');

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          id: 'new-paper-id',
          title: 'New Paper',
          status: 'pending',
        }),
      });

      const result = await api.addPaper('https://example.com/paper.pdf', 'New Paper');

      expect(result.id).toBe('new-paper-id');
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/papers/add'),
        expect.objectContaining({
          method: 'POST',
          body: expect.stringContaining('https://example.com/paper.pdf'),
        })
      );
    });
  });

  describe('semanticSearch', () => {
    it('should return search results', async () => {
      await api.init();
      api.setToken('test-token');

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          query: 'test query',
          results: [
            { id: 'chunk1', score: 0.95, normalized_score: 1.0, text: 'Result 1' },
            { id: 'chunk2', score: 0.80, normalized_score: 0.5, text: 'Result 2' },
          ],
        }),
      });

      const result = await api.semanticSearch('paper-id', 'test query');

      expect(result.query).toBe('test query');
      expect(result.results).toHaveLength(2);
      expect(result.results[0].normalized_score).toBe(1.0);
    });
  });

  describe('saveAnnotation', () => {
    it('should save annotation', async () => {
      await api.init();
      api.setToken('test-token');

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ saved: true, id: 'ann-1' }),
      });

      const annotation = {
        id: 'ann-1',
        paper_id: 'paper-1',
        page: 0,
        type: 'highlight' as const,
        geometry: { x: 100, y: 200, width: 50, height: 20 },
        color: '#FFEB3B',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };

      await api.saveAnnotation(annotation);

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/annotations/save'),
        expect.objectContaining({ method: 'POST' })
      );
    });
  });

  describe('getBibtex', () => {
    it('should return bibtex when DOI exists', async () => {
      await api.init();
      api.setToken('test-token');

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          bibtex: '@article{test2024...}',
          doi: '10.1234/test',
          doi_link: 'https://doi.org/10.1234/test',
          source: 'doi',
        }),
      });

      const result = await api.getBibtex('paper-1');

      expect(result.bibtex).toContain('@article');
      expect(result.doi).toBe('10.1234/test');
    });

    it('should return null bibtex when no DOI', async () => {
      await api.init();
      api.setToken('test-token');

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          bibtex: null,
          doi: null,
          message: 'No DOI found',
        }),
      });

      const result = await api.getBibtex('paper-1');

      expect(result.bibtex).toBeNull();
    });
  });

  describe('getPdfUrl', () => {
    it('should generate correct PDF URL with token', async () => {
      await api.init();
      api.setToken('my-token');

      const url = api.getPdfUrl('paper-123');

      expect(url).toContain('/api/papers/paper-123/pdf');
      expect(url).toContain('token=my-token');
    });
  });
});
