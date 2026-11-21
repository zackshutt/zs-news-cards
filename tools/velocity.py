#!/usr/bin/env python3
"""Vitality meter for the news-card scan (Zack, Nov 21, 2026: "Reddit etc and better searches and
vitality meters would be helpful for you to find hits").

  python3 tools/velocity.py --cur /tmp/reddit.json [--prev scan/reddit-prev.json] [--save scan/reddit-prev.json]

Joins this run's Reddit pull (tools/reddit_fetch.py output) with the last run's snapshot and scores
every post on four meters, then groups posts about the same story across subs:
  per_h   lifetime upvotes per hour (what reddit_fetch already gives)
  now_h   upvotes per hour SINCE THE LAST RUN (true current speed; needs --prev)
  accel   now_h / per_h  (>1.2 = speeding up, <0.7 = cooling)
  spread  how many different subs carry the same link or near-same title (cross-posting = breakout)
  heat    one number to rank on: now_h (or per_h) x spread bonus x accel bonus x comment bonus
Flags: HEATING (accel >= 1.2 and now_h >= 100), BREAKOUT (spread >= 3 subs), FRESH-FAST (under 2h and 150+/h),
COOLING (accel < 0.7). Story groups with BREAKOUT or HEATING are scan candidates even under the
usual 500-upvote bar. --save writes this run as the next run's --prev (commit it with seen.json).
"""
import argparse, json, re, time
from collections import defaultdict

STOP = set("the a an of to in on for and is are be by with your you it this that from at as now just new has have was its after over".split())

def rows(p):
    d = json.load(open(p)); return d["rows"] if isinstance(d, dict) else d, (d.get("fetched_utc") if isinstance(d, dict) else None)

def words(t):
    return {w for w in re.findall(r"[a-z0-9]+", t.lower()) if w not in STOP and len(w) > 2}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--cur", required=True); ap.add_argument("--prev"); ap.add_argument("--save")
    ap.add_argument("--top", type=int, default=25); a = ap.parse_args()
    cur, t_cur = rows(a.cur)
    prev, t_prev = ({}, None)
    if a.prev:
        try:
            pr, t_prev = rows(a.prev); prev = {r["id"]: r for r in pr}
        except Exception: pass
    for r in cur:
        p = prev.get(r["id"]); r["now_h"] = None; r["accel"] = None
        if p:
            dt = r["age_h"] - p["age_h"]
            if dt < 0.25: continue
            r["now_h"] = round((r["score"] - p["score"]) / dt)
            r["accel"] = round(r["now_h"] / r["per_h"], 2) if r["per_h"] else None
    # story groups: same outbound link, or title word overlap >= 0.6
    groups = []
    for r in sorted(cur, key=lambda r: -r["score"]):
        w = words(r["title"]); link = r.get("link") or ""
        for g in groups:
            if (link and not link.startswith("https://www.reddit.com") and link == g["link"]) or \
               (len(w & g["w"]) >= 3 and len(w & g["w"]) / max(1, min(len(w), len(g["w"]))) >= 0.6):
                g["rows"].append(r); g["w"] |= w; break
        else:
            groups.append({"link": link, "w": set(w), "rows": [r]})
    out = []
    for g in groups:
        rs = g["rows"]; top = max(rs, key=lambda r: r["score"]); subs = sorted({r["sub"] for r in rs})
        speed = max([r["now_h"] for r in rs if r["now_h"] is not None] or [top["per_h"]])
        acc = top["accel"] or 1.0
        com = sum(r.get("comments", 0) for r in rs); ups = sum(r["score"] for r in rs)
        heat = speed * (1 + 0.5 * (len(subs) - 1)) * min(max(acc, 0.5), 2) * (1.2 if ups and com / ups > 0.15 else 1)
        flags = []
        if top["accel"] and top["accel"] >= 1.2 and (top["now_h"] or 0) >= 100: flags.append("HEATING")
        if len(subs) >= 3: flags.append("BREAKOUT")
        if top["age_h"] < 2 and top["per_h"] >= 150: flags.append("FRESH-FAST")
        if top["accel"] is not None and top["accel"] < 0.7: flags.append("COOLING")
        out.append({"title": top["title"], "subs": subs, "total_up": ups, "comments": com, "age_h": top["age_h"],
                    "per_h": top["per_h"], "now_h": top["now_h"], "accel": top["accel"], "heat": round(heat),
                    "flags": flags, "url": top["url"], "link": top.get("link")})
    out.sort(key=lambda o: -o["heat"])
    print(f"{'heat':>6} {'now/h':>6} {'life/h':>6} {'acc':>5} {'subs':>4} {'ups':>6} {'age':>5}  flags / title")
    for o in out[:a.top]:
        print(f"{o['heat']:>6} {str(o['now_h'] if o['now_h'] is not None else '-'):>6} {o['per_h']:>6} {str(o['accel'] or '-'):>5} {len(o['subs']):>4} {o['total_up']:>6} {o['age_h']:>5}  {','.join(o['flags'])} | {o['title'][:90]} [{'/'.join(o['subs'])}]")
    json.dump(out, open(a.cur.replace(".json", "-heat.json"), "w"), indent=1)
    if a.save:
        json.dump({"fetched_utc": t_cur or time.strftime('%Y-%m-%dT%H:%MZ', time.gmtime()), "rows": cur}, open(a.save, "w"))

if __name__ == "__main__":
    main()
