import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, fireEvent, screen, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ProjectSearchBox } from '@/components/search/ProjectSearchBox';
import { endpoints } from '@/lib/endpoints';

const PROJECT_ID = '11111111-1111-4111-8111-111111111111';
const NOTE_ID = '33333333-3333-4333-8333-333333333333';
const LINK_ID = '44444444-4444-4444-8444-444444444444';

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

let fetchMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
  fetchMock = vi.fn();
  vi.stubGlobal('fetch', fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('semantic search reranking', () => {
  it('triggers AI rerank and updates results', async () => {
    const initialResults = [
      { type: 'note', id: NOTE_ID, title: 'Note 1', snippet: 'First', rank: 1 },
      { type: 'link', id: LINK_ID, title: 'Link 1', snippet: 'Second', rank: 2 },
    ];
    const rerankedResults = [
      { type: 'link', id: LINK_ID, title: 'Link 1', snippet: 'Second', rank: 0, semantic: true },
      { type: 'note', id: NOTE_ID, title: 'Note 1', snippet: 'First', rank: 1, semantic: true },
    ];

    // Mock collected search GET response
    fetchMock
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(initialResults),
      })
      // Mock semantic search POST response
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(rerankedResults),
      });

    const wrapper = createWrapper();
    render(<ProjectSearchBox projectId={PROJECT_ID} />, { wrapper });

    // Type query and submit
    const input = screen.getByPlaceholderText('Search notes & links…');
    await act(async () => {
      fireEvent.change(input, { target: { value: 'test' } });
    });

    await act(async () => {
      fireEvent.submit(screen.getByRole('button', { name: 'Search' }).closest('form')!);
    });

    // Wait for initial results to appear
    await waitFor(() => expect(screen.getByText('Note 1')).toBeInTheDocument());

    // Click rerank button
    const rerankBtn = await waitFor(() => screen.getByRole('button', { name: 'Rerank with AI' }));
    await act(async () => {
      fireEvent.click(rerankBtn);
    });

    // Verify POST called with proper payload
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        endpoints.semanticSearch(PROJECT_ID),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ query: 'test' }),
          headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
        })
      )
    );

    // Wait for AI reranked badge to appear
    await waitFor(() => expect(screen.getByText('AI reranked')).toBeInTheDocument());
    // Both results still visible
    expect(screen.getByText('Note 1')).toBeInTheDocument();
    expect(screen.getByText('Link 1')).toBeInTheDocument();
  });
});
