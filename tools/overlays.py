#!/usr/bin/env python3
"""Overlay kit: make a story's image OURS by dropping in the world's own UI.

The rule (Zack, Nov 27, 2026): don't just slap the source image on the card.
Think about what world the story lives in and add that world's elements on
top: a game HUD, a console popup, a Windows dialog, a store page badge, an
FPS counter, a red circle on the thing that matters. Every element here is
drawn from scratch in the style of the UI (no lifted assets).

Render one element to a transparent PNG:
  python3 tools/overlays.py render KIND --out el.png [--text ...] [--sub ...] [--n N] [--scale 2]

Composite elements onto a photo (positions in photo pixels, w = target width):
  python3 tools/overlays.py comp PHOTO --out OUT.jpg \
      --el el1.png:X:Y:W [--el el2.png:X:Y:W ...] [--circle X:Y:R] [--arrow X1:Y1:X2:Y2]

Preview every kind on one sheet:
  python3 tools/overlays.py sheet --out sheet.png

KINDS
  achievement   Xbox-style toast       --text "Achievement unlocked"  --sub "Paid $70 for a gift card"  --n 50 (gamerscore)
  trophy        PlayStation-style popup --text "You've earned a trophy" --sub "Bought it twice"  (--n 0 bronze,1 silver,2 gold,3 platinum)
  steam-toast   Steam notification     --text "Gabe Newell"  --sub "is now playing Steam Machine"
  wanted        GTA-style wanted stars --n 5 (filled of 5)
  mission       big MISSION FAILED / PASSED banner  --text "MISSION FAILED"  --sub "RESPECT -100"
  win-error     Windows 11 dialog      --text "Windows"  --sub "Your PC needs 32GB of RAM to open Paint."
  fps           perf overlay counter   --text "FPS 12"  --sub "GPU 99%  VRAM 7.9/8GB"
  progress      update/download bar    --text "Installing update"  --n 37 (percent)
  ping          red notification badge --n 99
  breaking      lower-third bar        --text "BREAKING"  --sub "Nvidia confirms it"
  chat          Discord/Twitch-style chat line  --text "username"  --sub "message"
  price         store price tag, strike-through  --text "$499"  --sub "$799"
"""
import argparse, html, os, sys

CSS_BASE = """
*{margin:0;padding:0;box-sizing:border-box}
html,body{background:transparent}
body{display:inline-block;padding:24px;font-family:'Inter','Segoe UI',sans-serif}
"""

def esc(s):
    return html.escape(s or "")

def tpl(kind, text, sub, n):
    t, s = esc(text), esc(sub)
    if kind == "achievement":
        t = t or "Achievement unlocked"; n = 50 if n is None else n
        return f"""<style>
.a{{display:flex;align-items:center;gap:18px;background:linear-gradient(90deg,#1a1a1a,#2b2b2b);border-radius:60px;padding:14px 40px 14px 14px;box-shadow:0 10px 40px rgba(0,0,0,.6);min-width:560px}}
.i{{width:84px;height:84px;border-radius:50%;background:radial-gradient(circle at 35% 30%,#5fe35f,#107c10);display:flex;align-items:center;justify-content:center;color:#fff;font:900 46px 'Archivo Black'}}
.t{{color:#fff;font:600 24px Inter;opacity:.85}} .s{{color:#fff;font:800 34px Inter;margin-top:2px}}
.g{{color:#fff;font:800 26px Inter;margin-left:auto;padding-left:24px;opacity:.9}}
</style><div class=a><div class=i>🏆</div><div><div class=t>{t}</div><div class=s>{s}</div></div><div class=g>G {n}</div></div>"""
    if kind == "trophy":
        n = 0 if n is None else n
        col = ["#cd7f32", "#c0c0c0", "#ffd24a", "#a9d8ff"][max(0, min(3, n))]
        t = t or "You've earned a trophy."
        return f"""<style>
.a{{display:flex;align-items:center;gap:18px;background:rgba(20,22,30,.92);border-radius:14px;padding:16px 34px 16px 16px;box-shadow:0 10px 40px rgba(0,0,0,.6);min-width:560px;border:1px solid rgba(255,255,255,.12)}}
.i{{width:80px;height:80px;border-radius:10px;background:#0b0d14;display:flex;align-items:center;justify-content:center}}
.cup{{width:44px;height:50px;background:{col};clip-path:polygon(10% 0,90% 0,85% 45%,60% 62%,62% 80%,78% 80%,78% 100%,22% 100%,22% 80%,38% 80%,40% 62%,15% 45%);filter:drop-shadow(0 0 8px {col})}}
.t{{color:#cfd3dc;font:500 22px Inter}} .s{{color:#fff;font:700 32px Inter;margin-top:2px}}
</style><div class=a><div class=i><div class=cup></div></div><div><div class=t>{t}</div><div class=s>{s}</div></div></div>"""
    if kind == "steam-toast":
        return f"""<style>
.a{{width:600px;background:linear-gradient(180deg,#2a475e,#1b2838);border-radius:6px;padding:18px;display:flex;gap:18px;align-items:center;box-shadow:0 12px 40px rgba(0,0,0,.65);border-top:2px solid #66c0f4}}
.i{{width:84px;height:84px;border-radius:4px;background:linear-gradient(135deg,#66c0f4,#1b2838);border:3px solid #57cbde}}
.t{{color:#d2efa9;font:700 30px Inter}} .s{{color:#c7d5e0;font:500 24px Inter;margin-top:4px}}
</style><div class=a><div class=i></div><div><div class=t>{t}</div><div class=s>{s}</div></div></div>"""
    if kind == "wanted":
        n = 5 if n is None else n
        star = lambda on: f"<div class='st {'on' if on else ''}'></div>"
        return f"""<style>
.a{{display:flex;gap:10px}}
.st{{width:78px;height:78px;clip-path:polygon(50% 0,61% 35%,98% 35%,68% 57%,79% 91%,50% 70%,21% 91%,32% 57%,2% 35%,39% 35%);background:#3a3a3a;filter:drop-shadow(0 0 2px #000)}}
.st.on{{background:linear-gradient(180deg,#fff,#e8e8e8)}}
.wrap{{padding:8px;filter:drop-shadow(0 4px 6px rgba(0,0,0,.9))}}
</style><div class=wrap><div class=a>{''.join(star(i < n) for i in range(5))}</div></div>"""
    if kind == "mission":
        t = t or "MISSION FAILED"
        col = "#e8312a" if "FAIL" in t.upper() or "WASTED" in t.upper() or "BUSTED" in t.upper() else "#f5c518"
        return f"""<style>
.a{{width:1000px;text-align:center;padding:26px 0;background:linear-gradient(90deg,transparent,rgba(0,0,0,.75) 20%,rgba(0,0,0,.75) 80%,transparent)}}
.t{{font:400 110px Anton;letter-spacing:4px;color:{col};text-shadow:0 0 2px #000,4px 4px 0 #000;line-height:1}}
.s{{font:800 34px Inter;color:#fff;margin-top:12px;text-shadow:2px 2px 0 #000;letter-spacing:2px}}
</style><div class=a><div class=t>{t}</div>{f'<div class=s>{s}</div>' if s else ''}</div>"""
    if kind == "win-error":
        t = t or "Windows"
        return f"""<style>
.a{{width:620px;background:#f3f3f3;border-radius:10px;box-shadow:0 20px 60px rgba(0,0,0,.6);overflow:hidden;border:1px solid #c9c9c9}}
.h{{display:flex;justify-content:space-between;align-items:center;padding:12px 18px;font:500 20px 'Segoe UI',Inter;color:#111}}
.x{{font:400 22px Inter;color:#333}}
.b{{display:flex;gap:20px;padding:12px 26px 26px}}
.ic{{width:56px;height:56px;border-radius:50%;background:#c42b1c;color:#fff;font:700 38px Inter;display:flex;align-items:center;justify-content:center;flex:none}}
.m{{font:500 26px Inter;color:#111;line-height:1.3;padding-top:6px}}
.f{{background:#e9e9e9;padding:16px 22px;display:flex;justify-content:flex-end;gap:12px;border-top:1px solid #ddd}}
.btn{{font:500 20px Inter;padding:9px 30px;border-radius:6px;background:#fdfdfd;border:1px solid #ccc}} .btn.p{{background:#005fb8;color:#fff;border-color:#005fb8}}
</style><div class=a><div class=h><span>{t}</span><span class=x>✕</span></div><div class=b><div class=ic>✕</div><div class=m>{s}</div></div><div class=f><span class='btn p'>OK</span><span class=btn>Cancel</span></div></div>"""
    if kind == "fps":
        t = t or "FPS 12"
        return f"""<style>
.a{{background:rgba(0,0,0,.55);padding:12px 18px;border-radius:6px;font:800 44px 'Fira Sans','Inter';color:#ffef00;text-shadow:2px 2px 0 #000;line-height:1.15}}
.s{{font:700 26px 'Fira Sans',Inter;color:#7CFC00}}
</style><div class=a>{t}{f'<div class=s>{s}</div>' if s else ''}</div>"""
    if kind == "progress":
        n = 37 if n is None else n; t = t or "Installing update"
        return f"""<style>
.a{{width:680px;background:rgba(10,12,18,.88);border-radius:12px;padding:22px 26px;box-shadow:0 12px 40px rgba(0,0,0,.6)}}
.t{{color:#fff;font:700 28px Inter;display:flex;justify-content:space-between}}
.bar{{height:18px;background:#2a2e38;border-radius:9px;margin-top:16px;overflow:hidden}}
.f{{height:100%;width:{n}%;background:linear-gradient(90deg,#00a2ff,#3cf)}}
.s{{color:#aab;font:500 20px Inter;margin-top:10px}}
</style><div class=a><div class=t><span>{t}</span><span>{n}%</span></div><div class=bar><div class=f></div></div>{f'<div class=s>{s}</div>' if s else ''}</div>"""
    if kind == "ping":
        n = 99 if n is None else n
        return f"""<style>.a{{min-width:110px;height:110px;padding:0 26px;border-radius:55px;background:#f23f43;border:8px solid #fff;color:#fff;font:900 64px Inter;display:flex;align-items:center;justify-content:center;box-shadow:0 8px 30px rgba(0,0,0,.6)}}</style><div class=a>{n}</div>"""
    if kind == "breaking":
        t = t or "BREAKING"
        return f"""<style>
.a{{display:flex;align-items:stretch;box-shadow:0 10px 30px rgba(0,0,0,.6)}}
.t{{background:#d90000;color:#fff;font:400 54px Anton;padding:10px 26px;letter-spacing:2px;transform:skewX(-8deg)}}
.s{{background:#fff;color:#111;font:800 40px Inter;padding:14px 30px;display:flex;align-items:center}}
</style><div class=a><div class=t>{t}</div>{f'<div class=s>{s}</div>' if s else ''}</div>"""
    if kind == "chat":
        return f"""<style>
.a{{background:rgba(24,25,28,.92);border-radius:10px;padding:16px 22px;display:flex;gap:16px;align-items:flex-start;max-width:720px;box-shadow:0 10px 30px rgba(0,0,0,.5)}}
.av{{width:58px;height:58px;border-radius:50%;background:linear-gradient(135deg,#5865f2,#eb459e);flex:none}}
.u{{color:#f0b232;font:700 26px Inter}} .m{{color:#e8e8ea;font:500 28px Inter;margin-top:4px;line-height:1.3}}
</style><div class=a><div class=av></div><div><div class=u>{t}</div><div class=m>{s}</div></div></div>"""
    if kind == "price":
        return f"""<style>
.a{{background:#ffe600;color:#111;padding:18px 34px 18px 50px;clip-path:polygon(0 50%,12% 0,100% 0,100% 100%,12% 100%);box-shadow:0 10px 30px rgba(0,0,0,.5);display:flex;gap:22px;align-items:baseline}}
.t{{font:400 86px Anton;line-height:1}} .s{{font:800 40px Inter;text-decoration:line-through;text-decoration-color:#d90000;text-decoration-thickness:6px;opacity:.75}}
</style><div class=a><div class=t>{t}</div>{f'<div class=s>{s}</div>' if s else ''}</div>"""
    raise SystemExit(f"unknown kind {kind}")


def render(kind, out, text="", sub="", n=None, scale=2):
    from playwright.sync_api import sync_playwright
    page_html = f"<html><head><meta charset=utf8><style>{CSS_BASE}</style></head><body><div id=el>{tpl(kind, text, sub, n)}</div></body></html>"
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(device_scale_factor=scale, viewport={"width": 1400, "height": 900})
        pg.set_content(page_html); pg.wait_for_timeout(150)
        pg.locator("body").screenshot(path=out, omit_background=True)
        b.close()
    return out


def comp(photo, out, els, circles, arrows):
    from PIL import Image, ImageDraw, ImageFilter
    base = Image.open(photo).convert("RGBA")
    for spec in els:
        path, x, y, w = spec.rsplit(":", 3)
        el = Image.open(path).convert("RGBA"); w = int(w)
        el = el.resize((w, int(el.height * w / el.width)), Image.LANCZOS)
        base.alpha_composite(el, (int(x), int(y)))
    if circles or arrows:
        layer = Image.new("RGBA", base.size, (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
        lw = max(8, base.width // 120)
        for c in circles:
            x, y, r = map(int, c.split(":"))
            for k in range(2):
                d.ellipse([x - r - k * 6, y - r * 0.85 + k * 4, x + r + k * 3, y + r * 0.85 - k * 2], outline=(230, 20, 20, 255), width=lw)
        for a in arrows:
            x1, y1, x2, y2 = map(int, a.split(":"))
            d.line([x1, y1, x2, y2], fill=(230, 20, 20, 255), width=lw + 2)
            import math
            ang = math.atan2(y2 - y1, x2 - x1); L = lw * 5
            for s in (-0.5, 0.5):
                d.line([x2, y2, x2 - L * math.cos(ang + s), y2 - L * math.sin(ang + s)], fill=(230, 20, 20, 255), width=lw + 2)
        sh = layer.filter(ImageFilter.GaussianBlur(4)); sh2 = Image.new("RGBA", base.size, (0, 0, 0, 0))
        sh2.paste((0, 0, 0, 140), mask=sh.split()[3])
        base.alpha_composite(sh2, (4, 4)); base.alpha_composite(layer)
    base.convert("RGB").save(out, quality=95)
    return out


DEMO = [
    ("achievement", "Achievement unlocked", "Paid $80 for 30 FPS", 50),
    ("trophy", "You've earned a trophy.", "Bought the same game twice", 2),
    ("steam-toast", "Gabe Newell", "is now playing Steam Machine", None),
    ("wanted", "", "", 4),
    ("mission", "MISSION FAILED", "RAM PRICES +697%", None),
    ("win-error", "Windows", "Paint needs 2.8 GB of RAM to draw a circle.", None),
    ("fps", "FPS 12", "VRAM 7.9 / 8.0 GB", None),
    ("progress", "Installing update", "Do not turn off your PC", 37),
    ("ping", "", "", 99),
    ("breaking", "BREAKING", "Nvidia confirms it", None),
    ("chat", "gabefan_1998", "bro just let me buy the game", None),
    ("price", "$799", "$499", None),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd"); ap.add_argument("arg", nargs="?")
    ap.add_argument("--out", required=True); ap.add_argument("--text", default=""); ap.add_argument("--sub", default="")
    ap.add_argument("--n", type=int); ap.add_argument("--scale", type=int, default=2)
    ap.add_argument("--el", action="append", default=[]); ap.add_argument("--circle", action="append", default=[])
    ap.add_argument("--arrow", action="append", default=[])
    a = ap.parse_args()
    if a.cmd == "render":
        print(render(a.arg, a.out, a.text, a.sub, a.n, a.scale))
    elif a.cmd == "comp":
        print(comp(a.arg, a.out, a.el, a.circle, a.arrow))
    elif a.cmd == "sheet":
        from PIL import Image
        d = os.path.splitext(a.out)[0] + "_parts"; os.makedirs(d, exist_ok=True)
        ims = [Image.open(render(k, os.path.join(d, f"{k}.png"), t, s, n, 1)) for k, t, s, n in DEMO]
        cols = 3; cw = max(i.width for i in ims); rh = max(i.height for i in ims)
        S = Image.new("RGBA", (cols * cw, ((len(ims) + 2) // 3) * rh), (40, 60, 90, 255))
        for i, im in enumerate(ims):
            S.alpha_composite(im, ((i % cols) * cw, (i // cols) * rh))
        S.save(a.out); print(a.out)
    else:
        sys.exit("cmd: render | comp | sheet")


if __name__ == "__main__":
    main()
