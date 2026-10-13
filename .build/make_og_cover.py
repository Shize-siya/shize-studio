# -*- coding: utf-8 -*-
"""生成分享预览图 assets/og-cover.jpg（1200x630）。

素材都是 426x240 的录屏帧，这里取 6 张拼成 3x2 的墙，配上字标。
用于链接分享时各平台的卡片预览（og:image / twitter:image）。
"""
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "og-cover.jpg")

W, H = 1200, 630
BG = (5, 7, 10)
ACCENT = (58, 217, 255)
INK = (230, 241, 247)
DIM = (107, 124, 136)

TITLE_H = 146
MARGIN = 24
GAP = 16
COLS, ROWS = 3, 2

PICKS = [
    ("fps-08.gif", 0.45), ("fps-01.gif", 0.40), ("act-20.gif", 0.50),
    ("act-22.gif", 0.35), ("act-09.gif", 0.45), ("fps-03.gif", 0.40),
]

FONT_BOLD = [r"C:\Windows\Fonts\segoeuib.ttf", r"C:\Windows\Fonts\arialbd.ttf"]
FONT_CJK = [r"C:\Windows\Fonts\msyhbd.ttc", r"C:\Windows\Fonts\msyh.ttc",
            r"C:\Windows\Fonts\simhei.ttf"]


def pick_font(candidates, size):
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                continue
    return ImageFont.load_default()


def frame_at(path, frac):
    im = Image.open(path)
    n = getattr(im, "n_frames", 1)
    im.seek(min(n - 1, max(0, int(n * frac))))
    return im.convert("RGB")


def main():
    canvas = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(canvas)

    # 标题
    f_main = pick_font(FONT_BOLD, 54)
    f_sub = pick_font(FONT_CJK, 23)
    d.text((MARGIN + 6, 34), "SHIZE", font=f_main, fill=INK)
    w_shize = d.textlength("SHIZE ", font=f_main)
    d.text((MARGIN + 6 + w_shize, 34), "STUDIO", font=f_main, fill=ACCENT)
    d.text((MARGIN + 6, 100), "虚幻引擎 5 · 游戏功能演示", font=f_sub, fill=DIM)

    # 右上角准星标记
    cx, cy, r = W - MARGIN - 30, 60, 22
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(58, 217, 255, 255), width=3)
    for x0, y0, x1, y1 in [(cx, cy - r - 12, cx, cy - r + 4), (cx, cy + r - 4, cx, cy + r + 12),
                           (cx - r - 12, cy, cx - r + 4, cy), (cx + r - 4, cy, cx + r + 12, cy)]:
        d.line([x0, y0, x1, y1], fill=ACCENT, width=3)

    # 缩略图墙
    cell_w = (W - MARGIN * 2 - GAP * (COLS - 1)) // COLS
    cell_h = (H - TITLE_H - MARGIN - GAP * (ROWS - 1)) // ROWS

    for i, (name, frac) in enumerate(PICKS[:COLS * ROWS]):
        path = os.path.join(ROOT, "assets", name)
        if not os.path.exists(path):
            continue
        r, c = divmod(i, COLS)
        x = MARGIN + c * (cell_w + GAP)
        y = TITLE_H + r * (cell_h + GAP)
        # 铺满裁切（源为 16:9，格子也按接近 16:9 估）
        im = frame_at(path, frac)
        scale = max(cell_w / im.width, cell_h / im.height)
        im = im.resize((max(1, round(im.width * scale)), max(1, round(im.height * scale))), Image.LANCZOS)
        left = (im.width - cell_w) // 2
        top = (im.height - cell_h) // 2
        canvas.paste(im.crop((left, top, left + cell_w, top + cell_h)), (x, y))
        d.rectangle([x - 1, y - 1, x + cell_w, y + cell_h], outline=(58, 217, 255, 60), width=1)

    canvas.save(OUT, "JPEG", quality=86, optimize=True, progressive=True)
    print("og-cover: %dx%d  %.0f KB" % (W, H, os.path.getsize(OUT) / 1024))


if __name__ == "__main__":
    main()
