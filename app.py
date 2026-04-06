import re
import io
import streamlit as st
import pdfplumber
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet


def find_value(pattern, text):
    match = re.search(pattern, text, re.MULTILINE)
    return match.group(1).strip() if match else "Not found"


def extract_bill_to_block(text):
    normalized = text.replace("\r", "\n")
    normalized = re.sub(r"[ \t]+", " ", normalized)

    patterns = [
        r"BILL TO\s*(.*?)\s*INVOICE\s*#",
        r"BILL TO\s*(.*?)\s*DATE\s+\d{2}/\d{2}/\d{4}",
        r"BILL TO\s*(.*?)\s*DUE DATE\s+\d{2}/\d{2}/\d{4}",
        r"BILL TO\s*(.*?)\s*TERMS\s+",
    ]

    for pattern in patterns:
        match = re.search(pattern, normalized, re.DOTALL | re.IGNORECASE)
        if match:
            block = match.group(1).strip()
            block = re.sub(r"\s{2,}", "\n", block)
            return block if block else "Not found"

    return "Not found"


st.title("Invoice Summary Tool")

uploaded_files = st.file_uploader(
    "Upload invoice PDFs",
    type="pdf",
    accept_multiple_files=True
)

if uploaded_files:
    for file in uploaded_files:
        st.subheader(file.name)

        with pdfplumber.open(file) as pdf:
            full_text = ""
            first_page_text = ""

            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text:
                    full_text += page_text + "\n"
                    if i == 0:
                        first_page_text = page_text

        invoice_number = find_value(r"INVOICE\s+#\s*([A-Za-z0-9\-]+)", full_text)
        invoice_date = find_value(r"DATE\s+(\d{2}/\d{2}/\d{4})", full_text)
        due_date = find_value(r"DUE DATE\s+(\d{2}/\d{2}/\d{4})", full_text)
        subtotal = find_value(r"SUBTOTAL\s+([\$]?[0-9,]+\.\d{2})", full_text)
        tax = find_value(r"TAX\s+([\$]?[0-9,]+\.\d{2})", full_text)
        total = find_value(r"TOTAL\s+([\$]?[0-9,]+\.\d{2})", full_text)
        balance_due = find_value(r"BALANCE DUE\s+\$?([0-9,]+\.\d{2})", full_text)
        bill_to = extract_bill_to_block(full_text)

        st.write("**Invoice #**", invoice_number)
        st.write("**Invoice Date**", invoice_date)
        st.write("**Due Date**", due_date)
        st.write("**Bill To**")
        st.text(bill_to)
        st.write("**Subtotal**", subtotal)
        st.write("**Tax**", tax)
        st.write("**Total**", total)
        st.write("**Balance Due**", balance_due)

        with st.expander("Debug: First page extracted text"):
            st.text(first_page_text)

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

        content.append(Paragraph("<b>Operating Expenses</b>", styles["Heading3"]))
        content.append(Spacer(1, 8))
        content.append(Paragraph(f"Subtotal: {subtotal}", styles["Normal"]))
        content.append(Paragraph(f"Tax: {tax}", styles["Normal"]))
        content.append(Paragraph(f"Total: {total}", styles["Normal"]))
        content.append(Paragraph(f"Balance Due: {balance_due}", styles["Normal"]))

        doc.build(content)
        buffer.seek(0)

        st.download_button(
            label="Download Summary PDF",
            data=buffer,
            file_name=f"summary_{file.name}",
            mime="application/pdf"
        )
