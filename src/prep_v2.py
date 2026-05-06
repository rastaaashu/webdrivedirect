"""Prep real assets: extract DD logo, resize car photos, resize skyline, generate webp."""
from PIL import Image, ImageFilter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMG_DIR = ROOT / "dist" / "assets" / "img"
LOGO_SRC = ROOT / "photo_2026-05-06_08-04-59.jpg"

WIDTHS = (640, 1024, 1600)


def save_variants(img: Image.Image, basename: str, widths=WIDTHS, quality=82):
    out = []
    for w in widths:
        ratio = w / img.width
        h = int(img.height * ratio)
        resized = img.resize((w, h), Image.LANCZOS)
        rgb = resized.convert("RGB") if resized.mode != "RGB" else resized
        jp = IMG_DIR / f"{basename}-{w}.jpg"
        rgb.save(jp, "JPEG", quality=quality, optimize=True, progressive=True)
        wp = IMG_DIR / f"{basename}-{w}.webp"
        rgb.save(wp, "WEBP", quality=quality, method=6)
        out.append((w, jp.stat().st_size, wp.stat().st_size))
    return out


def extract_logo():
    """Crop the DD + wordmark from the brand poster, preserving the dark hex texture
    (it blends with the nav background)."""
    src = Image.open(LOGO_SRC)
    W, H = src.size  # 1280x853
    # The logo lockup (DD mark + DRIVE DIRECT wordmark) occupies roughly x=270..990, y=60..420
    logo = src.crop((270, 60, 990, 420))
    # Save full lockup
    logo.save(IMG_DIR / "logo-lockup.png", "PNG")
    # Just the DD mark for favicon / app icon use
    dd = src.crop((480, 60, 770, 290))
    dd.save(IMG_DIR / "logo-dd.png", "PNG")
    # Wordmark only
    wm = src.crop((280, 280, 985, 410))
    wm.save(IMG_DIR / "logo-wordmark.png", "PNG")
    return logo.size, dd.size, wm.size


def prep_cars():
    # Lucid Blue: original is 3918x2938. Crop tighter so the car fills frame.
    lb = Image.open(IMG_DIR / "ioniq5-lucidblue-original.jpg")
    # crop to ~16:9 centered on the car
    W, H = lb.size
    aspect = 16 / 9
    new_h = int(W / aspect)
    if new_h <= H:
        top = (H - new_h) // 2
        lb_crop = lb.crop((0, top, W, top + new_h))
    else:
        new_w = int(H * aspect)
        left = (W - new_w) // 2
        lb_crop = lb.crop((left, 0, left + new_w, H))
    save_variants(lb_crop, "car-hero", quality=85)

    # About-section variant: same image, slightly tighter crop
    save_variants(lb_crop, "car-about", quality=85)


def prep_skyline():
    sk = Image.open(IMG_DIR / "la-skyline-original.jpg")
    # 2846x1601 — wide. Keep aspect, just resize.
    save_variants(sk, "la-skyline", quality=80)


if __name__ == "__main__":
    print("[1/3] extracting logo...")
    sizes = extract_logo()
    print(f"  lockup={sizes[0]}, dd={sizes[1]}, wordmark={sizes[2]}")

    print("[2/3] prepping car photos...")
    prep_cars()

    print("[3/3] prepping skyline...")
    prep_skyline()

    print("\ndone. files in", IMG_DIR)
