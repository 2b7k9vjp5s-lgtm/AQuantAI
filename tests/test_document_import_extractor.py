from __future__ import annotations

from io import BytesIO

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from industry_alpha.document_import_contracts import DocumentImportError
from industry_alpha.document_import_extractor import extract_pdf


def embedded_text_pdf(page_count: int) -> bytes:
    writer = PdfWriter()
    for number in range(1, page_count + 1):
        page = writer.add_blank_page(width=200, height=200)
        font = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
        page[NameObject("/Resources")] = DictionaryObject(
            {
                NameObject("/Font"): DictionaryObject(
                    {NameObject("/F1"): writer._add_object(font)}
                )
            }
        )
        stream = DecodedStreamObject()
        stream.set_data(
            f"BT /F1 12 Tf 20 100 Td (Page {number} exact text) Tj ET".encode()
        )
        page[NameObject("/Contents")] = writer._add_object(stream)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


@pytest.mark.parametrize("page_count", [1, 30, 300])
def test_spawned_extractor_preserves_page_order_and_contract(page_count):
    result = extract_pdf(embedded_text_pdf(page_count))
    assert len(result.pages) == page_count
    assert result.extractor_version == "6.14.2"
    assert result.pages[0].text.strip() == "Page 1 exact text"
    assert result.pages[-1].page_number == page_count


def test_extractor_rejects_signature_and_image_only_pdf():
    with pytest.raises(DocumentImportError, match="invalid_pdf_signature"):
        extract_pdf(b"not-a-pdf")
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buffer = BytesIO()
    writer.write(buffer)
    with pytest.raises(DocumentImportError, match="embedded_text_unavailable"):
        extract_pdf(buffer.getvalue())
