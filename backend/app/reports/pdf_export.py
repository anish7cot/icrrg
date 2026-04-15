"""PDF export service — converts Markdown report content to styled PDF."""

from __future__ import annotations

import io
import logging
from datetime import date, datetime

import markdown
from xhtml2pdf import pisa

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CSS stylesheet for PDF rendering
# ---------------------------------------------------------------------------

_PDF_CSS = """
@page {
    size: A4;
    margin: 2cm 2.5cm;

    @frame footer {
        -pdf-frame-content: page-footer;
        bottom: 0;
        height: 1cm;
        margin-left: 2.5cm;
        margin-right: 2.5cm;
    }
}

body {
    font-family: Helvetica, Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.6;
    color: #1a1a1a;
}

/* Cover section */
.cover {
    text-align: center;
    padding-top: 80px;
    padding-bottom: 40px;
    margin-bottom: 30px;
    border-bottom: 3px solid #1565c0;
}

.cover h1 {
    font-size: 26pt;
    color: #1565c0;
    margin-bottom: 8px;
    font-weight: 700;
}

.cover .subtitle {
    font-size: 14pt;
    color: #424242;
    margin-bottom: 6px;
}

.cover .meta {
    font-size: 10pt;
    color: #757575;
    margin-top: 20px;
}

.cover .meta span {
    display: inline-block;
    margin: 0 12px;
}

/* Badge styles */
.audience-badge {
    display: inline-block;
    padding: 4px 14px;
    border-radius: 12px;
    font-size: 10pt;
    font-weight: 600;
    margin-top: 10px;
}

.audience-developer {
    background-color: #e3f2fd;
    color: #1565c0;
}

.audience-manager {
    background-color: #f3e5f5;
    color: #7b1fa2;
}

.audience-leadership {
    background-color: #fce4ec;
    color: #c62828;
}

/* Headings */
h1 {
    font-size: 20pt;
    color: #1565c0;
    margin-top: 28px;
    margin-bottom: 10px;
    padding-bottom: 6px;
    border-bottom: 1px solid #e0e0e0;
}

h2 {
    font-size: 16pt;
    color: #1a237e;
    margin-top: 22px;
    margin-bottom: 8px;
}

h3 {
    font-size: 13pt;
    color: #283593;
    margin-top: 18px;
    margin-bottom: 6px;
}

/* Paragraphs and lists */
p {
    margin: 6px 0;
}

ul, ol {
    margin: 6px 0;
    padding-left: 20px;
}

li {
    margin: 3px 0;
}

strong {
    font-weight: 700;
}

em {
    font-style: italic;
}

/* Tables */
table {
    width: 100%;
    border-collapse: collapse;
    margin: 14px 0;
    font-size: 10pt;
}

th, td {
    border: 1px solid #bdbdbd;
    padding: 8px 10px;
    text-align: left;
}

th {
    background-color: #e8eaf6;
    font-weight: 700;
    color: #1a237e;
}

tr:nth-child(even) td {
    background-color: #f5f5f5;
}

/* Code blocks */
code {
    font-family: Courier, monospace;
    font-size: 9pt;
    background-color: #f5f5f5;
    padding: 1px 4px;
    border-radius: 3px;
}

pre {
    background-color: #f5f5f5;
    padding: 12px;
    border-radius: 6px;
    border: 1px solid #e0e0e0;
    font-size: 9pt;
    overflow-x: auto;
    white-space: pre-wrap;
    word-wrap: break-word;
}

pre code {
    background: none;
    padding: 0;
}

/* Blockquotes */
blockquote {
    border-left: 4px solid #1565c0;
    margin: 14px 0;
    padding: 8px 16px;
    background-color: #f5f5f5;
    color: #424242;
}

blockquote p {
    margin: 4px 0;
}

/* Horizontal rules */
hr {
    border: none;
    border-top: 1px solid #e0e0e0;
    margin: 20px 0;
}

/* Footer */
#page-footer {
    font-size: 8pt;
    color: #9e9e9e;
    text-align: center;
    border-top: 1px solid #e0e0e0;
    padding-top: 4px;
}
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_pdf(
    markdown_content: str,
    repository: str,
    audience_type: str,
    date_range_start: date,
    date_range_end: date,
    generated_at: datetime | None = None,
) -> bytes:
    """Convert Markdown report content to a styled PDF.

    Returns the PDF as raw bytes ready to be served via HTTP response.
    """
    # Convert Markdown → HTML
    md = markdown.Markdown(
        extensions=["tables", "fenced_code", "nl2br", "sane_lists"],
    )
    body_html = md.convert(markdown_content)

    # Build audience label
    audience_labels = {
        "developer": "Developer Technical Report",
        "manager": "Engineering Manager Summary",
        "leadership": "Executive Security Briefing",
    }
    audience_label = audience_labels.get(audience_type, audience_type.title() + " Report")
    audience_css_class = f"audience-{audience_type}"

    # Format dates
    date_str = f"{date_range_start.isoformat()} — {date_range_end.isoformat()}"
    gen_str = (generated_at or datetime.utcnow()).strftime("%B %d, %Y at %H:%M UTC")

    # Assemble full HTML document
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>{_PDF_CSS}</style>
</head>
<body>
    <!-- Cover Section -->
    <div class="cover">
        <h1>Security Report</h1>
        <p class="subtitle">{repository}</p>
        <div class="audience-badge {audience_css_class}">{audience_label}</div>
        <p class="meta">
            <span>Period: {date_str}</span>
            <br>
            <span>Generated: {gen_str}</span>
        </p>
    </div>

    <!-- Report Content -->
    {body_html}

    <!-- Footer for every page -->
    <div id="page-footer">
        ICRRG — {repository} — {audience_label} — Page <pdf:pagenumber> of <pdf:pagecount>
    </div>
</body>
</html>"""

    # Render HTML → PDF
    pdf_buffer = io.BytesIO()
    pisa_status = pisa.CreatePDF(
        src=html,
        dest=pdf_buffer,
        encoding="utf-8",
    )

    if pisa_status.err:
        logger.error("PDF generation failed with %d errors", pisa_status.err)
        raise RuntimeError(f"PDF generation failed with {pisa_status.err} error(s)")

    pdf_bytes = pdf_buffer.getvalue()
    logger.info(
        "PDF generated: %s %s report, %d bytes",
        repository, audience_type, len(pdf_bytes),
    )
    return pdf_bytes
