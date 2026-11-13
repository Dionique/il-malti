#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Нарисовать иконки приложения (icon-192.png, icon-512.png).

Иконка нужна для установки на телефон и компьютер (REQ-OFFLINE-02). Цвета
взяты из styles.css, чтобы иконка совпадала с шапкой приложения.

    python3 tools/make_icons.py
"""

import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ACCENT = (200, 16, 46)      # --accent: #c8102e
ACCENT_DARK = (122, 10, 28)  # второй конец градиента в шапке
WHITE = (255, 255, 255)

# системные шрифты macOS; если не найдётся — возьмём встроенный
FONTS = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/Library/Fonts/Arial Bold.ttf",
]


def load_font(size):
    for path in FONTS:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def make(size):
    img = Image.new("RGB", (size, size), ACCENT)
    draw = ImageDraw.Draw(img)

    # диагональный градиент, как у логотипа в шапке
    for i in range(size):
        k = i / float(size - 1)
        color = tuple(int(ACCENT[c] + (ACCENT_DARK[c] - ACCENT[c]) * k) for c in range(3))
        draw.line([(0, i), (size, i)], fill=color)

    font = load_font(int(size * 0.42))
    text = "MT"
    box = draw.textbbox((0, 0), text, font=font)
    draw.text(((size - (box[2] - box[0])) / 2 - box[0],
               (size - (box[3] - box[1])) / 2 - box[1]),
              text, font=font, fill=WHITE)
    return img


def main():
    for size in (192, 512):
        path = os.path.join(ROOT, "icon-%d.png" % size)
        make(size).save(path, "PNG", optimize=True)
        print("  записано %s (%d КБ)" % (os.path.relpath(path, ROOT),
                                         os.path.getsize(path) // 1024))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
