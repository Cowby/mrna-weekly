#!/usr/bin/env python3
"""Convert Markdown to styled PDF using WeasyPrint.
Usage: python3 md-to-pdf.py <input.md> [output.pdf]
"""

import sys
import os
import markdown
from weasyprint import HTML

if len(sys.argv) < 2:
    print("Usage: python3 md-to-pdf.py <input.md> [output.pdf]", file=sys.stderr)
    sys.exit(1)

input_file = sys.argv[1]
output_file = sys.argv[2] if len(sys.argv) > 2 else input_file.rsplit('.', 1)[0] + '.pdf'

with open(input_file, 'r', encoding='utf-8') as f:
    md_text = f.read()

# Convert markdown to HTML
html_body = markdown.markdown(md_text, extensions=['tables', 'fenced_code', 'toc'])

# Full HTML with professional styling
html_doc = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  @page {{
    size: A4;
    margin: 2cm 1.8cm 2.5cm 1.8cm;
    @bottom-center {{
      content: "Page " counter(page) " of " counter(pages);
      font-size: 8pt;
      color: #999;
      font-family: Helvetica, Arial, sans-serif;
    }}
  }}

  body {{
    font-family: Helvetica, Arial, sans-serif, 'Noto Color Emoji', 'Noto Emoji';
    font-size: 10pt;
    line-height: 1.5;
    color: #2d2d2d;
  }}

  h1 {{
    font-size: 22pt;
    color: #1a1a2e;
    border-bottom: 2.5px solid #16537e;
    padding-bottom: 6px;
    margin-top: 10px;
    margin-bottom: 15px;
  }}

  h2 {{
    font-size: 15pt;
    color: #16537e;
    border-bottom: 1px solid #ddd;
    padding-bottom: 4px;
    margin-top: 22px;
    margin-bottom: 10px;
  }}

  h3 {{
    font-size: 12pt;
    color: #1e40af;
    margin-top: 18px;
    margin-bottom: 6px;
  }}

  h4 {{
    font-size: 10.5pt;
    color: #333;
    margin-top: 10px;
    margin-bottom: 4px;
  }}

  p {{
    margin: 0 0 8px 0;
  }}

  blockquote {{
    border-left: 3px solid #16537e;
    margin: 8px 0;
    padding: 6px 12px;
    background: #f8f9fb;
    color: #444;
    font-size: 9.5pt;
  }}

  blockquote p {{
    margin: 2px 0;
  }}

  ul, ol {{
    margin: 4px 0 10px 0;
    padding-left: 22px;
  }}

  li {{
    margin-bottom: 4px;
  }}

  strong {{
    color: #1a1a1a;
  }}

  em {{
    color: #555;
  }}

  a {{
    color: #2563eb;
    text-decoration: none;
  }}

  code {{
    background: #f4f1f9;
    color: #c7254e;
    padding: 1px 4px;
    border-radius: 3px;
    font-size: 9pt;
    font-family: 'Courier New', monospace;
    word-wrap: break-word;
    overflow-wrap: break-word;
  }}

  pre {{
    background: #f8f8f8;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    padding: 10px 12px;
    margin: 8px 0;
    font-size: 8.5pt;
    line-height: 1.4;
    white-space: pre-wrap;
    word-wrap: break-word;
    overflow-wrap: break-word;
    page-break-inside: avoid;
  }}

  pre code {{
    background: none;
    color: #333;
    padding: 0;
    font-size: 8.5pt;
  }}

  hr {{
    border: none;
    border-top: 1px solid #ccc;
    margin: 15px 0;
  }}

  table {{
    border-collapse: collapse;
    width: 100%;
    margin: 10px 0;
    font-size: 9pt;
  }}

  th, td {{
    border: 1px solid #ddd;
    padding: 6px 8px;
    text-align: left;
    word-wrap: break-word;
    overflow-wrap: break-word;
  }}

  table {{
    table-layout: fixed;
  }}

  th {{
    background: #f0f4f8;
    font-weight: bold;
    color: #16537e;
  }}
</style>
</head>
<body>
{html_body}
</body>
</html>"""

HTML(string=html_doc).write_pdf(output_file)
print(f"PDF generated: {output_file} ({os.path.getsize(output_file) // 1024}KB)")
