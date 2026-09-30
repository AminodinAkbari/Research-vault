/**
 * Highlight marks engine — port of the offset/mark algorithm from
 * app/templates/links/read.html.
 *
 * Offsets are global character positions over the concatenated text of every
 * text node under the article root (tree order, whitespace included).
 * Highlights are applied in descending start order so that earlier (higher)
 * marks never invalidate the offsets of the ones applied after them.
 */

import { resolveHighlightColor } from "./constants";

export interface MarkSpec {
  id: string;
  start_offset: number;
  end_offset: number;
  color?: string | null;
}

/** Text nodes under `root` in tree order (whitespace-only nodes included). */
export function textNodesUnder(root: Node): Text[] {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const nodes: Text[] = [];
  while (walker.nextNode()) {
    nodes.push(walker.currentNode as Text);
  }
  return nodes;
}

/**
 * Whether `text` lies entirely before the boundary point `(element, childIndex)`
 * — i.e. before child #childIndex of `element`.
 */
function isTextNodeBeforeElementBoundary(text: Text, element: Element, childIndex: number): boolean {
  const relation = element.compareDocumentPosition(text);
  if (relation & Node.DOCUMENT_POSITION_CONTAINED_BY) {
    let child: Node | null = text;
    while (child && child.parentNode !== element) {
      child = child.parentNode;
    }
    if (!child) return false;
    const index = Array.prototype.indexOf.call(element.childNodes, child);
    return index >= 0 && index < childIndex;
  }
  return (relation & Node.DOCUMENT_POSITION_PRECEDING) !== 0;
}

/**
 * Global character offset of `offsetInNode` inside `targetNode`.
 * Element boundaries (a selection can end at an element edge) resolve to the
 * text position they sit against. Returns -1 when the node is not inside `root`.
 */
export function computeGlobalOffset(
  root: Node,
  targetNode: Node,
  offsetInNode: number
): number {
  if (!root.contains(targetNode)) return -1;

  if (targetNode.nodeType === Node.TEXT_NODE) {
    let charCount = 0;
    for (const node of textNodesUnder(root)) {
      if (node === targetNode) {
        return charCount + offsetInNode;
      }
      charCount += node.textContent?.length ?? 0;
    }
    return -1;
  }

  if (targetNode.nodeType !== Node.ELEMENT_NODE) return -1;
  const element = targetNode as Element;
  if (offsetInNode < 0 || offsetInNode > element.childNodes.length) return -1;

  let charCount = 0;
  for (const node of textNodesUnder(root)) {
    if (!isTextNodeBeforeElementBoundary(node, element, offsetInNode)) {
      return charCount;
    }
    charCount += node.textContent?.length ?? 0;
  }
  return charCount;
}

/** Unwrap every mark and merge the split text nodes back together. */
export function clearAllMarks(root: HTMLElement): void {
  root.querySelectorAll("mark.highlight").forEach((mark) => {
    const parent = mark.parentNode;
    if (!parent) return;
    while (mark.firstChild) {
      parent.insertBefore(mark.firstChild, mark);
    }
    parent.removeChild(mark);
  });
  root.normalize();
}

/** Clear existing marks, then paint every valid highlight as a `<mark>`. */
export function applyMarks(root: HTMLElement, highlights: MarkSpec[]): void {
  clearAllMarks(root);
  if (highlights.length === 0) return;

  const initialNodes = textNodesUnder(root);
  const totalLength = initialNodes.reduce(
    (sum, node) => sum + (node.textContent?.length ?? 0),
    0
  );
  if (totalLength === 0) return;

  const sorted = [...highlights].sort(
    (a, b) => b.start_offset - a.start_offset
  );

  for (const highlight of sorted) {
    const { start_offset: start, end_offset: end } = highlight;
    if (!Number.isFinite(start) || !Number.isFinite(end)) continue;
    if (start >= end || start < 0 || end > totalLength) continue;

    // The DOM changed with every applied mark — recompute node positions.
    const currentNodes = textNodesUnder(root);
    const nodeStarts: number[] = [];
    let cumulative = 0;
    for (const node of currentNodes) {
      nodeStarts.push(cumulative);
      cumulative += node.textContent?.length ?? 0;
    }

    let startNodeIdx = 0;
    while (
      startNodeIdx < currentNodes.length - 1 &&
      nodeStarts[startNodeIdx + 1] <= start
    ) {
      startNodeIdx++;
    }
    let endNodeIdx = startNodeIdx;
    while (
      endNodeIdx < currentNodes.length - 1 &&
      nodeStarts[endNodeIdx + 1] <= end
    ) {
      endNodeIdx++;
    }
    // Offset 0 of node i and the end of node i-1 are the same position;
    // keeping the boundary inside the earlier node avoids wrapping the empty
    // shell of a previously applied mark.
    while (endNodeIdx > startNodeIdx && nodeStarts[endNodeIdx] === end) {
      endNodeIdx--;
    }

    const startNode = currentNodes[startNodeIdx];
    const endNode = currentNodes[endNodeIdx];
    if (!startNode || !endNode || !startNode.parentNode || !endNode.parentNode) {
      continue;
    }

    const startOffsetInNode = start - nodeStarts[startNodeIdx];
    const endOffsetInNode = end - nodeStarts[endNodeIdx];
    const backgroundColor = resolveHighlightColor(highlight.color);

    if (startNode === endNode) {
      const text = startNode.textContent ?? "";
      const mark = document.createElement("mark");
      mark.className = "highlight";
      mark.style.backgroundColor = backgroundColor;
      mark.dataset.highlightId = highlight.id;
      mark.textContent = text.substring(startOffsetInNode, endOffsetInNode);

      const parent = startNode.parentNode;
      parent.insertBefore(
        document.createTextNode(text.substring(0, startOffsetInNode)),
        startNode
      );
      parent.insertBefore(mark, startNode);
      parent.insertBefore(
        document.createTextNode(text.substring(endOffsetInNode)),
        startNode
      );
      parent.removeChild(startNode);
    } else {
      const range = document.createRange();
      range.setStart(startNode, startOffsetInNode);
      range.setEnd(endNode, endOffsetInNode);
      const mark = document.createElement("mark");
      mark.className = "highlight";
      mark.style.backgroundColor = backgroundColor;
      mark.dataset.highlightId = highlight.id;
      // Range.surroundContents() throws whenever the range partially selects a
      // block element (any cross-paragraph selection), so the range contents are
      // extracted and re-wrapped manually instead.
      const contents = range.extractContents();
      mark.appendChild(contents);
      range.insertNode(mark);
    }
  }
}
