import os
from docx import Document
from pypdf import PdfReader


def extract_from_file(path: str, mime: str | None = None) -> str:
    _, ext = os.path.splitext(path.lower())
    if ext.endswith(".pdf"):
        reader = PdfReader(path)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        return text
    if ext.endswith(".docx"):
        doc = Document(path)
        return "\n".join(p.text for p in doc.paragraphs)
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()
