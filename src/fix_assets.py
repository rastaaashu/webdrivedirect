"""
fix_assets.py — fix the logo (transparent bg) and car (remove plate).

Logo: chroma-key out the dark business-card background while preserving
the white "D" and the blue "D".

Car: paint over the front license plate with bumper-matching gray so it
looks plateless.
"""

from pathlib import Path
from PIL import Image, ImageFilter
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DIST_IMG = ROOT / "dist" / "assets" / "img"


def remove_dark_bg(src: Path, out: Path) -> None:
    """Take a logo PNG with a near-black background and produce a
    transparent-background version. Soft alpha based on luminance, with
    a small boost for the brightly-colored foreground (white + blue)."""
    img = Image.open(src).convert("RGBA")
    arr = np.asarray(img).astype(np.float32)
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    # Luminance 0..255
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    # Saturation-ish: distance from grayscale
    mx = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    sat = mx - mn

    # Alpha: low-lum AND low-saturation = background -> transparent.
    # Otherwise keep. Soft transition between 18 and 64 luminance.
    alpha = np.clip((lum - 18) / 46.0, 0, 1)
    # Saturated colors (the blue D) keep full alpha even at lower lum
    alpha = np.maximum(alpha, np.clip((sat - 22) / 28.0, 0, 1))
    alpha = (alpha * 255).astype(np.uint8)

    # Slightly suppress remaining bg-tinted dark pixels by darkening shadows
    rgb = arr[..., :3].astype(np.uint8)
    out_arr = np.dstack([rgb, alpha])
    Image.fromarray(out_arr, "RGBA").save(out, "PNG", optimize=True)


def make_lockup(dd_path: Path, out: Path, target_w: int = 900) -> None:
    """Compose a clean transparent lockup: DD mark on top, DRIVE DIRECT
    wordmark below. Uses the cleaned DD as the mark; renders the wordmark
    as text via Pillow (no system font dependency hard requirement)."""
    from PIL import ImageDraw, ImageFont

    dd = Image.open(dd_path).convert("RGBA")
    # Resize DD mark
    mark_w = int(target_w * 0.42)
    ratio = mark_w / dd.width
    mark = dd.resize((mark_w, int(dd.height * ratio)), Image.LANCZOS)

    # Try to load a heavy sans font; fall back to default
    font_path = None
    for cand in [
        r"C:\Windows\Fonts\seguibl.ttf",   # Segoe UI Black
        r"C:\Windows\Fonts\arialbd.ttf",   # Arial Bold
        r"C:\Windows\Fonts\impact.ttf",
    ]:
        if Path(cand).exists():
            font_path = cand
            break

    word_font_size = int(target_w * 0.18)
    if font_path:
        font = ImageFont.truetype(font_path, word_font_size)
    else:
        font = ImageFont.load_default()

    # Measure wordmark text
    tmp = Image.new("RGBA", (10, 10))
    d = ImageDraw.Draw(tmp)
    full = "DRIVE DIRECT"
    bbox = d.textbbox((0, 0), full, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    pad = int(target_w * 0.04)
    canvas_h = mark.height + pad + th + pad
    canvas_w = max(target_w, tw + pad * 2)
    canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))

    # Paste DD mark centered
    canvas.paste(mark, ((canvas_w - mark.width) // 2, 0), mark)

    # Draw DRIVE in white, DIRECT in lucid blue, with a space between
    draw = ImageDraw.Draw(canvas)
    drive_w = draw.textbbox((0, 0), "DRIVE ", font=font)[2]
    direct_w = draw.textbbox((0, 0), "DIRECT", font=font)[2]
    total = drive_w + direct_w
    word_x = (canvas_w - total) // 2
    word_y = mark.height + pad - bbox[1]  # offset by ascent so glyphs sit nicely

    draw.text((word_x, word_y), "DRIVE", fill=(255, 255, 255, 255), font=font)
    draw.text((word_x + drive_w, word_y), "DIRECT", fill=(135, 166, 197, 255), font=font)

    canvas.save(out, "PNG", optimize=True)


def remove_plate(src: Path, out: Path) -> None:
    """Paint over the front license plate of the Ioniq 5 cutout.
    Uses a tight cyan/turquoise color match (the plate is much more
    saturated/cyan than the slate-blue body) restricted to the front-
    bumper region. Replaces matched pixels with the dark gray bumper
    color sampled just below the plate (lower bumper trim)."""
    img = Image.open(src).convert("RGBA")
    arr = np.array(img)
    rgba = arr.copy()
    rgb = arr[..., :3].astype(np.float32)
    a = arr[..., 3]
    h, w = a.shape

    r, g, bch = rgb[..., 0], rgb[..., 1], rgb[..., 2]

    # Plate cyan/turquoise: green and blue both significantly > red.
    # Body slate-blue: red, green, blue all closer together (delta small).
    # Use a tight chromaticity test that body cannot satisfy.
    plate = (
        (bch > r + 35)
        & (g > r + 25)
        & (bch > 110) & (bch < 240)
        & ((bch + g) / 2.0 - r > 30)
        & (a > 200)
    )

    # Hard-restrict to the lower-left front-bumper region of the car.
    band = np.zeros_like(plate)
    band[int(h * 0.60):int(h * 0.82), int(w * 0.05):int(w * 0.32)] = True
    plate &= band

    if plate.sum() < 80:
        Image.fromarray(rgba, "RGBA").save(out, "PNG", optimize=True)
        return

    ys, xs = np.where(plate)
    y0, y1 = int(ys.min()), int(ys.max())
    x0, x1 = int(xs.min()), int(xs.max())

    pad = max(3, int(min(h, w) * 0.005))
    y0 = max(0, y0 - pad); y1 = min(h - 1, y1 + pad)
    x0 = max(0, x0 - pad); x1 = min(w - 1, x1 + pad)

    # Sample bumper color from a strip directly *below* the plate
    # (the lower bumper trim is a clean dark gray).
    sy0 = min(h - 1, y1 + 4)
    sy1 = min(h - 1, y1 + 22)
    sample = rgba[sy0:sy1 + 1, x0:x1 + 1, :3]
    sample_a = rgba[sy0:sy1 + 1, x0:x1 + 1, 3]
    mask = sample_a > 200
    if mask.sum() < 10:
        bumper = np.array([60, 65, 72], dtype=np.uint8)
    else:
        bumper = sample[mask].mean(axis=0).astype(np.uint8)

    fill_h = y1 - y0 + 1
    fill_w = x1 - x0 + 1
    fill = np.zeros((fill_h, fill_w, 4), dtype=np.uint8)
    fill[..., :3] = bumper
    # Subtle vertical gradient for recess realism
    grad = np.linspace(-14, 10, fill_h, dtype=np.float32)[:, None]
    fill[..., :3] = np.clip(fill[..., :3].astype(np.float32) + grad[..., None], 0, 255).astype(np.uint8)
    fill[..., 3] = 255

    # Only replace pixels where the original was opaque AND looked like the plate
    region = rgba[y0:y1 + 1, x0:x1 + 1]
    sub_plate = plate[y0:y1 + 1, x0:x1 + 1]
    region_alpha = region[..., 3]
    place = sub_plate & (region_alpha > 200)
    # Dilate the plate mask so we cover any lingering halo around it
    from PIL import ImageFilter as _IF
    pmask = Image.fromarray((place.astype(np.uint8) * 255), "L")
    pmask = pmask.filter(_IF.MaxFilter(5))
    place = np.asarray(pmask) > 0
    region[place] = fill[place]
    rgba[y0:y1 + 1, x0:x1 + 1] = region

    out_img = Image.fromarray(rgba, "RGBA")
    # Light blur ONLY on the patched rectangle to blend edges
    patch = out_img.crop((x0, y0, x1 + 1, y1 + 1)).filter(ImageFilter.GaussianBlur(radius=0.8))
    out_img.paste(patch, (x0, y0))

    out_img.save(out, "PNG", optimize=True)


def regenerate_sizes(src_png: Path, base: str, sizes=(640, 1024, 1600, 2200)) -> None:
    """Regenerate the multi-resolution PNG + WEBP set for a cutout."""
    img = Image.open(src_png).convert("RGBA")
    for w in sizes:
        ratio = w / img.width
        h = int(img.height * ratio)
        resized = img.resize((w, h), Image.LANCZOS)
        png_path = DIST_IMG / f"{base}-{w}.png"
        webp_path = DIST_IMG / f"{base}-{w}.webp"
        resized.save(png_path, "PNG", optimize=True)
        resized.save(webp_path, "WEBP", quality=90, method=6)
        print(f"  wrote {png_path.name} + {webp_path.name}  ({w}x{h})")


def main() -> None:
    print("[1/3] Removing dark background from DD mark...")
    dd_clean = DIST_IMG / "logo-dd-clean.png"
    remove_dark_bg(DIST_IMG / "logo-dd.png", dd_clean)

    print("[2/3] Composing transparent lockup...")
    make_lockup(dd_clean, DIST_IMG / "logo-lockup.png", target_w=900)

    print("[3/3] Removing license plate from car cutout...")
    src_orig = DIST_IMG / "car-cutout-original.png"
    src_2200 = DIST_IMG / "car-cutout-2200.png"
    base_src = src_orig if src_orig.exists() else src_2200
    fixed = DIST_IMG / "car-cutout-fixed.png"
    remove_plate(base_src, fixed)
    regenerate_sizes(fixed, "car-cutout")
    print("Done.")


if __name__ == "__main__":
    main()
