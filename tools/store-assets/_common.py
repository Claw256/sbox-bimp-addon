"""Shared helpers for procedural Sandbox store thumbnail generators."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, Tuple

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

# 4x supersampling for razor-sharp anti-aliased vector shapes.
SS = 4

# Required store thumbnail sizes: square, landscape, portrait.
SIZES: list[tuple[int, int]] = [
    (512, 512),
    (910, 512),
    (512, 910),
]

# Repository root is two levels up from tools/store-assets/.
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "store" / "thumbnails"

# Exact Sandbox dark-slate palette.
PALETTE = {
    "bg_top": (27, 33, 36),        # #1b2124
    "bg_bottom": (13, 17, 19),     # #0d1113
    "title_white": (241, 245, 242),  # #f1f5f2
    "metal_dark": (44, 52, 56),    # #2c3438
    "metal_mid": (62, 72, 78),     # #3e484e
    "metal_light": (96, 110, 118), # #606e76
    "bezel_black": (10, 13, 15),   # #0a0d0f
    "chassis_top": (34, 41, 45),   # #22292d
    "chassis_bot": (20, 25, 28),   # #14191c
    "rubber_dark": (18, 22, 25),   # #121619
    "screen_top": (22, 29, 36),    # #161d24
    "screen_bot": (12, 16, 20),    # #0c1014
    "accent_deep": (45, 93, 161),  # #2d5da1
    "accent_blue": (77, 144, 252), # #4d90fc
    "accent_mid": (104, 145, 224), # #6891e0
    "accent_light": (145, 180, 255),  # #91b4ff
}

FONT_CANDIDATES = [
    Path(r"D:\Games\Steam\steamapps\common\sbox\core\fonts\Inter-Bold.ttf"),
    Path(r"D:\Games\Steam\steamapps\common\sbox\core\fonts\Inter-ExtraBold.ttf"),
    Path(r"C:\Program Files (x86)\Steam\steamapps\common\sbox\core\fonts\Inter-Bold.ttf"),
    Path(r"C:\Windows\Fonts\segoeuib.ttf"),
    Path(r"C:\Windows\Fonts\arialbd.ttf"),
    Path(r"C:\Windows\Fonts\calibrib.ttf"),
]

_FONT_PATH_CACHE: Path | None = None


def resolve_font_path() -> Path:
    """Find the best available bold sans-serif TrueType font."""
    global _FONT_PATH_CACHE
    if _FONT_PATH_CACHE is not None:
        return _FONT_PATH_CACHE
    for candidate in FONT_CANDIDATES:
        if candidate.is_file():
            _FONT_PATH_CACHE = candidate
            return candidate
    raise FileNotFoundError(
        "No bold sans-serif font found. Checked: "
        + ", ".join(str(p) for p in FONT_CANDIDATES)
    )


def load_bold_font(size_1x: float) -> ImageFont.FreeTypeFont:
    """Load the bold sans-serif font scaled for the 4x supersampled canvas."""
    font_path = resolve_font_path()
    return ImageFont.truetype(str(font_path), int(round(size_1x * SS)))


def s(val: float) -> float:
    """Scale a 1x coordinate or dimension to supersampled space."""
    return val * SS


def make_vertical_gradient(
    width: int,
    height: int,
    top_rgb: Tuple[int, int, int],
    bottom_rgb: Tuple[int, int, int],
) -> Image.Image:
    """Create a smooth vertical RGB gradient of the given size."""
    grad_1d = Image.linear_gradient("L").resize((1, height), Image.Resampling.BILINEAR)
    grad_full = grad_1d.resize((width, height), Image.Resampling.NEAREST)
    top_img = Image.new("RGB", (width, height), top_rgb)
    bot_img = Image.new("RGB", (width, height), bottom_rgb)
    return Image.composite(bot_img, top_img, grad_full)


def add_radial_glow(
    canvas: Image.Image,
    cx_1x: float,
    cy_1x: float,
    rx_1x: float,
    ry_1x: float,
    color_rgb: Tuple[int, int, int],
    alpha_peak: int,
    blur_1x: float,
) -> Image.Image:
    """Composite a smooth elliptical radial glow onto an RGBA supersampled canvas."""
    w_ss, h_ss = canvas.size
    w_1x, h_1x = w_ss // SS, h_ss // SS

    # Render glow at 1x resolution and upscale smoothly for fast, band-free blur.
    layer = Image.new("RGBA", (w_1x, h_1x), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.ellipse(
        [cx_1x - rx_1x, cy_1x - ry_1x, cx_1x + rx_1x, cy_1x + ry_1x],
        fill=(*color_rgb, alpha_peak),
    )
    layer = layer.filter(ImageFilter.GaussianBlur(radius=blur_1x))
    layer_ss = layer.resize((w_ss, h_ss), Image.Resampling.BILINEAR)
    return Image.alpha_composite(canvas, layer_ss)


def make_background(
    w_1x: int,
    h_1x: int,
    glow_cx_1x: float,
    glow_cy_1x: float,
    glow_rx_1x: float,
    glow_ry_1x: float,
) -> Image.Image:
    """Build the 4x supersampled dark-slate background with subtle Sandbox-blue glow."""
    bg_1x = make_vertical_gradient(
        w_1x, h_1x, PALETTE["bg_top"], PALETTE["bg_bottom"]
    ).convert("RGBA")

    # Subtle edge vignette for depth.
    vignette_mask = Image.radial_gradient("L").resize(
        (w_1x, h_1x), Image.Resampling.BILINEAR
    )
    # Darken outer corners gently (max ~35% darkening at extreme corners).
    vignette_alpha = vignette_mask.point(lambda p: int((p / 255.0) ** 2.2 * 85))
    vignette_layer = Image.new("RGBA", (w_1x, h_1x), (6, 8, 10, 0))
    vignette_layer.putalpha(vignette_alpha)
    bg_1x = Image.alpha_composite(bg_1x, vignette_layer)

    canvas = bg_1x.resize((w_1x * SS, h_1x * SS), Image.Resampling.BILINEAR)

    # Outer soft Sandbox-blue ambient halo.
    canvas = add_radial_glow(
        canvas,
        cx_1x=glow_cx_1x,
        cy_1x=glow_cy_1x,
        rx_1x=glow_rx_1x * 1.15,
        ry_1x=glow_ry_1x * 1.15,
        color_rgb=PALETTE["accent_mid"],
        alpha_peak=58,
        blur_1x=max(glow_rx_1x, glow_ry_1x) * 0.55,
    )
    # Tighter brighter core glow directly behind the silhouette.
    canvas = add_radial_glow(
        canvas,
        cx_1x=glow_cx_1x,
        cy_1x=glow_cy_1x,
        rx_1x=glow_rx_1x * 0.72,
        ry_1x=glow_ry_1x * 0.72,
        color_rgb=PALETTE["accent_blue"],
        alpha_peak=72,
        blur_1x=max(glow_rx_1x, glow_ry_1x) * 0.36,
    )
    return canvas


def draw_vertical_gradient_rounded_rect(
    canvas: Image.Image,
    bbox_ss: Tuple[float, float, float, float],
    radius_ss: float,
    top_rgb: Tuple[int, int, int],
    bot_rgb: Tuple[int, int, int],
    outline_rgba: Tuple[int, int, int, int] | None = None,
    outline_width_ss: int = 0,
) -> Image.Image:
    """Draw a vertically gradient-filled rounded rectangle onto an RGBA canvas."""
    x0, y0, x1, y1 = (int(round(v)) for v in bbox_ss)
    rw = max(1, x1 - x0)
    rh = max(1, y1 - y0)

    grad = make_vertical_gradient(rw, rh, top_rgb, bot_rgb).convert("RGBA")
    mask = Image.new("L", (rw, rh), 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.rounded_rectangle([0, 0, rw - 1, rh - 1], radius=radius_ss, fill=255)
    grad.putalpha(mask)

    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    layer.paste(grad, (x0, y0))
    canvas = Image.alpha_composite(canvas, layer)

    if outline_rgba is not None and outline_width_ss > 0:
        draw = ImageDraw.Draw(canvas)
        draw.rounded_rectangle(
            [x0, y0, x1, y1],
            radius=radius_ss,
            outline=outline_rgba,
            width=outline_width_ss,
        )
    return canvas


def draw_centered_title(
    canvas: Image.Image,
    title: str,
    w_1x: int,
    top_y_1x: float,
    font_size_1x: float,
) -> Tuple[float, float, float, float]:
    """Draw a bold centered title and return its 1x bounding box (x0, y0, x1, y1)."""
    font = load_bold_font(font_size_1x)
    probe_draw = ImageDraw.Draw(canvas)
    raw_bbox = probe_draw.textbbox((0, 0), title, font=font)
    text_w_ss = raw_bbox[2] - raw_bbox[0]
    text_h_ss = raw_bbox[3] - raw_bbox[1]

    x_ss = (w_1x * SS - text_w_ss) / 2.0 - raw_bbox[0]
    y_ss = top_y_1x * SS - raw_bbox[1]

    # Subtle dark drop shadow for crisp legibility against any glow.
    shadow_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow_layer)
    sdraw.text(
        (x_ss, y_ss + s(2.5)),
        title,
        font=font,
        fill=(6, 9, 12, 165),
    )
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=s(3.0)))
    canvas.alpha_composite(shadow_layer)

    # Crisp off-white title text.
    draw = ImageDraw.Draw(canvas)
    draw.text((x_ss, y_ss), title, font=font, fill=(*PALETTE["title_white"], 255))

    actual_bbox = draw.textbbox((x_ss, y_ss), title, font=font)
    return (
        actual_bbox[0] / SS,
        actual_bbox[1] / SS,
        actual_bbox[2] / SS,
        actual_bbox[3] / SS,
    )


def assert_layout_valid(
    title_bbox_1x: Tuple[float, float, float, float],
    art_bbox_1x: Tuple[float, float, float, float],
    w_1x: int,
    h_1x: int,
    min_gap_1x: float = 16.0,
    min_edge_margin_1x: float = 16.0,
    label: str = "",
) -> None:
    """Assert title sits cleanly above artwork with no overlap or edge clipping."""
    tx0, ty0, tx1, ty1 = title_bbox_1x
    ax0, ay0, ax1, ay1 = art_bbox_1x
    ctx = f"[{label} {w_1x}x{h_1x}]"

    gap = ay0 - ty1
    if gap < min_gap_1x:
        raise AssertionError(
            f"{ctx} Title overlaps or is too close to artwork: "
            f"title_bottom={ty1:.1f}, art_top={ay0:.1f}, gap={gap:.1f}px < {min_gap_1x:.1f}px"
        )
    if tx0 < min_edge_margin_1x or tx1 > w_1x - min_edge_margin_1x:
        raise AssertionError(
            f"{ctx} Title clips horizontal margin: [{tx0:.1f}, {tx1:.1f}] in width {w_1x}"
        )
    if ty0 < min_edge_margin_1x:
        raise AssertionError(
            f"{ctx} Title clips top margin: y0={ty0:.1f} < {min_edge_margin_1x:.1f}"
        )
    if ax0 < min_edge_margin_1x or ax1 > w_1x - min_edge_margin_1x:
        raise AssertionError(
            f"{ctx} Artwork clips horizontal margin: [{ax0:.1f}, {ax1:.1f}] in width {w_1x}"
        )
    if ay1 > h_1x - min_edge_margin_1x:
        raise AssertionError(
            f"{ctx} Artwork clips bottom margin: y1={ay1:.1f} > {h_1x - min_edge_margin_1x:.1f}"
        )


def finalize_and_save(
    canvas_rgba: Image.Image,
    out_path: Path,
    target_size: Tuple[int, int],
) -> None:
    """Downsample 4x RGBA canvas to opaque RGB PNG and verify mode/size."""
    downsampled = canvas_rgba.resize(target_size, Image.Resampling.LANCZOS)
    opaque_bg = Image.new("RGB", target_size, PALETTE["bg_bottom"])
    opaque_bg.paste(downsampled, mask=downsampled.split()[3])
    rgb_img = opaque_bg.convert("RGB")

    assert rgb_img.mode == "RGB", f"Expected RGB mode, got {rgb_img.mode}"
    assert rgb_img.size == target_size, f"Expected {target_size}, got {rgb_img.size}"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    rgb_img.save(out_path, format="PNG", optimize=True)


def parse_cli_args(description: str, argv: Iterable[str] | None = None) -> Path:
    """Parse standard --out CLI argument and return resolved output directory."""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help=f"Output directory for generated PNGs (default: {DEFAULT_OUT_DIR})",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    return args.out
