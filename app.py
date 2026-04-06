import re
import io
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
)


CLIENT_NAME_MAP = {
    "Ash Grove Renewable Energy": "Ash Grove",
    "Ash Grove Renewable Energy LLC": "Ash Grove",
    "Drumgoon": "Drumgoon",
    "Marshall Ridge Renewable Energy": "Marshall Ridge",
    "Marshall Ridge Renewable Energy LLC": "Marshall Ridge",
    "VF Renewable": "VF Renewable",
    "VF Renewables": "VF Renewable",
    "Tri-Cross": "Tri-Cross",
    "Tri-Cross Renewables": "Tri-Cross",
    "East Valley Development": "TB-EVC",
}


def find_value(pattern, text):
    match = re.search(pattern, text, re.MULTILINE)
    return match.group(1).strip() if match else "Not found"


def extract_bill_to_block(text):
    normalized = text.replace("\r", " ")

    match = re.search(
        r"BILL TO INVOICE\s+#\s*\d+\s+(.*?)\s+DATE DESCRIPTION AMOUNT",
        normalized,
        re.DOTALL | re.IGNORECASE
    )

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
        month = date_match.group(1)
        year = date_match.group(3)
        return f"{month}-{year}"
    return "unknown-date"


def build_output_filename(bill_to, invoice_date, invoice_number):
    client_name = get_client_short_name(bill_to)
    invoice_month = format_invoice_month(invoice_date)
    return f"{client_name} {invoice_month} Invoice #{invoice_number}.pdf"


def build_summary_pdf(invoice_number, invoice_date, due_date, bill_to, tax, total, balance_due):
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

    company_style = ParagraphStyle(
        "CompanyStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=13,
        spaceAfter=0,
    )

    label_style = ParagraphStyle(
        "LabelStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=12,
        textColor=colors.black,
    )

    value_style = ParagraphStyle(
        "ValueStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=12,
        textColor=colors.black,
    )

    invoice_title_style = ParagraphStyle(
        "InvoiceTitleStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=24,
        alignment=2,
    )

    section_label_style = ParagraphStyle(
        "SectionLabelStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=12,
        spaceAfter=4,
    )

    bill_to_style = ParagraphStyle(
        "BillToStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=13,
    )

    totals_label_style = ParagraphStyle(
        "TotalsLabelStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=12,
        alignment=2,
    )

    totals_value_style = ParagraphStyle(
        "TotalsValueStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=12,
        alignment=2,
    )

    totals_bold_style = ParagraphStyle(
        "TotalsBoldStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=12,
        alignment=2,
    )

    story = []

    company_block = [
        Paragraph("Taurus Biogas LLC", company_style),
        Paragraph("2175 NW Raleigh St. Suite 110", company_style),
        Paragraph("Portland, OR 97210 USA", company_style),
        Paragraph("+15038539392", company_style),
        Paragraph("www.taurusbiogas.com", company_style),
    ]

    invoice_info_table = Table(
        [
            [Paragraph("INVOICE", invoice_title_style)],
            [Spacer(1, 0.08 * inch)],
            [Table(
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
                    ("TOPPADDING", (0, 0), (-1, -1), 1),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ])
            )]
        ],
        colWidths=[2.4 * inch],
        style=TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ])
    )

    header_table = Table(
        [
            [
                company_block,
                invoice_info_table,
            ]
        ],
        colWidths=[3.7 * inch, 2.7 * inch],
        style=TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ])
    )

    story.append(header_table)
    story.append(Spacer(1, 0.28 * inch))

    bill_to_lines = [line.strip() for line in bill_to.split("\n") if line.strip()]
    if not bill_to_lines:
        bill_to_lines = ["Not found"]

    bill_to_paragraphs = [Paragraph(line, bill_to_style) for line in bill_to_lines]

    bill_to_table = Table(
        [[Paragraph("BILL TO", section_label_style)]] +
        [[line] for line in bill_to_paragraphs],
        colWidths=[3.25 * inch],
        style=TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ])
    )

    story.append(bill_to_table)
    story.append(Spacer(1, 0.45 * inch))

    totals_rows = [
        [Paragraph("TAX", totals_label_style), Paragraph(tax, totals_value_style)],
        [Paragraph("TOTAL", totals_label_style), Paragraph(total, totals_value_style)],
        [Paragraph("BALANCE DUE", totals_bold_style), Paragraph(f"${balance_due}", totals_bold_style)],
    ]

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
            ("LINEABOVE", (0, 2), (-1, 2), 0.75, colors.black),
        ])
    )

    story.append(Spacer(1, 2.2 * inch))
    story.append(totals_table)

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


st.title("Invoice Summary Tool")

uploaded_files = st.file_uploader(
    "Upload invoice PDFs",
    type="pdf",
    accept_multiple_files=True
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

        invoice_date = find_value(
            r"DUE DATE\s+\d{2}/\d{2}/\d{4}.*?\bDATE\s+(\d{2}/\d{2}/\d{4})",
            full_text
        )
        if invoice_date == "Not found":
            invoice_date = find_value(r"DATE\s+(\d{2}/\d{2}/\d{4})", full_text)

        due_date = find_value(r"DUE DATE\s+(\d{2}/\d{2}/\d{4})", full_text)
        tax = find_value(r"TAX\s+([\$]?[0-9,]+\.\d{2})", full_text)
        total = find_value(r"TOTAL\s+([\$]?[0-9,]+\.\d{2})", full_text)
        balance_due = find_value(r"BALANCE DUE\s+\$?([0-9,]+\.\d{2})", full_text)
        bill_to = extract_bill_to_block(full_text)

        pdf_bytes = build_summary_pdf(
            invoice_number=invoice_number,
            invoice_date=invoice_date,
            due_date=due_date,
            bill_to=bill_to,
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

        st.write(f"**Ready:** {output_name}")

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
