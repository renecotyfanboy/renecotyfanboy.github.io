"""Site-matched interactive charts, for notebooks rendered into the site.

`xy` (https://github.com/reflex-dev/xy) exports a chart as a *complete* HTML
document — doctype, head, inline engine, the lot — with no external requests.
That can't be pasted into a page, so a chart is written to public/charts/ and
embedded as an iframe. The isolation is a feature: the chart's stylesheet and
the site's can't reach each other, which matters for a pre-1.0 library.

Usage in a MyST notebook cell:

    ```{code-cell} python
    import xysite

    chart = xy.scatter_chart(xy.scatter(x, y), xysite.theme())
    xysite.embed(chart, "counts-vs-bias", caption="Drag to zoom.")
    ```

Add the `remove-input` cell tag if the plotting code should not be shown.
"""

from __future__ import annotations

import hashlib
import html
import os
import re
from pathlib import Path

import xy
from IPython.display import Markdown, display

ROOT = Path(__file__).resolve().parent.parent
CHARTS = ROOT / "public" / "charts"


def _post() -> str:
    """The slug of the notebook being rendered.

    Set by scripts/build_notebooks.py, which renders each document in its own
    execution. Charts are namespaced by it, so two notebooks using the same
    chart name cannot silently overwrite each other's output.
    """
    post = os.environ.get("XYSITE_POST", "").strip()
    if not post:
        raise RuntimeError(
            "XYSITE_POST is not set — render through "
            "`python3 scripts/build_notebooks.py`."
        )
    return post


# Mirrors the tokens in src/styles/global.css. Keep the two in step.
INK_850 = "#101216"
INK_700 = "#23262e"
LINE = "#2a2e37"
FOG_300 = "#a8adb7"
GOLD = "#e8b45c"

PALETTE = [
    "#e8b45c",  # gold
    "#d4441f",  # ember
    "#5ec8c0",  # teal
    "#a184d6",  # violet
    "#ef7d2e",  # flare
    "#6fa8dc",  # blue
    "#f3d29a",  # gold soft
    "#8c2f1a",  # deep
]

# xy inlines its whole engine in the first <script> of every document it
# exports. Three charts in one post therefore ship it three times, on three
# URLs the HTTP cache cannot share, so it is hoisted into one hashed file.
_ENGINE_RE = re.compile(r"<script>\s*(var xy=.*?)</script>", re.DOTALL)

# xy's exported CSP allows inline scripts only, and no font source beyond
# data:. Both have to admit 'self' once the engine is an external file and the
# document pulls the site's fonts from /fonts/ (see _CSS below).
_CSP_PATCHES = (
    ("script-src 'unsafe-inline'", "script-src 'self' 'unsafe-inline'"),
    ("font-src data:", "font-src 'self' data:"),
)


def _externalise_engine(doc: str) -> str:
    """Move the inline engine of `doc` into a shared file, and link to it.

    Returns the document unchanged if xy's export shape stops matching, so a
    library upgrade degrades to the old duplicated-but-working output.
    """
    match = _ENGINE_RE.search(doc)
    if match is None:
        return doc

    engine = match.group(1)
    digest = hashlib.sha256(engine.encode("utf-8")).hexdigest()[:16]
    name = f"xy-engine.{digest}.js"

    CHARTS.mkdir(parents=True, exist_ok=True)
    target = CHARTS / name
    if not target.exists():
        target.write_text(engine, encoding="utf-8")
        # Drop engines from a previous xy version: charts are regenerated on
        # every build, so nothing can still be pointing at them.
        for stale in CHARTS.glob("xy-engine.*.js"):
            if stale.name != name:
                stale.unlink()

    doc = doc[: match.start()] + f'<script src="/charts/{name}"></script>' + doc[match.end() :]
    for old, new in _CSP_PATCHES:
        doc = doc.replace(old, new)
    return doc


# Injected into the exported document. The iframe is same-origin, so it can
# pull the site's subset Computer Modern straight from /fonts/.
_CSS = f"""
@font-face {{
  font-family: "CMU Serif";
  font-style: normal;
  font-weight: 400;
  font-display: swap;
  src: url("/fonts/cmu-serif-500-roman.woff2") format("woff2");
}}
@font-face {{
  font-family: "CMU Serif";
  font-style: normal;
  font-weight: 700;
  font-display: swap;
  src: url("/fonts/cmu-serif-700-roman.woff2") format("woff2");
}}
html, body {{
  margin: 0;
  padding: 0;
  /* The chart is sized 100%/100%, so the document has to have a height for it
     to resolve against. */
  height: 100%;
  overflow: hidden;
  background: {INK_850};
  font-family: "CMU Serif", Georgia, serif;
}}
/* xy mounts into this div; it needs a resolved height of its own, otherwise a
   chart sized 100% collapses to its intrinsic height. */
#chart {{
  display: block;
  width: 100%;
  height: 100%;
}}
"""


def theme(**overrides) -> xy.Theme:
    """The site theme. Pass through to `xy.theme` to override any token."""
    style = {"font_family": "'CMU Serif', Georgia, serif"}
    style.update(overrides.pop("style", None) or {})

    tokens = dict(
        background=INK_850,
        plot_background=INK_850,
        grid_color=INK_700,
        axis_color=LINE,
        text_color=FOG_300,
        crosshair_color=GOLD,
        selection_color=GOLD,
        palette=PALETTE,
    )
    tokens.update(overrides)
    return xy.theme(style=style, **tokens)


def embed(
    chart,
    name: str,
    *,
    caption: str | None = None,
    height: int = 420,
    responsive: bool = True,
) -> None:
    """Write `chart` to public/charts/<post>/<name>.html and emit the markup.

    Emits a <figure>, so the chart picks up the site's wide breakout and
    caption styling like any other figure.

    `height` sizes the iframe; the chart is stretched to fill it. Pass
    `responsive=False` to keep a chart's own fixed width and height instead.
    """
    if "/" in name or name.startswith("."):
        raise ValueError(f"chart name must be a plain filename stem, got {name!r}")

    if responsive:
        # xy defaults to a fixed 900x420 card, which would sit in a corner of
        # the iframe. Fill it instead, and let the iframe own the dimensions.
        chart.width = "100%"
        chart.height = "100%"

    post = _post()
    target = CHARTS / post / f"{name}.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        _externalise_engine(chart.to_html(custom_css=_CSS)), encoding="utf-8"
    )

    title = caption or f"Interactive chart: {name}"
    figcaption = f"<figcaption>{html.escape(caption)}</figcaption>" if caption else ""

    # `display(Markdown(...))` rather than `print(...)`: nbconvert renders
    # stdout as an indented literal block, which would show the markup instead
    # of embedding it. A text/markdown output is passed through verbatim.
    display(
        Markdown(
            f'<figure id="fig-{html.escape(name, quote=True)}">'
            f'<iframe class="xy-embed" src="/charts/{post}/{name}.html"'
            f' height="{int(height)}" loading="lazy"'
            f' title="{html.escape(title, quote=True)}"></iframe>'
            f"{figcaption}"
            f"</figure>"
        )
    )
