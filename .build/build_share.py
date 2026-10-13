# -*- coding: utf-8 -*-
"""把 shize-studio 打包成可上传资料库的 dist/（index.html + 压缩后的动图）。

原始 GIF 全部保留不动；dist/ 里只放被 index.html 引用到的动图，
统一转成动图 WebP（体积约为 GIF 的 1/4~1/5，浏览器支持良好）。
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
    refs = sorted(set(re.findall(r"assets/[A-Za-z0-9_\-]+\.gif", html)))
    if not refs:
        print("no gif referenced", file=sys.stderr)
        return 1

    if os.path.isdir(DIST):
        shutil.rmtree(DIST)
    os.makedirs(DIST_ASSETS, exist_ok=True)

    t0 = time.time()
    src_bytes = dst_bytes = 0
    for k, rel in enumerate(refs, 1):
        src = os.path.join(ROOT, rel)
        dst = os.path.join(DIST_ASSETS, os.path.basename(rel).rsplit(".", 1)[0] + ".webp")
        convert(src, dst)
        src_bytes += os.path.getsize(src)
        dst_bytes += os.path.getsize(dst)
        print("[%2d/%d] %-14s %6.2fMB -> %5.2fMB" % (
            k, len(refs), os.path.basename(rel),
            os.path.getsize(src) / 1048576, os.path.getsize(dst) / 1048576), flush=True)

    for rel in refs:
        html = html.replace(rel, rel.rsplit(".", 1)[0] + ".webp")
    with open(os.path.join(DIST, "index.html"), "w", encoding="utf-8", newline="") as f:
        f.write(html)

    print("=" * 46)
    print("动图 %d 个：%.1fMB -> %.1fMB（%.1f 倍）" % (
        len(refs), src_bytes / 1048576, dst_bytes / 1048576, src_bytes / max(dst_bytes, 1)))
    print("dist 总大小：%.1f MB  用时 %.0fs" % (
        sum(os.path.getsize(os.path.join(dp, f))
            for dp, _, fs in os.walk(DIST) for f in fs) / 1048576, time.time() - t0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
