"""Generate a professional S3 Manager Pro icon.

Design: Blue gradient circle with a white cloud/bucket symbol and download arrow.
"""
from PIL import Image, ImageDraw, ImageFont
import os


def generate_pro_icon():
    """Generate a professional 256x256 icon."""
    size = 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background: rounded square with gradient-like effect
    # Outer shadow
    draw.rounded_rectangle([6, 6, size-6, size-6], radius=40, fill="#064273")
    # Main background
    draw.rounded_rectangle([8, 8, size-8, size-8], radius=38, fill="#0984e3")
    # Inner highlight (top)
    draw.rounded_rectangle([12, 12, size-12, size//2], radius=34, fill="#3da2f2")

    # Draw a bucket shape (trapezoid)
    bucket_points = [
        (80, 95),   # top-left
        (176, 95),  # top-right
        (166, 175), # bottom-right
        (90, 175),  # bottom-left
    ]
    draw.polygon(bucket_points, fill="#ffffff")

    # Bucket rim (top bar)
    draw.rounded_rectangle([72, 85, 184, 100], radius=4, fill="#ffffff")

    # Bucket handle (arc on top)
    draw.arc([105, 55, 151, 95], start=180, end=0, fill="#ffffff", width=6)

    # Download arrow in the bucket
    # Arrow body (vertical line)
    draw.rectangle([123, 110, 133, 150], fill="#0984e3")
    # Arrow head (triangle pointing down)
    arrow_head = [(108, 145), (148, 145), (128, 170)]
    draw.polygon(arrow_head, fill="#0984e3")

    # Small cloud shape on top-right
    draw.ellipse([155, 50, 195, 80], fill="#ffffff")
    draw.ellipse([170, 45, 210, 75], fill="#ffffff")
    draw.ellipse([185, 55, 215, 80], fill="#ffffff")
    draw.rectangle([160, 65, 210, 80], fill="#ffffff")

    # "PRO" badge bottom-right
    draw.rounded_rectangle([170, 185, 235, 210], radius=8, fill="#00c853")
    try:
        font_small = ImageFont.truetype("segoeui.ttf", 16)
    except (OSError, IOError):
        try:
            font_small = ImageFont.truetype("arial.ttf", 16)
        except (OSError, IOError):
            font_small = ImageFont.load_default()

    draw.text((182, 188), "PRO", fill="#ffffff", font=font_small)

    # Save as .ico with multiple sizes
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_icon.ico")

    sizes_list = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    imgs = [img.resize(s, Image.LANCZOS) for s in sizes_list]

    imgs[0].save(icon_path, format="ICO", sizes=sizes_list, append_images=imgs[1:])

    # Also save as PNG for GitHub/README
    png_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_icon.png")
    img.save(png_path, format="PNG")

    print(f"Icon saved: {icon_path}")
    print(f"PNG saved: {png_path}")
    return icon_path


if __name__ == "__main__":
    generate_pro_icon()
