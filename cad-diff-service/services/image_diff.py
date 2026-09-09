import cv2
import numpy as np
from pdf2image import convert_from_path
from skimage.metrics import structural_similarity as ssim
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
import base64

# Detection runs on a downscaled copy of the page; crops are still cut from the
# full-resolution render. Real revisions (new walls, moved text/symbols) are
# far larger than what's lost at this working size, so accuracy is unaffected
# but SSIM + contour finding run on ~15-20x fewer pixels.
DETECTION_MAX_DIM = 1200


def _pdf_to_image(path: str, dpi: int = 150) -> np.ndarray:
    """Rasterize page 1 of a PDF to a grayscale numpy image."""
    pages = convert_from_path(path, dpi=dpi, first_page=1, last_page=1)
    pil_image = pages[0]
    image = np.array(pil_image.convert("RGB"))
    return cv2.cvtColor(image, cv2.COLOR_RGB2BGR)


def _pdf_pair_to_images(path_a: str, path_b: str, dpi: int = 150) -> tuple:
    """Rasterize both pages concurrently — poppler subprocess calls are I/O
    bound, so running them in parallel roughly halves this step's wall time."""
    with ThreadPoolExecutor(max_workers=2) as pool:
        future_a = pool.submit(_pdf_to_image, path_a, dpi)
        future_b = pool.submit(_pdf_to_image, path_b, dpi)
        return future_a.result(), future_b.result()


def _align_images(img_a: np.ndarray, img_b: np.ndarray) -> tuple:
    """Resize B to match A's dimensions (simple alignment for same-page-size scans)."""
    h, w = img_a.shape[:2]
    img_b_resized = cv2.resize(img_b, (w, h))
    return img_a, img_b_resized


def _downscale_for_detection(img: np.ndarray, max_dim: int = DETECTION_MAX_DIM) -> tuple:
    """Shrink to a bounded working size for detection. Returns the resized
    image and the scale factor needed to map coordinates back to full res."""
    h, w = img.shape[:2]
    scale = min(1.0, max_dim / max(h, w))
    if scale >= 1.0:
        return img, 1.0
    small = cv2.resize(img, (max(int(w * scale), 1), max(int(h * scale), 1)),
                        interpolation=cv2.INTER_AREA)
    return small, scale


def _find_change_regions(gray_a: np.ndarray, gray_b: np.ndarray, min_area: int = 40):
    """Compute SSIM diff map and extract bounding boxes of differing regions.
    Expects (and returns boxes in) the downscaled working resolution."""
    score, diff = ssim(gray_a, gray_b, full=True)
    diff = (diff * 255).astype("uint8")

    thresh = cv2.threshold(diff, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]

    kernel = np.ones((9, 9), np.uint8)
    dilated = cv2.dilate(thresh, kernel, iterations=2)

    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    boxes = []
    for c in contours:
        area = cv2.contourArea(c)
        if area < min_area:
            continue
        x, y, w, h = cv2.boundingRect(c)
        boxes.append((x, y, w, h))

    return boxes, score


def _encode_crop(crop: np.ndarray) -> str:
    """Encode an OpenCV image region as a base64 PNG data URL."""
    _, buf = cv2.imencode(".png", crop)
    encoded = base64.b64encode(buf).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def _describe_location(x, y, page_width, page_height):
    col = "left" if x < page_width / 3 else "right" if x > 2 * page_width / 3 else "center"
    row = "top" if y < page_height / 3 else "bottom" if y > 2 * page_height / 3 else "middle"
    if row == "middle" and col == "center":
        return "center of the drawing"
    return f"{row}-{col} area"


def diff_images(path_a: str, path_b: str, min_area: int = 200, crop_pad: int = 6):
    """Returns (result_dict, base_image_b) — base_image_b is a PIL Image of
    the full revision-B render, used by services/redline.py to build the
    markup PDF."""
    img_a, img_b = _pdf_pair_to_images(path_a, path_b)

    img_a, img_b = _align_images(img_a, img_b)

    gray_a = cv2.cvtColor(img_a, cv2.COLOR_BGR2GRAY)
    gray_b = cv2.cvtColor(img_b, cv2.COLOR_BGR2GRAY)

    page_h, page_w = gray_a.shape[:2]

    # Detect on a downscaled copy (fast), then map boxes back to full res.
    gray_a_small, scale = _downscale_for_detection(gray_a)
    gray_b_small, _ = _downscale_for_detection(gray_b)  # same input size as A -> same scale

    boxes_small, similarity_score = _find_change_regions(
        gray_a_small, gray_b_small, min_area=max(int(min_area * scale * scale), 4)
    )

    # Scale boxes up to full resolution, with a small pad to absorb rounding
    # error introduced by the downscale/upscale round trip.
    boxes = []
    for (x, y, w, h) in boxes_small:
        fx0 = max(int(x / scale) - crop_pad, 0)
        fy0 = max(int(y / scale) - crop_pad, 0)
        fx1 = min(int((x + w) / scale) + crop_pad, page_w)
        fy1 = min(int((y + h) / scale) + crop_pad, page_h)
        boxes.append((fx0, fy0, fx1 - fx0, fy1 - fy0))

    changes = []
    for (x, y, w, h) in boxes:
        crop_before = img_a[y:y+h, x:x+w]
        crop_after = img_b[y:y+h, x:x+w]

        before_data_url = _encode_crop(crop_before)
        after_data_url = _encode_crop(crop_after)

        center_x, center_y = x + w / 2, y + h / 2
        location_label = _describe_location(center_x, center_y, page_w, page_h)

        changes.append({
            "type": "modified",
            "entity": "region",
            "layer": None,
            "location": {"x": center_x, "y": center_y},
            "location_label": location_label,
            "description": f"A region was modified in the {location_label}.",
            "before": {"crop": before_data_url, "bbox": [x, y, x + w, y + h]},
            "after": {"crop": after_data_url, "bbox": [x, y, x + w, y + h]},
            "region_crop": after_data_url,
            # already pixel-space in the full-res revision-B render — no
            # conversion needed for the redline overlay
            "redline_bbox": [x, y, x + w, y + h],
        })

    base_image_b = Image.fromarray(cv2.cvtColor(img_b, cv2.COLOR_BGR2RGB))

    return {
        "revision_a": path_a,
        "revision_b": path_b,
        "confidence": "visual-estimate",
        "changes": changes,
    }, base_image_b