# ZS news cards post mortem, Nov 20, 2026 (X image 1 + captions)

Trigger: Zack, on the Win7 RTX 50 X post (44 likes): "These cards have kinda fallen off in terms of design for initial one. Worth a post mortem on posts that've done well in the past and refining the strategy for both text and visual." Data pulled Nov 20 ~14:00Z: every @ZackShutt media post since Nov 13 (37 posts, public_metrics), and every Facebook post since Nov 11 (post_media_view).

## 1. What the numbers say

- **Facebook didn't fall off.** In the same 9 days the cards did KFC funeral 2.12M, Gabe "gates of Hell" 1.52M, Nvidia SSD 1.24M, Nvidia director 1.19M, Win7 RTX 50 206K at 16h, Tiny Terraces 377K, Win11 security check 413K. The Win7 story worked on Facebook and died on X. **So the problem is X-specific: image 1 and the caption.**
- **X two-image cards (n=15):** a hit-or-nothing split. Gabe 42,060; RAM "hawks" ruling 3,106; Nvidia SSD 2,759. The other 12 had a median of about 49 likes: Altman round three 266, Jensen avalanche 245, Win11 check 104, Visa leak 77, Nvidia director 67, Xbox boot 49, Win7 44, McDonald's 32, KFC 28, Discord Linux 28, Siri 9.
- **X video posts in the same week (n=22) had a median of 121 likes** (2,154; 790; 664; 490; 341 at the top). On ordinary stories, video beats the card on X by about 2.5x.

## 2. Image 1, winners vs losers (graded on a 1x phone mock)

Winners, all readable in under a second at feed size (about 165 px wide):
- Gabe: the Steam logo filling the frame on Steam blue. No text; the famous mark carries it.
- RAM ruling: the viewer's own RAM sticks, full-bleed. The thing at stake, not a person.
- Nvidia SSD: the GeForce forum post. The Nvidia logo and a big title read in the feed, and the "30gb per 1h" line is highlighted.

Losers:
- Win7: a 3-line quote card covering about 15% of the frame on an empty gradient. The text is about 5 px tall in the feed.
- Visa leak: three small bank logos.
- McDonald's in Discord: a photo of fries (next to the story, not the story).
- Siri limits: an iCloud cloud.
- Xbox boot: a console product shot.
- GTA+ (today): a 5-line text receipt with no number in it.

Rule: image 1 is the hook, not the evidence folder. It has to be one famous mark, the viewer's own thing, a hard-cropped receipt with a huge highlighted line, or a number poster. The full rules are in `claude/zs-news-card-layout-scan.md` Part 2 and Part 4.

## 3. Caption, winners vs losers

- The winners' first line had the famous name plus a quote or "your" stake: Gabe Newell is "literally guarding the gates of Hell"; A federal judge says Samsung, Micron and SK hynix moved like "hawks"; Nvidia users say ... writing gigabytes to your SSD. The losers led with a plain fact with no stakes ("Windows 7 can now run an RTX 5060 ...", "McDonald's just put ...", "Apple is putting daily limits ...").
- Two of the three winners were short (238 and 266 characters, all visible including the take). The long bullet format worked once, on a PSA (Nvidia SSD 599 characters, 1,760 bookmarks). It did nothing for weak stories: 593 (44 likes), 595 (77), 559 (32), 679 (104).
- The phone mock shows X cuts at about 275 characters. On the Win7 and GTA+ posts the fold landed mid-bullet, so the take never showed. Proposal (needs Zack's OK, because it changes his Nov 18 long-format rule): default 270 characters or less with the take visible; long bullets only for PSA or fix stories, with the check line above the fold.

## 4. Process change (Zack, Nov 20)

Every post gets the phone mock loop (layout-scan Part 4, `tools/postmock.py`): render, mock at 1x, score, fix the weakest element, repeat up to 3 rounds, then pitch the mock itself. Worked example, GTA+ v1 vs v2:
- v1: text receipt image 1, 624-character caption with the fold mid-bullet.
- v2: number poster image 1 ("$7.99 A MONTH / in single-player GTA 6" under the gta+ logo), 224-character caption with the take visible.
- Mocks are in the repo under `scan/mocks/2026-11-20-gta6-gta-plus-v1.png` and `-v2.png`.

## 5. Routing implication

On X, two-image cards are for hit 8+ stories with an image 1 that passes the one-second test. Everything else on X goes to Zack's video version or skips X. Facebook routing is unchanged.
