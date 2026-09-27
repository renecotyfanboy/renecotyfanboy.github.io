#!/usr/bin/env python3
"""Export the marimo POC as static files for Astro and GitHub Pages."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "interactive" / "photon_counts.py"
OUTPUT = ROOT / "public" / "notebooks" / "marimo"


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for mode, filename in (("run", "index.html"), ("edit", "edit.html")):
        subprocess.run(
            [
                sys.executable, "-m", "marimo", "export", "html-wasm", str(SOURCE),
                "--output", str(OUTPUT / filename), "--mode", mode,
                "--no-sandbox", "--force",
            ],
            cwd=ROOT,
            check=True,
        )
    print("marimo POC ready at /lab/marimo/")


if __name__ == "__main__":
    main()
