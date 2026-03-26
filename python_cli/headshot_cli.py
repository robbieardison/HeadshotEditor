#!/usr/bin/env python3
"""
HeadshotEditor — Python-only pipeline: rembg matting + circular plate compositing
(same layout defaults as the web compositor). No server or frontend required.

Example:
  python headshot_cli.py -i ~/Photos/portrait.jpg
  python headshot_cli.py -i ./in.png -o ./out.png --bg-color "#1a4d8c"
  python headshot_cli.py -i ./in.png --plate-fill linear --gradient-angle 90
"""

from __future__ import annotations

import argparse
import math
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from rembg import remove


def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.strip().lstrip("#")
    if len(h) != 6:
        raise ValueError(f"Expected #RRGGBB, got {h!r}")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def make_plate_layer(
    w: int,
    h: int,
    cx: float,
    cy: float,
    r: float,
    plate_fill: str,
    bg_color: str,
    bg_color_2: str,
    gradient_angle_deg: float,
) -> Image.Image:
    """Solid fill or polarized linear/radial gradient inside the circle (matches web UI)."""
    rgb1 = hex_to_rgb(bg_color)
    rgb2 = hex_to_rgb(bg_color_2)
    if plate_fill == "solid":
        plate = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        pd = ImageDraw.Draw(plate)
        pd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*rgb1, 255))
        return plate

    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    mask = dist <= r

    if plate_fill == "radial":
        t = np.zeros_like(dist)
        inside = mask & (dist > 1e-9)
        t[inside] = np.clip(dist[inside] / r, 0.0, 1.0)
        rch = rgb1[0] + (rgb2[0] - rgb1[0]) * t
        gch = rgb1[1] + (rgb2[1] - rgb1[1]) * t
        bch = rgb1[2] + (rgb2[2] - rgb1[2]) * t
    elif plate_fill == "linear":
        rad = math.radians(gradient_angle_deg)
        x1 = cx + math.cos(rad) * r
        y1 = cy + math.sin(rad) * r
        x2 = cx - math.cos(rad) * r
        y2 = cy - math.sin(rad) * r
        vx, vy = x1 - x2, y1 - y2
        l2 = vx * vx + vy * vy
        if l2 < 1e-12:
            l2 = 1.0
        t = ((xx - x2) * vx + (yy - y2) * vy) / l2
        t = np.clip(t, 0.0, 1.0)
        rch = rgb1[0] + (rgb2[0] - rgb1[0]) * t
        gch = rgb1[1] + (rgb2[1] - rgb1[1]) * t
        bch = rgb1[2] + (rgb2[2] - rgb1[2]) * t
    else:
        raise ValueError(f"Unknown plate_fill: {plate_fill!r}")

    alpha = np.where(mask, 255, 0).astype(np.uint8)
    rgba = np.stack(
        [
            np.clip(rch, 0, 255),
            np.clip(gch, 0, 255),
            np.clip(bch, 0, 255),
            alpha.astype(np.float64),
        ],
        axis=-1,
    ).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


def composite(
    cutout: Image.Image,
    *,
    size: int = 800,
    plate_enabled: bool = True,
    bg_color: str = "#2d6cdf",
    bg_color_2: str = "#38bdf8",
    plate_fill: str = "solid",
    gradient_angle_deg: float = 135.0,
    circle_radius_pct: float = 28.0,
    circle_center_y: float = 0.62,
    subject_center_y: float = 0.62,
    subject_scale: float = 1.05,
    subject_y_offset: float = 0.0,
    plate_blur: float = 28.0,
    plate_off_x: float = 0.0,
    plate_off_y: float = 14.0,
    plate_opacity: float = 0.35,
    sub_blur: float = 18.0,
    sub_off_x: float = 0.0,
    sub_off_y: float = 10.0,
    sub_opacity: float = 0.28,
) -> Image.Image:
    """Mirror the browser canvas layout in HeadshotCompositor.tsx."""
    w = h = size
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    cx = w / 2
    cy_plate = h * circle_center_y
    subject_cy = h * subject_center_y
    r = min(w, h) * circle_radius_pct / 100.0

    if plate_enabled:
        if plate_opacity > 0:
            shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            dr = ImageDraw.Draw(shadow)
            dr.ellipse(
                [
                    cx - r + plate_off_x,
                    cy_plate - r + plate_off_y,
                    cx + r + plate_off_x,
                    cy_plate + r + plate_off_y,
                ],
                fill=(0, 0, 0, 255),
            )
            alpha = shadow.split()[3]
            shadow.putalpha(alpha.point(lambda p: int(p * plate_opacity)))
            blur_r = max(0.5, plate_blur / 2.0)
            shadow = shadow.filter(ImageFilter.GaussianBlur(radius=blur_r))
            out = Image.alpha_composite(out, shadow)

        plate = make_plate_layer(
            w, h, cx, cy_plate, r, plate_fill, bg_color, bg_color_2, gradient_angle_deg
        )
        out = Image.alpha_composite(out, plate)

    cutout = cutout.convert("RGBA")
    iw, ih = cutout.size
    base_w = w * 0.58 * subject_scale
    draw_w = max(1, int(round(base_w)))
    draw_h = max(1, int(round(draw_w * ih / iw)))
    resized = cutout.resize((draw_w, draw_h), Image.Resampling.LANCZOS)
    draw_x = int(round(cx - draw_w / 2))
    draw_y = int(round(subject_cy + r * 0.42 - draw_h + subject_y_offset))

    if sub_opacity > 0:
        alpha = resized.split()[3]
        black = Image.new("RGBA", resized.size, (0, 0, 0, 255))
        black.putalpha(alpha.point(lambda p: int(p * sub_opacity)))
        sh = black.filter(ImageFilter.GaussianBlur(radius=max(0.5, sub_blur / 2.0)))
        sx = draw_x + int(sub_off_x)
        sy = draw_y + int(sub_off_y)
        out.paste(sh, (sx, sy), sh)

    out.paste(resized, (draw_x, draw_y), resized)
    return out


def default_output_path(input_path: Path) -> Path:
    return input_path.with_name(f"{input_path.stem}_headshot.png")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Remove background and composite onto a circular plate with shadows.",
    )
    p.add_argument(
        "-i",
        "--input",
        required=True,
        type=Path,
        help="Input image path (JPEG, PNG, WebP).",
    )
    p.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output PNG path. Default: <input_stem>_headshot.png next to the input file.",
    )
    p.add_argument("--size", type=int, default=800, help="Canvas size (square pixels).")
    p.add_argument(
        "--no-plate",
        action="store_true",
        help="Disable the circular plate (and its shadow).",
    )
    p.add_argument("--bg-color", default="#2d6cdf", help="Plate color A (or solid fill) #RRGGBB.")
    p.add_argument(
        "--bg-color-2",
        default="#38bdf8",
        help="Plate color B for polarized gradients #RRGGBB.",
    )
    p.add_argument(
        "--plate-fill",
        choices=("solid", "linear", "radial"),
        default="solid",
        help="Solid color or polarized linear/radial gradient on the circle.",
    )
    p.add_argument(
        "--gradient-angle",
        type=float,
        default=135.0,
        help="Linear gradient angle in degrees (0–360). Ignored for solid/radial.",
    )
    p.add_argument(
        "--circle-radius-pct",
        type=float,
        default=28.0,
        help="Circle radius as %% of min(canvas width, height).",
    )
    p.add_argument(
        "--circle-center-y",
        type=float,
        default=0.62,
        help="Vertical position of plate center (0–1). Does not move the subject.",
    )
    p.add_argument(
        "--subject-center-y",
        type=float,
        default=0.62,
        help="Vertical anchor for the subject (0–1). Independent of --circle-center-y.",
    )
    p.add_argument("--subject-scale", type=float, default=1.05)
    p.add_argument("--subject-y-offset", type=float, default=0.0)
    p.add_argument("--plate-blur", type=float, default=28.0)
    p.add_argument("--plate-off-x", type=float, default=0.0)
    p.add_argument("--plate-off-y", type=float, default=14.0)
    p.add_argument("--plate-opacity", type=float, default=0.35)
    p.add_argument("--sub-blur", type=float, default=18.0)
    p.add_argument("--sub-off-x", type=float, default=0.0)
    p.add_argument("--sub-off-y", type=float, default=10.0)
    p.add_argument("--sub-opacity", type=float, default=0.28)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    input_path: Path = args.input.expanduser().resolve()
    if not input_path.is_file():
        raise SystemExit(f"Input not found: {input_path}")

    output_path: Path
    if args.output is not None:
        output_path = args.output.expanduser().resolve()
    else:
        output_path = default_output_path(input_path)

    raw = input_path.read_bytes()
    cutout_bytes = remove(raw)
    cutout = Image.open(BytesIO(cutout_bytes)).convert("RGBA")

    result = composite(
        cutout,
        size=args.size,
        plate_enabled=not args.no_plate,
        bg_color=args.bg_color,
        bg_color_2=args.bg_color_2,
        plate_fill=args.plate_fill,
        gradient_angle_deg=args.gradient_angle,
        circle_radius_pct=args.circle_radius_pct,
        circle_center_y=args.circle_center_y,
        subject_center_y=args.subject_center_y,
        subject_scale=args.subject_scale,
        subject_y_offset=args.subject_y_offset,
        plate_blur=args.plate_blur,
        plate_off_x=args.plate_off_x,
        plate_off_y=args.plate_off_y,
        plate_opacity=args.plate_opacity,
        sub_blur=args.sub_blur,
        sub_off_x=args.sub_off_x,
        sub_off_y=args.sub_off_y,
        sub_opacity=args.sub_opacity,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.save(output_path, "PNG")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
