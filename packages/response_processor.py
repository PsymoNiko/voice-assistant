from typing import Any
from markdown_it import MarkdownIt


def process_markdown(markdown: str) -> tuple[list[dict[str, Any]], str]:
    """Return UI blocks and speech-safe text without changing the original."""
    tokens = MarkdownIt().parse(markdown)
    blocks: list[dict[str, Any]] = []
    speech: list[str] = []
    for token in tokens:
        if token.type == "inline" and token.content.strip():
            blocks.append({"type": "text", "text": token.content})
            speech.append(token.content.strip())
        elif token.type == "fence":
            blocks.append({"type": "code", "language": token.info or "text", "content": token.content})
            speech.append("I included a code example below.")
        elif token.type == "heading_open":
            blocks.append({"type": "heading", "level": int(token.tag[1:])})
        elif token.type == "table_open":
            speech.append("The details are shown in the table below.")
    return blocks, " ".join(speech).strip()
