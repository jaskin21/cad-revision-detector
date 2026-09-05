import fitz  # pymupdf

def _extract_page_content(doc) -> dict:
    """Extract text blocks and drawing paths from page 1, keyed by a synthetic id."""
    page = doc[0]
    content = {}

    # Text blocks
    text_blocks = page.get_text("dict")["blocks"]
    for i, block in enumerate(text_blocks):
        if block.get("type") == 0:  # text block
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    key = f"text_{i}_{span['text'][:20]}_{round(span['bbox'][0])}_{round(span['bbox'][1])}"
                    content[key] = {
                        "kind": "text",
                        "text": span["text"],
                        "bbox": span["bbox"],  # [x0, y0, x1, y1]
                        "font": span.get("font"),
                        "size": span.get("size"),
                    }

    # Vector paths (lines, curves, shapes)
    drawings = page.get_drawings()
    for i, path in enumerate(drawings):
        rect = path["rect"]
        key = f"path_{i}_{round(rect.x0)}_{round(rect.y0)}"
        content[key] = {
            "kind": "path",
            "bbox": [rect.x0, rect.y0, rect.x1, rect.y1],
            "type": path.get("type"),
        }

    return content


def diff_pdf_vector(path_a: str, path_b: str):
    doc_a = fitz.open(path_a)
    doc_b = fitz.open(path_b)

    content_a = _extract_page_content(doc_a)
    content_b = _extract_page_content(doc_b)

    keys_a = set(content_a.keys())
    keys_b = set(content_b.keys())

    changes = []

    for key in keys_a - keys_b:
        data = content_a[key]
        changes.append({
            "type": "removed",
            "entity": data["kind"],
            "layer": None,
            "location": _bbox_to_location(data["bbox"]),
            "before": data,
            "after": None,
            "region_crop": None,
        })

    for key in keys_b - keys_a:
        data = content_b[key]
        changes.append({
            "type": "added",
            "entity": data["kind"],
            "layer": None,
            "location": _bbox_to_location(data["bbox"]),
            "before": None,
            "after": data,
            "region_crop": None,
        })

    doc_a.close()
    doc_b.close()

    return {
        "revision_a": path_a,
        "revision_b": path_b,
        "confidence": "exact",
        "changes": changes,
    }


def _bbox_to_location(bbox):
    x0, y0, x1, y1 = bbox
    return {"x": (x0 + x1) / 2, "y": (y0 + y1) / 2}