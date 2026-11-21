#!/usr/bin/env python3
"""Banger QC (Zack, Nov 21, 2026: reference the latest bangers on each platform and make sure the
design and text are set up for lots of reactions, eye-catching and viral).

  python3 tools/bangers.py fb  NEW_FB.png            [--out sheet.png]
  python3 tools/bangers.py x   NEW_X_IMAGE1 NEW_X_CARD [--out sheet.png]

Writes a sheet: the new post at phone size on the left, the current bangers from scan/bangers.json
at the same size on the right, and prints the checklist. Read the sheet and grade the new post
against the bangers line by line. Any NO = rebuild before pitching (same as a QC FAIL)."""
import json, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
CHECK = {
 "fb": [
  "1. ONE giant subject a gamer recognizes in half a second (famous face close-up, giant brand logo on brand color, the hardware itself tight, or the real scene) fills the photo area. No small tiles, no blurred UI walls, no generic stock.",
  "2. At most one receipt clip, in a corner away from the subject, with 3 to 8 highlighted words readable at this size. No tiny file lists or paragraphs.",
  "3. Headline: famous name or thing in the first words, a number, quote or villain, accent on the punch, no orphan word, readable at this size. Does it make you need to know more?",
  "4. Take row: a line people will smash like on or argue with (agree, joke or jab built from replies), not a summary, plus a reaction emoji that fits.",
  "5. Reaction bait: is there a side to take, a 'wait what', or something to tag a friend about? If people can't react in one word, it fails.",
  "6. Side by side with the bangers: same punch, contrast and saturation? Would it stop YOUR scroll next to them? If it looks quieter, busier or more homemade than every banger, rebuild.",
 ],
 "x": [
  "1. Image 1 reads in half a second at this size (the receipt, the face, or your hardware) and looks different from the card.",
  "2. The card: one giant recognizable subject, one readable receipt, punchy headline, take row with emoji.",
  "3. First caption line: famous name in the first five words with the fact or quote; the closer is a take people quote-post or argue with.",
  "4. Side by side with the X bangers: same clarity and punch? If it looks quieter, busier or more homemade, rebuild.",
 ],
}

def tile(p, w):
    im = Image.open(p).convert("RGB"); h = int(im.height * w / im.width); return im.resize((w, h))

def main():
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "banger-sheet.png"
    if "--out" in sys.argv: a.remove(out)
    plat, new = a[0], a[1:]
    ref = json.load(open(ROOT / "scan/bangers.json"))[plat]
    W = 360
    news = [tile(p, W) for p in new]
    refs = []
    for r in ref:
        fs = ([r["image1"]] if plat == "x" and r.get("image1") else []) + [r["file"]]
        ims = [tile(ROOT / f, W // (2 if plat == "x" else 1)) for f in fs if (ROOT / f).exists()]
        if ims: refs.append((ims, r["metric"]))
    try: font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
    except Exception: font = ImageFont.load_default()
    cols = 3; rh = max(sum(i.height for i in ims) if plat == "fb" else max(i.height for i in ims) for ims, _ in refs) + 30
    nh = sum(i.height for i in news) + 30 * len(news)
    H = max(nh + 40, ((len(refs) + cols - 1) // cols) * rh + 40)
    sheet = Image.new("RGB", (W + 40 + cols * (W + 20), H), (24, 24, 28)); d = ImageDraw.Draw(sheet)
    d.text((10, 8), "NEW POST (phone size)", fill="#FFD60A", font=font); y = 36
    for im in news: sheet.paste(im, (10, y)); y += im.height + 30
    for k, (ims, m) in enumerate(refs):
        x0 = W + 40 + (k % cols) * (W + 20); y0 = 8 + (k // cols) * rh
        d.text((x0, y0), f"BANGER: {m}", fill="#7CFC9A", font=font); xx = x0
        for im in ims: sheet.paste(im, (xx, y0 + 28)); xx += im.width
    sheet.save(out); print("sheet:", out)
    print("\nBANGER CHECK (answer YES/NO for each, any NO = rebuild):")
    for c in CHECK[plat]: print(c)

if __name__ == "__main__":
    main()
