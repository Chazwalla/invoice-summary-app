import streamlit as st
import pdfplumber

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
                full_text += page.extract_text() + "\n"

        # Show extracted text (for testing)
        st.text_area("Extracted Text", full_text, height=200)

        # Try to find key fields
        if "TOTAL" in full_text:
            st.write("Found TOTAL in document")
