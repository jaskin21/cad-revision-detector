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

    # Try to reconcile removed+added pairs that sit at nearly the same position
    for r_key in removed_keys:
        r_data = content_a[r_key]
        best_match = None
        best_dist = None

        for a_key in added_keys - matched_added:
            a_data = content_b[a_key]
            if a_data["kind"] != r_data["kind"]:
                continue
            dist = _bbox_distance(r_data["bbox"], a_data["bbox"])
            if dist < 5 and (best_dist is None or dist < best_dist):  # 5pt tolerance
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

    # Anything added that wasn't matched to a removal is a genuine addition
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

    doc_a.close()
    doc_b.close()

    return {
        "revision_a": path_a,
        "revision_b": path_b,
        "confidence": "exact",
        "changes": changes,
    }


def _bbox_distance(bbox1, bbox2):
    x1, y1 = (bbox1[0] + bbox1[2]) / 2, (bbox1[1] + bbox1[3]) / 2
    x2, y2 = (bbox2[0] + bbox2[2]) / 2, (bbox2[1] + bbox2[3]) / 2
    return ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5