#!/usr/bin/env python3
"""Zack's Take quote card (Coby Watts style). Usage: python3 zstake.py spec.json
Spec: out, background, bg_position, bg_darken, format (portrait|square), text (**bold** words),
name, handle, avatar, accent (border color), card_top (0-1 fraction of height), font_size."""
import base64, html, json, mimetypes, re, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

def uri(p):
    m = mimetypes.guess_type(p.name)[0] or "image/png"
    return f"data:{m};base64," + base64.b64encode(p.read_bytes()).decode()

def rich(t):
    out = []
    for part in re.split(r"(\*\*[^*]+\*\*)", t):
        if part.startswith("**"):
            out.append(f"<b>{html.escape(part[2:-2])}</b>")
        else:
            out.append(html.escape(part))
    return "".join(out)

CHECK = ('<svg viewBox="0 0 24 24" width="34" height="34"><path fill="#1D9BF0" d="M22.25 12c0-1.43-.88-2.67-2.19-3.34.46-1.39.2-2.9-.81-3.91s-2.52-1.27-3.91-.81c-.66-1.31-1.91-2.19-3.34-2.19s-2.67.88-3.33 2.19c-1.4-.46-2.91-.2-3.92.81s-1.26 2.52-.8 3.91c-1.31.67-2.2 1.91-2.2 3.34s.89 2.67 2.2 3.34c-.46 1.39-.21 2.9.8 3.91s2.52 1.26 3.91.81c.67 1.31 1.91 2.19 3.34 2.19s2.68-.88 3.34-2.19c1.39.45 2.9.2 3.91-.81s1.27-2.52.81-3.91c1.31-.67 2.19-1.91 2.19-3.34z"/>'
         '<path fill="#fff" d="M10.1 16.6l-3.9-3.9 1.4-1.4 2.5 2.5 5.7-5.7 1.4 1.4z"/></svg>')

def build(c, base):
    sq = c.get("format") == "square"
    W, H = 1080, (1080 if sq else 1350)
    acc = c.get("accent", "#E3262E")
    top = c.get("card_top", 0.40 if not sq else 0.34)
    fs = c.get("font_size", 58 if not sq else 52)
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:{W}px;height:{H}px;overflow:hidden;position:relative;background:#000;font-family:'Inter Display','Inter',sans-serif}}
.bg{{position:absolute;inset:0;background:url({uri(base/c['background'])}) {c.get('bg_position','center')}/cover;filter:brightness({1-c.get('bg_darken',0.05)})}}
.card{{position:absolute;left:48px;right:48px;top:{H*top:.0f}px;background:#000;border:9px solid {acc};border-radius:46px;
  padding:{44 if not sq else 36}px {58 if not sq else 50}px {50 if not sq else 40}px;box-shadow:0 24px 60px rgba(0,0,0,.6)}}
.who{{display:flex;align-items:center;gap:26px;margin-bottom:{34 if not sq else 26}px}}
.who img{{width:{128 if not sq else 112}px;height:{128 if not sq else 112}px;border-radius:50%;object-fit:cover;border:4px solid #fff}}
.nm{{color:#fff;font-weight:800;font-style:italic;font-size:{46 if not sq else 42}px;display:flex;align-items:center;gap:12px;line-height:1.1}}
.hd{{color:#fff;font-weight:700;font-size:{30 if not sq else 28}px;opacity:.95;display:flex;align-items:center;gap:8px;margin-top:4px}}
.tx{{color:#fff;font-size:{fs}px;line-height:1.16;font-weight:400;letter-spacing:-.4px}}
.tx b{{font-weight:900}}
</style></head><body><div class="bg"></div>
<div class="card"><div class="who"><img src="{uri(base/c['avatar'])}"><div>
<div class="nm">{html.escape(c.get('name','Zack Shutt'))}</div>
<div class="hd">{html.escape(c.get('handle','@ZackShutt'))} {CHECK}</div></div></div>
<div class="tx">{rich(c['text'])}</div></div></body></html>"""

def render(path):
    f = Path(path).resolve(); c = json.loads(f.read_text())
    out = str(f.with_name(c.get("out", f.stem + ".png")))
    H = 1080 if c.get("format") == "square" else 1350
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1080, "height": H})
        pg.set_content(build(c, f.parent), wait_until="load"); pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(200)
        pg.screenshot(path=out); b.close()
    return out

if __name__ == "__main__":
    print(render(sys.argv[1]))
