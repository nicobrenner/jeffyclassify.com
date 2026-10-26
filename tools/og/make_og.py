"""Render a jeffyclassify.com Open Graph card from a JSON spec.

Every og.png on the site was previously made by hand, which is why none of them
could be regenerated when the benchmark numbers turned out to be wrong. A card
is a published claim; it needs a source file like any other.

    python tools/og/make_og.py specs/polish-guy-was-right.json
    python tools/og/make_og.py specs/*.json            # rebuild everything

Spec (all keys optional except title and out):

    {
      "out":       "blog/polish-guy-was-right/og.png",   # relative to site root
      "title":     ["The Polish Guy", "Was Right"],      # 2nd line gets the accent
      "subtitle":  "one line of context",
      "kpis":      [{"value": "83.3%", "caption": "mean, 51 languages",
                     "color": "accent"}],
      "bars":      [{"label": "Jeffy", "value": 0.943, "display": "94%",
                     "color": "accent"}],
      "bar_note":  "optional caption under the bars",
      "bar_range": [0.70, 0.90],                         # zoom the bar axis
                                                         # (say so in bar_note)
      "footer_right": "embedding + logistic regression",
      "accent":    "#22c99a"                             # override per post
    }

Colors are hex, or a name from PALETTE. Bar `value` is 0..1; `display` is what
gets printed (so you can show "94%" or "118ms" or "<1ms").
"""

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent.parent  # site/
FONTS = Path(__file__).resolve().parent / "fonts"

W, H = 1200, 630
MARGIN = 60

PALETTE = {
    "accent":  "#22c99a",   # Jeffy green, the house accent
    "orange":  "#ff6d3a",
    "pink":    "#f472b6",
    "rose":    "#fb7185",
    "blue":    "#3b9eff",
    "purple":  "#a78bfa",
    "yellow":  "#facc15",
    "red":     "#f87171",
    "fg":      "#e8e8e6",
    "muted":   "#8a8880",
    "dim":     "#5a5a60",
    "bg":      "#0a0a0c",
    "surface": "#121216",
    "border":  "#2a2a30",
    "track":   "#33333a",
}


def color(name, default="fg"):
    if not name:
        name = default
    return PALETTE.get(name, name)


def font(weight, size):
    f = FONTS / f"IBMPlexMono-{weight}.ttf"
    if not f.exists():
        raise SystemExit(f"missing font {f}: the repo should vendor IBM Plex Mono")
    return ImageFont.truetype(str(f), size)


def text_w(draw, s, fnt):
    return draw.textbbox((0, 0), s, font=fnt)[2]


def fit(draw, s, weight, size, max_w, min_size=14):
    """Shrink until it fits. The old hand-made cards clipped their footers."""
    while size > min_size:
        fnt = font(weight, size)
        if text_w(draw, s, fnt) <= max_w:
            return fnt
        size -= 1
    return font(weight, min_size)


def grid(draw):
    for x in range(0, W, 40):
        draw.line([(x, 0), (x, H)], fill="#101014", width=1)
    for y in range(0, H, 40):
        draw.line([(0, y), (W, y)], fill="#101014", width=1)


def draw_kpis(draw, kpis, x, y, avail_w, accent):
    """KPI boxes left to right. Each box sizes to its own content."""
    gap = 20
    n = len(kpis)
    box_w = (avail_w - gap * (n - 1)) // n
    box_h = 158
    for i, k in enumerate(kpis):
        bx = x + i * (box_w + gap)
        draw.rounded_rectangle([bx, y, bx + box_w, y + box_h], radius=12,
                               fill=PALETTE["surface"], outline=PALETTE["border"], width=1)
        c = color(k.get("color"), "accent")
        if c == PALETTE["accent"] and k.get("color") is None:
            c = accent
        vf = fit(draw, k["value"], "Bold", 64, box_w - 36)
        draw.text((bx + box_w // 2, y + 56), k["value"], font=vf, fill=c, anchor="mm")
        cap = k.get("caption", "")
        if cap:
            cf = fit(draw, cap, "Regular", 16, box_w - 24)
            draw.text((bx + box_w // 2, y + 112), cap, font=cf,
                      fill=PALETTE["muted"], anchor="mm")
    return y + box_h


def draw_bars(draw, bars, x, y, w, accent, note=None, rng=None):
    """Horizontal bars with a right-hand value. Labels are right-aligned to the
    track so the tracks line up however long the names are."""
    lf = font("Regular", 19)
    label_w = max(text_w(draw, b["label"], lf) for b in bars) + 16
    vf = font("Medium", 19)
    value_w = max(text_w(draw, b.get("display", ""), vf) for b in bars) + 12
    track_x = x + label_w
    track_w = w - label_w - value_w
    # Tighten the rows as the list grows, so seven bars plus a note still clear
    # the footer rule instead of printing over it.
    row_h = 42 if len(bars) <= 5 else (38 if len(bars) == 6 else 34)
    bar_h = 15 if len(bars) <= 6 else 13

    for i, b in enumerate(bars):
        cy = y + i * row_h + row_h // 2
        draw.text((track_x - 16, cy), b["label"], font=lf,
                  fill=PALETTE["muted"], anchor="rm")
        draw.rounded_rectangle([track_x, cy - bar_h // 2, track_x + track_w, cy + bar_h // 2],
                               radius=bar_h // 2, fill=PALETTE["track"])
        c = color(b.get("color"), "accent")
        if b.get("color") is None:
            c = accent
        v = float(b["value"])
        if rng:
            # Zoom the axis so near-identical values are distinguishable. The
            # note under the bars must then say where the axis starts, or the
            # card is a lie by cropping.
            lo, hi = rng
            v = (v - lo) / (hi - lo)
        frac = max(0.0, min(1.0, v))
        # Always paint at least a stub, so a near-zero bar reads as "almost
        # nothing" rather than as a missing row.
        fill_w = max(bar_h, int(track_w * frac))
        draw.rounded_rectangle([track_x, cy - bar_h // 2, track_x + fill_w, cy + bar_h // 2],
                               radius=bar_h // 2, fill=c)
        if b.get("display"):
            draw.text((track_x + track_w + 12, cy), b["display"], font=vf, fill=c, anchor="lm")

    end = y + len(bars) * row_h
    if note:
        # Anchored to the column's left edge and bounded by its full width;
        # anchoring at track_x let a long note run off the card.
        nf = fit(draw, note, "Regular", 15, w, min_size=10)
        draw.text((x, end + 6), note, font=nf, fill=PALETTE["dim"])
        end += 24
    return end


def render(spec, out_path):
    accent = spec.get("accent") or PALETTE["accent"]
    img = Image.new("RGB", (W, H), PALETTE["bg"])
    draw = ImageDraw.Draw(img)
    grid(draw)

    # --- title -----------------------------------------------------------
    y = 56
    lines = spec["title"] if isinstance(spec["title"], list) else [spec["title"]]
    for i, line in enumerate(lines):
        tf = fit(draw, line, "Bold", 58, W - 2 * MARGIN)
        draw.text((MARGIN, y), line, font=tf,
                  fill=accent if i else PALETTE["fg"])
        y += tf.size + 12

    sub = spec.get("subtitle")
    if sub:
        sf = fit(draw, sub, "Regular", 21, W - 2 * MARGIN)
        draw.text((MARGIN, y + 6), sub, font=sf, fill=PALETTE["muted"])
        y += sf.size + 20

    # --- body: kpis left, bars right -------------------------------------
    body_y = max(y + 18, 236)
    kpis = spec.get("kpis") or []
    bars = spec.get("bars") or []
    footer_y = H - 78

    if kpis and bars:
        split = 560
        draw_kpis(draw, kpis, MARGIN, body_y, split - MARGIN, accent)
        draw_bars(draw, bars, split + 40, body_y, W - MARGIN - split - 40,
                  accent, spec.get("bar_note"), spec.get("bar_range"))
    elif kpis:
        draw_kpis(draw, kpis, MARGIN, body_y, W - 2 * MARGIN, accent)
    elif bars:
        # Centre a bars-only card in the space that is actually left.
        avail = footer_y - body_y - 20
        row_h = 42
        needed = len(bars) * row_h + (26 if spec.get("bar_note") else 0)
        draw_bars(draw, bars, MARGIN, body_y + max(0, (avail - needed) // 2),
                  W - 2 * MARGIN, accent, spec.get("bar_note"), spec.get("bar_range"))

    # --- footer ----------------------------------------------------------
    draw.line([(MARGIN, footer_y), (W - MARGIN, footer_y)], fill=PALETTE["border"], width=1)
    ff = font("SemiBold", 20)
    draw.text((MARGIN, footer_y + 26), "jeffyclassify.com", font=ff, fill=accent, anchor="lm")
    fr = spec.get("footer_right", "embedding + logistic regression")
    if fr:
        rf = fit(draw, fr, "Regular", 18,
                 W - 2 * MARGIN - text_w(draw, "jeffyclassify.com", ff) - 40)
        draw.text((W - MARGIN, footer_y + 26), fr, font=rf,
                  fill=PALETTE["muted"], anchor="rm")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "PNG", optimize=True)
    return out_path


def main(argv):
    if not argv:
        raise SystemExit(__doc__)
    for s in argv:
        spec = json.loads(Path(s).read_text())
        out = ROOT / spec["out"]
        render(spec, out)
        kb = out.stat().st_size / 1024
        print(f"{Path(s).name:40s} -> {spec['out']}  ({kb:.0f} KB)")


if __name__ == "__main__":
    main(sys.argv[1:])
