import ezdxf
from ezdxf.document import Drawing

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

    return {
        "revision_a": path_a,
        "revision_b": path_b,
        "confidence": "exact",
        "changes": changes,
    }


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