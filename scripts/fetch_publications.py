#!/usr/bin/env python3
"""Fetch publications from SciX by author name into src/data/publications.json,
which src/components/Publications.astro renders at build time.

SciX (the Science Explorer) is the successor to NASA ADS and serves the same
API, so an existing ADS token keeps working against api.scixplorer.org.

Token (kept secret, never printed): read from SCIX_TOKEN, or from a .env file
in the repo root (KEY=VALUE). If no token is found, the existing
src/data/publications.json is left untouched — so CI without the secret (and
the deployed site) keep the last fetched list.

Dependency-free (Python 3 stdlib).
Run locally:  python3 scripts/fetch_publications.py
"""

import json
import os
import re
import sys
import urllib.parse
import urllib.request

# An `orcid:` search only returns papers claimed under that ORCID and misses
# several (e.g. jaxspec). The author-name search is complete and, for a
# distinctive name, has no false positives. Adjust if your name needs it.
QUERY = 'author:"Dupourqué, S."'
MAX_AUTHORS = 8        # author lists longer than this are truncated...
HEAD_AUTHORS = 3       # ...to this many names + "et al."

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "src", "data", "publications.json")
ENV = os.path.join(ROOT, ".env")
API = "https://api.scixplorer.org/v1/search/query"
ABS_BASE = "https://scixplorer.org/abs/"


TOKEN_VAR = "SCIX_TOKEN"


def get_token():
    tok = os.environ.get(TOKEN_VAR)
    if tok:
        return tok.strip()
    if os.path.exists(ENV):
        with open(ENV, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line.startswith(TOKEN_VAR + "="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def fmt_author(name):
    name = name.strip()
    if "," in name:
        family, given = name.split(",", 1)
    else:
        parts = name.split()
        family, given = (parts[-1], " ".join(parts[:-1])) if parts else (name, "")
    family, given = family.strip(), given.strip()
    inits = []
    for tok in re.split(r"[\s.]+", given):
        tok = tok.strip("-")
        if tok:
            inits.append(tok[0].upper() + ".")
    return (" ".join(inits) + " " + family).strip() if inits else family


def fmt_authors(authors):
    names = [fmt_author(a) for a in authors if a and a.strip()]
    if len(names) > MAX_AUTHORS:
        return ", ".join(names[:HEAD_AUTHORS]) + ", et al."
    return ", ".join(names)


def clean_title(t):
    t = (t or "").replace("$", "").replace("{", "").replace("}", "")
    t = t.replace("─", "–")   # the API sometimes returns U+2500 (box draw) for an en dash
    return re.sub(r"\s+", " ", t).strip()


def title_key(t):
    """Loose title fingerprint, used to drop an arXiv preprint once its
    refereed version shows up. Punctuation and case drift between the two
    records, so only letters and digits are kept."""
    return re.sub(r"[^a-z0-9]+", "", clean_title(t).lower())[:80]


def first(v):
    if isinstance(v, list):
        return v[0] if v else ""
    return v or ""


def main():
    token = get_token()
    if not token:
        print(f"{TOKEN_VAR} not set (env or .env); "
              "keeping existing src/data/publications.json")
        return 0

    params = urllib.parse.urlencode({
        "q": QUERY,
        "fl": "bibcode,title,author,year,pub,volume,page,doi,citation_count,doctype",
        "rows": "200",
        "sort": "date desc",
    })
    req = urllib.request.Request(
        API + "?" + params,
        headers={"Authorization": "Bearer " + token, "Accept": "application/json"},
    )
    # SciX being unreachable must not block a deploy: the site is publishable
    # without fresh citation counts, and the committed JSON is a fine fallback.
    # Every failure here takes the same exit as a missing token.
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.load(resp)
    except (OSError, json.JSONDecodeError) as exc:  # URLError/HTTPError/timeout all subclass OSError
        print(f"SciX request failed ({exc}); keeping existing {os.path.relpath(OUT, ROOT)}",
              file=sys.stderr)
        return 0

    docs = data.get("response", {}).get("docs", [])

    # An empty result is never legitimate for a query that matched 16 papers
    # last week: it means the schema, the query or the account changed. Writing
    # it out would silently publish an Academia page reading "0 citations".
    if not docs:
        print(f"SciX returned no documents; keeping existing {os.path.relpath(OUT, ROOT)}",
              file=sys.stderr)
        return 0

    # Refereed titles, so a preprint still awaiting publication is listed but
    # the same paper does not appear twice once it is out.
    published = {title_key(first(d.get("title")))
                 for d in docs if d.get("doctype") == "article"}

    items = []
    for d in docs:
        doctype = d.get("doctype")
        if doctype not in ("article", "eprint"):   # drop proceedings, abstracts, software, theses, etc.
            continue
        bib = d.get("bibcode") or ""
        pub = d.get("pub") or ""
        if "yCat" in bib or pub.startswith("VizieR"):   # drop data catalogs, not papers
            continue
        preprint = doctype == "eprint"
        if preprint and title_key(first(d.get("title"))) in published:
            continue
        if bib:
            url = ABS_BASE + urllib.parse.quote(bib) + "/abstract"
        elif d.get("doi"):
            url = "https://doi.org/" + first(d["doi"])
        else:
            url = "#"
        item = {
            "title": clean_title(first(d.get("title"))),
            "authors": fmt_authors(d.get("author") or []),
            "venue": (d.get("pub") or "").replace(" and ", " & "),
            "volume": d.get("volume") or "",
            "page": first(d.get("page")),
            "year": str(d.get("year") or ""),
            "citations": d.get("citation_count") or 0,
            "url": url,
        }
        if preprint:
            # "arXiv e-prints, arXiv:2607.06977" reads badly next to
            # "Astronomy & Astrophysics 704, A302"; keep the same shape.
            item["venue"] = "arXiv"
            item["volume"] = item["page"].replace("arXiv:", "")
            item["page"] = ""
            item["preprint"] = True
        items.append(item)

    # Metrics are over refereed work only, so an unrefereed preprint picking up
    # early citations does not move the h-index.
    counts = sorted((it["citations"] for it in items if not it.get("preprint")),
                    reverse=True)
    h = 0
    while h < len(counts) and counts[h] >= h + 1:
        h += 1

    n_preprints = sum(1 for it in items if it.get("preprint"))
    out = {
        "stats": {
            "total": sum(counts),
            "h_index": h,
            "count": len(items) - n_preprints,
            "preprints": n_preprints,
        },
        "items": items,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    print("Wrote %d articles + %d preprints (total %d citations, h-index %d) -> %s"
          % (out["stats"]["count"], n_preprints, out["stats"]["total"], h,
             os.path.relpath(OUT, ROOT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
