from io import BytesIO
from pypdf import PdfReader


def extract_text_from_pdf(pdf_bytes: bytes) -> dict:
    reader = PdfReader(BytesIO(pdf_bytes))

    pages = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""

        pages.append({
            "page": page_number,
            "text": text.strip()
        })

    full_text = "\n\n".join(
        page["text"] for page in pages if page["text"]
    )

    return {
        "total_pages": len(reader.pages),
        "text": full_text,
        "pages": pages
    }