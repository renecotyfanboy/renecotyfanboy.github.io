---
title: "Executable notebooks on a static site"
description: >
  How the posts here are built: a Jupyter kernel runs the code, Astro renders
  the page, and nothing on screen is copy-pasted output.
date: 2026-08-15
tags: [meta, tooling]
source: prose
draft: true
---

Most scientific blog posts rot. Not the prose — the numbers. Someone writes an
analysis, pastes a figure and a table into the post, then changes the code six
months later. The post keeps claiming the old result, and there is no mechanism
that would ever notice.

The fix is to make the published page a *build artefact* of the analysis rather
than a transcription of it.

## The arrangement

Posts come in two flavours here.

**Prose posts** — like this one — are plain markdown in `src/content/posts/`.
Nothing clever.

**Notebook posts** live in `notebooks/` as
[MyST](https://mystmd.org) markdown — ordinary prose, where a
```` ```{code-cell} ```` fence is executed and a plain ```` ```python ````
fence is not. They run at build time: [jupytext](https://jupytext.readthedocs.io)
reads the file as a notebook, [nbclient](https://nbclient.readthedocs.io) runs
every cell against a Jupyter kernel, and
[nbconvert](https://nbconvert.readthedocs.io) writes markdown with the results
baked in. That markdown lands in the same content collection as the prose
posts, so from [Astro](https://astro.build)'s point of view there is only one
kind of post.

Keeping the source as markdown rather than `.ipynb` is deliberate: a notebook
is JSON, and JSON does not review well in a pull request.

The whole pipeline is two commands:

```bash
python3 scripts/build_notebooks.py
npm run build
```

The first executes the notebooks. The second turns the collection into HTML.
CI runs both on every push, which means a notebook that stops working *fails
the site build* instead of silently publishing a stale figure.

## Why not just export the notebook?

Exporting `.ipynb` to HTML is the obvious move and it is the one I avoided.
The output carries its own stylesheet, its own idea of typography, and a
structure that fights whatever design the surrounding site has. You end up with
a page that visibly belongs to a different website.

Rendering to *markdown* instead keeps the split clean: the notebook owns the
computation, the site owns the presentation. Tables come out as ordinary
tables, code as ordinary fenced blocks, figures as ordinary `<figure>`
elements — all of which the site already knows how to style.

## The part that needed work

Two details, both handled once in `scripts/build_notebooks.py`.

nbconvert emits no front matter, so the script carries the post's metadata
across from the notebook's own YAML header — the notebook stays the single
place where a title, date or tag list is authored.

And a cell's captured stdout comes out as an indented literal block. That is
correct for a stray `print`, but wrong for anything meant to *be* markup: a
`print(df.to_markdown())` would show pipe characters rather than a table. The
fix is on the notebook side — emit a rich output instead:

```python
display(Markdown(summary.to_markdown(index=False)))
```

Anything returned that way is passed through verbatim, which is also how the
interactive charts get embedded.

## Charts

Every chart on this site is interactive. They are built with
[xy](https://github.com/reflex-dev/xy), a Rust-backed charting library whose
HTML export is a single self-contained document with no external requests —
around half a megabyte, near enough constant no matter how many points go in,
because the engine sends the browser only what the screen can resolve.

That is a very different proposition from the usual route to interactivity,
which means shipping a Python runtime to the reader: several megabytes of
WebAssembly before the first pixel moves, and no JAX, which does not run in a
browser at all.

It is still half a megabyte per chart, and each one loads its own copy of the
engine. Frames are lazy-loaded, so nothing downloads until you scroll it into
view, but a post with four charts is a heavier page than one with four PNGs
would have been. That is the trade I have taken for now.

Because the export is a *whole document*, it cannot be pasted into a page.
Charts are written to `public/charts/` and embedded as iframes by a small
helper, `notebooks/xysite.py`, which carries the site's palette and pulls the
same Computer Modern the surrounding text uses — the fonts are served from the
same origin, so a chart's axis labels are set in the same typeface as the
paragraph above it. The isolation an iframe gives is worth having on its own
while the library is pre-1.0: its stylesheet and the site's cannot reach each
other.

One consequence worth naming: chart files are large, version-coupled build
artefacts, so they are not committed. A plain `npm run build` leaves the frames
empty; `npm run build:all` is the one that regenerates them.
