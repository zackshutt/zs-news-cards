#!/usr/bin/env python3
"""Non-person image sourcing the cloud scan can do on its own (Zack, Nov 25, 2026).

  python3 tools/imgsource.py steam "Cyberpunk 2077" --out DIR   official Steam art: library_hero (3840x1240),
                                                                background, header, 1920px screenshots
  python3 tools/imgsource.py og URL --out DIR                    the page's og:image plus its biggest <img>s
                                                                (official newsrooms: nvidianews, news.xbox.com,
                                                                blog.playstation.com, nintendo.com, blogs.windows.com,
                                                                openai.com/news, rockstargames.com/newswire)
  python3 tools/imgsource.py logo nvidia --out FILE.png [--bg auto|#hex] [--size 1080]
                                                                simple-icons mark, big, on its brand color
Every download is size-checked; anything under 1000px wide is dropped. Use this for games,
hardware, products, scenes and brand marks. People come from tools/faces.py only.
"""
import argparse, json, os, re, sys, urllib.parse, urllib.request
from io import BytesIO
from PIL import Image

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131 Safari/537.36"}


def get(url, t=20):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=t).read()


def save(url, out, minw=1000):
    try:
        b = get(url)
        im = Image.open(BytesIO(b))
        if im.width < minw:
            return None
        im.convert("RGB").save(out, quality=94)
        return {"file": out, "w": im.width, "h": im.height, "url": url}
    except Exception as e:
        return None


def steam(q, out):
    os.makedirs(out, exist_ok=True)
    appid = q if q.isdigit() else None
    if not appid:
        r = json.loads(get("https://store.steampowered.com/api/storesearch/?cc=us&l=en&term=" + urllib.parse.quote(q)))
        if not r.get("items"):
            sys.exit("no Steam match for " + q)
        appid, name = str(r["items"][0]["id"]), r["items"][0]["name"]
    d = json.loads(get(f"https://store.steampowered.com/api/appdetails?appids={appid}&cc=us&l=en"))[appid]["data"]
    urls = [("hero", f"https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/{appid}/library_hero.jpg"),
            ("hero", f"https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/library_hero.jpg"),
            ("background", d.get("background_raw") or d.get("background", ""))]
    urls += [(f"shot{i+1}", s["path_full"]) for i, s in enumerate(d.get("screenshots", [])[:8])]
    got, seen = [], set()
    for tag, u in urls:
        if not u or tag in seen:
            continue
        r = save(u, os.path.join(out, f"{appid}-{tag}.jpg"))
        if r:
            seen.add(tag); r["tag"] = tag; got.append(r)
    print(json.dumps({"appid": appid, "name": d.get("name"), "images": got}, indent=1))


def og(url, out):
    os.makedirs(out, exist_ok=True)
    html = get(url).decode("utf-8", "ignore")
    cands = re.findall(r'<meta[^>]+(?:property|name)="(?:og:image|twitter:image)(?::src)?"[^>]+content="([^"]+)"', html)
    cands += re.findall(r'<img[^>]+(?:src|data-src)="([^"]+\.(?:jpe?g|png|webp)[^"]*)"', html)
    cands += [m.split()[0] for s in re.findall(r'srcset="([^"]+)"', html) for m in s.split(",")[-1:]]
    got, seen = [], set()
    for c in cands:
        u = urllib.parse.urljoin(url, c.replace("&amp;", "&"))
        if u in seen or re.search(r"(logo|icon|avatar|sprite|social-image)", u, re.I):
            continue
        seen.add(u)
        r = save(u, os.path.join(out, f"og{len(got)+1}.jpg"))
        if r:
            got.append(r)
        if len(got) >= 6:
            break
    got.sort(key=lambda r: -r["w"] * r["h"])
    print(json.dumps({"page": url, "images": got}, indent=1))


def logo(slug, out, bg="auto", size=1080):
    meta = json.loads(get("https://raw.githubusercontent.com/simple-icons/simple-icons/develop/data/simple-icons.json"))
    meta = meta if isinstance(meta, list) else meta.get("icons", [])
    def sl(t): return re.sub(r"[^a-z0-9]", "", t.lower().replace("+", "plus").replace(".", "dot").replace("&", "and"))
    m = next((x for x in meta if x.get("slug", sl(x["title"])) == slug or sl(x["title"]) == sl(slug)), None)
    if not m:
        sys.exit("no simple-icons mark for " + slug)
    s = m.get("slug", sl(m["title"]))
    svg = get(f"https://raw.githubusercontent.com/simple-icons/simple-icons/develop/icons/{s}.svg").decode()
    color = "#" + m["hex"]
    if bg == "auto":
        bgc, fg = color, "#ffffff"
        if int(m["hex"][:2], 16) * .3 + int(m["hex"][2:4], 16) * .59 + int(m["hex"][4:], 16) * .11 > 200:
            bgc, fg = "#111111", color
    else:
        bgc, fg = bg, "#ffffff"
    svg = svg.replace("<path ", f'<path fill="{fg}" ')
    page = f"""<html><body style="margin:0;width:{size}px;height:{size}px;display:flex;align-items:center;justify-content:center;
background:radial-gradient(circle at 50% 45%, color-mix(in srgb,{bgc} 100%, white 18%) 0%, {bgc} 55%, color-mix(in srgb,{bgc} 100%, black 45%) 100%)">
<div style="width:{int(size*.56)}px;height:{int(size*.56)}px">{svg.replace('<svg ', '<svg width="100%" height="100%" ')}</div></body></html>"""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width": size, "height": size})
        pg.set_content(page); pg.screenshot(path=out); b.close()
    print(json.dumps({"file": out, "brand": m["title"], "hex": color}))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd"); ap.add_argument("arg")
    ap.add_argument("--out", required=True); ap.add_argument("--bg", default="auto"); ap.add_argument("--size", type=int, default=1080)
    a = ap.parse_args()
    {"steam": lambda: steam(a.arg, a.out), "og": lambda: og(a.arg, a.out),
     "logo": lambda: logo(a.arg, a.out, a.bg, a.size)}.get(a.cmd, lambda: sys.exit(__doc__))()
