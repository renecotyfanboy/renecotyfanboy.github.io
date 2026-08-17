---
title: Writing a post here
description: >
  A permanent draft. Every markdown feature this site styles, shown once as
  source and once rendered, followed by the checklist a post has to pass before
  it ships.
date: 2026-08-17
tags: [meta]
source: prose
draft: true
---

This post never ships. The `draft: true` line in its front matter is the whole
mechanism: `getPosts()` in `src/utils/posts.ts` filters drafts whenever
`import.meta.env.PROD` is set, so a production build leaves it out of the blog
index, the tag pages, the RSS feed and the sitemap, and never generates
`/blog/writing-a-post` at all. `npm run dev` renders it like any other post,
with a `draft` chip next to the date.

Deleting that one line is the entire publish action. There is no second switch.

Everything below is both the documentation and the demonstration: each section
shows the source, then what the source turns into on this page.

## Two kinds of post

**Prose posts** are plain markdown in `src/content/posts/`. Write the file,
you are done. This is one.

**Notebook posts** are authored in `notebooks/` as MyST markdown and rendered
into `src/content/posts/` by `scripts/build_notebooks.py`, which executes every
code cell first. Their front matter is written in the notebook's own YAML
header and carried across by the script.

One rule follows from that, and it is the easiest way to lose an afternoon:

> Never edit a generated file in `src/content/posts/`. Anything with
> `generated: true` is build output — the next `npm run notebooks` overwrites
> it, and a rename deletes it outright.

Which kind you are writing decides where the file lives. Everything else in
this post applies to both.

## Front matter

The schema lives in `src/content.config.ts` and is enforced at build time: a
missing `title` or an unparseable `date` fails the build rather than shipping a
broken page.

````markdown
---
title: What Gaussian errors do to a faint X-ray spectrum
description: >
  Fitting binned counts with a χ² statistic is standard practice and quietly
  biased. A short numerical experiment on how bad it gets.
date: 2026-08-16
tags: [statistics, x-ray, inference]
source: prose
draft: true
---
````

| Field | Required | What it does |
| --- | --- | --- |
| `title` | yes | The `<h1>`, the `<title>`, the card on `/blog`, the RSS entry. |
| `description` | no, but write one | The lede under the title, plus `meta description`, `og:description`, the blurb on the card and the RSS summary. It is the only thing a reader sees before deciding to click. |
| `date` | yes | `YYYY-MM-DD`. Sorts the index, drives the older/newer pager, becomes the RSS `pubDate`. Rendered in UTC. |
| `tags` | no | Free text, lowercase. Each becomes `/tags/<slug>`. |
| `draft` | no | `true` hides the post from every production build. Absent means published. |
| `source` | no | `prose` or `notebook`. `notebook` adds the chip and the provenance banner. Defaults to `prose`. |
| `notebook` | never | Derived from the source path by the build script. |
| `generated` | never | Written by `scripts/build_notebooks.py` on its own output. It is what lets the script delete a post whose notebook disappeared — so setting it by hand on a prose post schedules that post's deletion. |

Two things the schema will not catch. Unknown keys are dropped silently, so
`tag:` instead of `tags:` produces an untagged post and no error. And a date in
the future publishes immediately; nothing here holds a post back until then.

The filename is the URL. `writing-a-post.md` serves at `/blog/writing-a-post`,
and renaming it after publication breaks every inbound link — this is a static
site, there is nothing to issue a redirect.

## Headings

Start at `##`. The `#` level belongs to the post title, which the layout
renders from the front matter; a second one in the body gives the page two
`<h1>`s and a screen reader no idea which is the title.

`##` gets the short spectral underline. `###` is quieter, for subdivisions.
Both, and only these two, feed the table of contents in the left rail — which
appears above 84rem of viewport and only when there are more than two of them.
`####` renders, but goes nowhere near the rail.

Heading text becomes the anchor id, so `## The checklist` is linkable as
`#the-checklist`. Renaming a heading breaks any link that pointed at it.

## The text column

Body text is capped at 68 characters. Figures, tables and charts break out into
a wider band on each side; nothing else does. That is a grid in `.prose`, not
something a post opts into — put a table in a post and it widens itself.

Ordinary marks all work as expected: *emphasis*, **strong**,
`inline code`, [links](https://astro.build), and footnote-ish asides are just
parentheses, since there is no footnote styling.

- Lists get a gold marker.
- Second item, to show the spacing between them.
  1. Nested ordered lists work.
  2. Two deep is already too many.

> A blockquote carries the spectral edge on the left and sets in italics. Good
> for one sentence you want to stop on. Bad for four paragraphs.

## Code

A fence with a language is highlighted with Shiki (the `vesper` theme) and gets
an ember edge — that edge means *this is source, read it*.

```python
import numpy as np

rng = np.random.default_rng(20260817)
counts = rng.poisson(expected(TRUTH))
```

A fence with **no** language renders in the quieter output style instead. That
is the same treatment a notebook's captured stdout gets, so use it for terminal
output and results rather than for code you want read:

```
total expected counts at truth: 143.2
```

Long lines scroll horizontally rather than wrap — `wrap: false` in
`astro.config.mjs` — so keep them under about 80 characters if the reader
should see the whole thing without dragging.

## Maths

`remark-math` and KaTeX are on. Inline maths goes between single dollars —
`$\chi^2$` sets as $\chi^2$ — and a display equation needs its delimiters on
lines of their own:

````markdown
$$
\log p_X(x) = \log p_Z(f^{-1}(x)) + \log\left|\det J_{f^{-1}}(x)\right|
$$
````

$$
\log p_X(x) = \log p_Z(f^{-1}(x)) + \log\left|\det J_{f^{-1}}(x)\right|
$$

Own lines, and this one is worth remembering: `$$E = mc^2$$` written on a
single line is *not* a display equation. It parses as inline maths and lands
mid-paragraph at text size, in-line style, with no error and nothing on screen
that obviously looks wrong.

The KaTeX stylesheet is only loaded for posts whose body matches a `$…$` or
`$$…$$` pattern, so a post with no maths pays nothing for it. The test is a
regex over the raw markdown, which means a `$` inside a code fence is enough to
pull the sheet in — harmless, just not free.

Display equations scroll rather than overflow, but a very long one still reads
badly on a phone. Break it before you have to.

## Tables

Ordinary GFM tables. Every one is wrapped in a scroll container by
`src/plugins/rehype-table-scroll.mjs`, because a single unbreakable token in a
DataFrame cell is otherwise enough to put the whole page into horizontal
scroll.

| Estimator | Bias at 200 counts | Bias at 20 counts |
| --- | --- | --- |
| Cash | −0.1% | −0.4% |
| χ², model variance | −0.3% | −2.1% |
| χ², data variance | −3.8% | −14.6% |

Numbers are set in tabular figures, so columns line up. Headers are small caps
in the mono face. You do not have to align the pipes in the source; nothing
reads the source but you.

## Figures

Anything you want captioned or widened goes in a `<figure>`. Raw HTML works in
markdown here, and a top-level `<figure>` is what the grid widens — so this
diagram sits wider than the paragraph above it:

<figure>
<svg viewBox="0 0 720 168" width="720" role="img" aria-label="Two authoring paths converging on the content collection: notebooks are executed into markdown, prose posts are written as markdown directly; Astro builds both into the site.">
<style>
.d-box { fill: var(--ink-850); stroke: var(--line); }
.d-hot { stroke: var(--ember); }
.d-t { fill: var(--fog-300); font-family: var(--font-mono); font-size: 12px; }
.d-s { fill: var(--fog-500); font-family: var(--font-mono); font-size: 10px; }
.d-a { stroke: var(--fog-500); fill: none; }
</style>
<defs><marker id="d-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0 L8 4 L0 8 z" fill="var(--fog-500)"/></marker></defs>
<rect class="d-box" x="1" y="8" width="150" height="46" rx="4"/>
<text class="d-t" x="76" y="30" text-anchor="middle">notebooks/*.md</text>
<text class="d-s" x="76" y="45" text-anchor="middle">MyST + code cells</text>
<rect class="d-box d-hot" x="191" y="8" width="170" height="46" rx="4"/>
<text class="d-t" x="276" y="30" text-anchor="middle">build_notebooks.py</text>
<text class="d-s" x="276" y="45" text-anchor="middle">executes every cell</text>
<rect class="d-box" x="1" y="112" width="150" height="46" rx="4"/>
<text class="d-t" x="76" y="134" text-anchor="middle">this file</text>
<text class="d-s" x="76" y="149" text-anchor="middle">plain markdown</text>
<rect class="d-box" x="401" y="60" width="170" height="46" rx="4"/>
<text class="d-t" x="486" y="82" text-anchor="middle">src/content/posts/</text>
<text class="d-s" x="486" y="97" text-anchor="middle">one collection</text>
<rect class="d-box" x="611" y="60" width="108" height="46" rx="4"/>
<text class="d-t" x="665" y="82" text-anchor="middle">dist/</text>
<text class="d-s" x="665" y="97" text-anchor="middle">astro build</text>
<path class="d-a" d="M151 31 H186" marker-end="url(#d-arrow)"/>
<path class="d-a" d="M361 31 H381 Q391 31 391 41 V78 H396" marker-end="url(#d-arrow)"/>
<path class="d-a" d="M151 135 H381 Q391 135 391 125 V88 H396" marker-end="url(#d-arrow)"/>
<path class="d-a" d="M571 83 H606" marker-end="url(#d-arrow)"/>
</svg>
<figcaption>Both authoring paths land in the same content collection, so from Astro's point of view there is only one kind of post. The ember box is the only step that runs code.</figcaption>
</figure>

For an image, put the file next to the post and reference it relatively —
`![alt](./exposure-map.png)` — which routes it through Astro's asset pipeline
(hashing, sizing, `dist/_assets/`). A path like `/img/foo.png` is served from
`public/` untouched, which is right for something already optimised and wrong
for a 4 MB screenshot. Relative images are checked at build: a typo in the
filename fails the build instead of shipping a broken image.

Alt text is not optional. It is the only version of the figure some readers get.

## Charts are notebook-only

The interactive charts are produced by `xysite.embed()` inside an executed
notebook cell. They cannot be written into a prose post: each one is a complete
standalone HTML document written to `public/charts/<post>/`, and the helper
refuses to run outside the build script.

If a prose post needs a chart, it wants to be a notebook post. Move it to
`notebooks/`, add the jupytext header, and let the pipeline own it.

Chart files are not committed. `npm run build` alone leaves the iframes empty;
`npm run build:all` is the one that regenerates them.

## The checklist

### Before you start

- **Pick the kind.** Any executed code, any chart, any number that could go
  stale → notebook post in `notebooks/`. Otherwise prose in
  `src/content/posts/`.
- **Pick the filename carefully.** It is the permanent URL. Lowercase,
  hyphenated, no date prefix.

### Front matter

- `title` and `date` present; `date` as `YYYY-MM-DD`.
- `description` written, one or two sentences — it is the card, the search
  result and the RSS summary.
- `tags` lowercase, and *reused*. Check `/blog` for the existing set first:
  two spellings that slug the same share one page, and the newest post's
  spelling silently becomes the label for all of them.
- `source: notebook` only on notebook posts; `generated` and `notebook` never
  set by hand.
- `draft: true` while writing.

### The body

- Starts at `##`, no `#` anywhere.
- More than two `##`/`###` headings if you want the contents rail.
- Every fence carries a language, except deliberate output blocks.
- Display equations have their `$$` on separate lines. A single-line
  `$$…$$` silently renders inline.
- Every figure has a caption and every image has alt text.
- Relative image paths (`./foo.png`), not `public/` ones, unless the asset is
  deliberately unprocessed.
- Long code lines under ~80 characters; they scroll, they do not wrap.

### Before publishing

- `npm run dev` — read the post at `/blog/<slug>`. Check the contents rail, the
  tags, the pager at the foot, and every chart iframe actually has a chart in
  it.
- Narrow the window to a phone width. Tables and equations are where this
  breaks.
- Notebook post: `npm run notebooks` and confirm it executes clean, then read
  the regenerated markdown diff. A changed number is a real result changing.
- Remove `draft: true`.
- `npm run build` — this is what enforces the schema, resolves the images and
  catches a broken relative link.
- `npm run check` for the typecheck, if anything outside `src/content/` was
  touched.

### After pushing

CI runs the same three steps on every push to `master` — typecheck, execute the
notebooks, build — and only deploys if all of them pass. A notebook that stops
working fails the deploy rather than publishing a stale figure. Check the run,
then check the live page: the post on `/blog`, its `/tags/` pages, and the
entry in `/rss.xml`.

One thing CI cannot check: publishing pushes the post to the RSS feed, where
edits do not propagate cleanly. Read it once more before you delete the draft
flag.
