import re
import io
import zipfile
import streamlit as st
import pdfplumber
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet


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

    cleaned = re.sub(r"\b(LLC|L\.L\.C\.|INC|CORP|CORPORATION|LTD)\b", "", first_line, flags=re.IGNORECASE)
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


def build_summary_pdf(invoice_number, invoice_date, due_date, bill_to, subtotal, tax, total, balance_due):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()

    content = []

    content.append(Paragraph("Taurus Biogas LLC", styles["Title"]))
    content.append(Paragraph("INVOICE SUMMARY", styles["Heading2"]))
    content.append(Spacer(1, 12))

    content.append(Paragraph(f"Invoice #: {invoice_number}", styles["Normal"]))
    content.append(Paragraph(f"Invoice Date: {invoice_date}", styles["Normal"]))
    content.append(Paragraph(f"Due Date: {due_date}", styles["Normal"]))
    content.append(Spacer(1, 12))

    content.append(Paragraph("<b>Bill To:</b>", styles["Heading3"]))
    content.append(Paragraph(bill_to.replace("\n", "<br/>"), styles["Normal"]))
    content.append(Spacer(1, 12))

    content.append(Paragraph(f"Subtotal: {subtotal}", styles["Normal"]))
    content.append(Paragraph(f"Tax: {tax}", styles["Normal"]))
    content.append(Paragraph(f"Total: {total}", styles["Normal"]))
    content.append(Paragraph(f"Balance Due: {balance_due}", styles["Normal"]))

    doc.build(content)
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
        invoice_date = find_value(r"DUE DATE\s+\d{2}/\d{2}/\d{4}.*?\bDATE\s+(\d{2}/\d{2}/\d{4})", full_text)
        if invoice_date == "Not found":
            invoice_date = find_value(r"DATE\s+(\d{2}/\d{2}/\d{4})", full_text)

        due_date = find_value(r"DUE DATE\s+(\d{2}/\d{2}/\d{4})", full_text)
        subtotal = find_value(r"SUBTOTAL\s+([\$]?[0-9,]+\.\d{2})", full_text)
        tax = find_value(r"TAX\s+([\$]?[0-9,]+\.\d{2})", full_text)
        total = find_value(r"TOTAL\s+([\$]?[0-9,]+\.\d{2})", full_text)
        balance_due = find_value(r"BALANCE DUE\s+\$?([0-9,]+\.\d{2})", full_text)
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
