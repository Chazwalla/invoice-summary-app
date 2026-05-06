import re
import io
import base64
import zipfile
import streamlit as st
import pdfplumber

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
)


st.set_page_config(
    page_title="Invoice Summary Generator",
    page_icon="🌲",
    layout="centered"
)


def load_logo_base64(path="PineLogo.png"):
    try:
        with open(path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode()
    except FileNotFoundError:
        return ""


pine_logo = load_logo_base64()


st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Manrope:wght@700;800&display=swap');

    .stApp {{
        background:
            radial-gradient(circle at 15% 70%, rgba(24, 60, 43, 0.10), transparent 28%),
            radial-gradient(circle at 85% 75%, rgba(24, 60, 43, 0.09), transparent 30%),
            linear-gradient(180deg, #fbfaf6 0%, #f4f6f1 100%);
        font-family: 'Inter', sans-serif;
    }}

    .stApp::before {{
        content: "♮ ♮ ♮";
        position: fixed;
        left: 5%;
        bottom: 7%;
        font-size: 9rem;
        letter-spacing: 2.5rem;
        color: rgba(24, 60, 43, 0.06);
        transform: rotate(-2deg);
        pointer-events: none;
        z-index: 0;
    }}

    .stApp::after {{
        content: "♮ ♮";
        position: fixed;
        right: 4%;
        bottom: 10%;
        font-size: 11rem;
        letter-spacing: 2rem;
        color: rgba(24, 60, 43, 0.055);
        transform: rotate(2deg);
        pointer-events: none;
        z-index: 0;
    }}

    .main .block-container {{
        max-width: 820px;
        padding-top: 3.2rem;
        position: relative;
        z-index: 1;
    }}

    h1 {{
        text-align: center;
        font-family: 'Manrope', sans-serif !important;
        font-size: 2.45rem !important;
        font-weight: 800 !important;
        color: #10251b;
        margin-bottom: 0.35rem !important;
        letter-spacing: -0.03em;
    }}

    .app-logo {{
        display: flex;
        justify-content: center;
        margin-bottom: 1rem;
    }}

    .app-logo img {{
        width: 54px;
        height: auto;
        opacity: 0.96;
    }}

    .app-subtitle {{
        text-align: center;
        color: #5f6b63;
        font-size: 1rem;
        margin-bottom: 2rem;
    }}

    [data-testid="stFileUploader"] {{
        background: rgba(255, 255, 255, 0.92);
        border: 1px solid #e2e5df;
        border-radius: 20px;
        padding: 26px;
        box-shadow: 0 16px 42px rgba(16, 37, 27, 0.10);
        backdrop-filter: blur(6px);
    }}

    [data-testid="stFileUploader"] section {{
        border: 1.5px dashed rgba(24, 60, 43, 0.34);
        border-radius: 16px;
        background: rgba(255, 255, 255, 0.65);
    }}

    .stDownloadButton button {{
        border-radius: 11px;
        border: 1px solid #183c2b;
        color: #183c2b;
        background: rgba(255,255,255,0.92);
        font-weight: 700;
        padding: 0.55rem 1rem;
    }}

    .stDownloadButton button:hover {{
        background: #183c2b;
        color: white;
        border-color: #183c2b;
    }}

    .ready-card {{
        background: rgba(255,255,255,0.94);
        border: 1px solid #e2e5df;
        border-radius: 15px;
        padding: 14px 16px;
        margin: 14px 0 8px 0;
        box-shadow: 0 6px 18px rgba(16, 37, 27, 0.06);
        color: #10251b;
        font-weight: 700;
    }}
</style>
""", unsafe_allow_html=True)


CLIENT_NAME_MAP = {
    "Ash Grove Renewable Energy": "Ash Grove",
    "Ash Grove Renewable Energy LLC": "Ash Grove",
    "Drumgoon": "Drumgoon",
    "Drumgoon Digester Renewable Energy": "Drumgoon",
    "Marshall Ridge Renewable Energy": "Marshall Ridge",
    "Marshall Ridge Renewable Energy LLC": "Marshall Ridge",
    "VF Renewable": "VF Renewable",
    "VF Renewables": "VF Renewable",
    "Tri-Cross": "Tri-Cross",
    "Tri-Cross Renewables": "Tri-Cross",
    "East Valley Development": "TB-EVC",
}


def find_value(pattern, text):
    match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
    return match.group(1).strip() if match else "Not found"


def extract_bill_to_block(text):
    normalized = text.replace("\r", " ")

    patterns = [
        r"BILL TO\s+(.*?)\s+INVOICE\s+#",
        r"BILL TO INVOICE\s+#\s*\d+\s+(.*?)\s+DATE DESCRIPTION AMOUNT",
    ]

    for pattern in patterns:
        match = re.search(pattern, normalized, re.DOTALL | re.IGNORECASE)
        if match:
            block = match.group(1)
            block = re.sub(r"DATE\s+\d{2}/\d{2}/\d{4}", "", block)
            block = re.sub(r"DUE DATE\s+\d{2}/\d{2}/\d{4}", "", block)
            block = re.sub(r"TERMS\s+Net\s+\d+", "", block)
            block = re.sub(r"\s+DUE\b", "", block)

            parts = re.split(r"\s{2,}|\n", block)
            cleaned = "\n".join([p.strip() for p in parts if p.strip()])
            return cleaned if cleaned else "Not found"

    return "Not found"


def get_client_short_name(bill_to):
    first_line = bill_to.split("\n")[0].strip() if bill_to != "Not found" else "Unknown Client"

    for key, short_name in CLIENT_NAME_MAP.items():
        if key.lower() in first_line.lower():
            return short_name

    cleaned = re.sub(
        r"\b(LLC|L\.L\.C\.|INC|CORP|CORPORATION|LTD)\b",
        "",
        first_line,
        flags=re.IGNORECASE
    )
    cleaned = cleaned.replace(",", "").strip()
    return cleaned


def format_invoice_month(invoice_date):
    date_match = re.search(r"(\d{2})/(\d{2})/(\d{4})", invoice_date)
    if date_match:
        return f"{date_match.group(1)}-{date_match.group(3)}"
    return "unknown-date"


def build_output_filename(bill_to, invoice_date, invoice_number):
    client_name = get_client_short_name(bill_to)
    invoice_month = format_invoice_month(invoice_date)
    return f"{client_name} {invoice_month} Invoice #{invoice_number}.pdf"


def money_is_nonzero(value):
    if value == "Not found":
        return False
    cleaned = value.replace("$", "").replace(",", "").strip()
    try:
        return float(cleaned) != 0
    except ValueError:
        return False


def clean_balance_due(value):
    if value == "Not found":
        return value
    return value.replace("$", "").strip()


def build_summary_pdf(invoice_number, invoice_date, due_date, bill_to, subtotal, tax, total, balance_due):
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        rightMargin=0.6 * inch,
        leftMargin=0.6 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
    )

    styles = getSampleStyleSheet()

    company_style = ParagraphStyle("CompanyStyle", parent=styles["Normal"], fontName="Helvetica", fontSize=10, leading=13)
    label_style = ParagraphStyle("LabelStyle", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=10, leading=12)
    value_style = ParagraphStyle("ValueStyle", parent=styles["Normal"], fontName="Helvetica", fontSize=10, leading=12)
    invoice_title_style = ParagraphStyle("InvoiceTitleStyle", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=22, leading=24, alignment=2)
    section_label_style = ParagraphStyle("SectionLabelStyle", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=10, leading=12)
    bill_to_style = ParagraphStyle("BillToStyle", parent=styles["Normal"], fontName="Helvetica", fontSize=10, leading=13)
    totals_label_style = ParagraphStyle("TotalsLabelStyle", parent=styles["Normal"], fontName="Helvetica", fontSize=10, leading=12, alignment=2)
    totals_value_style = ParagraphStyle("TotalsValueStyle", parent=styles["Normal"], fontName="Helvetica", fontSize=10, leading=12, alignment=2)
    totals_bold_style = ParagraphStyle("TotalsBoldStyle", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=10, leading=12, alignment=2)

    story = []

    logo = Image("TaurusLogo.png", width=1.5 * inch, height=0.6 * inch)

    company_block = [
        logo,
        Spacer(1, 6),
        Paragraph("Taurus Biogas LLC", company_style),
        Paragraph("2175 NW Raleigh St. Suite 110", company_style),
        Paragraph("Portland, OR 97210 USA", company_style),
        Paragraph("+15038539392", company_style),
        Paragraph("www.taurusbiogas.com", company_style),
    ]

    story.append(Table(
        [[company_block, Paragraph("INVOICE", invoice_title_style)]],
        colWidths=[3.7 * inch, 2.7 * inch],
        style=TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ])
    ))

    story.append(Spacer(1, 0.25 * inch))

    bill_to_lines = [line.strip() for line in bill_to.split("\n") if line.strip()]
    if not bill_to_lines:
        bill_to_lines = ["Not found"]

    bill_to_table = Table(
        [[Paragraph("BILL TO", section_label_style)]] +
        [[Paragraph(line, bill_to_style)] for line in bill_to_lines],
        colWidths=[3.25 * inch],
        style=TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ])
    )

    invoice_info_table = Table(
        [
            [Paragraph("INVOICE #", label_style), Paragraph(str(invoice_number), value_style)],
            [Paragraph("DATE", label_style), Paragraph(invoice_date, value_style)],
            [Paragraph("DUE DATE", label_style), Paragraph(due_date, value_style)],
            [Paragraph("TERMS", label_style), Paragraph("Net 30", value_style)],
        ],
        colWidths=[1.0 * inch, 1.35 * inch],
        style=TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ])
    )

    story.append(Table(
        [[bill_to_table, invoice_info_table]],
        colWidths=[3.7 * inch, 2.7 * inch],
        style=TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ])
    ))

    totals_rows = []

    if money_is_nonzero(tax):
        totals_rows.append([Paragraph("SUBTOTAL", totals_label_style), Paragraph(subtotal, totals_value_style)])

    totals_rows.extend([
        [Paragraph("TAX", totals_label_style), Paragraph(tax, totals_value_style)],
        [Paragraph("TOTAL", totals_label_style), Paragraph(total, totals_value_style)],
        [Paragraph("BALANCE DUE", totals_bold_style), Paragraph(f"${clean_balance_due(balance_due)}", totals_bold_style)],
    ])

    totals_table = Table(
        totals_rows,
        colWidths=[1.8 * inch, 1.5 * inch],
        hAlign="RIGHT",
        style=TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LINEABOVE", (0, len(totals_rows) - 1), (-1, len(totals_rows) - 1), 0.75, colors.black),
        ])
    )

    story.append(Spacer(1, 2.65 * inch))
    story.append(totals_table)

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


if pine_logo:
    st.markdown(
        f"<div class='app-logo'><img src='data:image/png;base64,{pine_logo}' /></div>",
        unsafe_allow_html=True
    )

st.title("Invoice Summary Generator")
st.markdown(
    "<div class='app-subtitle'>Upload invoice PDFs to generate one-page summary invoices.</div>",
    unsafe_allow_html=True
)

uploaded_files = st.file_uploader(
    "Upload invoice PDFs",
    type="pdf",
    accept_multiple_files=True,
    label_visibility="collapsed"
)

if uploaded_files:
    summary_files = []

    for file in uploaded_files:
        with pdfplumber.open(file) as pdf:
            full_text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    full_text += page_text + "\n"

        invoice_number = find_value(r"INVOICE\s+#\s*([A-Za-z0-9\-]+)", full_text)
        invoice_date = find_value(r"\bDATE\s+(\d{2}/\d{2}/\d{4})", full_text)
        due_date = find_value(r"\bDUE DATE\s+(\d{2}/\d{2}/\d{4})", full_text)
        subtotal = find_value(r"SUBTOTAL\s+([\$]?[0-9,]+\.\d{2})", full_text)
        tax = find_value(r"^TAX\s+([\$]?[0-9,]+\.\d{2})", full_text)
        total = find_value(r"^TOTAL\s+([\$]?[0-9,]+\.\d{2})", full_text)
        balance_due = find_value(r"^BALANCE DUE\s+\$?([0-9,]+\.\d{2})", full_text)
        bill_to = extract_bill_to_block(full_text)

        pdf_bytes = build_summary_pdf(
            invoice_number=invoice_number,
            invoice_date=invoice_date,
            due_date=due_date,
            bill_to=bill_to,
            subtotal=subtotal,
            tax=tax,
            total=total,
            balance_due=balance_due
        )

        output_name = build_output_filename(
            bill_to=bill_to,
            invoice_date=invoice_date,
            invoice_number=invoice_number
        )

        summary_files.append((output_name, pdf_bytes))

        st.markdown(f"<div class='ready-card'>Ready: {output_name}</div>", unsafe_allow_html=True)

        st.download_button(
            label=f"Download {output_name}",
            data=pdf_bytes,
            file_name=output_name,
            mime="application/pdf"
        )

    if summary_files:
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for output_name, pdf_bytes in summary_files:
                zip_file.writestr(output_name, pdf_bytes)

        zip_buffer.seek(0)

        st.download_button(
            label="Download All Summaries (ZIP)",
            data=zip_buffer.getvalue(),
            file_name="invoice_summaries.zip",
            mime="application/zip"
        )
