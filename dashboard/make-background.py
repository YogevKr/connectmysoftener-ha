"""Generate the blurred water backgrounds used by the Softener dashboard.

Run it with:
    uv run --with pillow python dashboard/make-background.py

Then copy a result to `config/www/` and point the dashboard `background:` at it,
for example `url("/local/softener-bg.jpg")`. Keep the aspect ratio 16:9.
"""

from __future__ import annotations

from PIL import Image, ImageChops, ImageDraw, ImageFilter

WIDTH, HEIGHT = 1920, 1080

VARIANTS = {
    "deep-sea": (
        ((4, 10, 16), (7, 24, 33)),
        (
            (0.34, 0.44, 560, (0, 120, 165), 0.70),
            (0.76, 0.68, 480, (0, 150, 150), 0.35),
            (0.58, 0.16, 660, (14, 52, 88), 0.45),
        ),
    ),
    "teal": (
        ((5, 11, 15), (8, 26, 28)),
        (
            (0.66, 0.40, 540, (0, 140, 150), 0.62),
            (0.22, 0.72, 520, (70, 130, 90), 0.30),
            (0.44, 0.90, 520, (12, 70, 110), 0.45),
        ),
    ),
    "ocean-bright": (
        ((5, 16, 26), (10, 38, 54)),
        (
            (0.30, 0.42, 620, (0, 150, 205), 0.85),
            (0.78, 0.72, 520, (0, 205, 200), 0.45),
            (0.55, 0.20, 700, (20, 70, 120), 0.55),
        ),
    ),
}


def gradient(top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    """Return a vertical gradient."""
    image = Image.new("RGB", (WIDTH, HEIGHT), top)
    draw = ImageDraw.Draw(image)
    for y in range(HEIGHT):
        ratio = y / HEIGHT
        draw.line(
            [(0, y), (WIDTH, y)],
            fill=tuple(int(top[i] + (bottom[i] - top[i]) * ratio) for i in range(3)),
        )
    return image


def add_glow(
    image: Image.Image,
    x: float,
    y: float,
    radius: float,
    color: tuple[int, int, int],
    strength: float,
) -> Image.Image:
    """Add one soft radial glow."""
    layer = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
    draw = ImageDraw.Draw(layer)
    box = (x * WIDTH - radius, y * HEIGHT - radius, x * WIDTH + radius, y * HEIGHT + radius)
    draw.ellipse(box, fill=tuple(int(channel * strength) for channel in color))
    return ImageChops.add(image, layer.filter(ImageFilter.GaussianBlur(radius * 0.5)))


def finish(image: Image.Image, vignette: float = 0.62) -> Image.Image:
    """Blur the whole image and darken the corners."""
    image = image.filter(ImageFilter.GaussianBlur(42))
    mask = Image.new("L", (WIDTH, HEIGHT), 0)
    ImageDraw.Draw(mask).ellipse(
        (-WIDTH * 0.28, -HEIGHT * 0.40, WIDTH * 1.28, HEIGHT * 1.40), fill=255
    )
    mask = mask.filter(ImageFilter.GaussianBlur(240))
    dark = Image.blend(image, Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0)), vignette)
    return Image.composite(image, dark, mask)


def main() -> None:
    """Write every variant to the current directory."""
    for name, (colors, glows) in VARIANTS.items():
        image = gradient(*colors)
        for x, y, radius, color, strength in glows:
            image = add_glow(image, x, y, radius, color, strength)
        path = f"background-{name}.jpg"
        finish(image).save(path, quality=88, optimize=True)
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
