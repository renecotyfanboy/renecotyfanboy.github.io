# /// script
# requires-python = ">=3.12"
# dependencies = ["marimo==0.25.0"]
# [tool.marimo.display]
# theme = "dark"
# ///

import marimo

__generated_with = "0.25.0"
app = marimo.App(
    width="medium",
    app_title="Counting photons",
    css_file="interactive/theme.css",
)


@app.cell
def _():
    import math
    import random
    import statistics
    from collections import Counter

    import marimo as mo

    return Counter, math, mo, random, statistics


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Counting photons

    A steady source does not give the same number of photons in every
    exposure. Change its brightness and watch the counting noise change.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    rate = mo.ui.slider(
        start=1, stop=40, step=1, value=8,
        label="Expected photons per exposure", show_value=True, full_width=True,
    )
    exposures = mo.ui.slider(
        start=100, stop=2000, step=100, value=800,
        label="Number of exposures", show_value=True, full_width=True,
    )
    mo.vstack([rate, exposures], gap=1.5)
    return exposures, rate


@app.cell
def _(exposures, math, random, rate):
    # Knuth's Poisson sampler, using only Python's standard library.
    # Fixing the seed makes comparisons reproducible.
    rng = random.Random(42)
    expected = rate.value
    draws = []
    for _ in range(exposures.value):
        _product, _count = 1.0, 0
        while _product > math.exp(-expected):
            _product *= rng.random()
            _count += 1
        draws.append(_count - 1)
    return draws, expected


@app.cell(hide_code=True)
def _(Counter, draws, expected, math, mo, statistics):
    _histogram = Counter(draws)
    _last = max(max(draws), math.ceil(expected + 5 * math.sqrt(expected)))
    _probabilities = [math.exp(-expected)]
    for _k in range(1, _last + 1):
        _probabilities.append(_probabilities[-1] * expected / _k)

    _top = max(max(_histogram.values()) / len(draws), max(_probabilities)) * 1.15
    _width, _height = 620, 220
    _bar_width = _width / (_last + 1)
    _bars, _grid, _ticks, _points = [], [], [], []
    for _i in range(5):
        _y = 35 + _height * _i / 4
        _grid.append(
            f'<line x1="58" x2="678" y1="{_y}" y2="{_y}" stroke="#2a2e37"/>'
            f'<text x="48" y="{_y + 4}" text-anchor="end">{_top * (1 - _i / 4):.0%}</text>'
        )
    for _k, _probability in enumerate(_probabilities):
        _x = 58 + _k * _bar_width
        _h = _histogram[_k] / len(draws) / _top * _height
        _bars.append(
            f'<rect x="{_x + 1:.2f}" y="{255 - _h:.2f}" '
            f'width="{max(1, _bar_width - 2):.2f}" height="{_h:.2f}" '
            f'fill="#e8b45c" fill-opacity="0.72" rx="1">'
            f'<title>{_k} photons: {_histogram[_k]} exposures</title></rect>'
        )
        _points.append(f'{_x + _bar_width / 2:.2f},{255 - _probability / _top * _height:.2f}')
        if _k % max(1, math.ceil((_last + 1) / 10)) == 0:
            _ticks.append(f'<text x="{_x + _bar_width / 2:.2f}" y="278" text-anchor="middle">{_k}</text>')

    _chart = mo.Html(
        f'<svg viewBox="0 0 720 318" role="img" '
        f'aria-label="Photon-count histogram for {len(draws)} exposures with expected count {expected}" '
        f'style="width:100%;height:auto;font:13px var(--marimo-monospace-font);fill:#a8adb7">'
        f'<text x="58" y="18">Fraction of exposures</text>'
        f'{"".join(_grid)}{"".join(_bars)}'
        f'<polyline points="{" ".join(_points)}" fill="none" stroke="#65c7bd" stroke-width="2.5"/>'
        f'{"".join(_ticks)}<text x="368" y="310" text-anchor="middle">Photons per exposure</text></svg>'
    )
    mo.vstack([
        _chart,
        mo.Html('<p class="chart-legend"><span style="color:#e8b45c">■ Simulated exposures</span>'
                ' <span style="color:#65c7bd">— Poisson prediction</span></p>'),
        mo.md(f"""
        | Expected mean | Measured mean | Measured standard deviation |
        | :--- | :--- | :--- |
        | {expected:.2f} | {statistics.mean(draws):.2f} | {statistics.pstdev(draws):.2f} |
        """),
    ])
    return


@app.cell(hide_code=True)
def _(expected, math, mo):
    mo.md(
        f"""
        **What changes?** At {expected} expected photons, the theoretical relative
        scatter of a single exposure is **{1 / math.sqrt(expected):.1%}**
        ($1 / \\sqrt{{\\lambda}}$). The chance of recording no photons is
        **{math.exp(-expected):.2%}**.

        More exposures make the histogram smoother. More photons per exposure
        reduce the *relative* noise. The random seed stays fixed so each setting
        gives the same result.
        """
    )
    return


if __name__ == "__main__":
    app.run()
