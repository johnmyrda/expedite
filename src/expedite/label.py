"""Pillow-based 4x6 label rendering."""

import sys
import textwrap
from pathlib import Path
from typing import TypeAlias

from PIL import Image, ImageDraw, ImageFont

from expedite.config import LABEL_SIZE_PX
from expedite.models import Order

LabelFont: TypeAlias = ImageFont.ImageFont | ImageFont.FreeTypeFont


def _font_paths(bold: bool) -> tuple[str, ...]:
    """Return likely cross-platform TrueType font paths/names.

    Pillow's ``ImageFont.truetype`` does not reliably resolve family names on
    Windows. If none of these are found, use Pillow's scalable default font
    with the requested size instead of the tiny bitmap default.
    """

    if sys.platform == "win32":
        windows_fonts = Path.home().anchor + "Windows/Fonts"
        return (
            str(Path(windows_fonts) / ("arialbd.ttf" if bold else "arial.ttf")),
            str(Path(windows_fonts) / ("segoeuib.ttf" if bold else "segoeui.ttf")),
            "arialbd.ttf" if bold else "arial.ttf",
            "segoeuib.ttf" if bold else "segoeui.ttf",
        )

    if sys.platform == "darwin":
        return (
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
            if bold
            else "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/Supplemental/Helvetica.ttc",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
        )

    return (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        "Arial Bold.ttf" if bold else "Arial.ttf",
        "Arial.ttf",
    )


def _font(size: int, bold: bool = False) -> LabelFont:
    for path in _font_paths(bold):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def _draw_wrapped(
    draw: ImageDraw.ImageDraw,
    text: str,
    xy: tuple[int, int],
    font: LabelFont,
    width: int,
    line_gap: int = 8,
) -> int:
    x, y = xy
    for paragraph in (text or "").splitlines() or [""]:
        for line in textwrap.wrap(paragraph, width=width) or [""]:
            draw.text((x, y), line, fill="black", font=font)
            bbox = draw.textbbox((x, y), line or " ", font=font)
            y += bbox[3] - bbox[1] + line_gap
    return int(y)


def label_filename(order: Order) -> str:
    timestamp = order.timestamp.strftime("%Y%m%d_%H%M%S")
    return f"order_{order.order_id}_{timestamp}.png"


def render_label(order: Order) -> Path:
    labels_dir = order.event.path / "labels"
    labels_dir.mkdir(parents=True, exist_ok=True)
    output_path = labels_dir / label_filename(order)

    image = Image.new("RGB", LABEL_SIZE_PX, "white")
    draw = ImageDraw.Draw(image)

    margin = 50
    width, height = LABEL_SIZE_PX
    draw.rectangle((20, 20, width - 20, height - 20), outline="black", width=4)

    title_font = _font(54, bold=True)
    header_font = _font(34, bold=True)
    body_font = _font(34)
    small_font = _font(26)

    y = margin
    draw.text((margin, y), f"Order #{order.order_id}", fill="black", font=title_font)
    y += 78
    draw.line((margin, y, width - margin, y), fill="black", width=3)
    y += 35

    draw.text((margin, y), "Name", fill="black", font=header_font)
    y += 42
    y = _draw_wrapped(draw, order.name, (margin, y), body_font, width=25)
    y += 22

    draw.text((margin, y), "Phone", fill="black", font=header_font)
    y += 42
    y = _draw_wrapped(draw, order.phone, (margin, y), body_font, width=25)
    y += 22

    draw.text((margin, y), "Work Request", fill="black", font=header_font)
    y += 42
    y = _draw_wrapped(draw, order.work_request, (margin, y), body_font, width=28)
    y += 22

    draw.text((margin, y), "Cost", fill="black", font=header_font)
    y += 42
    y = _draw_wrapped(draw, str(order.cost), (margin, y), body_font, width=25)

    footer = order.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    draw.text((margin, height - 90), footer, fill="black", font=small_font)

    image.save(output_path)
    return output_path
