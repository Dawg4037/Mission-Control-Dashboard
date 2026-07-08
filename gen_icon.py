#!/usr/bin/env python3
"""Generates mission_control.ico (used by make_desktop_shortcut.bat).
Only needed if you cloned this repo without the .ico file.
Requires: pip install pillow
"""
import random
from PIL import Image, ImageDraw


def make(size):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size
    d.ellipse([s * 0.02] * 2 + [s * 0.98] * 2, fill=(6, 12, 26, 255),
              outline=(27, 58, 92, 255), width=max(1, s // 64))
    random.seed(7)
    for _ in range(int(s * s / 300)):
        x, y = random.uniform(s * 0.1, s * 0.9), random.uniform(s * 0.1, s * 0.9)
        if (x - s / 2) ** 2 + (y - s / 2) ** 2 < (s * 0.45) ** 2:
            r = random.uniform(0.5, s / 90)
            d.ellipse([x - r, y - r, x + r, y + r],
                      fill=(159, 216, 232, random.randint(120, 255)))
    d.ellipse([s * 0.13, s * 0.40, s * 0.87, s * 0.72],
              outline=(79, 216, 235, 220), width=max(1, s // 40))
    d.ellipse([s * 0.30, s * 0.30, s * 0.70, s * 0.70], fill=(18, 40, 63, 255),
              outline=(79, 216, 235, 255), width=max(1, s // 32))
    d.arc([s * 0.32, s * 0.42, s * 0.68, s * 0.58], 200, 340,
          fill=(255, 179, 71, 255), width=max(1, s // 40))
    cx, cy, r = s * 0.87, s * 0.56, s * 0.07
    d.polygon([(cx, cy - r), (cx - r * .7, cy + r * .8), (cx + r * .7, cy + r * .8)],
              fill=(255, 179, 71, 255))
    return img


sizes = [16, 24, 32, 48, 64, 128, 256]
imgs = [make(z) for z in sizes]
imgs[-1].save("mission_control.ico", format="ICO",
              sizes=[(z, z) for z in sizes], append_images=imgs[:-1])
print("mission_control.ico written")
