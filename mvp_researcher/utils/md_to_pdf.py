"""Render a markdown report to a PDF on disk.

Thin wrapper around md2pdf. We write the markdown to a temp file because
md2pdf only accepts file paths, not strings, then run the conversion.
"""
from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile


_DEFAULT_CSS = """
body { font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
       max-width: 760px; margin: 2em auto; line-height: 1.55; color: #222; }
h1, h2, h3 { line-height: 1.25; }
h1 { font-size: 1.9em; border-bottom: 1px solid #ddd; padding-bottom: 0.2em; }
h2 { font-size: 1.4em; margin-top: 1.6em; }
h3 { font-size: 1.1em; }
code { background: #f3f3f3; padding: 0 0.2em; border-radius: 3px; }
pre  { background: #f6f8fa; padding: 0.8em; overflow-x: auto; }
a    { color: #0a58ca; }
hr   { border: none; border-top: 1px solid #eee; margin: 2em 0; }
"""


def markdown_to_pdf(markdown_text: str, output_path: str | Path) -> Path:
    """Write `markdown_text` to `output_path` as a PDF. Returns the path."""
    from md2pdf.core import md2pdf  # imported lazily; PDF deps are heavy

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as md_file:
        md_file.write(markdown_text)
        md_path = md_file.name
    with NamedTemporaryFile("w", suffix=".css", delete=False, encoding="utf-8") as css_file:
        css_file.write(_DEFAULT_CSS)
        css_path = css_file.name

    md2pdf(str(output), md_file_path=md_path, css_file_path=css_path)
    return output
