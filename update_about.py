#!/usr/bin/env python3
"""Update shared About text across Typst and HTML sources."""

from __future__ import annotations

import html
import re
from pathlib import Path

ABOUT_SOURCE = Path("about.txt")
CV_FILE = Path("cv/main.typ")
INDEX_FILE = Path("index.html")

CV_START = "// BEGIN GENERATED ABOUT"
CV_END = "// END GENERATED ABOUT"
HTML_START = "<!-- BEGIN GENERATED ABOUT -->"
HTML_END = "<!-- END GENERATED ABOUT -->"


def load_about_text() -> str:
    return ABOUT_SOURCE.read_text(encoding="utf-8").strip()


def parse_inline(text: str) -> list[tuple[str, tuple[str, ...]]]:
    pattern = re.compile(r"(`[^`]+`|\[[^\]]+\]\([^)]+\))")
    tokens: list[tuple[str, tuple[str, ...]]] = []
    position = 0

    for match in pattern.finditer(text):
        if match.start() > position:
            tokens.append(("text", (text[position:match.start()],)))

        token = match.group(0)
        if token.startswith("`"):
            tokens.append(("code", (token[1:-1],)))
        else:
            link_match = re.fullmatch(r"\[([^\]]+)\]\(([^)]+)\)", token)
            if link_match is None:
                tokens.append(("text", (token,)))
            else:
                tokens.append(("link", (link_match.group(1), link_match.group(2))))

        position = match.end()

    if position < len(text):
        tokens.append(("text", (text[position:],)))

    return tokens


def replace_marked_block(content: str, start: str, end: str, replacement: str) -> str:
    pattern = re.compile(
        rf"^[ \t]*{re.escape(start)}.*?^[ \t]*{re.escape(end)}",
        re.MULTILINE | re.DOTALL,
    )
    if not pattern.search(content):
        raise RuntimeError(f"Could not find marker block: {start} ... {end}")
    return pattern.sub(replacement, content, count=1)


def render_cv_block(text: str) -> str:
    parts = []
    for token_type, values in parse_inline(text):
        if token_type == "text":
            parts.append(values[0])
        elif token_type == "code":
            parts.append(f"`{values[0]}`")
        else:
            label, url = values
            parts.append(f'#link("{url}")[{label}]')

    typst_text = "".join(parts)
    return "\n".join(
        [
            CV_START,
            typst_text,
            CV_END,
        ]
    )


def render_html_block(text: str) -> str:
    rendered = []
    for token_type, values in parse_inline(text):
        if token_type == "text":
            rendered.append(html.escape(values[0]))
        elif token_type == "code":
            rendered.append(f"<code>{html.escape(values[0])}</code>")
        else:
            label, url = values
            rendered.append(f'<a href="{html.escape(url, quote=True)}">{html.escape(label)}</a>')
    html_text = "".join(rendered)
    return "\n".join(
        [
            f"          {HTML_START}",
            f"          <p>{html_text}</p>",
            f"          {HTML_END}",
        ]
    )


def main() -> None:
    about_text = load_about_text()

    cv_content = CV_FILE.read_text(encoding="utf-8")
    cv_content = replace_marked_block(cv_content, CV_START, CV_END, render_cv_block(about_text))
    CV_FILE.write_text(cv_content, encoding="utf-8")

    index_content = INDEX_FILE.read_text(encoding="utf-8")
    index_content = replace_marked_block(
        index_content,
        HTML_START,
        HTML_END,
        render_html_block(about_text),
    )
    INDEX_FILE.write_text(index_content, encoding="utf-8")

    print(f"Updated {CV_FILE}")
    print(f"Updated {INDEX_FILE}")


if __name__ == "__main__":
    main()
