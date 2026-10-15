import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { ReactNode } from "react";
import { act, fireEvent, render, renderHook, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { endpoints } from "@/lib/endpoints";
import { ExplainRequest, ExplainResponse, HighlightRead } from "@/lib/types";
import { pickExplainedHighlight, useExplainText } from "@/hooks/useLinks";
import { ExplainCard, ExplainCardProps } from "@/components/reader/ExplainCard";

const PROJECT_ID = "11111111-1111-4111-8111-111111111111";
const LINK_ID = "22222222-2222-4222-8222-222222222222";

/** A highlight exactly as the backend returns it (see tests/test_explain.py). */
function backendHighlight(
  overrides: Record<string, unknown> = {}
): Record<string, unknown> {
  return {
    id: "33333333-3333-4333-8333-333333333333",
    link_id: LINK_ID,
    selected_text: "attention mechanism",
    annotation: "This means self-attention is important.",
    start_offset: 50,
    end_offset: 69,
    color: "yellow",
    created_at: "2026-01-02T03:04:05Z",
    ...overrides,
  };
}

const REQUEST = {
  selected_text: "attention mechanism",
  start_offset: 50,
  end_offset: 69,
} as const;

describe("explain endpoint contract", () => {
  it("builds the path from app/api/v1/links.py", () => {
    expect(endpoints.linkExplain(PROJECT_ID, LINK_ID)).toBe(
      `/api/v1/projects/${PROJECT_ID}/links/${LINK_ID}/explain`
    );
  });

  it("accepts the ExplainRequest payload used by tests/test_explain.py", () => {
    expect(ExplainRequest.parse(REQUEST)).toEqual({ ...REQUEST });
  });

  it("rejects a blank selection or out-of-contract offsets", () => {
    expect(
      ExplainRequest.safeParse({ ...REQUEST, selected_text: "" }).success
    ).toBe(false);
    expect(ExplainRequest.safeParse({ ...REQUEST, start_offset: -1 }).success).toBe(
      false
    );
    expect(ExplainRequest.safeParse({ ...REQUEST, end_offset: "10" }).success).toBe(
      false
    );
  });

  it("parses the list-of-HighlightRead response shape", () => {
    const parsed = ExplainResponse.parse([backendHighlight()]);
    expect(parsed).toHaveLength(1);
    const highlight: HighlightRead = parsed[0];
    expect(highlight.annotation).toBe(
      "This means self-attention is important."
    );
    expect(highlight.color).toBe("yellow");
    expect(highlight.created_at).toBeInstanceOf(Date);
  });
});

describe("pickExplainedHighlight", () => {
  it("returns the highlight created by the explain call", () => {
    const older = backendHighlight({
      id: "44444444-4444-4444-8444-444444444444",
      annotation: null,
      color: "blue",
      created_at: "2025-12-01T00:00:00Z",
    });
    const created = backendHighlight({
      id: "55555555-5555-4555-8555-555555555555",
      created_at: "2026-01-02T03:04:05Z",
    });
    const highlights = ExplainResponse.parse([older, created]);

    const picked = pickExplainedHighlight(highlights, REQUEST);
    expect(picked?.id).toBe(created.id);
    expect(picked?.annotation).toBe("This means self-attention is important.");
  });

  it("prefers the newest duplicate of the same range", () => {
    const first = backendHighlight({
      id: "44444444-4444-4444-8444-444444444444",
      created_at: "2025-12-01T00:00:00Z",
    });
    const second = backendHighlight({
      id: "55555555-5555-4555-8555-555555555555",
      created_at: "2026-01-02T03:04:05Z",
    });
    const highlights = ExplainResponse.parse([first, second]);

    expect(pickExplainedHighlight(highlights, REQUEST)?.id).toBe(second.id);
  });

  it("returns undefined when nothing matches the request", () => {
    const highlights = ExplainResponse.parse([
      backendHighlight({ start_offset: 0, end_offset: 9, selected_text: "other" }),
    ]);
    expect(pickExplainedHighlight(highlights, REQUEST)).toBeUndefined();
  });
});

describe("useExplainText", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  const createWrapper = () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    return ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };

  beforeEach(() => {
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("POSTs the selection to the explain endpoint and exposes the result", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve([backendHighlight()]),
    });

    const { result } = renderHook(() => useExplainText(PROJECT_ID, LINK_ID), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.explainText(REQUEST);
    });

    expect(fetchMock).toHaveBeenCalledWith(
      `/api/v1/projects/${PROJECT_ID}/links/${LINK_ID}/explain`,
      expect.objectContaining({
        method: "POST",
        credentials: "include",
        body: JSON.stringify(REQUEST),
        headers: expect.objectContaining({
          "Content-Type": "application/json",
        }),
      })
    );

    await waitFor(() => expect(result.current.explainResult).toHaveLength(1));
    expect(result.current.explainError).toBeFalsy();
    expect(
      pickExplainedHighlight(result.current.explainResult ?? [], REQUEST)
        ?.annotation
    ).toBe("This means self-attention is important.");
  });

  it("surfaces a 502 AI failure for the inline retry UI", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 502,
      json: () => Promise.resolve({ detail: "AI explanation service unavailable" }),
    });

    const { result } = renderHook(() => useExplainText(PROJECT_ID, LINK_ID), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.explainText(REQUEST).catch(() => undefined);
    });

    // TanStack Query notifies observers through its batched scheduler, so the
    // error reaches the hook on a later tick than the mutateAsync rejection.
    await waitFor(() =>
      expect(result.current.explainError).toMatchObject({
        status: 502,
        body: { detail: "AI explanation service unavailable" },
      })
    );
    expect(result.current.isExplaining).toBe(false);
    expect(result.current.explainResult).toBeUndefined();

    act(() => {
      result.current.resetExplain();
    });
    await waitFor(() => expect(result.current.explainError).toBeFalsy());
  });
});

describe("ExplainCard", () => {
  const makeProps = (): ExplainCardProps => ({
    quote: "attention mechanism",
    anchor: { top: 100, left: 40, bottom: 120 },
    isPending: false,
    explanation: null,
    error: null,
    isSavingNote: false,
    noteSaved: false,
    onRetry: vi.fn(),
    onSaveNote: vi.fn(),
    onClose: vi.fn(),
  });

  it("shows the quote and a loading skeleton while pending", () => {
    render(<ExplainCard {...makeProps()} isPending />);

    expect(screen.getByText("attention mechanism")).toBeInTheDocument();
    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Save as Note" })
    ).not.toBeInTheDocument();
  });

  it("keeps the skeleton up before the mutation reports a state", () => {
    render(<ExplainCard {...makeProps()} />);
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("renders the explanation with a Save as Note action", () => {
    const props = makeProps();
    render(
      <ExplainCard {...props} explanation="This means self-attention is important." />
    );

    expect(
      screen.getByText("This means self-attention is important.")
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Save as Note" }));
    expect(props.onSaveNote).toHaveBeenCalledTimes(1);
  });

  it("locks the note action once the note is saved", () => {
    render(
      <ExplainCard
        {...makeProps()}
        explanation="Explained."
        noteSaved
      />
    );

    expect(screen.getByRole("button", { name: "Saved" })).toBeDisabled();
  });

  it("shows an inline error with Retry when the AI call fails", () => {
    const props = makeProps();
    render(<ExplainCard {...props} error="AI explanation service unavailable" />);

    expect(screen.getByRole("alert")).toHaveTextContent(
      "AI explanation service unavailable"
    );
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(props.onRetry).toHaveBeenCalledTimes(1);
  });

  it("closes via the header button and Escape", () => {
    const props = makeProps();
    render(
      <ExplainCard {...props} explanation="Explained." />
    );

    fireEvent.click(screen.getByRole("button", { name: "Close explanation" }));
    expect(props.onClose).toHaveBeenCalledTimes(1);

    fireEvent.keyDown(document, { key: "Escape" });
    expect(props.onClose).toHaveBeenCalledTimes(2);
  });
});
