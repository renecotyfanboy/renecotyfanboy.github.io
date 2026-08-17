---
title: What thousands of ranked games say about balance
description: 'A side project: pulling tens of thousands of League of Legends matches
  and asking what can actually be inferred about champion balance, and what is just
  the matchmaker talking.'
date: '2026-08-17'
tags:
- statistics
- inference
- games
source: notebook
draft: true
notebook: notebooks/league-of-legends-balance.md
generated: true
---

I played a lot of League of Legends. At some point the interesting question
stopped being *how do I climb* and became *how would you even measure whether a
champion is overpowered*.

Win rate is the obvious answer and it is close to useless on its own. It is a
marginal over a population that chose to play that champion, in matches the
system deliberately balanced to 50%.

## What I want this post to cover

### The data

Where the matches come from, how many, over what patch window, and what a
single match record actually contains. Worth being explicit about the sampling:
matches are not drawn uniformly from the population of players.

### Why raw win rate is the wrong statistic

The two confounders to separate:

- **Selection.** Who picks this champion, and how good are they at the game
  independently of it? A champion played mostly by dedicated one-tricks looks
  stronger than it is.
- **Matchmaking.** The system targets a 50% win rate per player. Any signal has
  to be read against a process actively erasing it.

### A model instead of a statistic

The plan is a hierarchical model: per-player skill, per-champion effect, and
per-matchup interaction, fit jointly so the champion effect is estimated
*conditional* on who is playing it. Bradley–Terry-ish on the match outcome, with
partial pooling doing the work on the long tail of rarely-played champions.

TODO — decide whether the matchup interaction is identifiable at this sample
size, or whether it needs to be regularised down to a low-rank term.

### What actually came out

The part worth publishing: which champions move when you condition properly,
and by how much. Also the ones that do not move, which is the more interesting
result — where the naive win rate was already telling the truth.

### How much of it is noise

Posterior intervals on the champion effects, and an honest statement of what
sample size would be needed to resolve a 1% effect.

## Why this is on an astrophysics blog

Because it is the same problem. A population of noisy measurements, a selection
function that is not ignorable, and a latent quantity you want conditional on
covariates you only partly observe. Swap champions for clusters and matchmaking
for Malmquist bias and the machinery is unchanged.
