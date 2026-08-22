#!/usr/bin/env python3
"""Flag label text that overflows its enclosing rect in the hand-authored SVGs.

Width model: a label is `len(text) * font-size * 0.602` px wide. 0.602 em is the
advance width of the Menlo / SFMono / Consolas family every diagram declares, and
one constant covers every glyph only because those families are monospaced. So
this lint is valid for monospace SVGs only -- point it at a diagram set drawn in
a proportional face and the numbers are noise, because a real check would need
per-glyph metrics from the font file.

Font size for a label, highest priority first:

  1. `font-size` attribute on the `<text>` element
  2. `font-size` from a `<style>` block class rule matched against `class=`
  3. `font-size` inherited from an enclosing `<g>`
  4. `font-size` on the root `<svg>`, else 13

A rect encloses a label when the baseline falls inside it vertically and the
label's horizontal midpoint falls inside it; of the rects that qualify, the
smallest by area wins. Labels that land in no rect are wire annotations and go
unchecked -- they have no box to overflow. An enclosed label must clear both
rect edges by MIN_INSET px.

Usage: `svg_fitment.py [path ...]`. With no arguments it lints the whole repo:
fault diagrams, routine diagrams, and assets/*.svg. Exits 1 if any label overflows.
"""

import html
import re
import sys
from pathlib import Path

ADVANCE_EM = 0.602  # monospace advance width, in em
MIN_INSET = 4.0  # px a label must keep clear of each rect edge
TOLERANCE = 0.5  # px of slack before an overflow is worth reporting
DEFAULT_FONT_SIZE = 13.0  # px, when no ancestor declares one

REPO_ROOT = Path(__file__).resolve().parents[2]
SCOPE = ("faults/*/*/diagram.svg", "routines/**/diagram.svg", "assets/*.svg")

TAG_RE = re.compile(r"<(/?)(svg|g|text|rect)\b([^>]*)>", re.S)
ATTR_RE = re.compile(r'([\w:.-]+)\s*=\s*"([^"]*)"')
STYLE_RE = re.compile(r"<style\b[^>]*>(.*?)</style>", re.S)
RULE_RE = re.compile(r"([^{}]+)\{([^{}]*)\}", re.S)
CLASS_SELECTOR_RE = re.compile(r"^\.([\w-]+)$")
DECL_RE = re.compile(r"(?:^|;)\s*font-size\s*:\s*([^;]+)")
LENGTH_RE = re.compile(r"^([\d.]+)(?:px)?$")
MARKUP_RE = re.compile(r"<[^>]+>")


def parse_length(value):
    """Return `value` as px, or None if it is absent or in a unit we can't resolve."""
    match = LENGTH_RE.match((value or "").strip())
    return float(match.group(1)) if match else None


def class_font_sizes(source):
    """Map class name -> font size in px, for every `.cls { font-size: ... }` rule."""
    sizes = {}
    for block in STYLE_RE.findall(source):
        for selectors, body in RULE_RE.findall(block):
            declaration = DECL_RE.search(body)
            if not declaration:
                continue
            size = parse_length(declaration.group(1))
            if size is None:
                continue
            for selector in selectors.split(","):
                match = CLASS_SELECTOR_RE.match(selector.strip())
                if match:
                    sizes[match.group(1)] = size
    return sizes


def text_font_size(attrs, class_sizes, inherited):
    size = parse_length(attrs.get("font-size"))
    if size is not None:
        return size
    # Under the real cascade a class rule outranks a presentation attribute, but
    # these diagrams use the attribute as a deliberate per-label override.
    for name in attrs.get("class", "").split():
        if name in class_sizes:
            size = class_sizes[name]
    return size if size is not None else inherited


def label_span(x, width, anchor):
    """Return (left, right) of a label drawn at `x` under `text-anchor`."""
    if anchor == "end":
        return x - width, x
    if anchor == "middle":
        return x - width / 2, x + width / 2
    return x, x + width


def enclosing_rect(rects, left, right, baseline):
    midpoint = (left + right) / 2
    best = None
    for rect in rects:
        rx, ry, rw, rh = rect
        if ry <= baseline <= ry + rh and rx <= midpoint <= rx + rw:
            if best is None or rw * rh < best[2] * best[3]:
                best = rect
    return best


def audit(path):
    """Return a list of (label, overflow_px, side, box_width) for one SVG."""
    source = path.read_text(encoding="utf-8")
    class_sizes = class_font_sizes(source)
    rects = []
    labels = []
    font_sizes = [DEFAULT_FONT_SIZE]

    for match in TAG_RE.finditer(source):
        closing, name, raw_attrs = match.group(1), match.group(2), match.group(3)
        if closing:
            if name in ("svg", "g") and len(font_sizes) > 1:
                font_sizes.pop()
            continue
        attrs = dict(ATTR_RE.findall(raw_attrs))
        self_closing = raw_attrs.rstrip().endswith("/")

        if name in ("svg", "g"):
            size = parse_length(attrs.get("font-size"))
            if not self_closing:
                font_sizes.append(size if size is not None else font_sizes[-1])
            continue

        if name == "rect":
            try:
                rects.append(
                    (
                        float(attrs["x"]),
                        float(attrs["y"]),
                        float(attrs["width"]),
                        float(attrs["height"]),
                    )
                )
            except (KeyError, ValueError):
                pass  # a rect without a literal box can't enclose anything
            continue

        end = source.find("</text>", match.end())
        if self_closing or end < 0:
            continue
        text = html.unescape(MARKUP_RE.sub("", source[match.end() : end])).strip()
        if not text:
            continue
        try:
            x, baseline = float(attrs["x"]), float(attrs["y"])
        except (KeyError, ValueError):
            continue  # positioned by transform or dx/dy; out of this model's reach
        size = text_font_size(attrs, class_sizes, font_sizes[-1])
        width = len(text) * size * ADVANCE_EM
        left, right = label_span(x, width, attrs.get("text-anchor", "start"))
        labels.append((text, left, right, baseline))

    violations = []
    for text, left, right, baseline in labels:
        rect = enclosing_rect(rects, left, right, baseline)
        if rect is None:
            continue
        rx, _, rw, _ = rect
        for side, overflow in (
            ("left", (rx + MIN_INSET) - left),
            ("right", right - (rx + rw - MIN_INSET)),
        ):
            if overflow > TOLERANCE:
                violations.append((text, overflow, side, rw))
    return violations


def collect(argv):
    if argv:
        return [Path(arg) for arg in argv]
    return sorted(path for pattern in SCOPE for path in REPO_ROOT.glob(pattern))


def main(argv):
    paths = collect(argv)
    if not paths:
        print("svg fitment: no SVGs matched, check the scope globs", file=sys.stderr)
        return 1

    total = 0
    for path in paths:
        for text, overflow, side, box_width in audit(path):
            total += 1
            label = text if len(text) <= 60 else text[:57] + "..."
            print(
                f"{path}: {overflow:.1f}px past {side} inset "
                f"(box width {box_width:.0f}) -- {label!r}"
            )

    if total:
        print(f"\nsvg fitment: {total} overflowing label(s) in {len(paths)} SVG(s)")
        return 1
    print(f"svg fitment: {len(paths)} SVG(s) clean")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
