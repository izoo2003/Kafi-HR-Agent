"""Compose an original, visually rich Kafi hiring poster (PIL + Cloudflare art).

No chairs / office furniture — abstract commodities / growth / network visuals only.
"""
from __future__ import annotations

import io
import logging
import math
import re
from typing import Sequence

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from app.core.cloudflare_images import generate_image_bytes
from app.core.config import Settings

logger = logging.getLogger(__name__)

_NAVY = (22, 42, 74)
_NAVY_DEEP = (12, 24, 48)
_ACCENT = (43, 108, 176)
_TEAL = (26, 143, 140)
_TEAL_BRIGHT = (46, 180, 170)
_GOLD = (201, 162, 39)
_GOLD_LIGHT = (232, 198, 78)
_INK = (18, 28, 45)
_MUTED = (90, 102, 120)
_SOFT = (244, 247, 252)
_WHITE = (255, 255, 255)
_CARD = (255, 255, 255)
_RAIL_DESC = (43, 108, 176)
_RAIL_RESP = (26, 143, 140)
_RAIL_SKILL = (201, 162, 39)


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibrib.ttf" if bold else "C:/Windows/Fonts/calibri.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _wrap(
    draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int
) -> list[str]:
    words = (text or "").replace("\r\n", "\n").split()
    if not words:
        return []
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        trial = f"{current} {word}"
        if draw.textlength(trial, font=font) <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _bullet_lines(raw: str, *, limit: int = 5) -> list[str]:
    lines: list[str] = []
    for part in re.split(r"[\n•]+", raw or ""):
        item = part.strip().lstrip("-*• ").strip()
        if item:
            lines.append(item)
        if len(lines) >= limit:
            break
    return lines


def _description_body(raw: str) -> str:
    text = (raw or "").strip()
    text = re.sub(r"\n\nHow to apply\s*[\s\S]*$", "", text, flags=re.IGNORECASE).rstrip()
    text = re.sub(r"\n*Apply Here\s*->\s*\S+", "", text, flags=re.IGNORECASE).rstrip()
    kept: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if re.fullmatch(r"(#\w+\s*)+", stripped):
            continue
        kept.append(stripped)
    return " ".join(kept)


def _poster_sanitize_line(text: str) -> str:
    """Strip hashtags, URLs, and apply CTAs — poster shows email in footer only."""
    line = (text or "").strip()
    line = re.sub(r"https?://\S+", "", line, flags=re.IGNORECASE)
    line = re.sub(r"#\w+", "", line)
    line = re.sub(r"\s+", " ", line).strip()
    return line


def _poster_sanitize_block(raw: str) -> str:
    text = _description_body(raw)
    text = re.sub(r"https?://\S+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"#\w+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _wrap_paragraphs(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    max_width: int,
) -> list[str]:
    """Wrap text respecting newlines and word boundaries."""
    if not text or max_width <= 0:
        return []
    out: list[str] = []
    for paragraph in (text or "").replace("\r\n", "\n").split("\n"):
        paragraph = _poster_sanitize_line(paragraph)
        if not paragraph:
            continue
        words = paragraph.split()
        if not words:
            continue
        current = words[0]
        for word in words[1:]:
            trial = f"{current} {word}"
            if draw.textlength(trial, font=font) <= max_width:
                current = trial
            else:
                out.append(current)
                current = word
        out.append(current)
    return out


def _layout_wrapped_items(
    draw: ImageDraw.ImageDraw,
    items: list[str],
    font: ImageFont.ImageFont,
    max_width: int,
    *,
    bullet: bool = False,
    max_lines: int,
) -> list[str]:
    lines: list[str] = []
    for item in items:
        item = _poster_sanitize_line(item)
        if not item:
            continue
        wrap_w = max_width - (18 if bullet else 0)
        wrapped = _wrap_paragraphs(draw, item, font, wrap_w)
        for i, line in enumerate(wrapped):
            if bullet:
                lines.append(f"• {line}" if i == 0 else f"   {line}")
            else:
                lines.append(line)
        if len(lines) >= max_lines:
            break
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        if lines:
            last = lines[-1]
            if len(last) > 3:
                lines[-1] = last[:-1] + "…" if last.endswith(".") else last + "…"
    return lines


def append_apply_here_line(description: str, form_url: str) -> str:
    text = (description or "").rstrip()
    url = (form_url or "").strip()
    if not url:
        return text
    if not url.lower().startswith("http://") and not url.lower().startswith("https://"):
        url = "https://" + url.lstrip("/")
    text = re.sub(r"\n\nHow to apply\s*[\s\S]*$", "", text, flags=re.IGNORECASE).rstrip()
    text = re.sub(r"\n*Apply Here\s*->\s*\S+", "", text, flags=re.IGNORECASE).rstrip()
    return f"{text}\n\nApply Here -> {url}".strip()


def _lerp(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


def _vertical_gradient(
    size: tuple[int, int], top: tuple[int, int, int], bottom: tuple[int, int, int]
) -> Image.Image:
    w, h = size
    img = Image.new("RGB", size)
    pix = img.load()
    for y in range(h):
        color = _lerp(top, bottom, y / max(h - 1, 1))
        for x in range(w):
            pix[x, y] = color
    return img


def _diagonal_gradient(
    size: tuple[int, int], c1: tuple[int, int, int], c2: tuple[int, int, int]
) -> Image.Image:
    w, h = size
    img = Image.new("RGB", size)
    pix = img.load()
    denom = max(w + h - 2, 1)
    for y in range(h):
        for x in range(w):
            pix[x, y] = _lerp(c1, c2, (x + y) / denom)
    return img


def _rounded_rect(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    radius: int,
    fill: tuple[int, int, int] | tuple[int, int, int, int],
    outline: tuple[int, int, int] | None = None,
    width: int = 1,
) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def _draw_soft_shadow(
    base: Image.Image,
    box: tuple[int, int, int, int],
    *,
    radius: int = 16,
    blur: int = 10,
    opacity: int = 55,
) -> Image.Image:
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    x0, y0, x1, y1 = box
    od.rounded_rectangle(
        (x0 + 4, y0 + 6, x1 + 4, y1 + 6),
        radius=radius,
        fill=(16, 24, 40, opacity),
    )
    overlay = overlay.filter(ImageFilter.GaussianBlur(blur))
    return Image.alpha_composite(base.convert("RGBA"), overlay)


def _atmosphere_prompt(title: str, company: str) -> str:
    """Abstract brand atmosphere — explicitly no chairs / furniture / people."""
    return (
        f"Abstract premium brand background for {company} hiring {title}: "
        "flowing golden wheat fields of light, soft teal and deep navy gradients, "
        "geometric mesh lines, luminous particles, growth curves, modern fintech "
        "commodities aesthetic, cinematic bokeh, empty composition for text overlay. "
        "STRICTLY NO chairs, NO office furniture, NO desks, NO people, NO faces, "
        "NO hands, NO text, NO letters, NO logos, NO watermarks, NO photoreal objects."
    )


def _fit_art_panel(art: Image.Image, panel_w: int, panel_h: int) -> Image.Image:
    art = art.convert("RGB")
    scale = max(panel_w / art.width, panel_h / art.height)
    nw, nh = int(art.width * scale), int(art.height * scale)
    art = art.resize((nw, nh), Image.Resampling.LANCZOS)
    left = (nw - panel_w) // 2
    top = (nh - panel_h) // 2
    art = art.crop((left, top, left + panel_w, top + panel_h))
    overlay = Image.new("RGB", art.size, _NAVY_DEEP)
    return Image.blend(art, overlay, 0.42)


def _paste_kafi_logo(canvas: Image.Image, *, top_right_x: int, top: int, max_w: int = 200) -> None:
    from app.core.config import BASE_DIR

    logo_path = BASE_DIR / "config" / "branding" / "kafi_logo.png"
    if not logo_path.is_file():
        logger.warning("Kafi logo missing at %s", logo_path)
        return
    try:
        logo = Image.open(logo_path).convert("RGBA")
    except Exception:
        logger.exception("Failed to open Kafi logo")
        return
    if logo.width <= 0 or logo.height <= 0:
        return
    scale = min(max_w / logo.width, 78 / logo.height)
    nw = max(1, int(logo.width * scale))
    nh = max(1, int(logo.height * scale))
    logo = logo.resize((nw, nh), Image.Resampling.LANCZOS)
    pad = 12
    plate_w, plate_h = nw + pad * 2, nh + pad * 2
    plate = Image.new("RGBA", (plate_w, plate_h), (255, 255, 255, 235))
    # Soft shadow under plate
    shadow = Image.new("RGBA", (plate_w + 8, plate_h + 8), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle((2, 4, plate_w + 2, plate_h + 4), radius=14, fill=(0, 0, 0, 60))
    shadow = shadow.filter(ImageFilter.GaussianBlur(5))
    px = top_right_x - plate_w
    py = top
    base = canvas.convert("RGBA")
    base.alpha_composite(shadow, (px - 2, py - 2))
    # Rounded plate via mask
    mask = Image.new("L", (plate_w, plate_h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, plate_w, plate_h), radius=14, fill=255)
    rounded = Image.new("RGBA", (plate_w, plate_h), (0, 0, 0, 0))
    rounded.paste(plate, (0, 0))
    rounded.putalpha(mask)
    base.alpha_composite(rounded, (px, py))
    base.alpha_composite(logo, (px + pad, py + pad))
    canvas.paste(base.convert("RGB"))


def _draw_growth_visual(draw: ImageDraw.ImageDraw, cx: int, cy: int, scale: float = 1.0) -> None:
    """Abstract rising bars + orbit rings (no furniture)."""
    # Orbit rings
    for i, r in enumerate((70, 95, 120)):
        rr = int(r * scale)
        color = _GOLD_LIGHT if i % 2 == 0 else _TEAL_BRIGHT
        draw.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=color, width=2)
    # Rising bars
    bars = [28, 44, 36, 62, 50, 78]
    bw = int(14 * scale)
    gap = int(10 * scale)
    total_w = len(bars) * bw + (len(bars) - 1) * gap
    x0 = cx - total_w // 2
    base_y = cy + int(55 * scale)
    for i, h in enumerate(bars):
        hh = int(h * scale)
        x = x0 + i * (bw + gap)
        fill = _GOLD if i % 2 == 0 else _TEAL
        draw.rounded_rectangle((x, base_y - hh, x + bw, base_y), radius=4, fill=fill)
    # Center node
    draw.ellipse((cx - 10, cy - 10, cx + 10, cy + 10), fill=_WHITE)
    draw.ellipse((cx - 6, cy - 6, cx + 6, cy + 6), fill=_GOLD)


def _draw_wheat_arcs(draw: ImageDraw.ImageDraw, ox: int, oy: int) -> None:
    """Stylized golden wheat-inspired arcs (brand motif, not a chair)."""
    for i, offset in enumerate((-18, 0, 18)):
        pts = []
        for t in range(0, 55, 2):
            ang = math.radians(-70 + t * 2.2)
            r = 40 + t * 1.1
            x = ox + offset * 0.35 + int(r * math.sin(ang))
            y = oy + int(r * math.cos(ang))
            pts.append((x, y))
        if len(pts) >= 2:
            draw.line(pts, fill=_GOLD_LIGHT if i != 1 else _GOLD, width=3)


def _draw_network_mesh(draw: ImageDraw.ImageDraw, width: int, height: int) -> None:
    """Subtle dotted mesh across the body for depth."""
    step = 48
    nodes: list[tuple[int, int]] = []
    for y in range(360, height - 200, step):
        for x in range(40, width - 40, step):
            if (x // step + y // step) % 3 == 0:
                nodes.append((x, y))
                draw.ellipse((x - 2, y - 2, x + 2, y + 2), fill=(200, 210, 225))
    for i, (x1, y1) in enumerate(nodes):
        for x2, y2 in nodes[i + 1 : i + 4]:
            if abs(x1 - x2) + abs(y1 - y2) < 110:
                draw.line([(x1, y1), (x2, y2)], fill=(210, 218, 230), width=1)


def _section_icon(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    color: tuple[int, int, int],
    kind: str,
) -> None:
    draw.ellipse((x, y, x + 28, y + 28), fill=color)
    if kind == "about":
        draw.ellipse((x + 10, y + 8, x + 18, y + 16), fill=_WHITE)
        draw.rectangle((x + 12, y + 17, x + 16, y + 22), fill=_WHITE)
    elif kind == "resp":
        draw.rectangle((x + 8, y + 9, x + 20, y + 11), fill=_WHITE)
        draw.rectangle((x + 8, y + 14, x + 20, y + 16), fill=_WHITE)
        draw.rectangle((x + 8, y + 19, x + 16, y + 21), fill=_WHITE)
    else:
        # skills spark
        draw.polygon(
            [(x + 14, y + 6), (x + 17, y + 13), (x + 24, y + 14), (x + 18, y + 19), (x + 20, y + 26), (x + 14, y + 22), (x + 8, y + 26), (x + 10, y + 19), (x + 4, y + 14), (x + 11, y + 13)],
            fill=_WHITE,
        )


# Default recruitment poster palette (high-contrast red / yellow / black template)
_TEMPLATE_BLACK = (12, 12, 14)
_TEMPLATE_RED = (233, 49, 70)
_TEMPLATE_YELLOW = (255, 214, 0)
_TEMPLATE_YELLOW_SOFT = (252, 228, 90)


def _draw_dot_grid(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    *,
    cols: int = 4,
    rows: int = 4,
    spacing: int = 14,
    radius: int = 3,
    color: tuple[int, int, int] = _WHITE,
) -> None:
    for row in range(rows):
        for col in range(cols):
            cx = x + col * spacing
            cy = y + row * spacing
            draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=color)


def _description_lines(raw: str, *, limit: int = 6) -> list[str]:
    """Split description into poster sentences (no hashtags / URLs)."""
    body = _poster_sanitize_block(raw)
    if not body:
        return []
    parts = re.split(r"(?<=[.!?])\s+", body)
    lines = [p.strip() for p in parts if p.strip()]
    return lines[:limit] if lines else [body[:200]]


def _draw_column_card(
    draw: ImageDraw.ImageDraw,
    *,
    x: int,
    y: int,
    col_w: int,
    heading: str,
    body_lines: list[str],
    header_fill: tuple[int, int, int],
    header_text: tuple[int, int, int],
    body_fill: tuple[int, int, int],
    body_text: tuple[int, int, int],
    font_section: ImageFont.ImageFont,
    font_body: ImageFont.ImageFont,
    line_h: int,
    pad_x: int,
    pad_y: int,
) -> int:
    """Draw header + body card; returns total column height."""
    header_h = 48
    text_h = max(line_h, len(body_lines) * line_h)
    body_h = text_h + pad_y * 2
    total_h = header_h + 8 + body_h

    _rounded_rect(draw, (x, y, x + col_w, y + header_h), 18, header_fill)
    draw.rectangle((x + 14, y + header_h - 3, x + col_w - 14, y + header_h), fill=_TEMPLATE_YELLOW)

    draw.text(
        (x + col_w / 2, y + header_h / 2),
        heading,
        fill=header_text,
        font=font_section,
        anchor="mm",
    )

    body_top = y + header_h + 8
    _rounded_rect(
        draw,
        (x, body_top, x + col_w, body_top + body_h),
        18,
        body_fill,
        outline=(255, 255, 255),
        width=2,
    )

    ty = body_top + pad_y
    max_y = body_top + body_h - pad_y
    for line in body_lines:
        if ty + line_h > max_y:
            break
        draw.text((x + pad_x, ty), line, fill=body_text, font=font_body)
        ty += line_h

    return total_h


def generate_default_template_poster_png(
    *,
    title: str,
    description_text: str,
    requirements_text: str,
    apply_email: str,
) -> bytes:
    """Classic red/black/yellow hiring poster when no custom poster fields are supplied."""
    width, height = 1080, 1350
    footer_h = 300
    body_bottom = height - footer_h

    img = Image.new("RGB", (width, height), _TEMPLATE_BLACK)
    draw = ImageDraw.Draw(img)

    font_title = _load_font(48, bold=True)
    font_banner = _load_font(22, bold=True)
    font_section = _load_font(19, bold=True)
    font_body = _load_font(15, bold=False)
    font_body_bold = _load_font(15, bold=True)
    font_btn = _load_font(26, bold=True)
    font_footer = _load_font(17, bold=False)
    font_email = _load_font(22, bold=True)

    role = (title or "OPEN ROLE").strip()
    if len(role) > 48:
        role = role[:45].rstrip() + "…"
    email = (apply_email or "hr@kafi-group.com").strip()

    # Decorative dot grids + top accents
    _draw_dot_grid(draw, 36, 28, color=_WHITE)
    _draw_dot_grid(draw, width - 90, 28, color=_WHITE)
    draw.rectangle((0, 0, width, 6), fill=_TEMPLATE_YELLOW)
    draw.rectangle((0, 14, width, 18), fill=_TEMPLATE_YELLOW)

    # Kafi logo (top-right)
    _paste_kafi_logo(img, top_right_x=width - 28, top=22, max_w=120)
    draw = ImageDraw.Draw(img)

    # Title bubble
    bubble_top = 52
    bubble_h = 132
    _rounded_rect(
        draw,
        (56, bubble_top, width - 56, bubble_top + bubble_h),
        32,
        _TEMPLATE_RED,
        outline=_TEMPLATE_YELLOW,
        width=3,
    )
    title_lines = _wrap(draw, role.upper(), font_title, width - 220)[:2]
    ty = bubble_top + 28
    for line in title_lines:
        draw.text((width / 2, ty), line, fill=_WHITE, font=font_title, anchor="mm")
        ty += 52

    banner_y = bubble_top + bubble_h + 16
    banner_poly = [
        (110, banner_y),
        (width - 72, banner_y - 6),
        (width - 52, banner_y + 40),
        (90, banner_y + 48),
    ]
    draw.polygon(banner_poly, fill=_WHITE)
    draw.polygon(
        [(112, banner_y + 2), (width - 74, banner_y - 4), (width - 54, banner_y + 38), (92, banner_y + 46)],
        fill=_TEMPLATE_YELLOW_SOFT,
    )
    draw.text(
        (width / 2, banner_y + 22),
        "WE'RE HIRING",
        fill=_TEMPLATE_BLACK,
        font=font_banner,
        anchor="mm",
    )

    col_gap = 24
    col_w = (width - 72 - col_gap) // 2
    left_x = 36
    right_x = left_x + col_w + col_gap
    content_top = banner_y + 64
    max_col_bottom = body_bottom - 28
    max_col_height = max_col_bottom - content_top

    pad_x, pad_y = 22, 18
    line_h = 22
    text_max_w = col_w - pad_x * 2
    max_lines_per_col = max(4, (max_col_height - 80) // line_h)

    desc_items = _description_lines(description_text, limit=12)
    req_items = _bullet_lines(requirements_text, limit=12)
    if not req_items:
        req_items = ["See job posting for full requirements"]

    desc_lines = _layout_wrapped_items(
        draw,
        desc_items,
        font_body,
        text_max_w,
        bullet=False,
        max_lines=max_lines_per_col,
    )
    req_lines = _layout_wrapped_items(
        draw,
        req_items,
        font_body_bold,
        text_max_w,
        bullet=True,
        max_lines=max_lines_per_col,
    )
    if not desc_lines:
        desc_lines = ["Role overview will be shared during interview."]

    left_h = _draw_column_card(
        draw,
        x=left_x,
        y=content_top,
        col_w=col_w,
        heading="DESCRIPTION",
        body_lines=desc_lines,
        header_fill=_TEMPLATE_RED,
        header_text=_WHITE,
        body_fill=_TEMPLATE_YELLOW,
        body_text=_TEMPLATE_BLACK,
        font_section=font_section,
        font_body=font_body,
        line_h=line_h,
        pad_x=pad_x,
        pad_y=pad_y,
    )
    right_h = _draw_column_card(
        draw,
        x=right_x,
        y=content_top,
        col_w=col_w,
        heading="REQUIREMENTS",
        body_lines=req_lines,
        header_fill=_TEMPLATE_YELLOW,
        header_text=_TEMPLATE_BLACK,
        body_fill=_TEMPLATE_RED,
        body_text=_WHITE,
        font_section=font_section,
        font_body=font_body_bold,
        line_h=line_h,
        pad_x=pad_x,
        pad_y=pad_y,
    )

    # Bottom decorative dots between columns and footer
    col_bottom = content_top + max(left_h, right_h) + 16
    if col_bottom < body_bottom - 40:
        _draw_dot_grid(draw, 36, col_bottom, color=_TEMPLATE_RED, cols=3, rows=2)
        _draw_dot_grid(draw, width - 70, col_bottom, color=_WHITE, cols=3, rows=2)

    # Footer
    draw.rectangle((0, body_bottom, width, height), fill=_WHITE)
    draw.rectangle((0, body_bottom, width, body_bottom + 5), fill=_TEMPLATE_YELLOW)
    draw.rectangle((0, body_bottom + 5, width, body_bottom + 9), fill=_TEMPLATE_BLACK)

    btn_w, btn_h = 340, 58
    btn_x = (width - btn_w) // 2
    btn_y = body_bottom + 32
    _rounded_rect(
        draw,
        (btn_x, btn_y, btn_x + btn_w, btn_y + btn_h),
        29,
        _TEMPLATE_RED,
        outline=_TEMPLATE_BLACK,
        width=2,
    )
    draw.text(
        (width / 2, btn_y + btn_h / 2),
        "APPLY NOW",
        fill=_WHITE,
        font=font_btn,
        anchor="mm",
    )

    draw.text(
        (width / 2, btn_y + btn_h + 28),
        "SEND YOUR CV TO :",
        fill=_TEMPLATE_BLACK,
        font=font_footer,
        anchor="ma",
    )
    draw.text(
        (width / 2, btn_y + btn_h + 54),
        email,
        fill=_TEMPLATE_RED,
        font=font_email,
        anchor="ma",
    )

    draw.polygon([(0, height - 26), (200, height), (0, height)], fill=_TEMPLATE_RED)
    draw.rectangle((0, height - 6, width, height), fill=_TEMPLATE_BLACK)

    out = io.BytesIO()
    img.save(out, format="PNG", optimize=True)
    return out.getvalue()


def generate_hiring_poster_png(
    *,
    title: str,
    company_name: str,
    description_text: str,
    requirements_text: str,
    skill_names: Sequence[str],
    form_url: str,
    apply_email: str,
    settings: Settings,
) -> bytes:
    """Vertical hiring poster with abstract brand visuals (no chairs)."""
    _ = form_url  # apply CTA on the image is email only, never a Google Form URL
    width, height = 1080, 1350
    img = _vertical_gradient((width, height), _SOFT, (226, 234, 246))

    # Body mesh
    draw = ImageDraw.Draw(img)
    _draw_network_mesh(draw, width, height)

    # Diagonal teal ribbon behind content
    ribbon = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    rd = ImageDraw.Draw(ribbon)
    rd.polygon(
        [(width - 40, 340), (width, 340), (width, height - 180), (width - 120, height - 180)],
        fill=(*_TEAL, 28),
    )
    rd.polygon(
        [(0, 380), (90, 380), (40, height - 200), (0, height - 200)],
        fill=(*_GOLD, 22),
    )
    img = Image.alpha_composite(img.convert("RGBA"), ribbon).convert("RGB")

    # Hero atmosphere (abstract only)
    hero_h = 340
    try:
        deco_bytes = generate_image_bytes(
            prompt=_atmosphere_prompt(title, company_name),
            settings=settings,
        )
        art = _fit_art_panel(Image.open(io.BytesIO(deco_bytes)), width, hero_h)
        img.paste(art, (0, 0))
    except Exception:
        logger.exception("Cloudflare atmosphere art failed; using brand gradient hero")
        hero = _diagonal_gradient((width, hero_h), _NAVY_DEEP, _TEAL)
        img.paste(hero, (0, 0))

    draw = ImageDraw.Draw(img)

    # Geometric overlays on hero (growth visual + wheat arcs — NOT chairs)
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    # Soft glass panel for hero art accent (right side under logo)
    od.rounded_rectangle(
        (width - 340, 120, width - 48, 300),
        radius=20,
        fill=(255, 255, 255, 28),
        outline=(255, 255, 255, 60),
        width=1,
    )
    _draw_growth_visual(od, width - 194, 210, scale=0.85)
    _draw_wheat_arcs(od, 120, 250)
    # Light beams
    for i in range(6):
        x = 200 + i * 55
        od.line([(x, 0), (x - 40, hero_h)], fill=(255, 255, 255, 35), width=2)
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    # Kafi logo top-right
    _paste_kafi_logo(img, top_right_x=width - 36, top=24, max_w=210)

    draw = ImageDraw.Draw(img)
    # Gold + teal dual accent under hero
    draw.rectangle((0, hero_h, width, hero_h + 4), fill=_GOLD)
    draw.rectangle((0, hero_h + 4, width, hero_h + 8), fill=_TEAL)

    font_eyebrow = _load_font(20, bold=True)
    font_hero = _load_font(46, bold=True)
    font_section = _load_font(18, bold=True)
    font_body = _load_font(17, bold=False)
    font_small = _load_font(14, bold=False)
    font_pill = _load_font(14, bold=True)
    font_btn = _load_font(22, bold=True)

    company = (company_name or "Kafi Group").strip()
    role = (title or "").strip()

    # Hero copy
    draw.text((48, 42), "CAREERS AT KAFI", fill=(200, 215, 235), font=font_small)
    badge = "NOW HIRING"
    bw = int(draw.textlength(badge, font=font_eyebrow)) + 40
    _rounded_rect(draw, (48, 78, 48 + bw, 118), 20, _TEAL)
    # Badge shine
    draw.arc((52, 82, 48 + bw - 4, 100), start=200, end=340, fill=_TEAL_BRIGHT, width=2)
    draw.text((48 + bw / 2, 98), badge, fill=_WHITE, font=font_eyebrow, anchor="mm")
    draw.text((48, 138), f"{company}", fill=(210, 222, 240), font=font_small)
    for i, line in enumerate(_wrap(draw, role, font_hero, width - 400)[:3]):
        draw.text((48, 172 + i * 52), line, fill=_WHITE, font=font_hero)

    y = hero_h + 40
    content_x = 48
    content_w = width - 96
    base_rgba = img.convert("RGBA")

    def add_card(
        heading: str,
        body_lines: list[str],
        rail: tuple[int, int, int],
        icon_kind: str,
        *,
        as_bullets: bool = True,
    ) -> None:
        nonlocal y, base_rgba
        if not body_lines:
            return
        line_h = 25
        wrapped_all: list[str] = []
        measure = ImageDraw.Draw(base_rgba)
        for item in body_lines:
            prefix = "•  " if as_bullets else ""
            wrapped = _wrap(measure, f"{prefix}{item}", font_body, content_w - 72)
            wrapped_all.extend(wrapped[:3])
        text_block = len(wrapped_all) * line_h + 8
        card_h = 56 + text_block + 18
        if y + card_h > height - 220:
            return
        box = (content_x, y, content_x + content_w, y + card_h)
        base_rgba = _draw_soft_shadow(base_rgba, box, radius=18, blur=8, opacity=45)
        d = ImageDraw.Draw(base_rgba)
        _rounded_rect(d, box, 18, _CARD, outline=(220, 226, 236), width=1)
        d.rectangle((content_x, y, content_x + 8, y + card_h), fill=rail)
        d.rectangle(
            (content_x + 8, y, content_x + content_w, y + 48),
            fill=(248, 250, 254),
        )
        _section_icon(d, content_x + 22, y + 10, rail, icon_kind)
        d.text((content_x + 58, y + 14), heading.upper(), fill=rail, font=font_section)
        ty = y + 58
        for line in wrapped_all:
            if ty > y + card_h - 20:
                break
            d.text((content_x + 28, ty), line, fill=_MUTED, font=font_body)
            ty += line_h
        y += card_h + 20

    blurb = _description_body(description_text)
    if blurb:
        add_card("About the role", [blurb], _RAIL_DESC, "about", as_bullets=False)

    responsibilities = _bullet_lines(requirements_text, limit=5)
    add_card("Key responsibilities", responsibilities, _RAIL_RESP, "resp", as_bullets=True)

    skills = [s.strip() for s in skill_names if (s or "").strip()][:8]
    if skills and y < height - 300:
        measure = ImageDraw.Draw(base_rgba)
        pill_rows: list[list[tuple[str, int]]] = [[]]
        row_w = 0
        max_row = content_w - 56
        for skill in skills:
            pw = int(measure.textlength(skill, font=font_pill)) + 30
            if pill_rows[-1] and row_w + pw + 10 > max_row:
                pill_rows.append([])
                row_w = 0
            pill_rows[-1].append((skill, pw))
            row_w += pw + 10
        card_h = 56 + len(pill_rows) * 42 + 22
        if y + card_h <= height - 220:
            box = (content_x, y, content_x + content_w, y + card_h)
            base_rgba = _draw_soft_shadow(base_rgba, box, radius=18, blur=8, opacity=45)
            d = ImageDraw.Draw(base_rgba)
            _rounded_rect(d, box, 18, _CARD, outline=(220, 226, 236), width=1)
            d.rectangle((content_x, y, content_x + 8, y + card_h), fill=_RAIL_SKILL)
            d.rectangle(
                (content_x + 8, y, content_x + content_w, y + 48),
                fill=(252, 248, 235),
            )
            _section_icon(d, content_x + 22, y + 10, _RAIL_SKILL, "skill")
            d.text(
                (content_x + 58, y + 14),
                "SKILLS & COMPETENCIES",
                fill=_RAIL_SKILL,
                font=font_section,
            )
            py = y + 60
            for row in pill_rows:
                px = content_x + 28
                for label, pw in row:
                    _rounded_rect(d, (px, py, px + pw, py + 30), 15, (236, 244, 252))
                    d.text(
                        (px + pw / 2, py + 15),
                        label,
                        fill=_ACCENT,
                        font=font_pill,
                        anchor="mm",
                    )
                    px += pw + 10
                py += 40
            y += card_h + 20

    img = base_rgba.convert("RGB")
    draw = ImageDraw.Draw(img)

    # Footer with gradient + glow button
    footer_top = height - 178
    footer = _vertical_gradient((width, height - footer_top), _NAVY_DEEP, (8, 18, 38))
    img.paste(footer, (0, footer_top))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, footer_top, width, footer_top + 5), fill=_TEAL)
    draw.rectangle((0, footer_top + 5, width, footer_top + 8), fill=_GOLD)

    btn_w, btn_h = 280, 58
    btn_x = (width - btn_w) // 2
    btn_y = footer_top + 30
    # Button glow
    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse(
        (btn_x - 20, btn_y - 8, btn_x + btn_w + 20, btn_y + btn_h + 18),
        fill=(*_TEAL, 55),
    )
    glow = glow.filter(ImageFilter.GaussianBlur(12))
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
    draw = ImageDraw.Draw(img)
    _rounded_rect(draw, (btn_x, btn_y, btn_x + btn_w, btn_y + btn_h), 29, _TEAL)
    draw.arc(
        (btn_x + 10, btn_y + 4, btn_x + btn_w - 10, btn_y + 30),
        start=200,
        end=340,
        fill=_TEAL_BRIGHT,
        width=2,
    )
    draw.text(
        (width / 2, btn_y + btn_h / 2),
        "APPLY NOW",
        fill=_WHITE,
        font=font_btn,
        anchor="mm",
    )

    email = (apply_email or "hr@kafi-group.com").strip()
    draw.text(
        (width / 2, btn_y + btn_h + 22),
        f"Email your CV to {email}",
        fill=(190, 205, 225),
        font=font_small,
        anchor="ma",
    )

    # Vignette
    vignette = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    vd = ImageDraw.Draw(vignette)
    vd.rectangle((0, 0, width, 16), fill=(0, 0, 0, 40))
    vd.rectangle((0, height - 16, width, height), fill=(0, 0, 0, 50))
    vignette = vignette.filter(ImageFilter.GaussianBlur(8))
    img = Image.alpha_composite(img.convert("RGBA"), vignette).convert("RGB")

    out = io.BytesIO()
    img.save(out, format="PNG", optimize=True)
    return out.getvalue()
