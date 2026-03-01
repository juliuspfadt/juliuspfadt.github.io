#!/usr/bin/env python3
"""
Fetch publications from ORCID and generate publications.html.

Usage:
    python3 update_publications.py          # preview to stdout
    python3 update_publications.py --write  # overwrite publications.html

The script:
  1. Pulls all works from the ORCID API.
  2. Deduplicates: groups works by normalized title, preferring published
     articles over preprints and latest versions over older ones.
  3. Fetches detailed metadata (authors, journal, DOI) for each selected work.
  4. Renders APA-style entries grouped by year.
  5. Preserves the Blog posts section at the bottom of publications.html.
"""

import json
import re
import sys
import urllib.request
from collections import defaultdict

ORCID_ID = "0000-0002-0758-5502"
ORCID_API = f"https://pub.orcid.org/v3.0/{ORCID_ID}"
BOLD_NAME = "Pfadt, J. M."
MAX_AUTHORS_BEFORE_ELLIPSIS = 20
PUBLICATIONS_FILE = "publications.html"

# Work types considered "published" (preferred over preprints)
PUBLISHED_TYPES = {"journal-article", "book-chapter", "book", "edited-book",
                   "dissertation-thesis", "conference-paper"}

# ── HTML shell ────────────────────────────────────────────────────────────────
HTML_TOP = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Publications | Julius M. Pfadt</title>
  <link rel="stylesheet" href="/style.css">
  <link href="https://fonts.googleapis.com/css2?family=PT+Serif&amp;family=Roboto&amp;family=Roboto+Slab&amp;family=STIX+Two+Text&amp;display=swap" rel="stylesheet">
  <!-- Google tag (gtag.js) -->
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-NCG60VZ1HG"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){dataLayer.push(arguments);}
    gtag('js', new Date());
    gtag('config', 'G-NCG60VZ1HG');
  </script>
</head>
<body>

  <header class="site-header" role="banner">
    <div class="wrapper">
      <a class="site-title" rel="author" href="/">Julius M. Pfadt</a>
      <nav class="site-nav">
        <input type="checkbox" id="nav-trigger" class="nav-trigger" />
        <label for="nav-trigger">
          <span class="menu-icon">
            <svg viewBox="0 0 18 15" width="18px" height="15px">
              <path d="M18,1.484c0,0.82-0.665,1.484-1.484,1.484H1.484C0.665,2.969,0,2.304,0,1.484l0,0C0,0.665,0.665,0,1.484,0 h15.032C17.335,0,18,0.665,18,1.484L18,1.484z M18,7.516C18,8.335,17.335,9,16.516,9H1.484C0.665,9,0,8.335,0,7.516l0,0 c0-0.82,0.665-1.484,1.484-1.484h15.032C17.335,6.031,18,6.696,18,7.516L18,7.516z M18,13.516C18,14.335,17.335,15,16.516,15H1.484 C0.665,15,0,14.335,0,13.516l0,0c0-0.82,0.665-1.483,1.484-1.483h15.032C17.335,12.031,18,12.695,18,13.516L18,13.516z"/>
            </svg>
          </span>
        </label>
        <div class="trigger">
          <a class="page-link" href="/publications.html">Publications</a>
          <a class="page-link" href="/software.html">Software</a>
          <a class="page-link" href="/talks.html">Talks</a>
        </div>
      </nav>
    </div>
  </header>

  <main class="page-content" aria-label="Content">
    <div class="wrapper">
      <article class="post">
        <header class="post-header">
          <h1 class="post-title">Publications</h1>
        </header>
        <div class="post-content">
          <h3>Scientific</h3>
"""

HTML_BOTTOM = """\

          <h3>Blog posts</h3>

          <h4>2021</h4>
          <ul>
            <li>A Bayesian Spectacles blog post presenting the preprint of &ldquo;Bayesian estimation of single-test reliability coefficients&rdquo;. <a href="https://www.bayesianspectacles.org/preprint-bayesian-estimation-of-single-test-reliability-coefficients/">https://www.bayesianspectacles.org/preprint-bayesian-estimation-of-single-test-reliability-coefficients/</a></li>
          </ul>
        </div>
      </article>
    </div>
  </main>

  <footer class="site-footer h-card">
    <div class="wrapper">
      <div class="footer-col-wrapper">
        <div class="footer-col footer-col-1">
          <ul class="contact-list">
            <li class="p-name">
              <p style="color:#000000;"><b>julius.pfadt at gmail.com</b></p>
              <p style="color:#000000; line-height:0">last edit Mar 1, 2026</p>
            </li>
          </ul>
        </div>
        <div class="footer-col footer-col-2">
          <ul class="social-media-list">
            <li><a href="https://github.com/juliuspfadt"><img alt="Github" src="/assets/images/github-mark.png" width="24" height="24"></a></li>
            <li><a href="https://www.linkedin.com/in/julius-m-pfadt-8b8a45179"><img alt="LinkedIn" src="/assets/images/linkedin-logo.png" width="24" height="24"></a></li>
            <li><a href="https://orcid.org/0000-0002-0758-5502"><img alt="ORCID" src="/assets/images/orcid.png" width="24" height="24"></a></li>
            <li><a href="https://scholar.google.com/citations?user=Db1-WloAAAAJ&amp;hl=en"><img alt="Google Scholar" src="/assets/images/google-scholar_icon.png" width="24" height="24"></a></li>
            <li><a href="https://www.researchgate.net/profile/Julius-Pfadt"><img alt="ResearchGate" src="/assets/images/researchgate.png" width="24" height="24"></a></li>
          </ul>
        </div>
      </div>
    </div>
  </footer>

</body>
</html>
"""

# ── Manual entries NOT tracked by ORCID ──────────────────────────────────────
MANUAL_ENTRIES = [
    {
        "year": 2025,
        "norm_title": "a tutorial on bayesian hypothesis testing of correlation coefficients using the bfpackmodule in jasp",
        "text": (
            '<li>Mulder, J., <strong>Pfadt, J. M.</strong>, &amp; Wagenmakers, E.-J. (2025). '
            'A tutorial on Bayesian hypothesis testing of correlation coefficients '
            'using the BFpack-module in JASP. <em>Behavior Research Methods, 57</em>(11), 311. '
            '<a href="https://doi.org/10.3758/s13428-025-02846-5">'
            'https://doi.org/10.3758/s13428-025-02846-5</a></li>'
        ),
    },
    {
        "year": 2023,
        "norm_title": "dissertation",
        "text": (
            '<li><strong>Pfadt, J. M.</strong> (2023), <em>The present and future of reliability '
            'analyis: Advances in theory and practice</em> [Doctoral dissertation, '
            'Ulm University]. <a href="https://doi.org/10.18725/OPARU-49700">'
            'http://dx.doi.org/10.18725/OPARU-49700</a></li>'
        ),
    },
    {
        "year": 2023,
        "norm_title": "reliability encyclopedia",
        "text": (
            '<li>Sijtsma, K., &amp; <strong>Pfadt, J. M.</strong> (2023). Reliability. In R. '
            'Tierney, F. Rizvi, &amp; K. Ercikan (Eds.), <em>International encyclopedia '
            'of education</em> (4th ed., pp. 21\u201334). Elsevier. '
            '<a href="https://doi.org/10.1016/B978-0-12-818630-5.10004-1">'
            'https://doi.org/10.1016/B978-0-12-818630-5.10004-1</a></li>'
        ),
    },
]

# ── Name overrides for contributors whose names need fixing ──────────────────
NAME_OVERRIDES = {
    "eric-jan wagenmakers": "Wagenmakers, E.-J.",
    "jan peter de ruiter": "De Ruiter, J. P.",
    "giuseppe arena, mr.": "Arena, G.",
    "giuseppe arena": "Arena, G.",
}


# ─── Helpers ─────────────────────────────────────────────────────────────────

def html_escape(s: str) -> str:
    """Minimal HTML escaping."""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


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
    """Group works by normalized title, pick best from each group."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for w in all_works:
        groups[w["norm_title"]].append(w)

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
    """Convert 'First M. Last' -> 'Last, F. M.' (best-effort)."""
    key = full.lower().strip()
    if key in NAME_OVERRIDES:
        return NAME_OVERRIDES[key]
    key_no_dot = key.rstrip(".")
    if key_no_dot in NAME_OVERRIDES:
        return NAME_OVERRIDES[key_no_dot]

    if "," in full:
        return full

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
            apa = f"<strong>{BOLD_NAME}</strong>"
        else:
            apa = html_escape(_to_apa_name(name))
        names.append(apa)

    if not names:
        return ""
    if len(names) > MAX_AUTHORS_BEFORE_ELLIPSIS:
        return ", ".join(names[:MAX_AUTHORS_BEFORE_ELLIPSIS]) + ", . . . " + names[-1]
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + ", &amp; " + names[-1]


def format_entry(detail: dict) -> tuple[int, str]:
    title_obj = detail.get("title", {}).get("title", {})
    title = html_escape(title_obj.get("value", "Unknown title"))
    wtype = detail.get("type", "")

    pd = detail.get("publication-date") or {}
    year = int((pd.get("year") or {}).get("value", 0))

    journal_obj = detail.get("journal-title") or {}
    journal = html_escape(journal_obj.get("value", ""))

    ext_ids = (detail.get("external-ids") or {}).get("external-id", [])
    doi = ""
    for eid in ext_ids:
        if eid.get("external-id-type") == "doi":
            doi = eid.get("external-id-value", "")
            break

    contributors = (detail.get("contributors") or {}).get("contributor", [])
    authors_str = format_authors(contributors)

    if wtype == "preprint":
        line = f"<li>{authors_str} ({year}). <em>{title}</em>."
        line += f" {journal}." if journal else " PsyArXiv."
    else:
        line = f"<li>{authors_str} ({year}). {title}."
        if journal:
            line += f" <em>{journal}</em>."

    if doi:
        doi_url = f"https://doi.org/{doi}"
        line += f' <a href="{doi_url}">{doi_url}</a>'

    line += "</li>"
    return year, line


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    write = "--write" in sys.argv

    print("Fetching works from ORCID …")
    data = api_get("works")
    groups = data.get("group", [])

    all_works = []
    for g in groups:
        for s in g.get("work-summary", []):
            all_works.append(extract_summary_info(s))

    print(f"  Found {len(all_works)} total work entries across {len(groups)} groups.")

    selected = deduplicate(all_works)
    print(f"  After deduplication: {len(selected)} unique works.")

    selected.sort(key=lambda w: (w["year"], w["month"]), reverse=True)

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
        skip = False
        if "PsyArXiv" in line:
            for w in selected:
                if w["type"] == "preprint":
                    wnt = w["norm_title"]
                    for mnt in manual_norm_titles:
                        if wnt.startswith(mnt) or mnt.startswith(wnt):
                            if w["title"][:30].lower() in line[:200].lower():
                                skip = True
                                break
                    if skip:
                        break
        if not skip:
            filtered_entries.append((year, line))
        else:
            print("  (suppressing ORCID preprint covered by manual entry)")

    entries = filtered_entries

    for me in MANUAL_ENTRIES:
        entries.append((me["year"], me["text"]))

    # Group by year, sort years descending
    by_year: dict[int, list[str]] = defaultdict(list)
    for year, line in entries:
        by_year[year].append(line)

    years_desc = sorted(by_year.keys(), reverse=True)

    # Build output
    lines = [HTML_TOP]
    for y in years_desc:
        lines.append(f"          <h4>{y}</h4>")
        lines.append("          <ul>")
        for entry in by_year[y]:
            lines.append(f"            {entry}")
        lines.append("          </ul>")
        lines.append("")

    lines.append(HTML_BOTTOM)

    output = "\n".join(lines)

    if write:
        with open(PUBLICATIONS_FILE, "w") as f:
            f.write(output)
        print(f"\n✓ Wrote {PUBLICATIONS_FILE}")
    else:
        print("\n" + "=" * 72)
        print("PREVIEW (pass --write to overwrite publications.html):")
        print("=" * 72)
        print(output)


if __name__ == "__main__":
    main()
