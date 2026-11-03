from __future__ import annotations

from lxml.html import fromstring, tostring
from lxml_html_clean import Cleaner

_BLOCK_TAGS = frozenset(
    {
        "address",
        "article",
        "aside",
        "blockquote",
        "div",
        "dl",
        "dt",
        "dd",
        "fieldset",
        "figcaption",
        "figure",
        "footer",
        "form",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "hr",
        "li",
        "main",
        "nav",
        "ol",
        "p",
        "pre",
        "section",
        "table",
        "tr",
        "ul",
    }
)

_ALLOWED_TAGS = [
    "a",
    "abbr",
    "b",
    "blockquote",
    "br",
    "code",
    "dd",
    "div",
    "dl",
    "dt",
    "em",
    "figcaption",
    "figure",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "i",
    "img",
    "li",
    "ol",
    "p",
    "pre",
    "s",
    "span",
    "strong",
    "sub",
    "sup",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "tr",
    "u",
    "ul",
]

_cleaner = Cleaner(
    scripts=True,
    javascript=True,
    comments=True,
    style=True,
    inline_style=True,
    links=True,
    meta=True,
    page_structure=True,
    processing_instructions=True,
    embedded=True,
    frames=True,
    forms=True,
    annoying_tags=True,
    safe_attrs_only=True,
    allow_tags=_ALLOWED_TAGS,
)


def html_to_text(html: str | None) -> str:
    """Flatten sanitized article HTML to plain text for AI, search and export.

    Block-level elements are separated with newlines so paragraphs and
    headings do not run together, mirroring the old plain-text extraction
    behaviour.
    """
    if not html:
        return ""

    try:
        doc = fromstring(html)
    except Exception:
        return html.strip()

    for element in doc.iter():
        tag = element.tag
        if not isinstance(tag, str):
            continue
        if tag in _BLOCK_TAGS or tag == "br":
            element.text = "\n" + (element.text or "")
            element.tail = (element.tail or "") + "\n"

    lines = [line.strip() for line in doc.text_content().splitlines()]
    return "\n".join(line for line in lines if line).strip()
