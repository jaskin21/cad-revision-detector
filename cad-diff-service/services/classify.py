import fitz  # pymupdf

def classify_file(path: str) -> str:
    if path.lower().endswith(".dxf"):
        return "dxf"
    if path.lower().endswith(".dwg"):
        return "dwg"
    if path.lower().endswith(".pdf"):
        doc = fitz.open(path)
        page = doc[0]
        has_text = len(page.get_text().strip()) > 0
        has_drawings = len(page.get_drawings()) > 0
        return "vector_pdf" if (has_text or has_drawings) else "raster_pdf"
    return "unknown"