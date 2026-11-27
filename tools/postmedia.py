#!/usr/bin/env python3
"""Pull a story's own media (images and video) and turn it into usable stills.

Usage:
  python3 tools/postmedia.py --out DIR URL [URL ...]

URLs are the media URLs the scan already gets from X (expansions
attachments.media_keys, media_fields url,variants,preview_image_url), an
outlet's hero image, an mp4, or a page URL whose og:image should be pulled.
For pbs.twimg.com images the largest size is requested. For videos (.mp4 /
.m3u8 / video.twimg.com) frames are extracted on scene changes (plus one
every 2s as a fallback), blurry and near-duplicate frames are dropped, and
the sharpest 12 are kept.

Writes DIR/<n>.jpg (full res), DIR/sheet.jpg (numbered contact sheet to Read
and pick from), and DIR/media.json (path, source url, width, height,
sharpness). Pick a still from the sheet, then build the card with it as the
photo area (layoutscan compose / protect as usual).

Rule kept by the scan: stills whose main subject is a real person are not
used from this tool; people come from the face library (tools/faces.py).
"""
import argparse, json, os, re, subprocess, sys, urllib.request, urllib.parse

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"}


def fetch(url, path):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r, open(path, "wb") as f:
        f.write(r.read())
    return path


def big_twimg(url):
    if "pbs.twimg.com/media/" in url:
        base = url.split("?")[0]
        m = re.match(r"(.*)\.(jpg|jpeg|png|webp)$", base)
        if m:
            return f"{m.group(1)}?format={m.group(2)}&name=orig"
        return base + "?name=orig"
    return url


def og_image(page):
    req = urllib.request.Request(page, headers=UA)
    html = urllib.request.urlopen(req, timeout=30).read().decode("utf8", "ignore")
    for pat in [r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)',
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image',
                r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)']:
        m = re.search(pat, html, re.I)
        if m:
            return urllib.parse.urljoin(page, m.group(1))
    return None


def sharpness(path):
    from PIL import Image, ImageFilter, ImageStat
    im = Image.open(path).convert("L")
    im.thumbnail((640, 640))
    return ImageStat.Stat(im.filter(ImageFilter.FIND_EDGES)).var[0]


def ahash(path):
    from PIL import Image
    im = Image.open(path).convert("L").resize((16, 16))
    px = list(im.getdata()); avg = sum(px) / len(px)
    return [p > avg for p in px]


def video_frames(src, out, start_idx):
    tmp = os.path.join(out, "_frames"); os.makedirs(tmp, exist_ok=True)
    vf = "select='gt(scene\\,0.25)+not(mod(n\\,48))',scale='min(1920,iw)':-2"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", src, "-vf", vf,
                    "-vsync", "vfr", "-q:v", "2", os.path.join(tmp, "f%04d.jpg")], check=False)
    frames = sorted(os.path.join(tmp, f) for f in os.listdir(tmp))
    scored = [(sharpness(f), f) for f in frames]
    scored.sort(reverse=True)
    kept, hashes = [], []
    for s, f in scored:
        h = ahash(f)
        if any(sum(a != b for a, b in zip(h, k)) < 20 for k in hashes):
            continue
        hashes.append(h); kept.append((s, f))
        if len(kept) >= 12:
            break
    res = []
    for i, (s, f) in enumerate(sorted(kept, key=lambda x: x[1])):
        dst = os.path.join(out, f"{start_idx + i}.jpg"); os.replace(f, dst); res.append(dst)
    subprocess.run(["rm", "-rf", tmp])
    return res


def sheet(items, out):
    from PIL import Image, ImageDraw, ImageFont
    if not items:
        return None
    cols = 4; tw = 480
    thumbs = []
    for it in items:
        im = Image.open(it["path"]).convert("RGB"); im.thumbnail((tw, tw))
        thumbs.append(im)
    th = max(t.height for t in thumbs)
    rows = (len(thumbs) + cols - 1) // cols
    S = Image.new("RGB", (cols * (tw + 10) + 10, rows * (th + 40) + 10), (20, 20, 24))
    d = ImageDraw.Draw(S)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
    except Exception:
        font = ImageFont.load_default()
    for i, (t, it) in enumerate(zip(thumbs, items)):
        x = 10 + (i % cols) * (tw + 10); y = 10 + (i // cols) * (th + 40)
        S.paste(t, (x, y + 30))
        d.text((x, y + 4), f"#{os.path.basename(it['path'])[:-4]}  {it['w']}x{it['h']}", fill=(255, 220, 0), font=font)
    p = os.path.join(out, "sheet.jpg"); S.save(p, quality=88)
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("urls", nargs="+")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    from PIL import Image
    items, n = [], 1
    for url in a.urls:
        try:
            low = url.lower().split("?")[0]
            if "video.twimg.com" in low or low.endswith((".mp4", ".m3u8", ".webm", ".mov")):
                src = url
                if not low.endswith(".m3u8") and not os.path.exists(url):
                    src = fetch(url, os.path.join(a.out, f"_v{n}.mp4"))
                for p in video_frames(src, a.out, n):
                    w, h = Image.open(p).size
                    items.append({"path": p, "src": url, "kind": "video-frame", "w": w, "h": h, "sharp": round(sharpness(p))}); n += 1
                if src != url and not os.path.exists(url):
                    os.remove(src)
                elif src != url:
                    os.remove(src)
                continue
            if not low.endswith((".jpg", ".jpeg", ".png", ".webp", ".gif")) and "pbs.twimg.com" not in low:
                og = og_image(url)
                if not og:
                    print(f"SKIP no og:image {url}", file=sys.stderr); continue
                url = og
            p = os.path.join(a.out, f"{n}.jpg")
            raw = fetch(big_twimg(url), p + ".raw")
            Image.open(raw).convert("RGB").save(p, quality=95); os.remove(raw)
            w, h = Image.open(p).size
            items.append({"path": p, "src": url, "kind": "image", "w": w, "h": h, "sharp": round(sharpness(p))}); n += 1
        except Exception as e:
            print(f"FAIL {url}: {e}", file=sys.stderr)
    sp = sheet(items, a.out)
    json.dump(items, open(os.path.join(a.out, "media.json"), "w"), indent=1)
    for it in items:
        flag = "" if min(it["w"], it["h"]) >= 700 else "  SMALL (crop only, not full-bleed)"
        print(f"{it['path']}  {it['kind']}  {it['w']}x{it['h']}  sharp {it['sharp']}{flag}")
    print("sheet:", sp)


if __name__ == "__main__":
    main()
