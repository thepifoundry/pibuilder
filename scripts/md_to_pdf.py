"""
Convert a Markdown file to PDF using markdown + weasyprint.

Usage
-----
    python scripts/md_to_pdf.py <input.md> [output.pdf]

If output path is omitted, the PDF is written alongside the input file.
"""

import sys
from pathlib import Path
import markdown
from weasyprint import HTML, CSS

CSS_STYLES = """
@page {
    size: A4;
    margin: 2.5cm 2.2cm 2.5cm 2.2cm;
}
body {
    font-family: "Helvetica Neue", Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.6;
    color: #1a1a1a;
}
h1 {
    font-size: 18pt;
    border-bottom: 2px solid #2c5f8a;
    padding-bottom: 6px;
    color: #2c5f8a;
    margin-top: 0;
}
h2 {
    font-size: 14pt;
    color: #2c5f8a;
    margin-top: 1.6em;
    border-left: 4px solid #2c5f8a;
    padding-left: 8px;
}
h3 {
    font-size: 11.5pt;
    color: #444;
    margin-top: 1.2em;
}
code, pre {
    font-family: "Courier New", Courier, monospace;
    font-size: 9.5pt;
    background: #f4f4f4;
    border-radius: 3px;
}
code {
    padding: 1px 4px;
}
pre {
    padding: 10px 14px;
    border-left: 3px solid #ccc;
    overflow-x: auto;
    white-space: pre-wrap;
}
table {
    border-collapse: collapse;
    width: 100%;
    font-size: 9.5pt;
    margin: 1em 0;
}
th {
    background: #2c5f8a;
    color: white;
    padding: 6px 10px;
    text-align: left;
}
td {
    padding: 5px 10px;
    border-bottom: 1px solid #ddd;
}
tr:nth-child(even) td {
    background: #f8f8f8;
}
hr {
    border: none;
    border-top: 1px solid #ccc;
    margin: 1.5em 0;
}
blockquote {
    margin: 0;
    padding: 6px 16px;
    border-left: 4px solid #2c5f8a;
    color: #555;
    background: #f0f5fa;
}
"""


def convert(md_path: Path, pdf_path: Path) -> None:
    md_text = md_path.read_text(encoding="utf-8")
    html_body = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "codehilite"],
    )
    full_html = f"<!DOCTYPE html><html><body>{html_body}</body></html>"
    HTML(string=full_html, base_url=str(md_path.parent)).write_pdf(
        str(pdf_path),
        stylesheets=[CSS(string=CSS_STYLES)],
    )
    print(f"Written: {pdf_path}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/md_to_pdf.py <input.md> [output.pdf]")
        sys.exit(1)
    md_path = Path(sys.argv[1]).resolve()
    pdf_path = Path(sys.argv[2]).resolve() if len(sys.argv) >= 3 else md_path.with_suffix(".pdf")
    convert(md_path, pdf_path)


if __name__ == "__main__":
    main()
