def diff_images(path_a: str, path_b: str):
    return {
        "revision_a": path_a,
        "revision_b": path_b,
        "confidence": "visual-estimate",
        "changes": []
    }