/**
 * Tests for TypeScript types and constants
 */
import { HIGHLIGHT_COLORS, type AnnotationType, type PanelState } from '../types';

describe('HIGHLIGHT_COLORS', () => {
  it('should have 10 colors', () => {
    expect(HIGHLIGHT_COLORS).toHaveLength(10);
  });

  it('should have valid hex colors', () => {
    const hexPattern = /^#[0-9A-F]{6}$/i;
    HIGHLIGHT_COLORS.forEach((color) => {
      expect(color).toMatch(hexPattern);
    });
  });

  it('should include yellow as first color', () => {
    expect(HIGHLIGHT_COLORS[0]).toBe('#FFEB3B');
  });
});

describe('Type exports', () => {
  it('should export AnnotationType', () => {
    const types: AnnotationType[] = [
      'highlight',
      'rectangle',
      'ellipse',
      'text',
      'comment',
      'ink',
      'image',
    ];
    expect(types).toHaveLength(7);
  });

  it('should export PanelState', () => {
    const states: PanelState[] = ['no_pdf', 'unsaved_pdf', 'saved_pdf'];
    expect(states).toHaveLength(3);
  });
});

describe('Paper type structure', () => {
  it('should validate paper object shape', () => {
    const paper = {
      id: '123',
      title: 'Test Paper',
      authors: 'John Doe',
      year: 2024,
      doi: '10.1234/test',
      source_url: 'https://example.com/paper.pdf',
      local_pdf_path: '/path/to/paper.pdf',
      added_at: '2024-01-01T00:00:00Z',
      indexed_at: '2024-01-01T00:00:00Z',
      embeddings_ready: true,
      status: 'indexed' as const,
      collection: 'default',
    };

    expect(paper.id).toBeDefined();
    expect(paper.title).toBeDefined();
    expect(paper.status).toBe('indexed');
  });
});

describe('Annotation type structure', () => {
  it('should validate annotation object shape', () => {
    const annotation = {
      id: 'ann-1',
      paper_id: 'paper-1',
      page: 0,
      type: 'highlight' as const,
      geometry: { x: 100, y: 200, width: 50, height: 20 },
      color: '#FFEB3B',
      opacity: 0.5,
      text_content: 'Test note',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    };

    expect(annotation.type).toBe('highlight');
    expect(annotation.geometry.x).toBe(100);
    expect(annotation.opacity).toBe(0.5);
  });

  it('should validate ink annotation with points', () => {
    const inkAnnotation = {
      id: 'ink-1',
      paper_id: 'paper-1',
      page: 0,
      type: 'ink' as const,
      geometry: {
        x: 0,
        y: 0,
        points: [
          { x: 10, y: 20 },
          { x: 15, y: 25 },
          { x: 20, y: 22 },
        ],
      },
      color: '#F44336',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    };

    expect(inkAnnotation.geometry.points).toHaveLength(3);
  });
});

describe('SearchResult type structure', () => {
  it('should validate search result shape', () => {
    const result = {
      id: 'chunk-1',
      page: 2,
      bbox: { x: 50, y: 100, width: 200, height: 30 },
      text: 'This is the matched text content.',
      score: 0.85,
      normalized_score: 0.9,
    };

    expect(result.score).toBeGreaterThan(0);
    expect(result.score).toBeLessThanOrEqual(1);
    expect(result.normalized_score).toBeGreaterThanOrEqual(0);
    expect(result.normalized_score).toBeLessThanOrEqual(1);
  });
});
