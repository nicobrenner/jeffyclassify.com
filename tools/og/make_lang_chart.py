"""Render the two language charts for the Polish post, as inline SVG.

Sources of truth, both in the jeffy repo, so the charts cannot drift from the
numbers the prose quotes:
    data/eval_results/labse_51_results.csv   our per-language accuracy
    data/eval_results/training_results.csv   xlmr_full and xlmr_zero per language

    python tools/og/make_lang_chart.py ranked > ranked.svg
    python tools/og/make_lang_chart.py zeroshot > zeroshot.svg

Static SVG rather than Chart.js: these are the first things on the page and must
paint before anything loads, and the post already runs a canvas.

Each bar carries data-* attributes; the page's own script turns them into a
tooltip on hover and on tap. SVG <title> alone is desktop-only and slow.
"""

import csv
import statistics
import sys
from pathlib import Path

REPO = Path.home() / "work/jeffy"
LABSE = REPO / "data/eval_results/labse_51_results.csv"
TRAIN = REPO / "data/eval_results/training_results.csv"

W = 720
HIGHLIGHT = {"pl": "#ff6d3a", "en": "#20d49a"}
# "Close to English" in the sense the post means: the languages a model trained
# on English already half-covers. Germanic plus Romance.
NEAR_EN = {"Germanic", "Romance"}


def load():
    labse = {}
    for r in csv.DictReader(open(LABSE)):
        code = r["language"].replace("-", "_").lower()
        labse[code] = {"acc": float(r["test_accuracy"]) * 100,
                       "n_test": int(r["n_test"]), "raw": r["language"]}
    for r in csv.DictReader(open(TRAIN)):
        code = r["language"].replace("-", "_").lower()
        if code in labse:
            labse[code]["name"] = r["name"]
            labse[code]["family"] = r["family"]
            for k in ("xlmr_full", "xlmr_zero"):
                labse[code][k] = float(r[k]) if r[k] not in ("", None) else None
    return labse


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


# ───────────────────────────── chart 1: ranked ──────────────────────────────

def ranked(d):
    H = 284
    PAD_L, PAD_R, PAD_T, PAD_B = 40, 8, 54, 30
    LO, HI = 74.0, 89.0   # fits every bar AND every XLM-R tick, so nothing clamps

    data = sorted(d.items(), key=lambda kv: -kv[1]["acc"])
    n = len(data)
    mean = statistics.mean(v["acc"] for _, v in data)
    plot_w, plot_h = W - PAD_L - PAD_R, H - PAD_T - PAD_B
    slot = plot_w / n
    bw = slot * 0.66

    def y_of(v):
        return PAD_T + plot_h * (1 - (v - LO) / (HI - LO))

    o = []; a = o.append
    a(f'<svg class="langchart" viewBox="0 0 {W} {H}" width="100%" role="img" '
      f'aria-labelledby="lc1-t lc1-d" xmlns="http://www.w3.org/2000/svg">')
    a(f'<title id="lc1-t">Accuracy across {n} languages</title>')
    a(f'<desc id="lc1-d">Frozen LaBSE embeddings plus logistic regression on MASSIVE '
      f'intent classification. Every language scores between {data[-1][1]["acc"]:.1f} and '
      f'{data[0][1]["acc"]:.1f} percent. Polish is 4th of {n}.</desc>')

    lx = PAD_L
    for code, name in (("en", "English"), ("pl", "Polish")):
        v = d[code]; rank = [i for i, (c, _) in enumerate(data) if c == code][0] + 1
        a(f'<rect x="{lx}" y="16" width="9" height="9" rx="2" fill="{HIGHLIGHT[code]}"/>')
        lab = f'{name} {v["acc"]:.1f}%  (#{rank})'
        a(f'<text x="{lx+15}" y="24.5" class="lc-legend" fill="{HIGHLIGHT[code]}">{lab}</text>')
        lx += 15 + len(lab) * 6.9 + 24
    a(f'<rect x="{lx}" y="20.5" width="11" height="2" fill="#6b6b76"/>')
    a(f'<text x="{lx+17}" y="24.5" class="lc-legend" fill="#8a8880">fine-tuned XLM-R</text>')

    for v in (76, 80, 84, 88):
        y = y_of(v)
        a(f'<line x1="{PAD_L}" y1="{y:.1f}" x2="{W-PAD_R}" y2="{y:.1f}" stroke="#2a2a30"/>')
        a(f'<text x="{PAD_L-6}" y="{y+3.5:.1f}" class="lc-grid" text-anchor="end">{v}%</text>')

    base = PAD_T + plot_h
    for i, (code, v) in enumerate(data):
        x = PAD_L + i * slot + (slot - bw) / 2
        y = y_of(v["acc"])
        fill = HIGHLIGHT.get(code, "#3c3c45")
        a(f'<rect class="lc-bar" x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" '
          f'height="{base-y:.1f}" rx="1.5" fill="{fill}" '
          f'data-name="{esc(v.get("name", code))}" data-code="{v["raw"]}" '
          f'data-acc="{v["acc"]:.2f}" data-rank="{i+1}" data-n="{n}" '
          f'data-xlmr="{v["xlmr_full"]:.1f}" data-family="{esc(v.get("family",""))}"/>')
        # Per-language fine-tuned XLM-R, drawn as a tick on each bar. This used
        # to be a single mean line across the whole chart, which invited exactly
        # the comparison it should not: one language's bar against 51 languages'
        # average. The honest version is per-language or nothing.
        ty = y_of(v["xlmr_full"])
        a(f'<rect x="{x-0.8:.1f}" y="{ty-1:.1f}" width="{bw+1.6:.1f}" height="2" '
          f'fill="#6b6b76" opacity="0.85" pointer-events="none"/>')

    y = y_of(mean)
    a(f'<line x1="{PAD_L}" y1="{y:.1f}" x2="{W-PAD_R}" y2="{y:.1f}" stroke="#20d49a" '
      f'stroke-width="1.5" stroke-dasharray="5 4"/>')
    a(f'<text x="{W-PAD_R-2}" y="{y-6:.1f}" class="lc-ref" fill="#20d49a" '
      f'text-anchor="end">our mean {mean:.1f}%</text>')

    a(f'<line x1="{PAD_L}" y1="{base}" x2="{W-PAD_R}" y2="{base}" stroke="#44444e"/>')
    a(f'<text x="{PAD_L}" y="{base+18}" class="lc-axis">best: {data[0][1].get("name")} '
      f'{data[0][1]["acc"]:.1f}%</text>')
    a(f'<text x="{W/2:.0f}" y="{base+18}" class="lc-axis" text-anchor="middle">'
      f'{n} languages, ranked</text>')
    a(f'<text x="{W-PAD_R}" y="{base+18}" class="lc-axis" text-anchor="end">'
      f'worst: {data[-1][1].get("name")} {data[-1][1]["acc"]:.1f}%</text>')
    a('</svg>')
    return "\n".join(o)


# ──────────────────── chart 2: vs zero-shot cross-lingual ───────────────────

def zeroshot(d):
    """The buried lede. 'Wait for the frontier to reach your language' is the
    zero-shot transfer story, and it works for Swedish and fails for Japanese."""
    H = 300
    PAD_L, PAD_R, PAD_T, PAD_B = 40, 8, 58, 44

    rows = [(c, v) for c, v in d.items() if v.get("xlmr_zero") is not None]
    for c, v in rows:
        v["gap"] = v["acc"] - v["xlmr_zero"]
    rows.sort(key=lambda kv: -kv[1]["gap"])
    n = len(rows)
    mean = statistics.mean(v["gap"] for _, v in rows)
    hi = max(v["gap"] for _, v in rows)

    plot_w, plot_h = W - PAD_L - PAD_R, H - PAD_T - PAD_B
    slot = plot_w / n
    bw = slot * 0.66
    base = PAD_T + plot_h

    def y_of(g):
        return base - plot_h * (g / (hi * 1.06))

    o = []; a = o.append
    a(f'<svg class="langchart" viewBox="0 0 {W} {H}" width="100%" role="img" '
      f'aria-labelledby="lc2-t lc2-d" xmlns="http://www.w3.org/2000/svg">')
    a(f'<title id="lc2-t">Our advantage over zero-shot cross-lingual transfer</title>')
    a(f'<desc id="lc2-d">A small head trained on each language beats XLM-R trained on '
      f'English only in all {n} non-English languages, by {mean:.1f} points on average. '
      f'The advantage is smallest for Germanic and Romance languages and largest for '
      f'languages furthest from English, reaching {hi:.0f} points for Japanese.</desc>')

    a(f'<rect x="{PAD_L}" y="16" width="9" height="9" rx="2" fill="#ff6d3a"/>')
    a(f'<text x="{PAD_L+15}" y="24.5" class="lc-legend" fill="#ff6d3a">'
      f'far from English</text>')
    a(f'<rect x="{PAD_L+170}" y="16" width="9" height="9" rx="2" fill="#4a7fb5"/>')
    a(f'<text x="{PAD_L+185}" y="24.5" class="lc-legend" fill="#6d9fd4">'
      f'Germanic and Romance</text>')

    for v in (0, 10, 20, 30, 40):
        if v > hi * 1.06:
            continue
        y = y_of(v)
        a(f'<line x1="{PAD_L}" y1="{y:.1f}" x2="{W-PAD_R}" y2="{y:.1f}" '
          f'stroke="{"#44444e" if v == 0 else "#2a2a30"}"/>')
        a(f'<text x="{PAD_L-6}" y="{y+3.5:.1f}" class="lc-grid" text-anchor="end">'
          f'{"+" if v else ""}{v}</text>')

    for i, (code, v) in enumerate(rows):
        x = PAD_L + i * slot + (slot - bw) / 2
        y = y_of(v["gap"])
        near = v.get("family") in NEAR_EN
        fill = "#4a7fb5" if near else "#ff6d3a"
        a(f'<rect class="lc-bar" x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" '
          f'height="{max(1.5, base-y):.1f}" rx="1.5" fill="{fill}" '
          f'data-name="{esc(v.get("name", code))}" data-code="{v["raw"]}" '
          f'data-acc="{v["acc"]:.2f}" data-zero="{v["xlmr_zero"]:.1f}" '
          f'data-gap="{v["gap"]:.1f}" data-family="{esc(v.get("family",""))}"/>')

    y = y_of(mean)
    a(f'<line x1="{PAD_L}" y1="{y:.1f}" x2="{W-PAD_R}" y2="{y:.1f}" stroke="#20d49a" '
      f'stroke-width="1.5" stroke-dasharray="5 4"/>')
    a(f'<text x="{W-PAD_R-2}" y="{y-6:.1f}" class="lc-ref" fill="#20d49a" '
      f'text-anchor="end">mean +{mean:.1f} points</text>')

    # name the two ends, because they are the argument
    for idx, anchor, dx in ((0, "start", 4), (n - 1, "end", -4)):
        code, v = rows[idx]
        x = PAD_L + idx * slot + slot / 2
        col = "#4a7fb5" if v.get("family") in NEAR_EN else "#ff6d3a"
        bar_y = y_of(v["gap"])
        # Lift the label clear of the axis when the bar is too short to sit on,
        # and drop a leader so it still clearly belongs to that bar.
        ly = min(bar_y - 8, base - 30)
        if bar_y - ly > 12:
            a(f'<line x1="{x:.1f}" y1="{ly+4:.1f}" x2="{x:.1f}" y2="{bar_y-1:.1f}" '
              f'stroke="{col}" stroke-width="1" opacity="0.5"/>')
        a(f'<text x="{x+dx:.1f}" y="{ly:.1f}" class="lc-callout" fill="{col}" '
          f'text-anchor="{anchor}">{esc(v["name"])} +{v["gap"]:.0f}</text>')

    a(f'<text x="{PAD_L}" y="{base+20}" class="lc-axis">'
      f'{n} non-English languages, ranked by advantage</text>')
    a(f'<text x="{W-PAD_R}" y="{base+20}" class="lc-axis" text-anchor="end">'
      f'we win {sum(1 for _, v in rows if v["gap"] > 0)} of {n}</text>')
    a(f'<text x="{PAD_L}" y="{base+36}" class="lc-axis lc-sub">'
      f'points of accuracy, ours minus XLM-R trained on English only</text>')
    a('</svg>')
    return "\n".join(o)


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "ranked"
    sys.stdout.write({"ranked": ranked, "zeroshot": zeroshot}[which](load()) + "\n")
