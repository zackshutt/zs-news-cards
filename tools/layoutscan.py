#!/usr/bin/env python3
"""ZS layout scan. Run BEFORE rendering any card (and again on every revision).

  python3 layoutscan.py spec.json            -> scan report + <out>-scan.png, exit 1 on FAIL
  python3 layoutscan.py cutcheck CUTOUT.png
        -> grades a transparent cutout's edge (holes, jagged outline, leftover hands/background).
           FAIL = do not use it anywhere; switch image 1 to a primary-source screenshot or a clean photo.
  python3 layoutscan.py qc FB.png X1.jpg X2.png [--out sheet.png]
        -> final QC gate after rendering (Nov 18, 2026): checks sizes, flags homemade-cutout
           edges in X image 1, and writes a contact sheet of how the posts look on a phone
           (FB feed width, X two-image post with X's center crops, plus 100% crops of edges).
           Read the sheet; send nothing until every image passes the "would Zack post this
           as-is?" bar.
  python3 layoutscan.py compose SRC OUT FORMAT SIDE [--take]
        -> writes a background sized to that format's photo area with the detected subject
           placed whole on SIDE (left|right|center) over a blurred fill of the same image, so
           clips can go on the other side. Use when the subject can't fit uncovered with a
           plain cover-crop (tall photo into the square X card, faces near the middle, etc.).

What the scan checks (per format, because portrait and square crop the photo differently):
  1. Finds the subject: faces (OpenCV frontal + profile) grown to a head box (hair, beard), plus
     any boxes listed in the spec's "protect": [[x,y,w,h], ...] (background-image pixels) for
     non-face subjects (a console, a GPU, a logo, the meme punchline).
  2. Maps them through the card's object-fit: cover crop (bg_position) into card pixels.
  3. FAIL if any clip/meme covers more than 8% of a protected box, if a protected box is cut off
     by the photo edges, or if it sinks into the black fade (bottom of the box below the fade
     midpoint). WARN if no subject was found (add "protect" by hand).
  4. Prints the free zones left and right of the subject, so clips go there.
"""
import json, sys
from pathlib import Path
import cv2
from PIL import Image, ImageDraw, ImageFilter

SLOTS = {
    "top-wide": dict(x=0.035, y=0.08, w=0.80, max_h=0.20), "top-right": dict(x=0.45, y=0.08, w=0.50, max_h=0.24),
    "left-tall": dict(x=0.055, y=0.27, w=0.25, max_h=0.32), "right-tall": dict(x=0.695, y=0.27, w=0.25, max_h=0.32),
    "center": dict(x=0.20, y=0.27, w=0.60, max_h=0.30), "meme-right": dict(x=0.815, y=0.42, w=0.155, max_h=0.15),
    "meme-left": dict(x=0.03, y=0.42, w=0.155, max_h=0.15), "hero-center": dict(x=0.06, y=0.17, w=0.88, max_h=0.36),
    "split-left": dict(x=0.00, y=0.06, w=0.56, max_h=0.56), "split-right": dict(x=0.44, y=0.06, w=0.56, max_h=0.56),
    "stack-right-1": dict(x=0.50, y=0.07, w=0.46, max_h=0.20), "stack-right-2": dict(x=0.50, y=0.29, w=0.46, max_h=0.30),
    "stack-left-1": dict(x=0.04, y=0.07, w=0.46, max_h=0.20), "stack-left-2": dict(x=0.04, y=0.29, w=0.46, max_h=0.30),
    "cascade-1": dict(x=0.04, y=0.06, w=0.66, max_h=0.20), "cascade-2": dict(x=0.18, y=0.24, w=0.66, max_h=0.20),
    "cascade-3": dict(x=0.30, y=0.42, w=0.66, max_h=0.18),
}
W = 1080


def geom(spec):
    square = spec.get("format") == "square"
    H = 1080 if square else 1350
    has_take = bool(spec.get("take"))
    pe = spec.get("photo_end") or ((0.55 if has_take else 0.64) if square else (0.63 if has_take else 0.70))
    return H, pe, H * pe


MODELS = Path(__file__).resolve().parent / "assets" / "models"
MODEL_URLS = {  # OpenCV 5 ships no cascade files; fetched once into assets/models
    "yunet.onnx": "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
    "haarcascade_frontalface_default.xml": "https://raw.githubusercontent.com/opencv/opencv/4.x/data/haarcascades/haarcascade_frontalface_default.xml",
}


def model(name):
    p = MODELS / name
    if not p.exists() or p.stat().st_size < 10000:
        import urllib.request
        MODELS.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(MODEL_URLS[name], p)
    return str(p)


def faces(img_path):
    bgr = cv2.imread(str(img_path))
    h, w = bgr.shape[:2]
    raw = []
    try:  # YuNet: handles glasses, beards, 3/4 angles
        sc = min(1.0, 1280 / max(w, h))
        small = cv2.resize(bgr, (round(w * sc), round(h * sc)))
        det = cv2.FaceDetectorYN.create(model("yunet.onnx"), "", (small.shape[1], small.shape[0]), 0.7)
        _, res = det.detect(small)
        for r in (res if res is not None else []):
            raw.append([v / sc for v in r[:4]])
    except Exception as e:
        print("WARN yunet failed:", e)
    if not raw:
        g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        c = cv2.CascadeClassifier(model("haarcascade_frontalface_default.xml"))
        ms = (max(24, w // 14),) * 2
        raw = [list(map(float, b)) for b in c.detectMultiScale(g, 1.1, 6, minSize=ms)]
    # ignore tiny background faces (crowds, posters): keep faces >= 35% the size of the biggest
    big = max((b[2] for b in raw), default=0)
    out = [[x, y, fw, fh] for x, y, fw, fh in raw if fw >= 0.35 * big]
    # merge overlapping detections
    merged = []
    for b in sorted(out, key=lambda b: -b[2] * b[3]):
        if not any(inter(b, m) > 0.3 * b[2] * b[3] for m in merged):
            merged.append(b)
    return merged


def head(b):  # face box (brows to chin) -> head box (hair, beard, ears)
    x, y, fw, fh = b
    return [x - 0.25 * fw, y - 0.15 * fh, fw * 1.5, fh * 1.35]


def inter(a, b):
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[0] + a[2], b[0] + b[2]), min(a[1] + a[3], b[1] + b[3])
    return max(0, x2 - x1) * max(0, y2 - y1)


def pos_frac(s):
    m = {"left": 0, "top": 0, "center": 50, "right": 100, "bottom": 100}
    parts = s.split()
    if len(parts) == 1:
        parts = parts * 2 if parts[0] == "center" else ([parts[0], "center"] if parts[0] in ("left", "right") else ["center", parts[0]])
    return [(m[p] if p in m else float(p.rstrip("%"))) / 100 for p in parts[:2]]


def bg_map(spec, base, ph):
    iw, ih = Image.open(base / spec["background"]).size
    s = max(W / iw, ph / ih)
    fx, fy = pos_frac(spec.get("bg_position", "center"))
    ox, oy = (W - iw * s) * fx, (ph - ih * s) * fy
    return lambda b: [b[0] * s + ox, b[1] * s + oy, b[2] * s, b[3] * s]


def clip_rects(spec, base, H, pe):
    floor = H * (pe - 0.075)
    items = list(spec.get("clips", [])) + ([spec["meme"]] if spec.get("meme") else [])
    out = []
    for c in items:
        iw, ih = Image.open(base / c["src"]).size
        sl = c.get("slot", "center")
        s = dict(SLOTS[sl]) if isinstance(sl, str) else {**dict(x=0.1, y=0.3, w=0.4, max_h=0.3), **sl}
        w = s["w"] * W; h = w / (iw / ih)
        mh = min(s.get("max_h", 1) * H, floor - s["y"] * H)
        if h > mh:
            h = mh; w = h * iw / ih
        out.append((c["src"], [s["x"] * W, s["y"] * H, w, h]))
    return out


def scan(spec_path):
    sp = Path(spec_path).resolve(); base = sp.parent; spec = json.loads(sp.read_text())
    H, pe, ph = geom(spec)
    mp = bg_map(spec, base, ph)
    fs = faces(base / spec["background"])
    prot = [("head", mp(head(b)), mp(b)) for b in fs]
    prot += [("protect", mp(b), mp(b)) for b in spec.get("protect", [])]
    clips = clip_rects(spec, base, H, pe)
    fade_mid = H * (pe - 0.11)   # fade is ~70% black here
    fails, warns = [], []
    if not prot:
        warns.append("no subject found: add \"protect\": [[x,y,w,h]] (background pixels) for the thing that must stay visible")
    for kind, b, core in prot:
        if core[0] < 0 or core[0] + core[2] > W or core[1] < 0 or b[0] < -0.15 * b[2] or b[0] + b[2] > W + 0.15 * b[2] or b[1] < -0.12 * b[3]:
            fails.append(f"{kind} {fmt(b)} is cut off by the photo edge")
        if core[1] + core[3] > fade_mid:
            fails.append(f"{kind} {fmt(core)} sinks into the black fade (bottom {core[1]+core[3]:.0f} > {fade_mid:.0f}); move it up or compose the bg")
        for src, r in clips:
            a, ac = inter(b, r), inter(core, r)
            if ac > 0.02 * core[2] * core[3] or a > 0.10 * b[2] * b[3]:
                fails.append(f"{src} {fmt(r)} covers {ac/(core[2]*core[3])*100:.0f}% of the {kind} core {fmt(core)} / {a/(b[2]*b[3])*100:.0f}% of {fmt(b)}")
    if prot:
        l = min(b[0] for _, b, _c in prot); r = max(b[0] + b[2] for _, b, _c in prot)
        print(f"free zones: left 0-{max(0,l):.0f}px ({max(0,l)/W:.2f}), right {min(W,r):.0f}-{W}px ({min(W,r)/W:.2f}-1.00); clip floor y={H*(pe-0.075):.0f}")
    # debug overlay
    prev = Image.new("RGB", (W, H), "black")
    bgi = Image.open(base / spec["background"]).convert("RGB")
    iw, ih = bgi.size; s = max(W / iw, ph / ih); fx, fy = pos_frac(spec.get("bg_position", "center"))
    prev.paste(bgi.resize((round(iw * s), round(ih * s))), (round((W - iw * s) * fx), round((ph - ih * s) * fy)))
    prev.paste((0, 0, 0), (0, int(ph), W, H))
    d = ImageDraw.Draw(prev)
    for _, b, core in prot:
        d.rectangle([core[0], core[1], core[0] + core[2], core[1] + core[3]], outline="cyan", width=4)
        d.rectangle([b[0], b[1], b[0] + b[2], b[1] + b[3]], outline="lime", width=6)
    for _, r in clips:
        d.rectangle([r[0], r[1], r[0] + r[2], r[1] + r[3]], outline="red", width=6)
    d.line([0, fade_mid, W, fade_mid], fill="orange", width=3)
    outp = sp.with_name(Path(spec.get("out", sp.stem + ".png")).stem + "-scan.png")
    prev.save(outp)
    for w_ in warns: print("WARN", w_)
    for f in fails: print("FAIL", f)
    print("PASS" if not fails else "FIX BEFORE RENDERING", "| overlay:", outp)
    return 0 if not fails else 1


def fmt(b):
    return "[%d,%d %dx%d]" % tuple(round(v) for v in b)


def compose(src, out, fmt_, side, take=True):
    spec = {"format": fmt_, "take": take}
    H, pe, ph = geom(spec); ph = round(ph)
    im = Image.open(src).convert("RGB"); iw, ih = im.size
    fb = [head(b) for b in faces(src)]
    if fb:
        x0 = min(b[0] for b in fb); y0 = min(b[1] for b in fb)
        x1 = max(b[0] + b[2] for b in fb); y1 = max(b[1] + b[3] for b in fb)
    else:
        x0, y0, x1, y1 = 0, 0, iw, ih
    # scale so the subject box fills ~78% of the usable photo height (above the fade midpoint)
    usable = ph - 0.11 * H - 30
    s = min(usable * 0.95 / (y1 - y0), ph * 1.6 / ih, W / iw * 1.4)
    if side != "center":  # leave the other ~40% of the width as clean blurred fill for the clips
        s = min(s, 0.62 * W / (x1 - x0), 0.72 * W / iw)
    sw, sh = round(iw * s), round(ih * s)
    sub = im.resize((sw, sh))
    cx = {"left": W * 0.30, "right": W * 0.70, "center": W * 0.5}[side]
    px = round(cx - (x0 + x1) / 2 * s)
    px = min(max(px, W - sw), 0) if sw >= W else min(max(px, 0), W - sw)
    py = round(20 - y0 * s)
    py = min(max(py, ph - sh), 0) if sh >= ph else max(py, 0)
    fill = im.resize((W, round(ih * W / iw))).crop((0, 0, W, ph)) if ih * W / iw >= ph else im.resize((round(iw * ph / ih), ph)).crop((0, 0, W, ph))
    fill = fill.filter(ImageFilter.GaussianBlur(28)).point(lambda v: int(v * 0.8))
    canvas = fill.copy()
    mask = Image.new("L", (sw, sh), 255)
    md = ImageDraw.Draw(mask)
    feather = 60
    for i in range(feather):  # soft edges where the sharp photo meets the blurred fill
        a = int(255 * i / feather)
        md.rectangle([i, i, sw - 1 - i, sh - 1 - i], outline=a)
    canvas.paste(sub, (px, py), mask)
    canvas.save(out, quality=94)
    print(f"composed {out} {W}x{ph} subject at x={px} y={py} scale={s:.2f}")


def edge_grade(alpha):
    """Return (verdict, notes) for a cutout alpha mask (uint8 array)."""
    import numpy as np
    a = (alpha > 127).astype("uint8") * 255
    notes = []
    cs, hier = cv2.findContours(a, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    if not cs:
        return "FAIL", ["empty mask"]
    big = max(cs, key=cv2.contourArea)
    area = cv2.contourArea(big)
    hull = cv2.convexHull(big)
    solidity = area / max(cv2.contourArea(hull), 1)
    rough = cv2.arcLength(big, True) / max(cv2.arcLength(hull, True), 1)
    holes = 0
    if hier is not None:
        holes = sum(1 for i, h in enumerate(hier[0]) if h[3] != -1 and cv2.contourArea(cs[i]) > area * 0.002)
    islands = sum(1 for c in cs if c is not big and cv2.contourArea(c) > area * 0.002) - holes
    c = big[:, 0, :].astype(float)
    k = 61
    pad = np.concatenate([c[-k:], c, c[:k]])
    sm = np.stack([np.convolve(pad[:, i], np.ones(k) / k, "same")[k:-k] for i in range(2)], 1)
    jag = float((np.linalg.norm(c - sm, axis=1) > 6).mean())  # share of outline that wiggles off a smooth path
    notes.append(f"solidity {solidity:.2f}, outline/hull {rough:.2f}, jag {jag:.3f}, holes {holes}, islands {max(islands,0)}")
    bad = rough > 1.30 or holes > 0 or islands > 0 or solidity < 0.80 or jag > 0.03
    return ("FAIL" if bad else "PASS"), notes


def cutcheck(path):
    import numpy as np
    im = Image.open(path)
    if im.mode != "RGBA":
        print("FAIL | no alpha channel: not a cutout")
        return 1
    v, notes = edge_grade(np.array(im.split()[3]))
    print(f"{v} | {path}: " + "; ".join(notes))
    if v == "FAIL":
        print("  -> do not use. Use a primary-source screenshot, a vector logo (npm simple-icons), a product shot "
              "shot on plain white (Evan-Amos/press kit) run through rembg, or a clean tight photo crop.")
    return 0 if v == "PASS" else 1


def flat_bg_cutout_check(path):
    """For composed image-1 JPGs (cutout pasted on a gradient): find the subject against the
    gradient by color distance and grade its outline the same way."""
    import numpy as np
    im = np.array(Image.open(path).convert("RGB")).astype("int16")
    h, w, _ = im.shape
    # model the background as the per-row median of the outer 6% columns (gradient-safe)
    edge = np.concatenate([im[:, : int(w * .06)], im[:, -int(w * .06):]], axis=1)
    bg = np.median(edge, axis=1)[:, None, :]
    diff = np.abs(im - bg).sum(axis=2)
    mask = (diff > 60).astype("uint8") * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), "uint8"))
    cover = (mask > 0).mean()
    if cover < 0.05 or cover > 0.92:
        return None  # full-bleed photo or nothing found: not a pasted cutout
    cs, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    big = max(cs, key=cv2.contourArea)
    if cv2.contourArea(big) / max(cv2.contourArea(cv2.convexHull(big)), 1) > 0.97 and len(cv2.approxPolyDP(big, 0.02 * cv2.arcLength(big, True), True)) <= 8:
        return None  # a rectangular screenshot/receipt panel on a background, not a cutout
    return edge_grade(mask)


def qc(fb, x1, x2, out=None, cutout_ok=False):
    import numpy as np
    fails = []
    for p, want in [(fb, (1080, 1350)), (x1, (1080, 1080)), (x2, (1080, 1080))]:
        if p and Path(p).exists():
            sz = Image.open(p).size
            if sz != want:
                fails.append(f"{Path(p).name} is {sz[0]}x{sz[1]}, expected {want[0]}x{want[1]}")
    if x1 and Path(x1).exists():
        g = flat_bg_cutout_check(x1)
        if g:
            v, notes = g
            print(f"X image 1 cutout edge: {v} ({'; '.join(notes)})")
            if v == "FAIL":
                fails.append("X image 1 is a pasted cutout with a rough/holed outline (homemade look)")
            elif not cutout_ok:
                fails.append("X image 1 is a pasted cutout: only allowed from a plain-background product shot or vector "
                             "logo that passed `cutcheck`; rerun with --cutout-ok once that is true")
    # contact sheet: FB at feed width, X two-image post as X crops it, 100% crops
    sheet = Image.new("RGB", (1600, 1500), (24, 24, 28))
    d = ImageDraw.Draw(sheet)
    x = 20
    if fb and Path(fb).exists():
        f = Image.open(fb).convert("RGB").resize((400, 500))
        sheet.paste(f, (x, 40)); d.text((x, 12), "FB feed (phone width)", fill="white"); x += 430
    imgs = [Image.open(p).convert("RGB") for p in (x1, x2) if p and Path(p).exists()]
    if imgs:
        d.text((x, 12), "X two-image post (phone, X center-crops each to 7:8)", fill="white")
        for i, im in enumerate(imgs):
            cw = int(im.height * 7 / 8)
            c = im.crop(((im.width - cw) // 2, 0, (im.width + cw) // 2, im.height)).resize((196, 224))
            sheet.paste(c, (x + i * 200, 40))
        d.text((x, 280), "Tapped open (full image)", fill="white")
        for i, im in enumerate(imgs):
            sheet.paste(im.resize((300, 300)), (x + i * 310, 300))
        # 100% crops of the busiest edges of image 1, where homemade cutouts show
        im = imgs[0]
        g = cv2.Canny(cv2.cvtColor(np.array(im), cv2.COLOR_RGB2GRAY), 80, 160)
        ys, xs = np.nonzero(g)
        d.text((x, 620), "X image 1 at 100% (check edges, halos, hands, artifacts)", fill="white")
        if len(xs):
            for i, (qx, qy) in enumerate([(np.percentile(xs, 5), np.percentile(ys, 95)), (np.percentile(xs, 95), np.percentile(ys, 5)),
                                         (np.median(xs), np.percentile(ys, 97))]):
                cx, cy = int(min(max(qx - 150, 0), im.width - 300)), int(min(max(qy - 150, 0), im.height - 300))
                sheet.paste(im.crop((cx, cy, cx + 300, cy + 300)), (x + i * 310, 640))
    out = out or str(Path(x2 or fb).with_name("qc-sheet.png"))
    sheet.save(out)
    print("QC sheet:", out)
    for f in fails:
        print("FAIL |", f)
    print("QC", "FAIL" if fails else "AUTO-PASS (now Read the sheet and grade every image by eye)")
    return 1 if fails else 0


if __name__ == "__main__":
    if sys.argv[1] == "cutcheck":
        sys.exit(cutcheck(sys.argv[2]))
    if sys.argv[1] == "qc":
        a = [x for x in sys.argv[2:] if not x.startswith("--")]
        o = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else None
        if o in a: a.remove(o)
        sys.exit(qc(*(a + [None] * 3)[:3], out=o, cutout_ok="--cutout-ok" in sys.argv))
    if sys.argv[1] == "compose":
        compose(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], "--notake" not in sys.argv)
    else:
        sys.exit(scan(sys.argv[1]))
