import fitz  # pymupdf
import os
import uuid
import io
import base64
from PIL import Image

CROP_DIR = "temp_uploads/crops"
os.makedirs(CROP_DIR, exist_ok=True)


def _extract_page_content(doc) -> dict:
    """Extract text blocks and drawing paths from page 1, keyed by a synthetic id."""
    page = doc[0]
    content = {}

    text_blocks = page.get_text("dict")["blocks"]
    for i, block in enumerate(text_blocks):
        if block.get("type") == 0:
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    key = f"text_{i}_{span['text'][:20]}_{round(span['bbox'][0])}_{round(span['bbox'][1])}"
                    content[key] = {
                        "kind": "text",
                        "text": span["text"],
                        "bbox": span["bbox"],
                        "font": span.get("font"),
                        "size": span.get("size"),
                    }

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


def _bbox_distance(bbox1, bbox2):
    x1, y1 = (bbox1[0] + bbox1[2]) / 2, (bbox1[1] + bbox1[3]) / 2
    x2, y2 = (bbox2[0] + bbox2[2]) / 2, (bbox2[1] + bbox2[3]) / 2
    return ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5


def _bbox_to_location(bbox):
    x0, y0, x1, y1 = bbox
    return {"x": (x0 + x1) / 2, "y": (y0 + y1) / 2}


def _render_page_image(doc, dpi=150):
    page = doc[0]
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    return img, zoom

def _save_pdf_crop(img, bbox, zoom, pad_px=40):
    x0, y0, x1, y1 = bbox
    px0 = max(int(x0 * zoom) - pad_px, 0)
    py0 = max(int(y0 * zoom) - pad_px, 0)
    px1 = min(int(x1 * zoom) + pad_px, img.width)
    py1 = min(int(y1 * zoom) + pad_px, img.height)
    crop = img.crop((px0, py0, px1, py1))

    buffer = io.BytesIO()
    crop.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def diff_pdf_vector(path_a: str, path_b: str):
    doc_a = fitz.open(path_a)
    doc_b = fitz.open(path_b)

    content_a = _extract_page_content(doc_a)
    content_b = _extract_page_content(doc_b)

    keys_a = set(content_a.keys())
    keys_b = set(content_b.keys())

    removed_keys = keys_a - keys_b
    added_keys = keys_b - keys_a

    changes = []
    matched_added = set()

    for r_key in removed_keys:
        r_data = content_a[r_key]
        best_match = None
        best_dist = None

        for a_key in added_keys - matched_added:
            a_data = content_b[a_key]
            if a_data["kind"] != r_data["kind"]:
                continue
            dist = _bbox_distance(r_data["bbox"], a_data["bbox"])
            if dist < 5 and (best_dist is None or dist < best_dist):
                best_match = a_key
                best_dist = dist

        if best_match:
            a_data = content_b[best_match]
            changes.append({
                "type": "modified",
                "entity": r_data["kind"],
                "layer": None,
                "location": _bbox_to_location(a_data["bbox"]),
                "before": r_data,
                "after": a_data,
                "region_crop": None,
            })
            matched_added.add(best_match)
        else:
            changes.append({
                "type": "removed",
                "entity": r_data["kind"],
                "layer": None,
                "location": _bbox_to_location(r_data["bbox"]),
                "before": r_data,
                "after": None,
                "region_crop": None,
            })

    for a_key in added_keys - matched_added:
        a_data = content_b[a_key]
        changes.append({
            "type": "added",
            "entity": a_data["kind"],
            "layer": None,
            "location": _bbox_to_location(a_data["bbox"]),
            "before": None,
            "after": a_data,
            "region_crop": None,
        })

    if changes:
        img_a, zoom_a = _render_page_image(doc_a)
        img_b, zoom_b = _render_page_image(doc_b)
        for change in changes:
            if change["before"] is not None:
                change["before"]["crop"] = _save_pdf_crop(img_a, change["before"]["bbox"], zoom_a)
            if change["after"] is not None:
                change["after"]["crop"] = _save_pdf_crop(img_b, change["after"]["bbox"], zoom_b)

    doc_a.close()
    doc_b.close()

    return {
        "revision_a": path_a,
        "revision_b": path_b,
        "confidence": "exact",
        "changes": changes,
    }