import re
import streamlit as st
import pdfplumber
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import io


def find_value(pattern, text):
    match = re.search(pattern, text, re.MULTILINE)
    return match.group(1).strip() if match else "Not found"


st.title("Invoice Summary Tool")

uploaded_files = st.file_uploader(
    "Upload invoice PDFs",
    type="pdf",
    accept_multiple_files=True
)

if uploaded_files:
    for file in uploaded_files:
        st.subheader(file.name)

        # Extract text from PDF
        with pdfplumber.open(file) as pdf:
            full_text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    full_text += page_text + "\n"

        # Extract fields
        invoice_number = find_value(r"INVOICE\s+#\s*([A-Za-z0-9\-]+)", full_text)
        invoice_date = find_value(r"DATE\s+(\d{2}/\d{2}/\d{4})", full_text)
        due_date = find_value(r"DUE DATE\s+(\d{2}/\d{2}/\d{4})", full_text)
        subtotal = find_value(r"SUBTOTAL\s+([\$]?[0-9,]+\.\d{2})", full_text)
        tax = find_value(r"TAX\s+([\$]?[0-9,]+\.\d{2})", full_text)
        total = find_value(r"TOTAL\s+([\$]?[0-9,]+\.\d{2})", full_text)
        balance_due = find_value(r"BALANCE DUE\s+\$?([0-9,]+\.\d{2})", full_text)

        # Display extracted data
        st.write("**Invoice #**", invoice_number)
        st.write("**Invoice Date**", invoice_date)
        st.write("**Due Date**", due_date)
        st.write("**Subtotal**", subtotal)
        st.write("**Tax**", tax)
        st.write("**Total**", total)
        st.write("**Balance Due**", balance_due)

        # Create summary PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer)
        styles = getSampleStyleSheet()

        content = []

        # Header
        content.append(Paragraph("Taurus Biogas LLC", styles["Title"]))
        content.append(Paragraph("INVOICE SUMMARY", styles["Heading2"]))
        content.append(Spacer(1, 12))

        # Invoice info
        content.append(Paragraph(f"Invoice #: {invoice_number}", styles["Normal"]))
        content.append(Paragraph(f"Invoice Date: {invoice_date}", styles["Normal"]))
        content.append(Paragraph(f"Due Date: {due_date}", styles["Normal"]))
        content.append(Spacer(1, 12))

        # Totals section
        content.append(Paragraph("<b>Operating Expenses</b>", styles["Heading3"]))
        content.append(Spacer(1, 8))

        content.append(Paragraph(f"Subtotal: {subtotal}", styles["Normal"]))
        content.append(Paragraph(f"Tax: {tax}", styles["Normal"]))
        content.append(Paragraph(f"Total: {total}", styles["Normal"]))
        content.append(Paragraph(f"Balance Due: {balance_due}", styles["Normal"]))

        doc.build(content)
        buffer.seek(0)

        # Download button
        st.download_button(
            label="Download Summary PDF",
            data=buffer,
            file_name=f"summary_{file.name}",
            mime="application/pdf"
        )
