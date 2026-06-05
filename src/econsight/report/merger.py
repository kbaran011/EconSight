from __future__ import annotations

import io

from pypdf import PdfReader, PdfWriter


def merge_pdfs(brief_bytes: bytes, full_bytes: bytes) -> bytes:
    writer = PdfWriter()
    for pdf_bytes in (brief_bytes, full_bytes):
        reader = PdfReader(io.BytesIO(pdf_bytes))
        for page in reader.pages:
            writer.add_page(page)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()
