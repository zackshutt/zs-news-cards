#!/usr/bin/env python3
"""Reddit pull for the news-card scan (Nov 17, 2026).

Why: the Composio Reddit tool (u/Little_Evidence) and reddit.com JSON/RSS were
returning HTTP 429/403 on the very first call, from the cloud sandbox. Arctic Shift
(arctic-shift.photon-reddit.com, free, no key) mirrors Reddit posts within minutes and
keeps updating scores, so we read it instead. Runs in plain bash, no Composio.

Usage:
  python3 tools/reddit_fetch.py --hours 3 [--subs a,b,c] [--sort per_h|score] [--out FILE]
  (top of day: --hours 24 --sort score; lab hot pool: --hours 36 --sort score)

Prints a ranked table (upvotes per hour) and writes JSON rows:
  {sub, id, title, score, comments, age_h, per_h, url, link, flags:[rising|new|R1|R2]}
"rising" = 150+/h or 500+ total; "new" = under 90 min with 20+ upvotes.
R1/R2 (section 6 cross-searches) are applied as keyword filters over the same pull,
since Arctic Shift text search needs a subreddit.
"""
import argparse, json, re, sys, time, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor

SUBS = ("PS5,pcgaming,pcmasterrace,nvidia,Amd,Steam,GamingLeaksAndRumours,technology,gaming,"
        "hardware,buildapc,buildapcsales,Windows11,Games,linux_gaming,xbox,NintendoSwitch,"
        "SteamDeck,linux,LinusTechTips").split(",")
API = "https://arctic-shift.photon-reddit.com/api/posts/search"
FIELDS = "id,title,score,num_comments,created_utc,url,subreddit,over_18"  # permalink/stickied are rejected (400)

R1_A = re.compile(r"locked out|by default|turned on|bricked|banned|won'?t launch", re.I)
R1_B = re.compile(r"windows|ps5|playstation|xbox|steam|nvidia|discord|reddit", re.I)
R2_A = re.compile(r"price (drop|cut|hike)|restock|msrp|shortage", re.I)
R2_B = re.compile(r"rtx|gpu|\bram\b|ddr5|ssd|5090|5080", re.I)


def get(sub, after, tries=3):
    q = urllib.parse.urlencode({"subreddit": sub, "after": after, "limit": 100,
                                "sort": "desc", "fields": FIELDS})
    for i in range(tries):
        try:
            req = urllib.request.Request(f"{API}?{q}", headers={"User-Agent": "zs-news-scan/1.0"})
            return sub, json.load(urllib.request.urlopen(req, timeout=25)).get("data", []), None
        except Exception as e:  # 429/5xx: back off and retry; 4xx other than 429: give up
            err = str(e)
            if "HTTP Error 4" in err and "429" not in err:
                break
            time.sleep(3 * (i + 1))
    return sub, [], err


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=float, default=6, help="posts created in the last N hours")
    ap.add_argument("--subs", default=",".join(SUBS))
    ap.add_argument("--out", default="")
    ap.add_argument("--top", type=int, default=40)
    ap.add_argument("--sort", choices=["per_h", "score"], default="per_h",
                    help="per_h = rising/velocity; score = top/hot of the window")
    a = ap.parse_args()
    now = time.time()
    after = int(now - a.hours * 3600)
    subs = [s for s in a.subs.split(",") if s]
    rows, errs = [], []
    with ThreadPoolExecutor(4) as ex:
        for sub, data, err in ex.map(lambda s: get(s, after), subs):
            if err:
                errs.append(f"{sub}: {err}")
            for p in data:
                if p.get("over_18"):
                    continue
                age = max((now - p["created_utc"]) / 3600, 0.05)
                sc = p.get("score", 0)
                t = p.get("title", "")
                flags = []
                if sc / age >= 150 or sc >= 500:
                    flags.append("rising")
                if age <= 1.5 and sc >= 20:
                    flags.append("new")
                if R1_A.search(t) and R1_B.search(t):
                    flags.append("R1")
                if R2_A.search(t) and R2_B.search(t):
                    flags.append("R2")
                rows.append({"sub": sub, "id": p["id"], "title": t, "score": sc,
                             "comments": p.get("num_comments", 0), "age_h": round(age, 1),
                             "per_h": round(sc / age), "link": p.get("url", ""),
                             "url": f"https://www.reddit.com/r/{sub}/comments/{p['id']}/",
                             "flags": flags})
    rows.sort(key=lambda r: -r[a.sort])
    for r in rows[: a.top]:
        print(f"{r['per_h']:>6}/h {r['score']:>6} {r['age_h']:>4}h r/{r['sub']:<22} "
              f"{','.join(r['flags']):<12} {r['title'][:90]}")
    print(f"\n{len(rows)} posts from {len(subs) - len(errs)}/{len(subs)} subs", file=sys.stderr)
    for e in errs:
        print("ERR", e, file=sys.stderr)
    if a.out:
        json.dump({"fetched_utc": int(now), "hours": a.hours, "errors": errs, "rows": rows},
                  open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
