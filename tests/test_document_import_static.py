from pathlib import Path


STATIC = Path(__file__).resolve().parents[1] / "document_import" / "static"


def test_document_import_page_is_chinese_first_and_does_not_embed_pdf():
    html = (STATIC / "document_import.html").read_text(encoding="utf-8")
    lowered = html.lower()
    assert "导入官方 PDF" in html
    assert "不会 OCR" in html
    assert "<iframe" not in lowered
    assert "<object" not in lowered
    assert 'id="review-button"' in html
    assert 'id="pages-more"' in html
    assert 'id="preview-button"' in html
    assert 'id="accept-button"' in html
    assert 'id="claim-status"' in html
    assert 'id="evidence-relation"' in html
    assert "预览零写入" in html
    assert "精确重开回执" in html
    javascript = (STATIC / "document_import.js").read_text(encoding="utf-8")
    assert "textContent" in javascript
    assert "innerHTML" not in javascript
    assert "/api/document-acceptances/" in javascript
    assert "after_page=" in javascript
