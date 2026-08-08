"""Pillow-based 4x6 label rendering."""

import textwrap
from pathlib import Path
from typing import TypeAlias

from PIL import Image, ImageDraw, ImageFont

from event_intake.config import LABEL_SIZE_PX
from event_intake.models import Order

LabelFont: TypeAlias = ImageFont.ImageFont | ImageFont.FreeTypeFont


def _font(size: int, bold: bool = False) -> LabelFont:
    names = (
        "Arial Bold.ttf" if bold else "Arial.ttf",
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
    )
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


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
