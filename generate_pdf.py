"""
==============================================================================
Intelligent Email Categorization Agent - Report PDF Generator
Student Name : Aditya khiratkar
PRN          : 24070521071
Institute    : Symbiosis Institute of Technology, Nagpur
==============================================================================
Compiles Project_Report.md into a formatted A4 academic PDF document.
"""

import sys
import os
import re
import markdown
from xhtml2pdf import pisa


def convert_md_to_pdf(md_path: str = "Project_Report.md", pdf_path: str = "Project_Report.pdf"):
    print(f"Reading markdown from {md_path}...")
    if not os.path.exists(md_path):
        print(f"Error: {md_path} does not exist!")
        sys.exit(1)

    with open(md_path, "r", encoding="utf-8") as f:
        text = f.read()

    # Clean mermaid blocks for PDF rendering if needed
    clean_text = re.sub(r"```mermaid.*?```", "*(Detailed architectural sequence and flowchart available in repository documentation)*", text, flags=re.DOTALL)

    # Convert markdown to HTML
    print("Converting Markdown to HTML...")
    html_content = markdown.markdown(clean_text, extensions=["extra", "tables"])

    # Professional academic styling
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Intelligent Email Categorization Agent - Project Report</title>
        <style>
            @page {{
                size: a4;
                margin: 2cm;
            }}
            body {{
                font-family: Helvetica, Arial, sans-serif;
                font-size: 9.5pt;
                line-height: 1.5;
                color: #1e293b;
            }}
            h1, h2, h3, h4, h5, h6 {{
                color: #0f172a;
                font-weight: bold;
            }}
            h1 {{
                font-size: 16pt;
                margin-top: 0;
                margin-bottom: 12px;
                border-bottom: 2px solid #2563eb;
                padding-bottom: 6px;
                text-align: center;
                color: #1e3a8a;
            }}
            h2 {{
                font-size: 12pt;
                margin-top: 18px;
                margin-bottom: 8px;
                border-bottom: 1px solid #cbd5e1;
                padding-bottom: 4px;
                color: #1e3a8a;
            }}
            h3 {{
                font-size: 10.5pt;
                margin-top: 14px;
                margin-bottom: 5px;
                color: #2563eb;
            }}
            p {{
                margin-top: 0;
                margin-bottom: 8px;
                text-align: justify;
            }}
            hr {{
                border: 0;
                border-top: 1px solid #cbd5e1;
                margin: 15px 0;
            }}
            ul, ol {{
                margin-top: 0;
                margin-bottom: 8px;
                padding-left: 20px;
            }}
            li {{
                margin-bottom: 3px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 8px;
                margin-bottom: 12px;
            }}
            table, th, td {{
                border: 1px solid #cbd5e1;
            }}
            th {{
                background-color: #f1f5f9;
                font-weight: bold;
                padding: 5px 6px;
                text-align: left;
                font-size: 8.5pt;
                color: #0f172a;
            }}
            td {{
                padding: 5px 6px;
                font-size: 8.5pt;
                vertical-align: top;
            }}
            pre {{
                font-family: Courier, monospace;
                background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                padding: 6px;
                margin-top: 4px;
                margin-bottom: 8px;
                font-size: 7.5pt;
                line-height: 1.3;
            }}
            code {{
                font-family: Courier, monospace;
                background-color: #f1f5f9;
                padding: 1px 3px;
                font-size: 8pt;
            }}
            blockquote {{
                border-left: 3px solid #2563eb;
                padding-left: 10px;
                margin: 6px 0;
                color: #334155;
                font-style: italic;
            }}
        </style>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """

    print("Compiling PDF via xhtml2pdf...")
    with open(pdf_path, "wb") as f_pdf:
        pisa_status = pisa.CreatePDF(html_template, dest=f_pdf)

    if pisa_status.err:
        print("Error: Conversion failed.")
        sys.exit(1)
    print(f"Success: PDF generated at: {pdf_path}")


if __name__ == "__main__":
    convert_md_to_pdf()
