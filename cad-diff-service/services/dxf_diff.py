def diff_dxf(path_a: str, path_b: str, type_a: str, type_b: str):
    return {
        "revision_a": path_a,
        "revision_b": path_b,
        "confidence": "exact",
        "changes": []
    }