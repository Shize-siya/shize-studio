# -*- coding: utf-8 -*-
"""把 shize-studio 打包成可上传资料库的 dist/（index.html + 压缩后的动图）。

原始 GIF 全部保留不动；dist/ 里只放被 index.html 引用到的素材：
- 引用到的 .gif 转成动图 WebP（体积约为 GIF 的 1/5），增量进行，
  源文件没变就复用上次的转换结果；
- 引用到的其他资源（如 og-cover.jpg）原样拷贝。
"""
import os
import re
import shutil
import sys
import time

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_HTML = os.path.join(ROOT, "index.html")
DIST = os.path.join(ROOT, "dist")
DIST_ASSETS = os.path.join(DIST, "assets")
QUALITY = 80
METHOD = 6


def convert(src: str, dst: str) -> None:
    im = Image.open(src)
    transparent = "transparency" in im.info
    frames = []
    for i in range(getattr(im, "n_frames", 1)):
        im.seek(i)
        frames.append(im.convert("RGBA" if transparent else "RGB"))
    frames[0].save(
        dst,
        save_all=True,
        append_images=frames[1:],
        format="WEBP",
        quality=QUALITY,
        method=METHOD,
        duration=im.info.get("duration", 100),
        loop=0,
    )


def main() -> int:
    html = open(SRC_HTML, encoding="utf-8").read()
    gif_refs = sorted(set(re.findall(r"assets/[A-Za-z0-9_\-]+\.gif", html)))
    other_refs = sorted(set(
        m for m in re.findall(r"assets/[A-Za-z0-9_\-]+\.[A-Za-z0-9]{2,5}", html)
        if not m.endswith(".gif")
    ))
    if not gif_refs:
        print("no gif referenced", file=sys.stderr)
        return 1

    os.makedirs(DIST_ASSETS, exist_ok=True)

    t0 = time.time()
    src_bytes = dst_bytes = 0
    converted = reused = 0
    for k, rel in enumerate(gif_refs, 1):
        src = os.path.join(ROOT, rel)
        dst = os.path.join(DIST_ASSETS, os.path.basename(rel).rsplit(".", 1)[0] + ".webp")
        if os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(src):
            reused += 1
        else:
            convert(src, dst)
            converted += 1
            print("[%2d/%d] %-14s %6.2fMB -> %5.2fMB" % (
                k, len(gif_refs), os.path.basename(rel),
                os.path.getsize(src) / 1048576, os.path.getsize(dst) / 1048576), flush=True)
        src_bytes += os.path.getsize(src)
        dst_bytes += os.path.getsize(dst)

    for rel in other_refs:
        src = os.path.join(ROOT, rel)
        if not os.path.exists(src):
            print("!! 引用的资源不存在: " + rel, file=sys.stderr)
            continue
        shutil.copy2(src, os.path.join(DIST, rel))

    for rel in gif_refs + other_refs:
        html = html.replace(rel, rel.rsplit(".", 1)[0] + ".webp" if rel.endswith(".gif") else rel)
    with open(os.path.join(DIST, "index.html"), "w", encoding="utf-8", newline="") as f:
        f.write(html)

    total = sum(os.path.getsize(os.path.join(dp, f))
                for dp, _, fs in os.walk(DIST) for f in fs)
    print("=" * 46)
    print("动图 %d 个（新转 %d，复用 %d）：%.1fMB -> %.1fMB（%.1f 倍）" % (
        len(gif_refs), converted, reused, src_bytes / 1048576, dst_bytes / 1048576,
        src_bytes / max(dst_bytes, 1)))
    print("其他资源 %d 个：%s" % (len(other_refs), ", ".join(other_refs) or "无"))
    print("dist 总大小：%.1f MB  用时 %.0fs" % (total / 1048576, time.time() - t0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
