"""PDF table serialization tests."""

from app.extractors.service import _append_pdf_tables, _serialize_pdf_tables


def test_serialize_pdf_tables_formats_rows():
    tables = [[["Account", "Balance"], ["Checking", "1,200 AED"]]]
    text = _serialize_pdf_tables(tables)
    assert "PDF tables" in text
    assert "Account | Balance" in text
    assert "Checking | 1,200 AED" in text


def test_append_pdf_tables_appends_to_existing_text():
    raw = "Statement header"
    tables = [[["Month", "Income"], ["Jan", "1800"]]]
    combined = _append_pdf_tables(raw, tables)
    assert combined.startswith("Statement header")
    assert "Month | Income" in combined


def test_append_pdf_tables_returns_raw_when_no_tables():
    assert _append_pdf_tables("only text", []) == "only text"
