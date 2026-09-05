import ezdxf
from ezdxf.document import Drawing
import os
import base64
import uuid
from PIL import Image
from ezdxf.bbox import extents
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

CROP_DIR = "temp_uploads/crops"
os.makedirs(CROP_DIR, exist_ok=True)
IMG_LONG_SIDE = 1600


def _extract_entities(doc: Drawing) -> dict:
    """Extract all modelspace entities, keyed by handle."""
    entities = {}
    msp = doc.modelspace()

    for entity in msp:
        handle = entity.dxf.handle
        entity_data = {
            "type": entity.dxftype(),
            "layer": entity.dxf.layer,
        }

        # Extract geometry depending on entity type
        if entity.dxftype() == "LINE":
            entity_data["start"] = tuple(entity.dxf.start)[:2]
            entity_data["end"] = tuple(entity.dxf.end)[:2]

        elif entity.dxftype() in ("LWPOLYLINE", "POLYLINE"):
            try:
                points = list(entity.get_points(format="xy"))
                entity_data["points"] = points
            except Exception:
                entity_data["points"] = []

        elif entity.dxftype() == "CIRCLE":
            entity_data["center"] = tuple(entity.dxf.center)[:2]
            entity_data["radius"] = entity.dxf.radius

        elif entity.dxftype() in ("TEXT", "MTEXT"):
            entity_data["text"] = entity.dxf.text if entity.dxftype() == "TEXT" else entity.text
            entity_data["insert"] = tuple(entity.dxf.insert)[:2]

        elif entity.dxftype() == "INSERT":  # block reference (e.g. a door/window symbol)
            entity_data["block_name"] = entity.dxf.name
            entity_data["insert"] = tuple(entity.dxf.insert)[:2]

        else:
            # Fallback: just record type + layer, no detailed geometry
            pass

        entities[handle] = entity_data

    return entities


def _entity_to_friendly_type(entity_data: dict) -> str:
    """Map raw DXF entity type to a more human-readable label."""
    type_map = {
        "LINE": "line",
        "LWPOLYLINE": "polyline",
        "POLYLINE": "polyline",
        "CIRCLE": "circle",
        "TEXT": "text",
        "MTEXT": "text",
        "INSERT": "block",
    }
    return type_map.get(entity_data["type"], entity_data["type"].lower())


def _get_location(entity_data: dict):
    """Best-effort single representative x/y point for a change, used for UI click-to-zoom."""
    if "start" in entity_data:
        x, y = entity_data["start"]
        return {"x": x, "y": y}
    if "center" in entity_data:
        x, y = entity_data["center"]
        return {"x": x, "y": y}
    if "insert" in entity_data:
        x, y = entity_data["insert"]
        return {"x": x, "y": y}
    if "points" in entity_data and entity_data["points"]:
        x, y = entity_data["points"][0]
        return {"x": x, "y": y}
    return None


def _get_extents(doc):
    bbox = extents(doc.modelspace())
    if not bbox.has_data:
        return (0.0, 0.0, 100.0, 100.0)
    return (bbox.extmin.x, bbox.extmin.y, bbox.extmax.x, bbox.extmax.y)


def _render_dxf_image(doc, out_path):
    xmin, ymin, xmax, ymax = _get_extents(doc)
    width = max(xmax - xmin, 1e-6)
    height = max(ymax - ymin, 1e-6)

    if width >= height:
        fig_w, fig_h = IMG_LONG_SIDE, max(int(IMG_LONG_SIDE * height / width), 1)
    else:
        fig_h, fig_w = IMG_LONG_SIDE, max(int(IMG_LONG_SIDE * width / height), 1)

    dpi = 100
    fig = plt.figure(figsize=(fig_w / dpi, fig_h / dpi), dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_aspect("equal")
    ax.axis("off")

    ctx = RenderContext(doc)
    backend = MatplotlibBackend(ax)
    Frontend(ctx, backend).draw_layout(doc.modelspace(), finalize=True)

    fig.savefig(out_path, dpi=dpi)
    plt.close(fig)

    return (xmin, ymin, xmax, ymax), (fig_w, fig_h)


def _world_to_pixel(x, y, extents_box, img_size):
    xmin, ymin, xmax, ymax = extents_box
    img_w, img_h = img_size
    px = (x - xmin) / (xmax - xmin) * img_w
    py = img_h - (y - ymin) / (ymax - ymin) * img_h
    return px, py


def _save_crop(image_path, center_x, center_y, extents_box, img_size, pad_px=80):
    img = Image.open(image_path)
    px, py = _world_to_pixel(center_x, center_y, extents_box, img_size)
    x0 = max(int(px - pad_px), 0)
    y0 = max(int(py - pad_px), 0)
    x1 = min(int(px + pad_px), img.width)
    y1 = min(int(py + pad_px), img.height)
    crop = img.crop((x0, y0, x1, y1))

    buffer = io.BytesIO()
    crop.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def diff_dxf(path_a: str, path_b: str, type_a: str, type_b: str):
    doc_a = ezdxf.readfile(path_a)
    doc_b = ezdxf.readfile(path_b)

    entities_a = _extract_entities(doc_a)
    entities_b = _extract_entities(doc_b)

    handles_a = set(entities_a.keys())
    handles_b = set(entities_b.keys())

    changes = []

    # Removed: present in A, missing in B
    for handle in handles_a - handles_b:
        data = entities_a[handle]
        changes.append({
            "type": "removed",
            "entity": _entity_to_friendly_type(data),
            "layer": data.get("layer"),
            "location": _get_location(data),
            "before": data,
            "after": None,
            "region_crop": None,
        })

    # Added: present in B, missing in A
    for handle in handles_b - handles_a:
        data = entities_b[handle]
        changes.append({
            "type": "added",
            "entity": _entity_to_friendly_type(data),
            "layer": data.get("layer"),
            "location": _get_location(data),
            "before": None,
            "after": data,
            "region_crop": None,
        })

    # Modified: present in both, but different
    for handle in handles_a & handles_b:
        data_a = entities_a[handle]
        data_b = entities_b[handle]
        if data_a != data_b:
            changes.append({
                "type": "modified",
                "entity": _entity_to_friendly_type(data_b),
                "layer": data_b.get("layer"),
                "location": _get_location(data_b),
                "before": data_a,
                "after": data_b,
                "region_crop": None,
            })

    if changes:
        img_a_path = os.path.join(CROP_DIR, f"full_a_{uuid.uuid4().hex[:8]}.png")
        img_b_path = os.path.join(CROP_DIR, f"full_b_{uuid.uuid4().hex[:8]}.png")
        extents_a, size_a = _render_dxf_image(doc_a, img_a_path)
        extents_b, size_b = _render_dxf_image(doc_b, img_b_path)

        for change in changes:
            loc = change.get("location")
            if not loc:
                continue
            if change["before"] is not None:
                change["before"]["crop"] = _save_crop(img_a_path, loc["x"], loc["y"], extents_a, size_a)
            if change["after"] is not None:
                change["after"]["crop"] = _save_crop(img_b_path, loc["x"], loc["y"], extents_b, size_b)

    return {
        "revision_a": path_a,
        "revision_b": path_b,
        "confidence": "exact",
        "changes": changes,
    }