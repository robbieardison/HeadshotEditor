#!/usr/bin/env python3
"""
HeadshotEditor — Python-only pipeline: rembg matting + circular plate compositing
(same layout defaults as the web compositor). No server or frontend required.

Example:
  python headshot_cli.py -i ~/Photos/portrait.jpg
  python headshot_cli.py -i ./in.png -o ./out.png --bg-color "#1a4d8c"
"""

from __future__ import annotations

import argparse
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter
from rembg import remove


def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.strip().lstrip("#")
    if len(h) != 6:
        raise ValueError(f"Expected #RRGGBB, got {h!r}")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def composite(
    cutout: Image.Image,
    *,
    size: int = 800,
    bg_color: str = "#2d6cdf",
    circle_radius_pct: float = 28.0,
    circle_center_y: float = 0.62,
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
    cy = h * circle_center_y
    r = min(w, h) * circle_radius_pct / 100.0

    if plate_opacity > 0:
        shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        dr = ImageDraw.Draw(shadow)
        dr.ellipse(
            [
                cx - r + plate_off_x,
                cy - r + plate_off_y,
                cx + r + plate_off_x,
                cy + r + plate_off_y,
            ],
            fill=(0, 0, 0, 255),
        )
        alpha = shadow.split()[3]
        shadow.putalpha(alpha.point(lambda p: int(p * plate_opacity)))
        blur_r = max(0.5, plate_blur / 2.0)
        shadow = shadow.filter(ImageFilter.GaussianBlur(radius=blur_r))
        out = Image.alpha_composite(out, shadow)

    plate = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    pd = ImageDraw.Draw(plate)
    rgb = hex_to_rgb(bg_color)
    pd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*rgb, 255))
    out = Image.alpha_composite(out, plate)

    cutout = cutout.convert("RGBA")
    iw, ih = cutout.size
    base_w = w * 0.58 * subject_scale
    draw_w = max(1, int(round(base_w)))
    draw_h = max(1, int(round(draw_w * ih / iw)))
    resized = cutout.resize((draw_w, draw_h), Image.Resampling.LANCZOS)
    draw_x = int(round(cx - draw_w / 2))
    draw_y = int(round(cy + r * 0.42 - draw_h + subject_y_offset))

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
    p.add_argument("--bg-color", default="#2d6cdf", help="Plate fill color #RRGGBB.")
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
        help="Vertical position of circle center (0–1).",
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
        bg_color=args.bg_color,
        circle_radius_pct=args.circle_radius_pct,
        circle_center_y=args.circle_center_y,
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
