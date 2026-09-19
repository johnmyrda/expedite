"""Pillow-based receipt label rendering for the Rongta RP332."""

import os
import sys
from io import BytesIO
from pathlib import Path
from typing import TypeAlias

from PIL import Image, ImageDraw, ImageFont, ImageOps

from expedite.config import LABEL_WIDTH_PX
from expedite.models import Order
from expedite.money import parse_money_amount
from expedite.storage.settings import receipt_settings

LabelFont: TypeAlias = ImageFont.ImageFont | ImageFont.FreeTypeFont


def _font_paths(bold: bool) -> tuple[str, ...]:
    """Return likely cross-platform TrueType font paths/names.

    Pillow's ``ImageFont.truetype`` does not reliably resolve family names on
    Windows. If none of these are found, use Pillow's scalable default font
    with the requested size instead of the tiny bitmap default.
    """

    if sys.platform == "win32":
        windows_fonts = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
        return (
            str(windows_fonts / ("arialbd.ttf" if bold else "arial.ttf")),
            str(windows_fonts / ("segoeuib.ttf" if bold else "segoeui.ttf")),
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


def _line_height(draw: ImageDraw.ImageDraw, font: LabelFont) -> int:
    bbox = draw.textbbox((0, 0), "Ag", font=font)
    return int(bbox[3] - bbox[1])


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: LabelFont, max_width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in (text or "").splitlines() or [""]:
        words = paragraph.split()
        if not words:
            lines.append("")
            continue

        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            if draw.textlength(candidate, font=font) <= max_width:
                current = candidate
            else:
                lines.extend(_break_long_line(draw, current, font, max_width))
                current = word
        lines.extend(_break_long_line(draw, current, font, max_width))
    return lines


def _break_long_line(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: LabelFont,
    max_width: int,
) -> list[str]:
    if draw.textlength(text, font=font) <= max_width:
        return [text]

    wrapped: list[str] = []
    current = ""
    for character in text:
        candidate = f"{current}{character}"
        if not current or draw.textlength(candidate, font=font) <= max_width:
            current = candidate
        else:
            wrapped.append(current)
            current = character
    if current:
        wrapped.append(current)
    return wrapped


def _draw_wrapped(
    draw: ImageDraw.ImageDraw,
    text: str,
    xy: tuple[int, int],
    font: LabelFont,
    max_width: int,
    line_gap: int = 6,
) -> int:
    x, y = xy
    line_height = _line_height(draw, font)
    for line in _wrap_text(draw, text, font, max_width):
        draw.text((x, y), line, fill="black", font=font)
        y += line_height + line_gap
    return int(y)


def _draw_centered(
    draw: ImageDraw.ImageDraw,
    text: str,
    y: int,
    font: LabelFont,
) -> int:
    text_width = draw.textlength(text, font=font)
    draw.text(((LABEL_WIDTH_PX - text_width) / 2, y), text, fill="black", font=font)
    return y + _line_height(draw, font)


def _receipt_logo(data: bytes | None, max_width: int, max_height: int = 180) -> Image.Image | None:
    if data is None:
        return None
    try:
        with Image.open(BytesIO(data)) as source:
            logo = source.convert("RGBA")
    except OSError:
        return None
    content_bounds = logo.getchannel("A").getbbox()
    if content_bounds is None:
        return None
    logo = logo.crop(content_bounds)
    logo.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
    flattened = Image.new("RGB", logo.size, "white")
    flattened.paste(logo, mask=logo.getchannel("A"))
    # Thermal printers render only black and white. Normalize arbitrary brand
    # colors so light logos do not disappear when converted to ESC/POS raster.
    return ImageOps.autocontrast(ImageOps.grayscale(flattened)).convert("RGB")


def label_filename(order: Order) -> str:
    timestamp = order.timestamp.strftime("%Y%m%d_%H%M%S")
    return f"order_{order.order_id}_{timestamp}.png"


def _receipt_cost(value: object) -> str:
    try:
        return "" if parse_money_amount(value).is_zero() else str(value)
    except ValueError:
        return str(value)


def render_label(order: Order) -> Path:
    labels_dir = order.event.path / "labels"
    labels_dir.mkdir(parents=True, exist_ok=True)
    output_path = labels_dir / label_filename(order)

    # Start with generous height, then crop to the actual receipt length. The
    # RP332 is a receipt printer, so labels should be variable-height instead
    # of fixed 4x6 shipping-label pages.
    settings = receipt_settings()
    notes_height_px = settings.notes_height_px
    image = Image.new("RGB", (LABEL_WIDTH_PX, 3200 + notes_height_px), "white")
    draw = ImageDraw.Draw(image)

    margin = 28
    content_width = LABEL_WIDTH_PX - (margin * 2)

    title_font = _font(42, bold=True)
    order_font = _font(38, bold=True)
    header_font = _font(26, bold=True)
    body_font = _font(30)
    small_font = _font(22)

    y = margin
    logo = _receipt_logo(settings.logo_png, content_width)
    if logo is not None:
        image.paste(logo, ((LABEL_WIDTH_PX - logo.width) // 2, y))
        y += logo.height + 12
    for line in _wrap_text(draw, settings.name, title_font, content_width):
        y = _draw_centered(draw, line, y, title_font) + 6
    y += 6
    y = _draw_centered(draw, f"Order #{order.order_id}", y, order_font) + 18
    draw.line((margin, y, LABEL_WIDTH_PX - margin, y), fill="black", width=3)
    y += 20

    for label, value in (
        ("Name", order.name),
        ("Phone", order.phone),
        ("Work Request", order.work_request),
        ("Cost", _receipt_cost(order.cost)),
    ):
        draw.text((margin, y), label.upper(), fill="black", font=header_font)
        y += _line_height(draw, header_font) + 8
        y = _draw_wrapped(draw, value, (margin, y), body_font, content_width)
        y += 18

    checkbox_size = 30
    draw.rectangle(
        (margin, y, margin + checkbox_size, y + checkbox_size),
        outline="black",
        width=3,
    )
    draw.text((margin + checkbox_size + 12, y), "PAID", fill="black", font=body_font)
    y += max(checkbox_size, _line_height(draw, body_font)) + 24

    draw.line((margin, y, LABEL_WIDTH_PX - margin, y), fill="black", width=2)
    y += 14
    draw.text((margin, y), "NOTES:", fill="black", font=header_font)
    y += _line_height(draw, header_font) + 8 + notes_height_px

    draw.line((margin, y, LABEL_WIDTH_PX - margin, y), fill="black", width=2)
    y += 14
    footer = order.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    y = _draw_centered(draw, footer, y, small_font)
    y += margin

    image.crop((0, 0, LABEL_WIDTH_PX, y)).save(output_path)
    return output_path
