#!/usr/bin/env python3
"""Face library for ZS news cards (Zack, Nov 25, 2026: "figure out how to source images of people").

The cloud scan does not pull photos of real people off the web. Faces come from Zack's team:
they drop photos into the Google Drive folder "ZS Card Faces" (or attach them in a session),
named  <slug>__<tag>.<ext>  e.g.  jensen-huang__smiling.jpg, sam-altman__talking.png.
The scan downloads new Drive files to a folder and runs `sync`, which checks quality, finds the
face, and files them under assets/faces/<slug>/ with an index the renderer can use.

  python3 tools/faces.py sync DIR            file new photos (prints PASS/REJECT per file)
  python3 tools/faces.py find "Jensen"       name or alias -> slug + available shots
  python3 tools/faces.py bg SLUG --fmt fb|square|tall [--tag T] [--side left|right] --out OUT.jpg
                                             background crop with the face whole, prints the
                                             protect box for the layout-scan spec
  python3 tools/faces.py missing             priority people with no usable photo yet
"""
import argparse, json, os, re, sys
import cv2
import numpy as np
from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(ROOT, "assets", "faces")
PEOPLE = os.path.join(LIB, "people.json")
INDEX = os.path.join(LIB, "index.json")
FMT = {"fb": (1080, 1350), "square": (1080, 1080), "tall": (1080, 1536)}
MIN_SHORT = 900      # px, short side of the source
MIN_FACE = 160       # px, face box width in the source


def load(p, d):
    return json.load(open(p)) if os.path.exists(p) else d


def norm(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def resolve(name):
    people = load(PEOPLE, {"people": []})["people"]
    n = norm(name)
    for p in people:
        if n == p["slug"] or n in [norm(a) for a in p.get("aliases", [])]:
            return p["slug"]
    for p in people:  # loose: any alias inside the query
        for a in [p["slug"]] + p.get("aliases", []):
            if norm(a) and norm(a) in n:
                return p["slug"]
    return n


def detect(img):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    g = cv2.equalizeHist(g)
    found = []
    for casc in ("haarcascade_frontalface_default.xml", "haarcascade_profileface.xml"):
        c = cv2.CascadeClassifier(os.path.join(ROOT, "tools", "models", casc))
        for flip in (False, True):
            gg = cv2.flip(g, 1) if flip else g
            for (x, y, w, h) in c.detectMultiScale(gg, 1.1, 6, minSize=(60, 60)):
                if flip:
                    x = g.shape[1] - x - w
                found.append((int(x), int(y), int(w), int(h)))
        if found:
            break
    if not found:
        return None
    return max(found, key=lambda b: b[2] * b[3])


def sync(src):
    idx = load(INDEX, {"shots": []})
    have = {(s["slug"], s["tag"]) for s in idx["shots"]}
    for fn in sorted(os.listdir(src)):
        if not re.search(r"\.(jpe?g|png|webp)$", fn, re.I):
            continue
        stem = os.path.splitext(fn)[0]
        slug, tag = (stem.split("__", 1) + ["main"])[:2]
        slug, tag = resolve(slug), norm(tag) or "main"
        img = cv2.imread(os.path.join(src, fn))
        if img is None:
            print("REJECT", fn, "unreadable"); continue
        h, w = img.shape[:2]
        if min(w, h) < MIN_SHORT:
            print("REJECT", fn, f"too small {w}x{h} (need {MIN_SHORT}px short side)"); continue
        face = detect(img)
        if face is None:
            print("REJECT", fn, "no face found (use a clear front or 3/4 view)"); continue
        if face[2] < MIN_FACE:
            print("REJECT", fn, f"face too small ({face[2]}px wide, need {MIN_FACE})"); continue
        sharp = cv2.Laplacian(cv2.cvtColor(img[face[1]:face[1]+face[3], face[0]:face[0]+face[2]], cv2.COLOR_BGR2GRAY), cv2.CV_64F).var()
        if sharp < 25:
            print("REJECT", fn, f"face is blurry (sharpness {sharp:.0f})"); continue
        while (slug, tag) in have:
            tag = tag + "-2" if not re.search(r"-\d+$", tag) else re.sub(r"\d+$", lambda m: str(int(m.group()) + 1), tag)
        os.makedirs(os.path.join(LIB, slug), exist_ok=True)
        out = os.path.join(LIB, slug, tag + ".jpg")
        s = min(1.0, 2400 / max(w, h))
        if s < 1:
            img = cv2.resize(img, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
            face = tuple(int(v * s) for v in face)
        cv2.imwrite(out, img, [cv2.IMWRITE_JPEG_QUALITY, 92])
        idx["shots"].append({"slug": slug, "tag": tag, "file": os.path.relpath(out, ROOT),
                             "w": img.shape[1], "h": img.shape[0], "face": list(face),
                             "sharp": round(sharp), "src": fn})
        have.add((slug, tag))
        print("PASS", fn, "->", os.path.relpath(out, ROOT), "face", face)
    json.dump(idx, open(INDEX, "w"), indent=1)


def shots(slug):
    return [s for s in load(INDEX, {"shots": []})["shots"] if s["slug"] == slug]


def bg(slug, fmt, tag, side, out):
    ss = shots(resolve(slug))
    if not ss:
        sys.exit(f"NO PHOTO for {slug}: fall back to logo / hardware / scene and ask Zack for one")
    s = next((x for x in ss if tag and x["tag"].startswith(tag)), None) or max(ss, key=lambda x: x["face"][2] * x["sharp"])
    im = Image.open(os.path.join(ROOT, s["file"])).convert("RGB")
    W, H = FMT[fmt]
    fx, fy, fw, fh = s["face"]
    # the photo area is the top ~58% of the card (headline + take row below); the face should
    # fill about a third of the card width and sit in the upper part of the photo area
    target_fw = W * (0.36 if fmt != "square" else 0.32)
    k = target_fw / fw
    k = max(k, W / im.width, H * 0.62 / im.height)  # never leave the photo area empty
    im2 = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    fx, fy, fw, fh = [round(v * k) for v in (fx, fy, fw, fh)]
    cx = {"left": 0.34, "right": 0.66}.get(side, 0.5) * W
    cy = H * (0.27 if fmt != "square" else 0.30)
    ox, oy = round(fx + fw / 2 - cx), round(fy + fh / 2 - cy)
    canvas = im2.resize((W, H)).filter(ImageFilter.GaussianBlur(40))  # blurred fill for any gap
    canvas.paste(im2, (-ox, -oy))
    canvas.save(out, quality=94)
    # protect: the head and shoulders, in output pixels
    px, py = fx - ox - round(fw * 0.35), fy - oy - round(fh * 0.45)
    prot = [max(0, px), max(0, py), min(W, round(fw * 1.7)), min(H, round(fh * 2.2))]
    gap = ox < 0 or oy < 0 or ox + W > im2.width or oy + H * 0.62 > im2.height
    print(json.dumps({"bg": out, "shot": s["file"], "protect": [prot], "padded_edges": gap}))


def missing():
    people = load(PEOPLE, {"people": []})["people"]
    have = {s["slug"] for s in load(INDEX, {"shots": []})["shots"]}
    for p in people:
        n = len(shots(p["slug"]))
        if n < 3:
            print(f'{p["slug"]:22} {n} of 3   {p.get("why", "")}')


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd")
    ap.add_argument("arg", nargs="?")
    ap.add_argument("--fmt", default="fb")
    ap.add_argument("--tag")
    ap.add_argument("--side", default="left")
    ap.add_argument("--out")
    a = ap.parse_args()
    if a.cmd == "sync": sync(a.arg)
    elif a.cmd == "find":
        sl = resolve(a.arg); print(sl, [x["tag"] for x in shots(sl)])
    elif a.cmd == "bg": bg(a.arg, a.fmt, a.tag, a.side, a.out)
    elif a.cmd == "missing": missing()
    else: sys.exit(__doc__)
