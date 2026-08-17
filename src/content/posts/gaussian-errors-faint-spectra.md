---
title: What Gaussian errors do to a faint X-ray spectrum
description: Fitting binned counts with a χ² statistic is standard practice and quietly
  biased. A short numerical experiment on how bad it gets, and where the bias comes
  from.
date: '2026-08-16'
tags:
- statistics
- x-ray
- inference
source: notebook
draft: true
notebook: notebooks/gaussian-errors-faint-spectra.md
generated: true
---

X-ray spectra are counts. Counts are Poisson. Yet a large share of the
literature still fits them by minimising a χ² statistic, which assumes the
errors are Gaussian with a known variance — usually estimated as $\sqrt{N}$
from the data itself.

That last part is the problem. Using the observed counts to set the weights
makes bins that happened to fluctuate low look *more* certain than they are,
and the fit is dragged towards them.

Every chart below is interactive: drag to zoom, double-click to reset.


```python
import numpy as np
from scipy.optimize import minimize
from IPython.display import Markdown, display

import xy
import xysite

rng = np.random.default_rng(20260816)
GOLD, EMBER, TEAL = xysite.PALETTE[:3]
```

## A deliberately simple model

One free parameter: the normalisation of a power law with fixed photon index,
observed through a flat response over 40 bins.


```python
E = np.linspace(0.5, 10.0, 41)          # bin edges, keV
Ec = 0.5 * (E[:-1] + E[1:])             # bin centres
dE = np.diff(E)

GAMMA = 1.8                             # fixed photon index
def expected(norm):
    """Expected counts per bin for a power law of given normalisation."""
    return norm * Ec ** (-GAMMA) * dE

TRUTH = 60.0
print(f"total expected counts at truth: {expected(TRUTH).sum():.1f}")
```

    total expected counts at truth: 117.0


## Three ways to fit it

The Cash statistic is the proper Poisson likelihood. The two χ² variants differ
only in where the variance comes from: the *data* (Neyman) or the *model*
(Pearson).


```python
def cash(norm, obs):
    mu = np.clip(expected(norm), 1e-12, None)
    return 2.0 * np.sum(mu - obs * np.log(mu))

def chi2_data(norm, obs):            # Neyman: variance from the observed counts
    var = np.clip(obs, 1.0, None)
    return np.sum((obs - expected(norm)) ** 2 / var)

def chi2_model(norm, obs):           # Pearson: variance from the model
    mu = np.clip(expected(norm), 1e-12, None)
    return np.sum((obs - mu) ** 2 / mu)

# Charts render in the browser, so labels can just be Unicode.
STATS = {
    "Cash (Poisson)": cash,
    "χ² (data variance)": chi2_data,
    "χ² (model variance)": chi2_model,
}
COLORS = {name: c for name, c in zip(STATS, (GOLD, EMBER, TEAL))}

def fit(stat, obs):
    res = minimize(stat, x0=np.array([TRUTH]), args=(obs,), method="Nelder-Mead")
    return float(res.x[0])
```

## What happens over 2000 realisations


```python
N_SIM = 2000
results = {name: np.empty(N_SIM) for name in STATS}

for i in range(N_SIM):
    obs = rng.poisson(expected(TRUTH))
    for name, stat in STATS.items():
        results[name][i] = fit(stat, obs)

edges = np.linspace(40, 80, 70)

chart = xy.scatter_chart(
    *[
        xy.stairs(np.histogram(vals, bins=edges)[0], edges,
                  name=name, color=COLORS[name], width=1.8)
        for name, vals in results.items()
    ],
    xy.vline(TRUTH, text="truth", color="#8a8f99", width=1, opacity=0.9),
    xy.x_axis(label="recovered normalisation"),
    xy.y_axis(label="realisations"),
    xy.legend(loc="upper right"),
    xysite.theme(),
)

xysite.embed(
    chart,
    "estimator-distributions",
    height=420,
    caption=(
        f"Recovered normalisation over {N_SIM} simulated observations of "
        f"{expected(TRUTH).sum():.0f} counts. The Poisson likelihood sits on the "
        "truth; taking the variance from the observed counts pulls the estimate "
        "low, and taking it from the model pushes it high by a comparable amount."
    ),
)
```


<figure id="fig-estimator-distributions"><iframe class="xy-embed" src="/charts/gaussian-errors-faint-spectra/estimator-distributions.html" height="420" loading="lazy" title="Recovered normalisation over 2000 simulated observations of 117 counts. The Poisson likelihood sits on the truth; taking the variance from the observed counts pulls the estimate low, and taking it from the model pushes it high by a comparable amount."></iframe><figcaption>Recovered normalisation over 2000 simulated observations of 117 counts. The Poisson likelihood sits on the truth; taking the variance from the observed counts pulls the estimate low, and taking it from the model pushes it high by a comparable amount.</figcaption></figure>


The numbers behind the chart:


```python
import pandas as pd

summary = pd.DataFrame({
    "statistic": list(results),
    "median": [np.median(v) for v in results.values()],
    "bias %": [100 * (np.median(v) - TRUTH) / TRUTH for v in results.values()],
    "scatter %": [100 * v.std() / TRUTH for v in results.values()],
}).round(2)

# display(Markdown(...)) rather than print(...): nbconvert renders stdout as an
# indented literal block, which would show the pipe characters instead of a table.
display(Markdown(summary.to_markdown(index=False)))
```


| statistic           |   median |   bias % |   scatter % |
|:--------------------|---------:|---------:|------------:|
| Cash (Poisson)      |    59.47 |    -0.89 |        9.1  |
| χ² (data variance)  |    52.16 |   -13.07 |        9.74 |
| χ² (model variance) |    68.83 |    14.71 |       10.07 |


## The same realisation, two estimators

The histograms show the marginal distributions, but they hide the pairing: each
realisation produces *both* estimates. Plotting one against the other shows the
offset is systematic rather than noise — essentially every point sits below the
diagonal.


```python
cash_est = results["Cash (Poisson)"]
chi2_est = results["χ² (data variance)"]
lim = [40, 80]

chart = xy.scatter_chart(
    xy.scatter(cash_est, chi2_est, size=4, opacity=0.45, name="realisation"),
    xy.line(lim, lim, color="#6f7178", width=1, dash="dashed", name="equality"),
    xy.x_axis(label="Cash estimate"),
    xy.y_axis(label="χ² (data variance) estimate"),
    xysite.theme(),
)

xysite.embed(
    chart,
    "cash-vs-chi2",
    height=420,
    caption=(
        "Paired estimates from the same 2000 simulated observations; the dashed "
        "line is equality."
    ),
)
```


<figure id="fig-cash-vs-chi2"><iframe class="xy-embed" src="/charts/gaussian-errors-faint-spectra/cash-vs-chi2.html" height="420" loading="lazy" title="Paired estimates from the same 2000 simulated observations; the dashed line is equality."></iframe><figcaption>Paired estimates from the same 2000 simulated observations; the dashed line is equality.</figcaption></figure>


## Where the bias goes as the exposure grows

The χ² bias is a small-count pathology. It does not disappear so much as it
becomes negligible compared to the statistical scatter.


```python
exposures = np.array([0.5, 1, 2, 5, 10, 25, 60, 150])
bias = {name: [] for name in STATS}

for scale in exposures:
    norm_true = TRUTH * scale
    draws = {name: [] for name in STATS}
    for _ in range(300):
        obs = rng.poisson(expected(norm_true))
        for name, stat in STATS.items():
            res = minimize(stat, x0=np.array([norm_true]), args=(obs,),
                           method="Nelder-Mead")
            draws[name].append(float(res.x[0]))
    for name in STATS:
        bias[name].append(100 * (np.median(draws[name]) - norm_true) / norm_true)

totals = np.array([expected(TRUTH * s).sum() for s in exposures])

chart = xy.line_chart(
    *[
        xy.line(totals, vals, name=name, color=COLORS[name], width=2)
        for name, vals in bias.items()
    ],
    *[
        xy.scatter(totals, vals, color=COLORS[name], size=5)
        for name, vals in bias.items()
    ],
    xy.hline(0, color="#3a3b42", width=1),
    # The automatic log domain pads down to a decade the data never reaches.
    xy.x_axis(label="total counts in the spectrum", type_="log",
              domain=(totals.min() * 0.8, totals.max() * 1.25)),
    xy.y_axis(label="median bias [%]"),
    xy.legend(loc="upper right"),
    xysite.theme(),
)

xysite.embed(
    chart,
    "bias-vs-exposure",
    height=420,
    caption=(
        "Median bias against total counts. The data-variance χ² needs a few "
        "thousand counts before its bias drops under one percent."
    ),
)
```


<figure id="fig-bias-vs-exposure"><iframe class="xy-embed" src="/charts/gaussian-errors-faint-spectra/bias-vs-exposure.html" height="420" loading="lazy" title="Median bias against total counts. The data-variance χ² needs a few thousand counts before its bias drops under one percent."></iframe><figcaption>Median bias against total counts. The data-variance χ² needs a few thousand counts before its bias drops under one percent.</figcaption></figure>


## The practical rule

Use the Poisson likelihood. It costs nothing — it is one line of code, it is
what `jaxspec` and every modern fitting package minimise by default, and it
removes an entire class of quiet systematic from the analysis.

If a χ² statistic is unavoidable, take the variance from the *model* rather
than from the data: the Pearson variant is far better behaved, as the last
chart shows. The one thing not to do is weight by the observed counts, which
is exactly the default in a lot of legacy tooling.
