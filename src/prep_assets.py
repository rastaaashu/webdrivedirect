"""Prep image assets: crop QR from business card, optimize images, generate webp."""
from PIL import Image, ImageFilter
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST_IMG = os.path.join(ROOT, "dist", "assets", "img")
os.makedirs(DIST_IMG, exist_ok=True)


def find_qr_bbox(img):
    """Find white square (QR background) in top-right region of business card."""
    w, h = img.size
    # QR is in top-right quadrant of business card
    search = img.crop((int(w * 0.65), 0, w, int(h * 0.55))).convert("L")
    sw, sh = search.size
    px = search.load()
    # Find bright pixels (white card area)
    threshold = 230
    rows_with_white = []
    cols_with_white = []
    for y in range(sh):
        white_count = sum(1 for x in range(sw) if px[x, y] >= threshold)
        if white_count > sw * 0.3:
            rows_with_white.append(y)
    for x in range(sw):
        white_count = sum(1 for y in range(sh) if px[x, y] >= threshold)
        if white_count > sh * 0.3:
            cols_with_white.append(x)
    if not rows_with_white or not cols_with_white:
        return None
    top = min(rows_with_white)
    bottom = max(rows_with_white)
    left = min(cols_with_white)
    right = max(cols_with_white)
    # Translate back to full image coords
    offset_x = int(w * 0.65)
    return (left + offset_x, top, right + offset_x, bottom)


def crop_qr():
    src = os.path.join(ROOT, "drivdd.jpg")
    img = Image.open(src)
    print(f"Source: {img.size}")
    # The QR's white card has roughly equal width and height.
    # Auto-detected left/top/right are good; bottom drifts into other white text below.
    # Constrain by treating it as a square anchored at detected top-left.
    bbox = find_qr_bbox(img)
    print(f"Detected raw bbox: {bbox}")
    if bbox:
        l, t, r, _ = bbox
        side = r - l
        b = t + side  # square
        pad = 4
        l = max(0, l - pad)
        t = max(0, t - pad)
        r = min(img.size[0], r + pad)
        b = min(img.size[1], b + pad)
        qr = img.crop((l, t, r, b))
        print(f"Tightened bbox: ({l},{t},{r},{b}) size={qr.size}")
    else:
        # Fallback to manual crop tuned for 1280x853 source
        qr = img.crop((1006, 105, 1240, 339))
    # Make square by padding to longest side
    sz = max(qr.size)
    square = Image.new("RGB", (sz, sz), (255, 255, 255))
    square.paste(qr, ((sz - qr.size[0]) // 2, (sz - qr.size[1]) // 2))
    # Upscale to 1024 with sharp resampling
    square = square.resize((1024, 1024), Image.LANCZOS)
    out = os.path.join(DIST_IMG, "qr.png")
    square.save(out, "PNG", optimize=True)
    print(f"QR -> {out} ({square.size})")
    # Also webp
    square.save(os.path.join(DIST_IMG, "qr.webp"), "WEBP", quality=95)


def optimize_hero():
    """Save the full business card at multiple sizes for srcset (mobile perf)."""
    src = os.path.join(ROOT, "drivdd.jpg")
    img = Image.open(src)
    # Multiple sizes: 1280 (full), 1024 (default), 640 (mobile)
    targets = [1280, 1024, 640]
    for w in targets:
        h = int(img.size[1] * (w / img.size[0]))
        resized = img if w == img.size[0] else img.resize((w, h), Image.LANCZOS)
        resized.save(os.path.join(DIST_IMG, f"poster-card-{w}.jpg"),
                     "JPEG", quality=88, optimize=True, progressive=True)
        resized.save(os.path.join(DIST_IMG, f"poster-card-{w}.webp"),
                     "WEBP", quality=85, method=6)
        print(f"Poster card {w}x{h}: jpg/webp")


def optimize_hero_logo():
    src = os.path.join(ROOT, "photo_2026-05-06_08-04-59.jpg")
    img = Image.open(src)
    img.save(os.path.join(DIST_IMG, "logo-poster.jpg"), "JPEG", quality=92, optimize=True)
    img.save(os.path.join(DIST_IMG, "logo-poster.webp"), "WEBP", quality=90)
    # Crop just the logo region for hero use (top-center area)
    w, h = img.size
    # Logo+text takes roughly upper-center area
    logo_crop = img.crop((int(w * 0.18), int(h * 0.05), int(w * 0.82), int(h * 0.6)))
    logo_crop.save(os.path.join(DIST_IMG, "logo-text.jpg"), "JPEG", quality=92, optimize=True)
    logo_crop.save(os.path.join(DIST_IMG, "logo-text.webp"), "WEBP", quality=90)
    print(f"Logo poster saved: {img.size}, cropped logo: {logo_crop.size}")


def crop_car_from_card():
    """Try to extract just the Hyundai Ioniq 5 from the business card for hero use."""
    src = os.path.join(ROOT, "drivdd.jpg")
    img = Image.open(src)
    w, h = img.size
    # Car is roughly in the middle-right of the business card image
    # Card is 1280x853. Car appears center-right, mid-vertical
    car = img.crop((int(w * 0.32), int(h * 0.18), int(w * 0.78), int(h * 0.85)))
    car.save(os.path.join(DIST_IMG, "car-hero.jpg"), "JPEG", quality=94, optimize=True)
    car.save(os.path.join(DIST_IMG, "car-hero.webp"), "WEBP", quality=92)
    print(f"Car crop saved: {car.size}")


def crop_skyline():
    src = os.path.join(ROOT, "drivdd.jpg")
    img = Image.open(src)
    w, h = img.size
    # Skyline is upper portion behind car, roughly center
    sky = img.crop((int(w * 0.25), 0, int(w * 0.95), int(h * 0.6)))
    sky.save(os.path.join(DIST_IMG, "skyline.jpg"), "JPEG", quality=90, optimize=True)
    sky.save(os.path.join(DIST_IMG, "skyline.webp"), "WEBP", quality=88)
    print(f"Skyline crop saved: {sky.size}")


if __name__ == "__main__":
    crop_qr()
    optimize_hero()
    optimize_hero_logo()
    crop_car_from_card()
    crop_skyline()
    print("Done.")
