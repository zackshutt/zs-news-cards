#!/usr/bin/env python3
"""ZS post mock: see the whole post the way a phone user sees it, BEFORE pitching (Zack, Nov 20, 2026:
"mock up the full post before and imagine you're viewing on phone screen ... go back and forth
internally until it's perfect on all fronts ... that way you're presenting me a fully refined post").

  python3 postmock.py x  CAPTION.txt IMG1 IMG2 [--out x-mock.png]
  python3 postmock.py fb CAPTION.txt FB.png    [--out fb-mock.png]

Renders at real phone size (390 pt wide, 1x) in dark mode:
  X : avatar + name row, the caption cut where X cuts it (280 chars, then "Show more"),
      the two images side by side center-cropped to 7:8 like the X timeline, action row.
  FB: page header, caption cut after 3 lines with "See more", the 4:5 card at feed width.
Then it prints how many caption characters are visible before "Show more" and the visible text.

Read the mock PNG at 1x. If you cannot read it on the mock, the viewer cannot read it.
Grade it with the checklist in claude/zs-news-card-layout-scan.md Part 4, fix, re-mock, repeat.
"""
import base64, html, sys
from pathlib import Path
from PIL import Image
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
AV = ROOT / "assets" / "zs-avatar.jpg"


def uri(p):
    p = Path(p)
    m = "image/png" if p.suffix == ".png" else "image/jpeg"
    return f"data:{m};base64," + base64.b64encode(p.read_bytes()).decode()


def coverage(p):
    """share of the frame with real detail (edges): flat backgrounds and soft gradients score ~0"""
    import cv2
    g = cv2.cvtColor(np.array(Image.open(p).convert("RGB").resize((540, 540))), cv2.COLOR_RGB2GRAY)
    e = cv2.Canny(g, 60, 140)
    cells = e.reshape(27, 20, 27, 20).max(axis=(1, 3))
    return float((cells > 0).mean())


def x_cut(t, n=280):
    if len(t) <= n:
        return t, False
    c = t[:n].rsplit(" ", 1)[0]
    return c, True


def fb_cut(t, n=150):
    if len(t) <= n:
        return t, False
    return t[:n].rsplit(" ", 1)[0], True


CSS = """*{margin:0;padding:0;box-sizing:border-box}body{width:390px;background:#000;color:#e7e9ea;
font-family:-apple-system,'Inter','Segoe UI',Roboto,sans-serif;font-size:15px;line-height:20px}
.post{padding:12px 16px;border-bottom:1px solid #2f3336}.row{display:flex;gap:10px}
.av{width:40px;height:40px;border-radius:50%;flex:0 0 40px}.nm b{color:#fff}.nm span{color:#71767b}
.txt{white-space:pre-wrap;margin-top:2px}.more{color:#1d9bf0}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:2px;margin-top:10px;border-radius:16px;overflow:hidden;border:1px solid #2f3336}
.grid img{width:100%;aspect-ratio:7/8;object-fit:cover;display:block}
.act{display:flex;justify-content:space-between;color:#71767b;margin-top:10px;font-size:13px}
.fb{background:#242526;color:#e4e6eb}.fbh{display:flex;gap:8px;padding:12px}.fbh small{color:#b0b3b8}
.fbt{padding:0 12px 10px;white-space:pre-wrap}.fbt .more{color:#b0b3b8;font-weight:600}
.fbimg{width:390px;display:block}.fbact{display:flex;justify-content:space-around;padding:10px;color:#b0b3b8;border-top:1px solid #3e4042}"""


def render(body, out, h=1400):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 390, "height": h}, device_scale_factor=1)
        pg.set_content(f"<html><head><style>{CSS}</style></head><body>{body}</body></html>")
        pg.wait_for_timeout(300)
        el = pg.locator("#post")
        el.screenshot(path=out)
        b.close()
    print("mock:", out)


def main():
    kind, cap = sys.argv[1], Path(sys.argv[2]).read_text().strip()
    args = [a for a in sys.argv[3:] if not a.startswith("--")]
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else f"{kind}-mock.png"
    if out in args:
        args.remove(out)
    if kind == "x":
        vis, cut = x_cut(cap)
        t = html.escape(vis) + (' <span class="more">… Show more</span>' if cut else "")
        imgs = "".join(f'<img src="{uri(a)}">' for a in args[:2])
        body = (f'<div id="post" class="post"><div class="row"><img class="av" src="{uri(AV)}"><div style="flex:1">'
                f'<div class="nm"><b>Zack Shutt</b> <span>@ZackShutt · 1m</span></div><div class="txt">{t}</div>'
                f'<div class="grid">{imgs}</div><div class="act"><span>💬 0</span><span>🔁 0</span><span>♡ 0</span><span>📊 0</span><span>🔖</span></div>'
                f'</div></div></div>')
        render(body, out)
        print(f"caption {len(cap)} chars; visible before Show more: {len(vis)}{' (cut)' if cut else ''}")
        print("visible text:", vis.replace(chr(10), " / "))
    else:
        vis, cut = fb_cut(cap)
        t = html.escape(vis) + (' <span class="more">... See more</span>' if cut else "")
        body = (f'<div id="post" class="fb"><div class="fbh"><img class="av" src="{uri(AV)}"><div><b>Zack Shutt</b><br><small>Just now · 🌎</small></div></div>'
                f'<div class="fbt">{t}</div><img class="fbimg" src="{uri(args[0])}"><div class="fbact"><span>👍 Like</span><span>💬 Comment</span><span>↗ Share</span></div></div>')
        render(body, out, 1000)
    print("Now Read the mock at 1x and grade it with layout-scan Part 4. Unreadable on the mock = unreadable on the phone.")

if __name__ == "__main__":
    main()
