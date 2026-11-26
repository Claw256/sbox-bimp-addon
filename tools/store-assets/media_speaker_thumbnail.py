"""Procedural store thumbnail generator for Media Speaker (wide boombox)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from _common import (
    PALETTE,
    SIZES,
    add_radial_glow,
    assert_layout_valid,
    draw_centered_title,
    draw_vertical_gradient_rounded_rect,
    finalize_and_save,
    make_background,
    parse_cli_args,
    s,
)

TITLE = "Media Speaker"
FILE_PREFIX = "media_speaker"

# Per-aspect layout specs in 1x pixel coordinates.
LAYOUTS = {
    (512, 512): {
        "title_y": 46.0,
        "font_size": 46.0,
        "body_w": 382.0,
        "body_h": 182.0,
        "handle_h": 40.0,
        "feet_h": 11.0,
        "art_top": 172.0,
    },
    (910, 512): {
        "title_y": 38.0,
        "font_size": 50.0,
        "body_w": 484.0,
        "body_h": 222.0,
        "handle_h": 46.0,
        "feet_h": 12.0,
        "art_top": 152.0,
    },
    (512, 910): {
        "title_y": 152.0,
        "font_size": 52.0,
        "body_w": 404.0,
        "body_h": 194.0,
        "handle_h": 42.0,
        "feet_h": 11.0,
        "art_top": 352.0,
    },
}


def draw_woofer(
    canvas: Image.Image,
    cx: float,
    cy: float,
    outer_r: float,
) -> Image.Image:
    """Draw a bold circular speaker bay with metallic ring, cone, and dust cap."""
    draw = ImageDraw.Draw(canvas)

    # 1. Recessed dark housing well.
    well_r = outer_r * 1.04
    draw.ellipse(
        [s(cx - well_r), s(cy - well_r), s(cx + well_r), s(cy + well_r)],
        fill=(*PALETTE["bezel_black"], 255),
    )

    # 2. Brushed-metal bevel ring (vertical gradient disc).
    canvas = draw_vertical_gradient_rounded_rect(
        canvas,
        (s(cx - outer_r), s(cy - outer_r), s(cx + outer_r), s(cy + outer_r)),
        radius_ss=s(outer_r),
        top_rgb=PALETTE["metal_light"],
        bot_rgb=PALETTE["metal_dark"],
    )

    draw = ImageDraw.Draw(canvas)

    # 3. Dark rubber surround.
    surround_r = outer_r * 0.87
    draw.ellipse(
        [
            s(cx - surround_r),
            s(cy - surround_r),
            s(cx + surround_r),
            s(cy + surround_r),
        ],
        fill=(14, 18, 21, 255),
    )
    # Subtle surround ridge highlight.
    ridge_r = outer_r * 0.80
    draw.ellipse(
        [s(cx - ridge_r), s(cy - ridge_r), s(cx + ridge_r), s(cy + ridge_r)],
        outline=(44, 52, 58, 170),
        width=max(1, int(s(2.0))),
    )

    # 4. Deep matte speaker cone.
    cone_r = outer_r * 0.72
    canvas = draw_vertical_gradient_rounded_rect(
        canvas,
        (s(cx - cone_r), s(cy - cone_r), s(cx + cone_r), s(cy + cone_r)),
        radius_ss=s(cone_r),
        top_rgb=(32, 39, 44),
        bot_rgb=(17, 21, 25),
    )
    draw = ImageDraw.Draw(canvas)
    # Subtle concentric acoustic ribs.
    for frac in (0.58, 0.45):
        rr = outer_r * frac
        draw.ellipse(
            [s(cx - rr), s(cy - rr), s(cx + rr), s(cy + rr)],
            outline=(50, 60, 66, 95),
            width=max(1, int(s(1.0))),
        )

    # 5. Center dome dust cap with crisp metallic sheen.
    cap_r = outer_r * 0.30
    # Soft shadow under dust cap.
    draw.ellipse(
        [
            s(cx - cap_r * 1.08),
            s(cy - cap_r * 0.98),
            s(cx + cap_r * 1.08),
            s(cy + cap_r * 1.14),
        ],
        fill=(8, 10, 12, 165),
    )
    canvas = draw_vertical_gradient_rounded_rect(
        canvas,
        (s(cx - cap_r), s(cy - cap_r), s(cx + cap_r), s(cy + cap_r)),
        radius_ss=s(cap_r),
        top_rgb=(104, 118, 128),
        bot_rgb=(36, 44, 49),
        outline_rgba=(140, 160, 175, 110),
        outline_width_ss=max(1, int(s(0.9))),
    )
    # Small specular glint on upper-left of dust cap.
    draw = ImageDraw.Draw(canvas)
    glint_x = cx - cap_r * 0.28
    glint_y = cy - cap_r * 0.28
    glint_r = cap_r * 0.20
    draw.ellipse(
        [
            s(glint_x - glint_r),
            s(glint_y - glint_r),
            s(glint_x + glint_r),
            s(glint_y + glint_r),
        ],
        fill=(220, 232, 245, 95),
    )
    return canvas


def render_media_speaker(w_1x: int, h_1x: int) -> Image.Image:
    """Render the Media Speaker thumbnail at 4x supersampling."""
    spec = LAYOUTS[(w_1x, h_1x)]
    cx = w_1x / 2.0
    body_w = spec["body_w"]
    body_h = spec["body_h"]
    handle_h = spec["handle_h"]
    feet_h = spec["feet_h"]

    art_y0 = spec["art_top"]
    body_x0 = cx - body_w / 2.0
    body_x1 = cx + body_w / 2.0
    body_y0 = art_y0 + handle_h
    body_y1 = body_y0 + body_h
    art_y1 = body_y1 + feet_h

    # Background + subtle ambient Sandbox-blue glow behind boombox.
    canvas = make_background(
        w_1x,
        h_1x,
        glow_cx_1x=cx,
        glow_cy_1x=(body_y0 + body_y1) * 0.5,
        glow_rx_1x=body_w * 0.62,
        glow_ry_1x=body_h * 0.82,
    )

    # Soft ground shadow under the boombox feet.
    canvas = add_radial_glow(
        canvas,
        cx_1x=cx,
        cy_1x=art_y1 + 2.0,
        rx_1x=body_w * 0.54,
        ry_1x=feet_h * 1.15,
        color_rgb=(4, 6, 8),
        alpha_peak=195,
        blur_1x=11.0,
    )

    # --- 1. Top brushed-metal carry handle with dark rubber center grip ---
    handle_w = body_w * 0.62
    hx0 = cx - handle_w / 2.0
    hx1 = cx + handle_w / 2.0
    bar_thick = max(11.0, handle_h * 0.32)
    strut_w = max(13.0, handle_w * 0.068)

    # Left & right vertical metallic struts.
    for sx0 in (hx0, hx1 - strut_w):
        canvas = draw_vertical_gradient_rounded_rect(
            canvas,
            (s(sx0), s(art_y0 + 3.0), s(sx0 + strut_w), s(body_y0 + 8.0)),
            radius_ss=s(4.0),
            top_rgb=PALETTE["metal_light"],
            bot_rgb=PALETTE["metal_dark"],
            outline_rgba=(16, 20, 23, 180),
            outline_width_ss=max(1, int(s(1.0))),
        )

    # Horizontal metallic handle bar bridging the struts.
    canvas = draw_vertical_gradient_rounded_rect(
        canvas,
        (s(hx0), s(art_y0), s(hx1), s(art_y0 + bar_thick)),
        radius_ss=s(bar_thick * 0.45),
        top_rgb=PALETTE["metal_light"],
        bot_rgb=PALETTE["metal_dark"],
        outline_rgba=(120, 136, 146, 110),
        outline_width_ss=max(1, int(s(1.0))),
    )

    # Centered dark rubber grip sleeve on the handle bar.
    grip_w = handle_w * 0.52
    gx0 = cx - grip_w / 2.0
    gx1 = cx + grip_w / 2.0
    grip_pad_y = 2.0
    canvas = draw_vertical_gradient_rounded_rect(
        canvas,
        (
            s(gx0),
            s(art_y0 - grip_pad_y),
            s(gx1),
            s(art_y0 + bar_thick + grip_pad_y),
        ),
        radius_ss=s((bar_thick + 2 * grip_pad_y) * 0.42),
        top_rgb=(36, 42, 47),
        bot_rgb=PALETTE["rubber_dark"],
        outline_rgba=(70, 82, 90, 120),
        outline_width_ss=max(1, int(s(1.0))),
    )

    # --- 2. Rubber feet ---
    foot_w = body_w * 0.13
    foot_inset = body_w * 0.085
    for fx0 in (body_x0 + foot_inset, body_x1 - foot_inset - foot_w):
        canvas = draw_vertical_gradient_rounded_rect(
            canvas,
            (s(fx0), s(body_y1 - 4.0), s(fx0 + foot_w), s(art_y1)),
            radius_ss=s(4.5),
            top_rgb=(32, 38, 42),
            bot_rgb=PALETTE["rubber_dark"],
            outline_rgba=(58, 68, 74, 110),
            outline_width_ss=max(1, int(s(0.9))),
        )

    # --- 3. Wide charcoal boombox chassis ---
    chassis_r = 18.0
    # Soft drop shadow behind chassis.
    ch_shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    csdraw = ImageDraw.Draw(ch_shadow)
    csdraw.rounded_rectangle(
        [s(body_x0 + 3), s(body_y0 + 8), s(body_x1 - 3), s(body_y1 + 10)],
        radius=s(chassis_r),
        fill=(4, 6, 8, 155),
    )
    ch_shadow = ch_shadow.filter(ImageFilter.GaussianBlur(radius=s(9.0)))
    canvas = Image.alpha_composite(canvas, ch_shadow)

    canvas = draw_vertical_gradient_rounded_rect(
        canvas,
        (s(body_x0), s(body_y0), s(body_x1), s(body_y1)),
        radius_ss=s(chassis_r),
        top_rgb=PALETTE["chassis_top"],
        bot_rgb=PALETTE["chassis_bot"],
        outline_rgba=(*PALETTE["metal_mid"], 210),
        outline_width_ss=int(s(1.6)),
    )

    # Thin metallic top & bottom trim rails.
    rail_inset_x = body_w * 0.055
    rail_h = max(4.5, body_h * 0.032)
    rail_margin_y = 6.5
    # Top rail.
    canvas = draw_vertical_gradient_rounded_rect(
        canvas,
        (
            s(body_x0 + rail_inset_x),
            s(body_y0 + rail_margin_y),
            s(body_x1 - rail_inset_x),
            s(body_y0 + rail_margin_y + rail_h),
        ),
        radius_ss=s(rail_h * 0.5),
        top_rgb=PALETTE["metal_light"],
        bot_rgb=PALETTE["metal_dark"],
    )
    # Bottom rail.
    canvas = draw_vertical_gradient_rounded_rect(
        canvas,
        (
            s(body_x0 + rail_inset_x),
            s(body_y1 - rail_margin_y - rail_h),
            s(body_x1 - rail_inset_x),
            s(body_y1 - rail_margin_y),
        ),
        radius_ss=s(rail_h * 0.5),
        top_rgb=PALETTE["metal_mid"],
        bot_rgb=(30, 36, 40),
    )

    # --- 4. Left & right circular speaker bays ---
    woofer_r = body_h * 0.355
    woofer_cy = (body_y0 + body_y1) * 0.5
    woofer_offset = body_w * 0.322
    canvas = draw_woofer(canvas, cx - woofer_offset, woofer_cy, woofer_r)
    canvas = draw_woofer(canvas, cx + woofer_offset, woofer_cy, woofer_r)

    # --- 5. Center recessed dark display + vibrant Sandbox-blue visualizer bars ---
    disp_w = body_w * 0.255
    disp_h = body_h * 0.56
    disp_x0 = cx - disp_w / 2.0
    disp_x1 = cx + disp_w / 2.0
    disp_y0 = woofer_cy - disp_h / 2.0
    disp_y1 = woofer_cy + disp_h / 2.0

    canvas = draw_vertical_gradient_rounded_rect(
        canvas,
        (s(disp_x0), s(disp_y0), s(disp_x1), s(disp_y1)),
        radius_ss=s(9.0),
        top_rgb=(12, 16, 20),
        bot_rgb=PALETTE["bezel_black"],
        outline_rgba=(*PALETTE["metal_mid"], 190),
        outline_width_ss=int(s(1.3)),
    )

    # Soft blue screen glow inside the center display.
    canvas = add_radial_glow(
        canvas,
        cx_1x=cx,
        cy_1x=woofer_cy + disp_h * 0.06,
        rx_1x=disp_w * 0.52,
        ry_1x=disp_h * 0.45,
        color_rgb=PALETTE["accent_blue"],
        alpha_peak=95,
        blur_1x=disp_w * 0.28,
    )

    # 7 crisp vertical spectrum visualizer bars (#2d5da1 -> #4d90fc -> #91b4ff).
    bar_heights = [0.36, 0.66, 0.94, 0.56, 0.86, 0.60, 0.34]
    n_bars = len(bar_heights)
    inner_pad_x = disp_w * 0.12
    inner_pad_top = disp_h * 0.17
    inner_pad_bot = disp_h * 0.16
    avail_w = disp_w - 2 * inner_pad_x
    avail_h = disp_h - inner_pad_top - inner_pad_bot

    gap_ratio = 0.36
    bar_w = avail_w / (n_bars + (n_bars - 1) * gap_ratio)
    bar_gap = bar_w * gap_ratio
    bar_base_y = disp_y1 - inner_pad_bot

    for i, frac in enumerate(bar_heights):
        bx0 = disp_x0 + inner_pad_x + i * (bar_w + bar_gap)
        bx1 = bx0 + bar_w
        bh = max(bar_w * 1.1, avail_h * frac)
        by0 = bar_base_y - bh
        by1 = bar_base_y

        # Gradient bar: bright #91b4ff peak -> #4d90fc mid -> #2d5da1 base.
        mid_y = by0 + bh * 0.42
        canvas = draw_vertical_gradient_rounded_rect(
            canvas,
            (s(bx0), s(by0), s(bx1), s(by1)),
            radius_ss=s(bar_w * 0.44),
            top_rgb=PALETTE["accent_light"],
            bot_rgb=PALETTE["accent_deep"],
        )
        # Subtle bright cap highlight at the top of each bar.
        draw = ImageDraw.Draw(canvas)
        cap_h = min(bh * 0.25, bar_w * 0.9)
        draw.rounded_rectangle(
            [s(bx0), s(by0), s(bx1), s(by0 + cap_h)],
            radius=s(bar_w * 0.42),
            fill=(*PALETTE["accent_light"], 235),
        )
        _ = mid_y  # kept for clarity

    # Tiny glowing power LED centered just below the display bezel.
    led_cx = cx
    led_cy = disp_y1 + (body_y1 - rail_margin_y - rail_h - disp_y1) * 0.50
    canvas = add_radial_glow(
        canvas,
        cx_1x=led_cx,
        cy_1x=led_cy,
        rx_1x=7.5,
        ry_1x=7.5,
        color_rgb=PALETTE["accent_blue"],
        alpha_peak=195,
        blur_1x=3.8,
    )
    draw = ImageDraw.Draw(canvas)
    led_r = 2.4
    draw.ellipse(
        [s(led_cx - led_r), s(led_cy - led_r), s(led_cx + led_r), s(led_cy + led_r)],
        fill=(*PALETTE["accent_light"], 255),
    )

    # --- 6. Centered title + non-overlap validation ---
    title_bbox = draw_centered_title(
        canvas,
        TITLE,
        w_1x=w_1x,
        top_y_1x=spec["title_y"],
        font_size_1x=spec["font_size"],
    )
    art_bbox = (body_x0, art_y0, body_x1, art_y1)
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
    """Generate all 3 Media Speaker store thumbnails and return their paths."""
    written: list[Path] = []
    for w, h in SIZES:
        canvas = render_media_speaker(w, h)
        out_path = out_dir / f"{FILE_PREFIX}_{w}x{h}.png"
        finalize_and_save(canvas, out_path, (w, h))
        written.append(out_path)
    return written


def main() -> None:
    out_dir = parse_cli_args("Generate Media Speaker store thumbnails.")
    paths = generate_all(out_dir)
    for p in paths:
        print(f"Generated: {p}")


if __name__ == "__main__":
    main()
