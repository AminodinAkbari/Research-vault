import { describe, it, expect, beforeEach, afterEach } from "vitest";
import {
  textNodesUnder,
  computeGlobalOffset,
  clearAllMarks,
  applyMarks,
  MarkSpec,
} from "@/lib/highlightMarks";
import { resolveHighlightColor } from "@/lib/constants";

/**
 * Port of the highlight offset/mark algorithm from app/templates/links/read.html.
 * Offsets are global character positions over the concatenated text of every
 * text node under the article root (tree order, whitespace included).
 */

const SIMPLE = "<p>Alpha beta gamma</p><p>Delta epsilon</p>";
// text nodes: "Alpha beta gamma" (0..16), "Delta epsilon" (16..29) => total 29

const NESTED = "<p>Intro <em>emphasis</em> tail</p>";
// text nodes: "Intro " (0..6), "emphasis" (6..14), " tail" (14..19) => total 19

let article: HTMLElement;

function build(html: string): HTMLElement {
  article = document.createElement("div");
  article.id = "reader-article";
  article.innerHTML = html;
  document.body.appendChild(article);
  return article;
}

function marks(): HTMLElement[] {
  return Array.from(article.querySelectorAll("mark.highlight"));
}

function offsetIsMarked(offset: number): boolean {
  const nodes = textNodesUnder(article);
  let cursor = 0;
  for (const node of nodes) {
    const end = cursor + node.textContent!.length;
    if (offset >= cursor && offset < end) {
      return node.parentElement?.closest("mark.highlight") !== null;
    }
    cursor = end;
  }
  return false;
}

function toHex(css: string): string {
  const match = css.match(/^rgb\((\d+),\s*(\d+),\s*(\d+)\)$/);
  if (match) {
    return `#${match
      .slice(1)
      .map((n) => Number(n).toString(16).padStart(2, "0"))
      .join("")}`;
  }
  return css.toLowerCase();
}

beforeEach(() => {
  document.body.innerHTML = "";
});

afterEach(() => {
  document.body.innerHTML = "";
});

describe("textNodesUnder", () => {
  it("returns text nodes in tree order, including whitespace-only nodes", () => {
    const root = build("<p>Alpha</p>\n<p>Beta <strong>Gamma</strong></p>");

    const nodes = textNodesUnder(root);

    expect(nodes.every((n) => n.nodeType === Node.TEXT_NODE)).toBe(true);
    expect(nodes.map((n) => n.textContent)).toEqual([
      "Alpha",
      "\n",
      "Beta ",
      "Gamma",
    ]);
  });

  it("returns an empty list for an element with no text", () => {
    const root = build("");
    expect(textNodesUnder(root)).toEqual([]);
  });
});

describe("computeGlobalOffset", () => {
  it("returns the cumulative offset of a node plus the offset inside it", () => {
    const root = build(NESTED);
    const nodes = textNodesUnder(root);

    expect(computeGlobalOffset(root, nodes[0], 3)).toBe(3);
    expect(computeGlobalOffset(root, nodes[1], 0)).toBe(6);
    expect(computeGlobalOffset(root, nodes[1], 2)).toBe(8);
    expect(computeGlobalOffset(root, nodes[2], 4)).toBe(18);
  });

  it("returns -1 when the node is not inside the root", () => {
    const root = build(NESTED);
    const outsider = document.createTextNode("elsewhere");

    expect(computeGlobalOffset(root, outsider, 0)).toBe(-1);
  });

  it("resolves element boundaries to the text position they sit against", () => {
    const root = build(NESTED);
    const paragraph = root.firstElementChild as HTMLElement;
    const emphasis = paragraph.querySelector("em") as HTMLElement;

    expect(computeGlobalOffset(root, paragraph, 0)).toBe(0);
    expect(computeGlobalOffset(root, paragraph, 2)).toBe(14);
    expect(computeGlobalOffset(root, paragraph, paragraph.childNodes.length)).toBe(19);
    expect(computeGlobalOffset(root, emphasis, 0)).toBe(6);
    expect(computeGlobalOffset(root, emphasis, emphasis.childNodes.length)).toBe(14);
  });

  it("resolves boundaries on the article root itself", () => {
    const root = build(SIMPLE);

    expect(computeGlobalOffset(root, root, 0)).toBe(0);
    expect(computeGlobalOffset(root, root, root.childNodes.length)).toBe(29);
  });

  it("returns -1 for an out-of-range element boundary", () => {
    const root = build(SIMPLE);

    expect(computeGlobalOffset(root, root, 99)).toBe(-1);
  });
});

describe("applyMarks", () => {
  it("wraps a range inside a single text node with a mark", () => {
    const root = build(SIMPLE);
    const original = root.textContent!;

    applyMarks(root, [{ id: "h1", start_offset: 6, end_offset: 10 }]);

    expect(marks()).toHaveLength(1);
    expect(marks()[0].textContent).toBe(original.slice(6, 10));
    expect(marks()[0].textContent).toBe("beta");
    expect(marks()[0].dataset.highlightId).toBe("h1");
    expect(root.textContent).toBe(original);
  });

  it("wraps a range spanning element boundaries without changing article text", () => {
    const root = build(NESTED);
    const original = root.textContent!;

    applyMarks(root, [{ id: "h1", start_offset: 3, end_offset: 16 }]);

    expect(marks()).toHaveLength(1);
    expect(marks()[0].textContent).toBe(original.slice(3, 16));
    expect(marks()[0].textContent).toBe("ro emphasis t");
    expect(root.textContent).toBe(original);
    expect(offsetIsMarked(3)).toBe(true);
    expect(offsetIsMarked(15)).toBe(true);
    expect(offsetIsMarked(16)).toBe(false);
  });

  it("wraps a range that starts and ends in different text nodes", () => {
    const root = build(SIMPLE);
    const original = root.textContent!;

    applyMarks(root, [{ id: "h1", start_offset: 12, end_offset: 20 }]);

    expect(marks()).toHaveLength(1);
    expect(marks()[0].textContent).toBe(original.slice(12, 20));
    expect(marks()[0].textContent).toBe("ammaDelt");
    expect(root.textContent).toBe(original);
  });

  it("applies out-of-order highlights so every range is marked", () => {
    const root = build(SIMPLE);
    const original = root.textContent!;

    applyMarks(root, [
      { id: "late", start_offset: 16, end_offset: 20 },
      { id: "early", start_offset: 0, end_offset: 5 },
    ]);

    expect(root.textContent).toBe(original);
    const texts = marks().map((m) => m.textContent);
    expect(texts).toContain(original.slice(16, 20));
    expect(texts).toContain(original.slice(0, 5));
    for (let i = 0; i < 5; i++) expect(offsetIsMarked(i)).toBe(true);
    for (let i = 5; i < 16; i++) expect(offsetIsMarked(i)).toBe(false);
    for (let i = 16; i < 20; i++) expect(offsetIsMarked(i)).toBe(true);
  });

  it("keeps every character of overlapping highlights marked with no text loss", () => {
    const root = build(SIMPLE);
    const original = root.textContent!;

    applyMarks(root, [
      { id: "a", start_offset: 0, end_offset: 10 },
      { id: "b", start_offset: 5, end_offset: 20 },
    ]);

    expect(root.textContent).toBe(original);
    expect(marks().length).toBeGreaterThanOrEqual(2);
    for (let i = 0; i < 20; i++) expect(offsetIsMarked(i)).toBe(true);
    expect(offsetIsMarked(20)).toBe(false);
  });

  it("renders adjacent highlights as separate marks", () => {
    const root = build(SIMPLE);
    const original = root.textContent!;

    applyMarks(root, [
      { id: "a", start_offset: 0, end_offset: 5 },
      { id: "b", start_offset: 5, end_offset: 10 },
    ]);

    expect(root.textContent).toBe(original);
    const texts = marks().map((m) => m.textContent).sort();
    expect(texts).toEqual(
      [original.slice(0, 5), original.slice(5, 10)].sort()
    );
    for (let i = 0; i < 10; i++) expect(offsetIsMarked(i)).toBe(true);
    expect(offsetIsMarked(10)).toBe(false);
  });

  it("skips invalid offsets without marking anything", () => {
    const root = build(SIMPLE);
    const original = root.textContent!;
    const total = original.length;

    const invalid: MarkSpec[] = [
      { id: "empty", start_offset: 10, end_offset: 10 },
      { id: "reversed", start_offset: 12, end_offset: 8 },
      { id: "negative", start_offset: -1, end_offset: 5 },
      { id: "beyond", start_offset: 0, end_offset: total + 1 },
      { id: "nan-start", start_offset: Number.NaN, end_offset: 5 },
      { id: "nan-end", start_offset: 0, end_offset: Number.NaN },
    ];

    expect(() => applyMarks(root, invalid)).not.toThrow();
    expect(marks()).toHaveLength(0);
    expect(root.textContent).toBe(original);
  });

  it("marks nothing when the highlight list is empty", () => {
    const root = build(SIMPLE);
    applyMarks(root, []);
    expect(marks()).toHaveLength(0);
  });

  it("does not throw on an article with no text", () => {
    const root = build("<div></div>");
    expect(() =>
      applyMarks(root, [{ id: "h1", start_offset: 0, end_offset: 4 }])
    ).not.toThrow();
    expect(marks()).toHaveLength(0);
  });

  it("replaces previously applied marks when applied again", () => {
    const root = build(SIMPLE);
    const original = root.textContent!;

    applyMarks(root, [{ id: "first", start_offset: 0, end_offset: 5 }]);
    expect(marks()).toHaveLength(1);

    applyMarks(root, [{ id: "second", start_offset: 16, end_offset: 21 }]);

    expect(marks()).toHaveLength(1);
    expect(marks()[0].dataset.highlightId).toBe("second");
    expect(marks()[0].textContent).toBe(original.slice(16, 21));
    expect(root.textContent).toBe(original);
  });
});

describe("clearAllMarks", () => {
  it("unwraps marks, merges split text nodes, and restores the article", () => {
    const root = build(SIMPLE);
    const before = root.innerHTML;
    const original = root.textContent!;

    applyMarks(root, [
      { id: "a", start_offset: 6, end_offset: 10 },
      { id: "b", start_offset: 16, end_offset: 21 },
    ]);
    expect(marks()).toHaveLength(2);

    clearAllMarks(root);

    expect(root.querySelectorAll("mark")).toHaveLength(0);
    expect(root.textContent).toBe(original);
    expect(root.innerHTML).toBe(before);
    expect(textNodesUnder(root)).toHaveLength(2);
  });

  it("is a no-op on an article without marks", () => {
    const root = build(SIMPLE);
    const before = root.innerHTML;
    clearAllMarks(root);
    expect(root.innerHTML).toBe(before);
  });
});

describe("mark colors", () => {
  it("applies the default yellow when no color is stored", () => {
    const root = build(SIMPLE);
    applyMarks(root, [{ id: "h1", start_offset: 0, end_offset: 5 }]);

    expect(toHex(marks()[0].style.backgroundColor)).toBe("#fff59d");
  });

  it("applies the stored named color", () => {
    const root = build(SIMPLE);
    applyMarks(root, [
      { id: "h1", start_offset: 0, end_offset: 5, color: "blue" },
    ]);

    expect(toHex(marks()[0].style.backgroundColor)).toBe("#b3e5fc");
  });

  it("falls back to yellow for an unknown stored color", () => {
    const root = build(SIMPLE);
    applyMarks(root, [
      { id: "h1", start_offset: 0, end_offset: 5, color: "chartreuse" },
    ]);

    expect(toHex(marks()[0].style.backgroundColor)).toBe("#fff59d");
  });
});

describe("resolveHighlightColor", () => {
  it("maps the six named colors to their hex values", () => {
    expect(resolveHighlightColor("yellow")).toBe("#fff59d");
    expect(resolveHighlightColor("blue")).toBe("#b3e5fc");
    expect(resolveHighlightColor("green")).toBe("#c8e6c9");
    expect(resolveHighlightColor("orange")).toBe("#ffccbc");
    expect(resolveHighlightColor("purple")).toBe("#e1bee7");
    expect(resolveHighlightColor("grey")).toBe("#f0f0f0");
  });

  it("renders legacy raw hex colors as-is", () => {
    expect(resolveHighlightColor("#abcdef")).toBe("#abcdef");
    expect(resolveHighlightColor("#ABC")).toBe("#ABC");
  });

  it("falls back to the default yellow for null, unknown, or invalid colors", () => {
    expect(resolveHighlightColor(null)).toBe("#fff59d");
    expect(resolveHighlightColor(undefined)).toBe("#fff59d");
    expect(resolveHighlightColor("")).toBe("#fff59d");
    expect(resolveHighlightColor("chartreuse")).toBe("#fff59d");
    expect(resolveHighlightColor("#gggggg")).toBe("#fff59d");
  });
});
