import cv2
import numpy as np
from pdf2image import convert_from_path
from skimage.metrics import structural_similarity as ssim
import os
import uuid


CROP_DIR = "temp_uploads/crops"
os.makedirs(CROP_DIR, exist_ok=True)


def _pdf_to_image(path: str, dpi: int = 150) -> np.ndarray:
    """Rasterize page 1 of a PDF to a grayscale numpy image."""
    pages = convert_from_path(path, dpi=dpi, first_page=1, last_page=1)
    pil_image = pages[0]
    image = np.array(pil_image.convert("RGB"))
    return cv2.cvtColor(image, cv2.COLOR_RGB2BGR)


def _align_images(img_a: np.ndarray, img_b: np.ndarray) -> tuple:
    """Resize B to match A's dimensions (simple alignment for same-page-size scans)."""
    h, w = img_a.shape[:2]
    img_b_resized = cv2.resize(img_b, (w, h))
    return img_a, img_b_resized


def _find_change_regions(gray_a: np.ndarray, gray_b: np.ndarray, min_area: int = 200):
    """Compute SSIM diff map and extract bounding boxes of differing regions."""
    score, diff = ssim(gray_a, gray_b, full=True)
    diff = (diff * 255).astype("uint8")

    # Threshold: areas with low similarity become white (255), rest black
    thresh = cv2.threshold(diff, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]

    # Dilate to merge nearby differing pixels into solid blobs
    kernel = np.ones((9, 9), np.uint8)
    dilated = cv2.dilate(thresh, kernel, iterations=2)

    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    boxes = []
    for c in contours:
        area = cv2.contourArea(c)
        if area < min_area:
            continue  # skip tiny noise
        x, y, w, h = cv2.boundingRect(c)
        boxes.append((x, y, w, h))

    return boxes, score


def diff_images(path_a: str, path_b: str):
    img_a = _pdf_to_image(path_a)
    img_b = _pdf_to_image(path_b)

    img_a, img_b = _align_images(img_a, img_b)

    gray_a = cv2.cvtColor(img_a, cv2.COLOR_BGR2GRAY)
    gray_b = cv2.cvtColor(img_b, cv2.COLOR_BGR2GRAY)

    boxes, similarity_score = _find_change_regions(gray_a, gray_b)

    changes = []
    for (x, y, w, h) in boxes:
        crop_before = img_a[y:y+h, x:x+w]
        crop_after = img_b[y:y+h, x:x+w]

        crop_id = uuid.uuid4().hex[:8]
        before_path = os.path.join(CROP_DIR, f"{crop_id}_before.png")
        after_path = os.path.join(CROP_DIR, f"{crop_id}_after.png")
        cv2.imwrite(before_path, crop_before)
        cv2.imwrite(after_path, crop_after)

        changes.append({
            "type": "modified",  # can't distinguish added/removed/modified from pixels alone
            "entity": "region",
            "layer": None,
            "location": {"x": x + w / 2, "y": y + h / 2},
            "before": {"crop": before_path, "bbox": [x, y, x + w, y + h]},
            "after": {"crop": after_path, "bbox": [x, y, x + w, y + h]},
            "region_crop": after_path,
        })

    return {
        "revision_a": path_a,
        "revision_b": path_b,
        "confidence": "visual-estimate",
        "changes": changes,
    }