"""Render the 51-language accuracy chart for the Polish post, as inline SVG.

Source of truth is data/eval_results/labse_51_results.csv in the jeffy repo, so
the chart cannot drift from the numbers the post quotes. Re-run it and paste
the output if the eval is ever re-run.

    python tools/og/make_lang_chart.py > /tmp/chart.svg

Deliberately static SVG rather than Chart.js: it is the first thing on the page,
it must paint before anything loads, and this post already runs a canvas.
"""

import csv
import statistics
import sys
from pathlib import Path

CSV = Path.home() / "work/jeffy/data/eval_results/labse_51_results.csv"

# Published reference for the same 51 MASSIVE languages, quoted in the post.
XLMR_MEAN = 85.1

W, H = 720, 284
# PAD_L leaves a gutter for the y labels; without it they sit behind the bars.
# PAD_T leaves room for the legend, which is where the two highlighted
# languages are named: callouts over rank 2 and rank 4 collided with each other.
PAD_L, PAD_R, PAD_T, PAD_B = 40, 8, 54, 30
LO, HI = 74.0, 87.5          # y range, chosen to show the spread without lying
HIGHLIGHT = {"pl": "#ff6d3a", "en": "#20d49a"}


def main():
    rows = list(csv.DictReader(open(CSV)))
    data = sorted(((r["language"], float(r["test_accuracy"]) * 100) for r in rows),
                  key=lambda x: -x[1])
    mean = statistics.mean(a for _, a in data)
    n = len(data)

    plot_w = W - PAD_L - PAD_R
    plot_h = H - PAD_T - PAD_B
    slot = plot_w / n
    bw = slot * 0.66

    def y_of(v):
        return PAD_T + plot_h * (1 - (v - LO) / (HI - LO))

    out = []
    a = out.append
    a(f'<svg class="langchart" viewBox="0 0 {W} {H}" width="100%" '
      f'role="img" aria-labelledby="lc-title lc-desc" '
      f'xmlns="http://www.w3.org/2000/svg">')
    a(f'<title id="lc-title">Accuracy on MASSIVE intent classification across {n} languages</title>')
    a(f'<desc id="lc-desc">Frozen LaBSE embeddings plus logistic regression. '
      f'Every language scores between {data[-1][1]:.1f} and {data[0][1]:.1f} percent. '
      f'Polish is {[i for i,(l,_) in enumerate(data) if l=="pl"][0]+1}th of {n}.</desc>')

    # legend, so the two highlighted languages are named once, out of the bars' way
    lx = PAD_L
    for lang, name in (("en", "English"), ("pl", "Polish")):
        acc = dict(data)[lang]
        rank = [i for i, (l, _) in enumerate(data) if l == lang][0] + 1
        a(f'<rect x="{lx}" y="16" width="9" height="9" rx="2" fill="{HIGHLIGHT[lang]}"/>')
        label = f"{name} {acc:.1f}%  (#{rank})"
        a(f'<text x="{lx+15}" y="24.5" class="lc-legend" fill="{HIGHLIGHT[lang]}">{label}</text>')
        lx += 15 + len(label) * 6.9 + 24

    # gridlines
    for v in (76, 80, 84):
        y = y_of(v)
        a(f'<line x1="{PAD_L}" y1="{y:.1f}" x2="{W-PAD_R}" y2="{y:.1f}" '
          f'stroke="#2a2a30" stroke-width="1"/>')
        a(f'<text x="{PAD_L-6}" y="{y+3.5:.1f}" class="lc-grid" text-anchor="end">{v}%</text>')

    # bars
    for i, (lang, acc) in enumerate(data):
        x = PAD_L + i * slot + (slot - bw) / 2
        y = y_of(acc)
        h = (PAD_T + plot_h) - y
        fill = HIGHLIGHT.get(lang, "#3c3c45")
        cls = " lc-hl" if lang in HIGHLIGHT else ""
        a(f'<rect class="lc-bar{cls}" x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" '
          f'height="{h:.1f}" rx="1.5" fill="{fill}">'
          f'<title>{lang}: {acc:.2f}%</title></rect>')

    # reference lines, both labelled as means so nothing reads as a per-language claim
    for v, label, col, dash in (
        (XLMR_MEAN, f"fine-tuned XLM-R, mean {XLMR_MEAN}%", "#8a8880", "5 4"),
        (mean,      f"Jeffy, mean {mean:.1f}%",             "#20d49a", "5 4"),
    ):
        y = y_of(v)
        a(f'<line x1="{PAD_L}" y1="{y:.1f}" x2="{W-PAD_R}" y2="{y:.1f}" '
          f'stroke="{col}" stroke-width="1.5" stroke-dasharray="{dash}"/>')
        a(f'<text x="{W-PAD_R-2}" y="{y-6:.1f}" class="lc-ref" fill="{col}" '
          f'text-anchor="end">{label}</text>')

    # x axis: rank, not 51 unreadable tick labels
    base = PAD_T + plot_h
    a(f'<line x1="{PAD_L}" y1="{base}" x2="{W-PAD_R}" y2="{base}" stroke="#44444e" stroke-width="1"/>')
    a(f'<text x="{PAD_L}" y="{base+18}" class="lc-axis">best: {data[0][0]} {data[0][1]:.1f}%</text>')
    a(f'<text x="{W/2:.0f}" y="{base+18}" class="lc-axis" text-anchor="middle">'
      f'{n} languages, ranked</text>')
    a(f'<text x="{W-PAD_R}" y="{base+18}" class="lc-axis" text-anchor="end">'
      f'worst: {data[-1][0]} {data[-1][1]:.1f}%</text>')
    # The provenance line lives in the figcaption, not here: inside the SVG it
    # scales with the viewBox and becomes unreadable at phone width, and the
    # denominator is exactly the thing that must never be unreadable.
    a('</svg>')

    sys.stdout.write("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
