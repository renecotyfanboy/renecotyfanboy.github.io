---
title: Normalising flows, and what they actually buy you
description: A flow turns a simple density into a complicated one through an invertible
  map. What that is worth in practice for posterior inference, and where it quietly
  fails.
date: '2026-08-17'
tags:
- inference
- machine-learning
- statistics
source: notebook
draft: true
notebook: notebooks/normalising-flows-for-posteriors.md
generated: true
---

A normalising flow is a change of variables you are allowed to train. Push a
simple base density — a standard normal, say — through an invertible map, and
the change-of-variables formula gives you the density of the result exactly:

$$\log p_X(x) = \log p_Z(f^{-1}(x)) + \log\left|\det J_{f^{-1}}(x)\right|$$

The whole design problem is making that Jacobian determinant cheap while
keeping the map expressive. Everything else is engineering.

## What I want this post to cover

### The constraint that shapes every architecture

Why a general $D \times D$ Jacobian is a non-starter, and the three ways out:
triangular maps (autoregressive), coupling layers, and continuous-time flows.
The trade each one makes between sampling speed and density-evaluation speed —
they are not symmetric, and which one you want depends on what you are doing
with the flow.

### Where this meets my actual work

Two uses that look similar and are not:

- **As a variational family.** Replace the mean-field Gaussian with a flow and
  minimise the KL to the posterior. You keep the likelihood in the loop.
- **As a surrogate posterior.** Train on simulations and never write the
  likelihood down at all — neural posterior estimation. This is what the
  `jaxspec` line of work uses.

TODO — the honest comparison is against HMC on the same problem, with a fixed
compute budget on both sides. That is the experiment worth running.

### Where they fail quietly

The section that justifies the post. Flows do not tell you when they are wrong:
a badly trained flow produces a confident, smooth, plausible posterior that is
simply not the right one. Topics to cover — mode dropping under a reverse-KL
objective, the amortisation gap, and behaviour outside the region the training
simulations covered.

TODO — work out which diagnostics actually catch this. Simulation-based
calibration is the obvious candidate; importance sampling with the flow as the
proposal is the other, and it has the advantage of being able to *fix* the
answer rather than only flag it.

### A worked example

Something small enough to run in the browser-facing build: a posterior with a
curved degeneracy where a Gaussian approximation visibly fails and a flow does
not. Charts side by side, with the exact posterior available for reference.

## Why bother

Because the alternative for the problems I care about is a sampler that needs a
tractable likelihood, and there are plenty of interesting forward models where
writing one down is either impossible or slower than simulating.
