#!/usr/bin/env python3
"""
Fetch publications from ORCID and generate the Scientific section of publications.md.

Usage:
    python3 update_publications.py          # preview to stdout
    python3 update_publications.py --write  # overwrite publications/publications.md

The script:
  1. Pulls all works from the ORCID API.
  2. Deduplicates: groups works by normalized title, preferring published
     articles over preprints and latest versions over older ones.
  3. Fetches detailed metadata (authors, journal, DOI) for each selected work.
  4. Renders APA-style entries grouped by year.
  5. Preserves the Blog posts section at the bottom of publications.md.
"""

import json
import re
import sys
import textwrap
import urllib.request
from collections import defaultdict

ORCID_ID = "0000-0002-0758-5502"
ORCID_API = f"https://pub.orcid.org/v3.0/{ORCID_ID}"
BOLD_NAME = "Pfadt, J. M."
MAX_AUTHORS_BEFORE_ELLIPSIS = 20
PUBLICATIONS_MD = "publications/publications.md"

# Work types considered "published" (preferred over preprints)
PUBLISHED_TYPES = {"journal-article", "book-chapter", "book", "edited-book",
                   "dissertation-thesis", "conference-paper"}

# ── Front matter and blog section kept verbatim ──────────────────────────────
FRONT_MATTER = textwrap.dedent("""\
    ---
    layout: page
    title:  "Publications"
    permalink: /publications
    ---
""")

BLOG_POSTS_SECTION = textwrap.dedent("""\
    ### Blog posts
    #### 2021
    - A Bayesian Spectacles blog post presenting the preprint of \
"Bayesian estimation of single-test reliability coefficients". \
[https://www.bayesianspectacles.org/preprint-bayesian-estimation-of-single-test-\
reliability-coefficients/](https://www.bayesianspectacles.org/preprint-bayesian-\
estimation-of-single-test-reliability-coefficients/)
""")

# ── Manual entries NOT tracked by ORCID ──────────────────────────────────────
MANUAL_ENTRIES = [
    {
        "year": 2025,
        "norm_title": "a tutorial on bayesian hypothesis testing of correlation coefficients using the bfpackmodule in jasp",
        "text": (
            "- Mulder, J., **Pfadt, J. M.**, & Wagenmakers, E.-J. (2025). "
            "A tutorial on Bayesian hypothesis testing of correlation coefficients "
            "using the BFpack-module in JASP. *Behavior Research Methods, 57*(11), 311. "
            "[https://doi.org/10.3758/s13428-025-02846-5]"
            "(https://doi.org/10.3758/s13428-025-02846-5)"
        ),
    },
    {
        "year": 2023,
        "norm_title": "dissertation",
        "text": (
            "- **Pfadt, J. M.** (2023), *The present and future of reliability "
            "analyis: Advances in theory and practice* [Doctoral dissertation, "
            "Ulm University]. [http://dx.doi.org/10.18725/OPARU-49700]"
            "(https://doi.org/10.18725/OPARU-49700)"
        ),
    },
    {
        "year": 2023,
        "norm_title": "reliability encyclopedia",
        "text": (
            "- Sijtsma, K., & **Pfadt, J. M.** (2023). Reliability. In R. "
            "Tierney, F. Rizvi, & K. Ercikan (Eds.), *International encyclopedia "
            "of education* (4th ed., pp. 21\u201334). Elsevier. "
            "[https://doi.org/10.1016/B978-0-12-818630-5.10004-1]"
            "(https://doi.org/10.1016/B978-0-12-818630-5.10004-1)"
        ),
    },
]

# ── Name overrides for contributors whose names need fixing ──────────────────
# Keys are lowercased full names as they appear in ORCID.
NAME_OVERRIDES = {
    "eric-jan wagenmakers": "Wagenmakers, E.-J.",
    "jan peter de ruiter": "De Ruiter, J. P.",
    "giuseppe arena, mr.": "Arena, G.",
    "giuseppe arena": "Arena, G.",
}


# ─── Helpers ─────────────────────────────────────────────────────────────────

def api_get(path: str) -> dict:
    url = f"{ORCID_API}/{path}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def normalize_title(title: str) -> str:
    """Normalize a title for deduplication matching."""
    t = title.lower().strip()
    t = re.sub(r"[^a-z0-9\s]", "", t)
    t = re.sub(r"\s+", " ", t)
    return t


def extract_summary_info(summary: dict) -> dict:
    """Pull key fields from a work-summary."""
    title_obj = summary.get("title", {}).get("title", {})
    title = title_obj.get("value", "")
    wtype = summary.get("type", "")
    pd = summary.get("publication-date") or {}
    year = int((pd.get("year") or {}).get("value", 0))
    month = int((pd.get("month") or {}).get("value", 0))

    ext_ids = (summary.get("external-ids") or {}).get("external-id", [])
    doi = ""
    for eid in ext_ids:
        if eid.get("external-id-type") == "doi":
            doi = eid.get("external-id-value", "")
            break

    version = 0
    m = re.search(r"_v(\d+)$", doi)
    if m:
        version = int(m.group(1))

    return {
        "title": title,
        "norm_title": normalize_title(title),
        "type": wtype,
        "year": year,
        "month": month,
        "doi": doi,
        "version": version,
        "put_code": summary["put-code"],
    }


def deduplicate(all_works: list[dict]) -> list[dict]:
    """Group works by normalized title, pick best from each group.

    Priority: published > preprint; within same type: newer date, higher version.
    Also merges groups whose titles are leading substrings of each other
    (e.g., a preprint with a shorter title that later got a subtitle on publication).
    """
    # Phase 1: exact-match groups
    groups: dict[str, list[dict]] = defaultdict(list)
    for w in all_works:
        groups[w["norm_title"]].append(w)

    # Phase 2: merge groups whose titles overlap (one starts with the other)
    keys = sorted(groups.keys(), key=len)
    merged: dict[str, list[dict]] = {}
    for k in keys:
        canonical = None
        for existing in merged:
            if existing.startswith(k) or k.startswith(existing):
                canonical = existing
                break
        if canonical is None:
            merged[k] = list(groups[k])
        else:
            longer = k if len(k) > len(canonical) else canonical
            if longer != canonical:
                merged[longer] = merged.pop(canonical) + groups[k]
            else:
                merged[canonical].extend(groups[k])

    # Phase 3: pick best from each merged group
    selected = []
    for canon_title, works in merged.items():
        published = [w for w in works if w["type"] in PUBLISHED_TYPES]
        preprints = [w for w in works if w["type"] == "preprint"]

        if published:
            best = max(published, key=lambda w: (w["year"], w["month"]))
        elif preprints:
            best = max(preprints, key=lambda w: (w["version"], w["year"], w["month"]))
        else:
            best = max(works, key=lambda w: (w["year"], w["month"]))

        selected.append(best)

    return selected


def fetch_detail(put_code: int) -> dict:
    return api_get(f"work/{put_code}")


def _to_apa_name(full: str) -> str:
    """Convert 'First M. Last' -> 'Last, F. M.' (best-effort).

    Handles name particles (van, de, den, von, etc.).
    """
    # Check overrides first
    key = full.lower().strip()
    if key in NAME_OVERRIDES:
        return NAME_OVERRIDES[key]
    key_no_dot = key.rstrip(".")
    if key_no_dot in NAME_OVERRIDES:
        return NAME_OVERRIDES[key_no_dot]

    if "," in full:
        return full  # already APA-ish

    parts = full.split()
    if len(parts) < 2:
        return full

    particles = {"van", "von", "de", "den", "der", "het", "la", "le", "di", "du"}

    last_start = len(parts) - 1
    while last_start > 0 and parts[last_start - 1].lower() in particles:
        last_start -= 1
    if last_start == 0:
        last_start = 1

    first_parts = parts[:last_start]
    last_parts = parts[last_start:]

    initials = " ".join(
        (p[0].upper() + ".") if not p.endswith(".") else p for p in first_parts
    )
    last = " ".join(last_parts)
    return f"{last}, {initials}"


def format_authors(contributors: list) -> str:
    names = []
    for c in contributors:
        cn = c.get("credit-name") or {}
        name = cn.get("value", "").strip()
        if not name:
            continue
        if "pfadt" in name.lower():
            apa = f"**{BOLD_NAME}**"
        else:
            apa = _to_apa_name(name)
        names.append(apa)

    if not names:
        return ""
    if len(names) > MAX_AUTHORS_BEFORE_ELLIPSIS:
        return ", ".join(names[:MAX_AUTHORS_BEFORE_ELLIPSIS]) + ", . . . " + names[-1]
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + ", & " + names[-1]


def format_entry(detail: dict) -> tuple[int, str]:
    title_obj = detail.get("title", {}).get("title", {})
    title = title_obj.get("value", "Unknown title")
    wtype = detail.get("type", "")

    pd = detail.get("publication-date") or {}
    year = int((pd.get("year") or {}).get("value", 0))

    journal_obj = detail.get("journal-title") or {}
    journal = journal_obj.get("value", "")

    ext_ids = (detail.get("external-ids") or {}).get("external-id", [])
    doi = ""
    for eid in ext_ids:
        if eid.get("external-id-type") == "doi":
            doi = eid.get("external-id-value", "")
            break

    contributors = (detail.get("contributors") or {}).get("contributor", [])
    authors_str = format_authors(contributors)

    if wtype == "preprint":
        line = f"- {authors_str} ({year}). *{title}*."
        line += f" {journal}." if journal else " PsyArXiv."
    else:
        line = f"- {authors_str} ({year}). {title}."
        if journal:
            line += f" *{journal}*."

    if doi:
        doi_url = f"https://doi.org/{doi}"
        line += f" [{doi_url}]({doi_url})"

    return year, line


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    write = "--write" in sys.argv

    print("Fetching works from ORCID …")
    data = api_get("works")
    groups = data.get("group", [])

    # Flatten all summaries across all groups
    all_works = []
    for g in groups:
        for s in g.get("work-summary", []):
            all_works.append(extract_summary_info(s))

    print(f"  Found {len(all_works)} total work entries across {len(groups)} groups.")

    # Deduplicate by normalized title
    selected = deduplicate(all_works)
    print(f"  After deduplication: {len(selected)} unique works.")

    # Sort by year desc, month desc
    selected.sort(key=lambda w: (w["year"], w["month"]), reverse=True)

    # Fetch full details
    entries: list[tuple[int, str]] = []
    for i, w in enumerate(selected):
        pc = w["put_code"]
        print(f"  [{i+1}/{len(selected)}] {w['title'][:70]}…")
        detail = fetch_detail(pc)
        year, line = format_entry(detail)
        entries.append((year, line))

    # Add manual entries; suppress ORCID preprints that a manual entry replaces
    manual_norm_titles = {me["norm_title"] for me in MANUAL_ENTRIES if "norm_title" in me}
    filtered_entries: list[tuple[int, str]] = []
    for year, line in entries:
        # Check if this is an ORCID preprint superseded by a manual entry
        skip = False
        if "PsyArXiv" in line:
            for w in selected:
                if w["type"] == "preprint":
                    # Check if this line corresponds to a work whose title matches a manual entry
                    wnt = w["norm_title"]
                    for mnt in manual_norm_titles:
                        if wnt.startswith(mnt) or mnt.startswith(wnt):
                            # This preprint is covered by a manual (published) entry
                            if w["title"][:30].lower() in line[:200].lower():
                                skip = True
                                break
                    if skip:
                        break
        if not skip:
            filtered_entries.append((year, line))
        else:
            print(f"  (suppressing ORCID preprint covered by manual entry)")

    entries = filtered_entries

    # Add all manual entries
    for me in MANUAL_ENTRIES:
        entries.append((me["year"], me["text"]))

    # Group by year, sort years descending
    by_year: dict[int, list[str]] = defaultdict(list)
    for year, line in entries:
        by_year[year].append(line)

    years_desc = sorted(by_year.keys(), reverse=True)

    # Build output
    lines = [FRONT_MATTER, "### Scientific"]
    for y in years_desc:
        lines.append(f"#### {y}")
        for entry in by_year[y]:
            lines.append(entry)
        lines.append("")

    lines.append(BLOG_POSTS_SECTION)

    output = "\n".join(lines)

    if write:
        with open(PUBLICATIONS_MD, "w") as f:
            f.write(output)
        print(f"\n✓ Wrote {PUBLICATIONS_MD}")
    else:
        print("\n" + "=" * 72)
        print("PREVIEW (pass --write to overwrite publications.md):")
        print("=" * 72)
        print(output)


if __name__ == "__main__":
    main()
