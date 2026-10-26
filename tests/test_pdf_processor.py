from io import BytesIO

import pytest
from pypdf import PdfWriter
from pypdf.errors import PdfReadError

from app.pdf_processor import extract_text_from_pdf


def make_blank_pdf(number_of_pages=1):
    writer = PdfWriter()

    for _ in range(number_of_pages):
        writer.add_blank_page(
            width=595,
            height=842
        )

    buffer = BytesIO()
    writer.write(buffer)

    return buffer.getvalue()


def test_single_page_pdf():
    pdf_bytes = make_blank_pdf(1)

    result = extract_text_from_pdf(pdf_bytes)

    assert result["total_pages"] == 1
    assert len(result["pages"]) == 1
    assert result["pages"][0]["page"] == 1
    assert result["text"] == ""


def test_multiple_page_pdf():
    pdf_bytes = make_blank_pdf(3)

    result = extract_text_from_pdf(pdf_bytes)

    assert result["total_pages"] == 3
    assert len(result["pages"]) == 3

    assert [
        page["page"] for page in result["pages"]
    ] == [1, 2, 3]


def test_invalid_pdf_raises_error():
    invalid_bytes = b"not a real PDF"

    with pytest.raises((PdfReadError, ValueError)):
        extract_text_from_pdf(invalid_bytes)


def test_empty_pdf_raises_error():
    with pytest.raises((PdfReadError, ValueError)):
        extract_text_from_pdf(b"")