"""
Builds a redlined PDF from a diff result: page 1 is revision B with numbered,
color-coded boxes over each detected change; page 2 is a legend/changelog
table. Source-agnostic — works the same whether the diff came from dxf_diff,
pdf_vector, or image_diff, as long as each change carries a `redline_bbox`
(pixel coordinates in the `base_image` passed in here).

Colors match the review UI's TYPE_STYLE (page.tsx) so the PDF and the web
view read the same way.
"""

import io
import base64
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

CHANGE_COLORS = {
    "added": (63, 125, 83),      # #3f7d53
    "removed": (177, 73, 60),    # #b1493c
    "modified": (180, 132, 42),  # #b4842a
}
DEFAULT_COLOR = (90, 90, 90)

BOX_PAD = 6
BADGE_RADIUS = 11
LEGEND_MARGIN = 40
LEGEND_ROW_HEIGHT = 26
LEGEND_FONT_SIZE = 13
MAX_DESC_CHARS = 70


def _load_font(size: int, bold: bool = False):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    try:
        return ImageFont.truetype(name, size)
    except Exception:
        return ImageFont.load_default()


def _change_bbox(change: dict) -> Optional[tuple]:
    """Pixel-space bbox to draw for this change. `redline_bbox` is the
    contract every engine is expected to fill in; the other fallbacks only
    help changes produced before an engine adds that field."""
    bbox = change.get("redline_bbox")
    if bbox:
        return tuple(bbox)
    for side in ("after", "before"):
        data = change.get(side)
        if data and data.get("bbox"):
            return tuple(data["bbox"])
    return None


def _draw_markup(base_image: Image.Image, changes: list) -> Image.Image:
    img = base_image.convert("RGB").copy()
    draw = ImageDraw.Draw(img)
    badge_font = _load_font(12, bold=True)

    for i, change in enumerate(changes, start=1):
        bbox = _change_bbox(change)
        if not bbox:
            continue
        x0, y0, x1, y1 = bbox
        x0, y0, x1, y1 = x0 - BOX_PAD, y0 - BOX_PAD, x1 + BOX_PAD, y1 + BOX_PAD
        color = CHANGE_COLORS.get(change.get("type"), DEFAULT_COLOR)

        draw.rounded_rectangle([x0, y0, x1, y1], radius=4, outline=color, width=3)

        bx, by = x0, y0
        draw.ellipse(
            [bx - BADGE_RADIUS, by - BADGE_RADIUS, bx + BADGE_RADIUS, by + BADGE_RADIUS],
            fill=color,
        )
        label = str(i)
        tb = draw.textbbox((0, 0), label, font=badge_font)
        tw, th = tb[2] - tb[0], tb[3] - tb[1]
        draw.text((bx - tw / 2 - tb[0], by - th / 2 - tb[1]), label, fill="white", font=badge_font)

    return img


def _build_legend_page(changes: list, page_size: tuple) -> Image.Image:
    width, height = page_size
    legend = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(legend)
    title_font = _load_font(18, bold=True)
    header_font = _load_font(LEGEND_FONT_SIZE, bold=True)
    row_font = _load_font(LEGEND_FONT_SIZE)

    draw.text((LEGEND_MARGIN, LEGEND_MARGIN), "Changes summary", fill=(28, 32, 36), font=title_font)

    col_x = {"num": LEGEND_MARGIN, "type": LEGEND_MARGIN + 40, "area": LEGEND_MARGIN + 150, "desc": LEGEND_MARGIN + 320}
    header_y = LEGEND_MARGIN + 40
    for key, label in (("num", "#"), ("type", "Type"), ("area", "Area"), ("desc", "Description")):
        draw.text((col_x[key], header_y), label, fill=(90, 90, 90), font=header_font)
    draw.line([(LEGEND_MARGIN, header_y + 20), (width - LEGEND_MARGIN, header_y + 20)],
               fill=(216, 219, 214), width=1)

    y = header_y + 30
    for i, change in enumerate(changes, start=1):
        if y > height - LEGEND_MARGIN:
            break  # TODO: spill remaining rows onto an additional legend page
        color = CHANGE_COLORS.get(change.get("type"), DEFAULT_COLOR)
        draw.ellipse([col_x["num"], y + 3, col_x["num"] + 10, y + 13], fill=color)
        draw.text((col_x["num"] + 16, y), str(i), fill=(28, 32, 36), font=row_font)
        draw.text((col_x["type"], y), (change.get("type") or "").capitalize(), fill=(28, 32, 36), font=row_font)
        draw.text((col_x["area"], y), change.get("location_label") or "—", fill=(28, 32, 36), font=row_font)

        desc = change.get("description") or f"A {change.get('entity', 'region')} was {change.get('type')}."
        if len(desc) > MAX_DESC_CHARS:
            desc = desc[: MAX_DESC_CHARS - 3] + "..."
        draw.text((col_x["desc"], y), desc, fill=(28, 32, 36), font=row_font)

        y += LEGEND_ROW_HEIGHT

    return legend


def _render_pages(base_image: Image.Image, changes: list) -> list:
    marked = _draw_markup(base_image, changes)
    legend = _build_legend_page(changes, marked.size)
    return [marked, legend]


def build_redline_pdf(base_image: Image.Image, changes: list, out_path: str) -> str:
    """Write the redlined PDF to disk. Returns out_path."""
    pages = _render_pages(base_image, changes)
    pages[0].save(out_path, "PDF", resolution=150.0, save_all=True, append_images=pages[1:])
    return out_path


def build_redline_pdf_base64(base_image: Image.Image, changes: list) -> str:
    """Same as build_redline_pdf but returns a base64 data URL — matches the
    base64 crop convention already used elsewhere in the diff response, so
    the Node worker doesn't need a separate file-fetch step."""
    pages = _render_pages(base_image, changes)
    buf = io.BytesIO()
    pages[0].save(buf, "PDF", resolution=150.0, save_all=True, append_images=pages[1:])
    encoded = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:application/pdf;base64,{encoded}"
