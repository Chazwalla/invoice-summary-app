import streamlit as st

st.title("Invoice Summary Tool")

uploaded_files = st.file_uploader(
    "Upload invoice PDFs",
    type="pdf",
    accept_multiple_files=True
)

if uploaded_files:
    st.write(f"{len(uploaded_files)} file(s) uploaded")

    for file in uploaded_files:
        st.write(f"- {file.name}")
