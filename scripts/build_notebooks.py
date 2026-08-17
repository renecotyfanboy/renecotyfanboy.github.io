#!/usr/bin/env python3
"""Execute notebooks/ and render them into Astro content collection entries.

Sources are MyST-markdown notebooks (jupytext): ordinary markdown, where a
```{code-cell} python fence is executed and a plain ```python fence is not.
Post metadata lives in the document's own YAML header and arrives here as
notebook metadata, so a post is authored in exactly one place.

Pipeline, all in-process:

    jupytext.read  ->  nbclient (execute)  ->  nbconvert (markdown)  ->  rewrite

Each document executes with `XYSITE_POST` set to its stem. The kernel inherits
it, which gives `xysite.embed` a per-post directory under public/charts/ so two
notebooks cannot claim the same chart filename.

Generated posts carry `generated: true`, which is what lets this script clean
up after a notebook that was renamed or deleted.

Usage:
    python3 scripts/build_notebooks.py                 # execute + render all
    python3 scripts/build_notebooks.py --no-execute    # re-render only
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path

import jupytext
import nbformat
import yaml
from nbclient import NotebookClient
from nbconvert import MarkdownExporter
from traitlets.config import Config

ROOT = Path(__file__).resolve().parent.parent
NOTEBOOKS = ROOT / "notebooks"
OUT = ROOT / "src" / "content" / "posts"
CHARTS = ROOT / "public" / "charts"
# Executed notebooks, kept so `--no-execute` can reuse their outputs.
CACHE = NOTEBOOKS / ".cache"

# .py is deliberately excluded: notebooks/ also holds plain modules (xysite.py)
# and globbing them would try to execute a library as a post.
SOURCE_SUFFIXES = (".md", ".ipynb")

EXECUTE_TIMEOUT = 600  # seconds per cell

# Metadata forwarded from the source document into the Astro front matter.
# `notebook` is deliberately absent: it is derived from the source path, so a
# renamed file cannot leave a stale link behind in the provenance banner.
PASSTHROUGH = (
    "title",
    "description",
    "date",
    "tags",
    "draft",
    "source",
)

FM_RE = re.compile(r"\A---\n(.*?)\n---\s*\n", re.DOTALL)


def sources() -> list[Path]:
    found = [p for p in sorted(NOTEBOOKS.iterdir()) if p.suffix in SOURCE_SUFFIXES]
    return [p for p in found if not p.name.startswith(("_", "."))]


def exporter() -> MarkdownExporter:
    """Markdown exporter honouring the usual hide-cell tags."""
    config = Config()
    config.MarkdownExporter.preprocessors = [
        "nbconvert.preprocessors.TagRemovePreprocessor"
    ]
    config.TagRemovePreprocessor.enabled = True
    config.TagRemovePreprocessor.remove_input_tags = {"remove-input"}
    config.TagRemovePreprocessor.remove_all_outputs_tags = {"remove-output"}
    config.TagRemovePreprocessor.remove_cell_tags = {"remove-cell"}
    return MarkdownExporter(config=config)


def _cell_key(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def save_cached_outputs(nb, stem: str) -> None:
    """Record each code cell's outputs, keyed by its source text.

    Only the outputs are stored, not the notebook: its metadata carries the
    post's front matter, including a `date` that is not JSON-serialisable.
    """
    CACHE.mkdir(parents=True, exist_ok=True)
    (CACHE / f"{stem}.json").write_text(
        json.dumps(
            {
                _cell_key(c.source): c.outputs
                for c in nb.cells
                if c.cell_type == "code"
            }
        ),
        encoding="utf-8",
    )


def restore_cached_outputs(nb, stem: str) -> None:
    """Splice the previous run's outputs into an unexecuted notebook.

    jupytext reads the markdown source, which carries prose but no results —
    so without this, `--no-execute` would quietly republish the post with every
    chart and table missing. Outputs are matched on the cell's source text, so
    prose edits are picked up while untouched code keeps its results, and a
    *changed* code cell is reported rather than silently shown stale.
    """
    path = CACHE / f"{stem}.json"
    if not path.exists():
        raise SystemExit(
            f"--no-execute: no cached run for {stem}. "
            "Run without the flag once to populate it."
        )

    cached = json.loads(path.read_text(encoding="utf-8"))

    stale = [
        i
        for i, cell in enumerate(nb.cells)
        if cell.cell_type == "code" and _cell_key(cell.source) not in cached
    ]
    for cell in nb.cells:
        if cell.cell_type == "code":
            # Round-tripping through JSON yields plain dicts; nbconvert reaches
            # for attributes on them, so rebuild them as NotebookNodes.
            cell.outputs = [
                nbformat.from_dict(o) for o in cached.get(_cell_key(cell.source), [])
            ]

    if stale:
        print(
            f"  ! {len(stale)} code cell(s) changed since the last run; their "
            "outputs are empty until you re-run without --no-execute",
            file=sys.stderr,
        )


def render(src: Path, *, execute: bool) -> tuple[str, dict]:
    nb = jupytext.read(src)

    if not execute:
        restore_cached_outputs(nb, src.stem)
        # Executing is what normally stamps `language_info`, and nbconvert uses
        # it to tag fenced code blocks. Without it the fast path silently drops
        # ```python down to ```, losing highlighting and producing a diff
        # against what CI writes for the very same source.
        nb.metadata.setdefault(
            "language_info",
            {"name": nb.metadata.get("kernelspec", {}).get("language", "python")},
        )

    if execute:
        # The kernel inherits this; xysite.embed refuses to run without it.
        os.environ["XYSITE_POST"] = src.stem
        # Charts are build artefacts; clear this post's directory so a renamed
        # chart cannot leave an orphan behind to be deployed.
        shutil.rmtree(CHARTS / src.stem, ignore_errors=True)

        print(f"• executing {src.name}")
        NotebookClient(
            nb,
            timeout=EXECUTE_TIMEOUT,
            kernel_name=nb.metadata.get("kernelspec", {}).get("name", "python3"),
            # Run with notebooks/ as the working directory so `import xysite`
            # resolves the same way it does when the notebook is opened.
            resources={"metadata": {"path": str(NOTEBOOKS)}},
        ).execute()

        save_cached_outputs(nb, src.stem)

    body, resources = exporter().from_notebook_node(
        nb, resources={"output_files_dir": f"{src.stem}_files"}
    )
    return body, resources


def write_outputs(resources: dict, stem: str) -> None:
    """Persist any binary outputs (images) nbconvert extracted."""
    for path, data in (resources.get("outputs") or {}).items():
        target = OUT / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)


def to_yaml_scalar(value):
    if isinstance(value, (dt.datetime, dt.date)):
        return value.isoformat()
    if isinstance(value, str):
        # A folded `description: >` carries a trailing newline; collapse it so
        # the front matter stays a single tidy line.
        return " ".join(value.split())
    return value


def post_process(src: Path, body: str, stem: str) -> str:
    nb = jupytext.read(src)
    meta = {
        k: to_yaml_scalar(v) for k, v in nb.metadata.items() if k in PASSTHROUGH
    }

    if "title" not in meta or "date" not in meta:
        raise SystemExit(f"{src.relative_to(ROOT)}: front matter needs title and date")

    meta.setdefault("source", "notebook")
    # Derived, never authored — assignment, not setdefault.
    meta["notebook"] = str(src.relative_to(ROOT))
    meta["generated"] = True

    # Astro's asset pipeline only picks up explicitly relative image paths.
    body = re.sub(rf"\]\((?={re.escape(stem)}_files/)", "](./", body)

    front = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False).strip()
    return f"---\n{front}\n---\n\n{body.strip()}\n"


def prune_orphans(known: set[str]) -> int:
    """Delete generated posts whose source notebook is gone.

    Without this, renaming a notebook publishes both the old and the new post
    forever: the stale markdown is committed, so a fresh CI checkout keeps it.
    Only files this script marked `generated: true` are ever removed.
    """
    removed = 0
    for md in sorted(OUT.glob("*.md")):
        if md.stem in known:
            continue

        match = FM_RE.match(md.read_text(encoding="utf-8"))
        meta = (yaml.safe_load(match.group(1)) if match else {}) or {}
        if not meta.get("generated"):
            continue  # hand-written post; not ours to delete

        md.unlink()
        shutil.rmtree(OUT / f"{md.stem}_files", ignore_errors=True)
        shutil.rmtree(CHARTS / md.stem, ignore_errors=True)
        print(f"  ✗ {md.relative_to(ROOT)} (source removed)")
        removed += 1

    return removed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--no-execute",
        action="store_true",
        help="re-render from the source without running any code",
    )
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    docs = sources()

    # Never a legitimate state for this repo, and the next line would take it
    # as "every generated post is an orphan" and delete the lot — with a zero
    # exit code, so CI would happily deploy the amputated blog.
    if not docs:
        raise SystemExit(f"no notebooks in {NOTEBOOKS.relative_to(ROOT)}")

    for src in docs:
        body, resources = render(src, execute=not args.no_execute)
        write_outputs(resources, src.stem)

        md = OUT / f"{src.stem}.md"
        md.write_text(post_process(src, body, src.stem), encoding="utf-8")
        print(f"  ✓ {md.relative_to(ROOT)}")

    removed = prune_orphans({src.stem for src in docs})
    suffix = f", {removed} orphan(s) removed" if removed else ""
    print(f"{len(docs)} notebook post(s) ready in {OUT.relative_to(ROOT)}{suffix}")


if __name__ == "__main__":
    main()
