#!/usr/bin/env bash
# Build a deployable copy of the site with some posts held back, and refuse to
# ship it if anything still points at them.
#
#   tools/stage_deploy.sh blog/polish-guy-was-right
#   tools/stage_deploy.sh                      # nothing held back
#
# Prints the staging directory. Deploy with:
#   source ~/.jeffy-ts/cf-env.sh
#   wrangler pages deploy "$STAGE" --project-name jeffy-landing --branch main --commit-dirty=true
#
# Why this exists: on 2026-10-26 a post was held back by excluding its directory
# from the upload, but its card stayed on /blog/ and its URL stayed in
# sitemap.xml. The result was a 404 reachable from the blog index, live, for
# days. Excluding a page is not the same as unlinking it, and only a check can
# tell the difference.

set -euo pipefail

SITE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAGE="${STAGE_DIR:-${TMPDIR:-/tmp}/jeffy-site-stage}"

rm -rf "$STAGE"
mkdir -p "$STAGE"

EXCLUDES=(--exclude='.git' --exclude='.wrangler' --exclude='tools')
for held in "$@"; do
  EXCLUDES+=(--exclude="${held%/}")
done
rsync -a "${EXCLUDES[@]}" "$SITE"/ "$STAGE"/

# Strip every reference to a held-back page: its card on any index, and its
# sitemap entry. Done on the staging copy only, so the repo keeps the real page.
for held in "$@"; do
  slug="$(basename "${held%/}")"

  python3 - "$STAGE" "$slug" <<'PY'
import re, sys
from pathlib import Path
stage, slug = Path(sys.argv[1]), sys.argv[2]

# sitemap: drop the whole <url> block that mentions the slug
sm = stage / "sitemap.xml"
if sm.exists():
    t = sm.read_text()
    t2 = re.sub(r'\s*<url>(?:(?!</url>).)*?' + re.escape(slug) + r'(?:(?!</url>).)*?</url>',
                '', t, flags=re.S)
    if t2 != t:
        sm.write_text(t2)
        print(f"  sitemap: removed {slug}")

# any index page: drop the <a ...slug...> card, matching nesting
for page in stage.rglob("index.html"):
    t = page.read_text()
    if slug not in t:
        continue
    out, i, cut = [], 0, 0
    while True:
        m = re.search(r'<a\s[^>]*href="[^"]*' + re.escape(slug) + r'/?"[^>]*>', t[i:])
        if not m:
            break
        start = i + m.start()
        # walk forward counting <a>/</a> so a nested anchor cannot end it early
        j, depth = i + m.end(), 1
        while depth and j < len(t):
            nxt = re.search(r'</?a\b', t[j:])
            if not nxt:
                break
            j += nxt.end()
            depth += -1 if t[j - 2:j] == '/a' else 1
        j = t.find('>', j - 1) + 1
        out.append(t[i:start]); i = j; cut += 1
    if cut:
        out.append(t[i:])
        page.write_text(''.join(out))
        print(f"  {page.relative_to(stage)}: removed {cut} link(s) to {slug}")
PY
done

# Refuse to ship a dangling reference. Checks the staged bytes, not the repo.
fail=0
for held in "$@"; do
  slug="$(basename "${held%/}")"
  hits=$(grep -rl "$slug" "$STAGE" 2>/dev/null || true)
  if [ -n "$hits" ]; then
    echo "ERROR: '$slug' is held back but still referenced in:" >&2
    echo "$hits" | sed 's/^/  /' >&2
    fail=1
  fi
done

# And catch the general case: any internal link to a page that is not there.
python3 - "$STAGE" <<'PY'
import re, sys
from pathlib import Path
stage = Path(sys.argv[1])
bad = []
for page in stage.rglob("*.html"):
    for href in re.findall(r'href="([^"#?:]+)"', page.read_text()):
        if href.startswith(("http", "//", "mailto:", "tel:")):
            continue
        base = stage if href.startswith("/") else page.parent
        t = (base / href.lstrip("/")).resolve()
        if t.is_dir() or href.endswith("/"):
            t = t / "index.html"
        if not t.exists():
            bad.append(f"{page.relative_to(stage)} -> {href}")
if bad:
    print("ERROR: internal links with no target in the staged site:", file=sys.stderr)
    for b in sorted(set(bad)):
        print("  " + b, file=sys.stderr)
    sys.exit(1)
print("link check: no dangling internal links")
PY
link_rc=$?

[ "$fail" = 0 ] && [ "$link_rc" = 0 ] || { echo "staging FAILED, nothing to deploy" >&2; exit 1; }

echo
echo "staged at: $STAGE"
