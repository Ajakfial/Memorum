"""
Generates Memorum's app icon set from scratch: a honey-to-teal gradient
hexagon on a plum-charcoal rounded square, matching the frontend's design
tokens (see frontend/src/styles/global.css). Produces every size/format
Tauri needs for Windows and macOS bundling.

Run once (already run to produce the committed assets):
    python3 generate_icons.py
"""
import math
import struct
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).parent / "icons"
OUT.mkdir(exist_ok=True)

BG = (23, 21, 31, 255)        # --bg
HONEY = (232, 163, 61, 255)   # --accent-honey
TEAL = (87, 214, 190, 255)    # --accent-teal
INK = (26, 20, 32, 255)       # dark text on the gradient


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(4))


def hexagon_points(cx, cy, r):
    # Flat-left/right hexagon, matching the CSS clip-path in global.css.
    pts = []
    for i in range(6):
        angle = math.radians(60 * i - 30)
        pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    return pts


def render(size: int) -> Image.Image:
    scale = 4  # supersample for clean edges, then downscale
    s = size * scale
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Rounded-square base
    radius = int(s * 0.22)
    draw.rounded_rectangle([0, 0, s - 1, s - 1], radius=radius, fill=BG)

    # Gradient hexagon (approximate via horizontal bands)
    cx, cy = s / 2, s / 2
    r = s * 0.34
    steps = 48
    for i in range(steps):
        t = i / (steps - 1)
        band_color = lerp(HONEY, TEAL, t)
        y0 = cy - r + (2 * r) * (i / steps)
        y1 = cy - r + (2 * r) * ((i + 1) / steps)
        mask = Image.new("L", (s, s), 0)
        mdraw = ImageDraw.Draw(mask)
        mdraw.polygon(hexagon_points(cx, cy, r), fill=255)
        band = Image.new("RGBA", (s, s), band_color)
        band_mask = Image.new("L", (s, s), 0)
        bmdraw = ImageDraw.Draw(band_mask)
        bmdraw.rectangle([0, y0, s, y1], fill=255)
        combined_mask = Image.composite(band_mask, Image.new("L", (s, s), 0), mask)
        img = Image.composite(band, img, combined_mask)

    # "M" mark in the center
    from PIL import ImageFont

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", int(s * 0.34))
    except Exception:
        font = ImageFont.load_default()
    draw = ImageDraw.Draw(img)
    text = "M"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((cx - tw / 2 - bbox[0], cy - th / 2 - bbox[1]), text, font=font, fill=INK)

    return img.resize((size, size), Image.LANCZOS)


def write_png(size: int, name: str):
    render(size).save(OUT / name)


def write_ico(sizes, name):
    images = [render(s) for s in sizes]
    images[0].save(OUT / name, format="ICO", sizes=[(s, s) for s in sizes])


def write_icns(sizes_and_types, name):
    """Hand-rolled ICNS writer: modern .icns files are just a container of
    PNG-encoded chunks keyed by OSType, so no native macOS tooling is needed
    to produce one."""
    chunks = b""
    for size, ostype in sizes_and_types:
        import io

        buf = io.BytesIO()
        render(size).save(buf, format="PNG")
        data = buf.getvalue()
        chunk = ostype.encode("ascii") + struct.pack(">I", len(data) + 8) + data
        chunks += chunk

    total_len = 8 + len(chunks)
    header = b"icns" + struct.pack(">I", total_len)
    (OUT / name).write_bytes(header + chunks)


if __name__ == "__main__":
    for size, name in [(32, "32x32.png"), (128, "128x128.png"), (256, "128x128@2x.png"), (1024, "app-icon.png")]:
        write_png(size, name)

    write_ico([16, 32, 48, 64, 128, 256], "icon.ico")

    write_icns(
        [(128, "ic07"), (256, "ic08"), (512, "ic09"), (1024, "ic10")],
        "icon.icns",
    )

    print("Icon set written to", OUT)
