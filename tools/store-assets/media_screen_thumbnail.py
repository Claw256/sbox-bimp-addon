"""Procedural store thumbnail generator for Media Screen (flatscreen TV)."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Tuple

from PIL import Image, ImageDraw, ImageFilter

from _common import (
    PALETTE,
    SIZES,
    SS,
    add_radial_glow,
    assert_layout_valid,
    draw_centered_title,
    draw_vertical_gradient_rounded_rect,
    finalize_and_save,
    make_background,
    parse_cli_args,
    s,
)

TITLE = "Media Screen"
FILE_PREFIX = "media_screen"

# Per-aspect layout specs in 1x pixel coordinates.
LAYOUTS = {
    (512, 512): {
        "title_y": 46.0,
        "font_size": 46.0,
        "tv_w": 362.0,
        "tv_h": 216.0,
        "tv_top": 152.0,
        "neck_w": 54.0,
        "neck_h": 42.0,
        "base_w": 176.0,
        "base_h": 15.0,
    },
    (910, 512): {
        "title_y": 38.0,
        "font_size": 50.0,
        "tv_w": 442.0,
        "tv_h": 258.0,
        "tv_top": 134.0,
        "neck_w": 64.0,
        "neck_h": 44.0,
        "base_w": 214.0,
        "base_h": 16.0,
    },
    (512, 910): {
        "title_y": 152.0,
        "font_size": 52.0,
        "tv_w": 392.0,
        "tv_h": 236.0,
        "tv_top": 334.0,
        "neck_w": 58.0,
        "neck_h": 48.0,
        "base_w": 192.0,
        "base_h": 16.0,
    },
}


def draw_rounded_play_triangle(
    draw: ImageDraw.ImageDraw,
    cx: float,
    cy: float,
    radius: float,
    fill_rgba: Tuple[int, int, int, int],
) -> None:
    """Draw a crisp optically-centered play triangle with subtly softened vertices."""
    # Optical right shift (~10% of radius) so the triangle feels visually centered.
    ocx = cx + radius * 0.11
    angles_deg = [-120.0, 0.0, 120.0]
    pts = [
        (
            ocx + radius * math.cos(math.radians(a)),
            cy + radius * math.sin(math.radians(a)),
        )
        for a in angles_deg
    ]
    # Rounded corners via thick line join approximation: inset polygon + corner circles.
    corner_r = radius * 0.14
    inset_scale = 1.0 - (corner_r / (radius * 0.52))
    inset_pts = [
        (ocx + (px - ocx) * inset_scale, cy + (py - cy) * inset_scale)
        for px, py in pts
    ]

    # Fill core triangle.
    draw.polygon(inset_pts, fill=fill_rgba)
    # Connect edges with rounded-width strokes & circles at corners.
    stroke_w = max(1, int(round(corner_r * 2.0)))
    for i in range(3):
        p0 = inset_pts[i]
        p1 = inset_pts[(i + 1) % 3]
        draw.line([p0, p1], fill=fill_rgba, width=stroke_w)
        draw.ellipse(
            [p0[0] - corner_r, p0[1] - corner_r, p0[0] + corner_r, p0[1] + corner_r],
            fill=fill_rgba,
        )


def render_media_screen(w_1x: int, h_1x: int) -> Image.Image:
    """Render the Media Screen thumbnail at 4x supersampling."""
    spec = LAYOUTS[(w_1x, h_1x)]
    cx = w_1x / 2.0
    tv_w = spec["tv_w"]
    tv_h = spec["tv_h"]
    tv_x0 = cx - tv_w / 2.0
    tv_x1 = cx + tv_w / 2.0
    tv_y0 = spec["tv_top"]
    tv_y1 = tv_y0 + tv_h

    neck_w = spec["neck_w"]
    neck_h = spec["neck_h"]
    base_w = spec["base_w"]
    base_h = spec["base_h"]
    stand_y1 = tv_y1 + neck_h + base_h - 4.0

    # Background + subtle ambient blue glow centered behind the TV panel.
    canvas = make_background(
        w_1x,
        h_1x,
        glow_cx_1x=cx,
        glow_cy_1x=(tv_y0 + tv_y1) * 0.5,
        glow_rx_1x=tv_w * 0.62,
        glow_ry_1x=tv_h * 0.72,
    )

    # Soft ground shadow under the stand base.
    canvas = add_radial_glow(
        canvas,
        cx_1x=cx,
        cy_1x=stand_y1 + 2.0,
        rx_1x=base_w * 0.62,
        ry_1x=base_h * 0.65,
        color_rgb=(4, 6, 8),
        alpha_peak=185,
        blur_1x=10.0,
    )

    # --- 1. Pedestal stand (neck + wide flat base) ---
    neck_x0 = cx - neck_w / 2.0
    neck_x1 = cx + neck_w / 2.0
    neck_y0 = tv_y1 - 4.0
    neck_y1 = tv_y1 + neck_h

    # Brushed-metal neck with horizontal lighting cue (darker edges, brighter center).
    canvas = draw_vertical_gradient_rounded_rect(
        canvas,
        (s(neck_x0), s(neck_y0), s(neck_x1), s(neck_y1)),
        radius_ss=s(3.0),
        top_rgb=(36, 43, 47),
        bot_rgb=PALETTE["metal_mid"],
    )
    # Subtle vertical specular highlight band on neck.
    neck_hl = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ndraw = ImageDraw.Draw(neck_hl)
    ndraw.rectangle(
        [s(cx - neck_w * 0.24), s(neck_y0), s(cx + neck_w * 0.24), s(neck_y1)],
        fill=(140, 158, 170, 32),
    )
    # Shadow directly beneath the TV chin on top of the neck.
    ndraw.rectangle(
        [s(neck_x0), s(neck_y0), s(neck_x1), s(tv_y1 + 10.0)],
        fill=(8, 10, 12, 130),
    )
    canvas = Image.alpha_composite(canvas, neck_hl)

    # Wide flat pedestal base.
    base_x0 = cx - base_w / 2.0
    base_x1 = cx + base_w / 2.0
    base_y0 = stand_y1 - base_h
    base_y1 = stand_y1

    canvas = draw_vertical_gradient_rounded_rect(
        canvas,
        (s(base_x0), s(base_y0), s(base_x1), s(base_y1)),
        radius_ss=s(base_h * 0.44),
        top_rgb=PALETTE["metal_mid"],
        bot_rgb=(28, 34, 38),
        outline_rgba=(*PALETTE["metal_light"], 90),
        outline_width_ss=int(s(1.0)),
    )
    # Crisp metallic top highlight on the stand base.
    bdraw = ImageDraw.Draw(canvas)
    bdraw.line(
        [
            (s(base_x0 + base_h * 0.6), s(base_y0 + 1.4)),
            (s(base_x1 - base_h * 0.6), s(base_y0 + 1.4)),
        ],
        fill=(*PALETTE["metal_light"], 145),
        width=max(1, int(s(1.2))),
    )

    # --- 2. TV outer bezel ---
    bezel_r = 12.0
    chin_h = 15.0
    side_bezel = 9.0
    top_bezel = 9.0

    # Soft cast shadow behind TV body.
    tv_shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    tsdraw = ImageDraw.Draw(tv_shadow)
    tsdraw.rounded_rectangle(
        [s(tv_x0 + 2), s(tv_y0 + 8), s(tv_x1 - 2), s(tv_y1 + 10)],
        radius=s(bezel_r),
        fill=(4, 6, 8, 150),
    )
    tv_shadow = tv_shadow.filter(ImageFilter.GaussianBlur(radius=s(9.0)))
    canvas = Image.alpha_composite(canvas, tv_shadow)

    # Main glossy piano-black bezel body.
    canvas = draw_vertical_gradient_rounded_rect(
        canvas,
        (s(tv_x0), s(tv_y0), s(tv_x1), s(tv_y1)),
        radius_ss=s(bezel_r),
        top_rgb=(19, 23, 27),
        bot_rgb=PALETTE["bezel_black"],
        outline_rgba=(*PALETTE["metal_mid"], 195),
        outline_width_ss=int(s(1.4)),
    )

    # Thin metallic lower chin bar clipped cleanly inside the rounded TV silhouette.
    chin_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    chin_grad = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    chin_y0 = tv_y1 - chin_h
    chin_grad = draw_vertical_gradient_rounded_rect(
        chin_grad,
        (s(tv_x0), s(chin_y0), s(tv_x1), s(tv_y1)),
        radius_ss=0,
        top_rgb=PALETTE["metal_mid"],
        bot_rgb=PALETTE["metal_dark"],
    )
    # Clip chin to the TV bezel mask (inset by outline width).
    bezel_mask = Image.new("L", canvas.size, 0)
    bmdraw = ImageDraw.Draw(bezel_mask)
    bmdraw.rounded_rectangle(
        [s(tv_x0 + 1.2), s(tv_y0 + 1.2), s(tv_x1 - 1.2), s(tv_y1 - 1.2)],
        radius=s(bezel_r - 1.0),
        fill=255,
    )
    chin_layer.paste(chin_grad, (0, 0), mask=bezel_mask)
    canvas = Image.alpha_composite(canvas, chin_layer)

    # Crisp hairline seam separating bezel from metallic chin.
    draw = ImageDraw.Draw(canvas)
    draw.line(
        [(s(tv_x0 + 2.0), s(chin_y0)), (s(tv_x1 - 2.0), s(chin_y0))],
        fill=(*PALETTE["metal_light"], 125),
        width=max(1, int(s(1.0))),
    )

    # Tiny glowing blue power LED on bottom-right of chin.
    led_cx = tv_x1 - 18.0
    led_cy = chin_y0 + chin_h * 0.52
    canvas = add_radial_glow(
        canvas,
        cx_1x=led_cx,
        cy_1x=led_cy,
        rx_1x=8.0,
        ry_1x=8.0,
        color_rgb=PALETTE["accent_blue"],
        alpha_peak=190,
        blur_1x=4.2,
    )
    draw = ImageDraw.Draw(canvas)
    led_r = 2.4
    draw.ellipse(
        [s(led_cx - led_r), s(led_cy - led_r), s(led_cx + led_r), s(led_cy + led_r)],
        fill=(*PALETTE["accent_light"], 255),
    )

    # --- 3. Screen interior ---
    scr_x0 = tv_x0 + side_bezel
    scr_x1 = tv_x1 - side_bezel
    scr_y0 = tv_y0 + top_bezel
    scr_y1 = chin_y0 - 6.0
    scr_w = scr_x1 - scr_x0
    scr_h = scr_y1 - scr_y0
    scr_cx = (scr_x0 + scr_x1) / 2.0
    scr_cy = (scr_y0 + scr_y1) / 2.0 - scr_h * 0.055

    canvas = draw_vertical_gradient_rounded_rect(
        canvas,
        (s(scr_x0), s(scr_y0), s(scr_x1), s(scr_y1)),
        radius_ss=s(4.5),
        top_rgb=PALETTE["screen_top"],
        bot_rgb=PALETTE["screen_bot"],
        outline_rgba=(6, 8, 10, 220),
        outline_width_ss=int(s(1.0)),
    )

    # Subtle diagonal glass sheen across the upper-left of the screen.
    sheen_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    shdraw = ImageDraw.Draw(sheen_layer)
    shdraw.polygon(
        [
            (s(scr_x0), s(scr_y0)),
            (s(scr_x0 + scr_w * 0.58), s(scr_y0)),
            (s(scr_x0 + scr_w * 0.24), s(scr_y1)),
            (s(scr_x0), s(scr_y1)),
        ],
        fill=(255, 255, 255, 9),
    )
    scr_mask = Image.new("L", canvas.size, 0)
    smdraw = ImageDraw.Draw(scr_mask)
    smdraw.rounded_rectangle(
        [s(scr_x0), s(scr_y0), s(scr_x1), s(scr_y1)],
        radius=s(4.5),
        fill=255,
    )
    sheen_clipped = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    sheen_clipped.paste(sheen_layer, (0, 0), mask=scr_mask)
    canvas = Image.alpha_composite(canvas, sheen_clipped)

    # Soft blue glow inside the screen behind the Play icon.
    play_r = min(scr_w, scr_h) * 0.225
    canvas = add_radial_glow(
        canvas,
        cx_1x=scr_cx,
        cy_1x=scr_cy,
        rx_1x=play_r * 2.1,
        ry_1x=play_r * 2.1,
        color_rgb=PALETTE["accent_blue"],
        alpha_peak=105,
        blur_1x=play_r * 0.95,
    )

    # Bold Sandbox-blue Play badge (circular badge + crisp off-white rounded play triangle).
    badge_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    badge_grad = draw_vertical_gradient_rounded_rect(
        badge_layer,
        (
            s(scr_cx - play_r),
            s(scr_cy - play_r),
            s(scr_cx + play_r),
            s(scr_cy + play_r),
        ),
        radius_ss=s(play_r),
        top_rgb=(96, 160, 255),
        bot_rgb=PALETTE["accent_deep"],
        outline_rgba=(*PALETTE["accent_light"], 195),
        outline_width_ss=int(s(1.6)),
    )
    canvas = Image.alpha_composite(canvas, badge_grad)

    draw = ImageDraw.Draw(canvas)
    draw_rounded_play_triangle(
        draw,
        cx=s(scr_cx),
        cy=s(scr_cy),
        radius=s(play_r * 0.48),
        fill_rgba=(*PALETTE["title_white"], 255),
    )

    # --- 4. Minimal clean progress bar along the bottom of the screen ---
    bar_pad_x = scr_w * 0.085
    bar_x0 = scr_x0 + bar_pad_x
    bar_x1 = scr_x1 - bar_pad_x
    bar_y = scr_y1 - scr_h * 0.125
    bar_h = max(5.5, scr_h * 0.036)
    progress = 0.40
    fill_x1 = bar_x0 + (bar_x1 - bar_x0) * progress

    # Unfilled track.
    draw.rounded_rectangle(
        [s(bar_x0), s(bar_y - bar_h / 2.0), s(bar_x1), s(bar_y + bar_h / 2.0)],
        radius=s(bar_h / 2.0),
        fill=(38, 49, 58, 220),
    )
    # Filled Sandbox-blue progress bar.
    draw.rounded_rectangle(
        [s(bar_x0), s(bar_y - bar_h / 2.0), s(fill_x1), s(bar_y + bar_h / 2.0)],
        radius=s(bar_h / 2.0),
        fill=(*PALETTE["accent_blue"], 255),
    )
    # Subtle glow on scrubber thumb.
    canvas = add_radial_glow(
        canvas,
        cx_1x=fill_x1,
        cy_1x=bar_y,
        rx_1x=bar_h * 1.9,
        ry_1x=bar_h * 1.9,
        color_rgb=PALETTE["accent_blue"],
        alpha_peak=145,
        blur_1x=bar_h * 0.9,
    )
    draw = ImageDraw.Draw(canvas)
    thumb_r = bar_h * 0.88
    draw.ellipse(
        [
            s(fill_x1 - thumb_r),
            s(bar_y - thumb_r),
            s(fill_x1 + thumb_r),
            s(bar_y + thumb_r),
        ],
        fill=(*PALETTE["title_white"], 255),
        outline=(*PALETTE["accent_light"], 220),
        width=max(1, int(s(1.0))),
    )

    # --- 5. Centered title + non-overlap validation ---
    title_bbox = draw_centered_title(
        canvas,
        TITLE,
        w_1x=w_1x,
        top_y_1x=spec["title_y"],
        font_size_1x=spec["font_size"],
    )
    art_bbox = (tv_x0, tv_y0, tv_x1, stand_y1)
    assert_layout_valid(
        title_bbox,
        art_bbox,
        w_1x=w_1x,
        h_1x=h_1x,
        min_gap_1x=24.0,
        min_edge_margin_1x=20.0,
        label=TITLE,
    )
    return canvas


def generate_all(out_dir: Path) -> list[Path]:
    """Generate all 3 Media Screen store thumbnails and return their paths."""
    written: list[Path] = []
    for w, h in SIZES:
        canvas = render_media_screen(w, h)
        out_path = out_dir / f"{FILE_PREFIX}_{w}x{h}.png"
        finalize_and_save(canvas, out_path, (w, h))
        written.append(out_path)
    return written


def main() -> None:
    out_dir = parse_cli_args("Generate Media Screen store thumbnails.")
    paths = generate_all(out_dir)
    for p in paths:
        print(f"Generated: {p}")


if __name__ == "__main__":
    main()
