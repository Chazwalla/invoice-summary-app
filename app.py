import re
import streamlit as st
import pdfplumber


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

        with pdfplumber.open(file) as pdf:
            full_text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    full_text += page_text + "\n"

        invoice_number = find_value(r"INVOICE\s+#\s*([A-Za-z0-9\-]+)", full_text)
        invoice_date = find_value(r"DATE\s+(\d{2}/\d{2}/\d{4})", full_text)
        due_date = find_value(r"DUE DATE\s+(\d{2}/\d{2}/\d{4})", full_text)
        subtotal = find_value(r"SUBTOTAL\s+([\$]?[0-9,]+\.\d{2})", full_text)
        tax = find_value(r"TAX\s+([\$]?[0-9,]+\.\d{2})", full_text)
        total = find_value(r"TOTAL\s+([\$]?[0-9,]+\.\d{2})", full_text)
        balance_due = find_value(r"BALANCE DUE\s+\$?([0-9,]+\.\d{2})", full_text)

        st.write("**Invoice #**", invoice_number)
        st.write("**Invoice Date**", invoice_date)
        st.write("**Due Date**", due_date)
        st.write("**Subtotal**", subtotal)
        st.write("**Tax**", tax)
        st.write("**Total**", total)
        st.write("**Balance Due**", balance_due)
