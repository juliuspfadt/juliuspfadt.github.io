#!/usr/bin/env python3
"""
Fetch publications from ORCID and regenerate publication outputs.

Usage:
    python3 update_publications.py          # preview summary
    python3 update_publications.py --write  # overwrite all generated files

The script:
  1. Pulls all works from the ORCID API.
  2. Deduplicates: groups works by normalized title, preferring published
     articles over preprints and latest versions over older ones.
  3. Fetches detailed metadata for each selected work.
  4. Regenerates:
       - publications.html
       - the generated publications block in cv/main.typ
  5. Preserves manual CV-only entries and manual replacements for works that
     are missing from ORCID or supersede ORCID preprints.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.parse
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from urllib.error import HTTPError, URLError

ORCID_ID = "0000-0002-0758-5502"
ORCID_API = f"https://pub.orcid.org/v3.0/{ORCID_ID}"
BOLD_NAME = "Pfadt, J. M."
MAX_AUTHORS_BEFORE_ELLIPSIS = 20

APA_SUBTITLE_SEPARATORS = {":", "?", "!"}
APA_PROTECTED_TITLE_WORDS = {
    "apa",
    "bayes",
    "bayesian",
    "bfpack",
    "cronbach",
    "cronbach's",
    "cronbach’s",
    "jasp",
    "orcid",
    "psyarxiv",
}

PUBLICATIONS_FILE = "publications.html"
CV_MAIN_FILE = "cv/main.typ"
REVIEWING_SECTION_TITLE = "Reviewing"
REVIEWING_PAGE_TITLE = "Ad-hoc reviewing"

GENERATED_PUBLICATIONS_START = "// BEGIN GENERATED PUBLICATIONS"
GENERATED_PUBLICATIONS_END = "// END GENERATED PUBLICATIONS"

# Work types considered "published" (preferred over preprints)
PUBLISHED_TYPES = {
    "journal-article",
    "book-chapter",
    "book",
    "edited-book",
    "dissertation-thesis",
    "conference-paper",
}

KEY_OVERRIDES_BY_DOI = {
    "10.1080/00273171.2021.1891855": "Pfadt2022BayesianEstimationSingletest",
    "10.3758/s13428-021-01778-0": "Pfadt2022TutorialBayesianSingletest",
    "10.1080/10705511.2022.2124162": "Pfadt2023ClassicalBayesianUncertainty",
    "10.1007/s11336-021-09789-8": "Sijtsma2021PartIIUse",
    "10.1007/s11336-021-09807-9": "Sijtsma2021RejoinderFutureReliability",
    "10.31234/osf.io/a27g4_v1": "Pfadt2025TutorialEstimatingPrecision",
    "10.31234/osf.io/ck3js_v1": "Pfadt2025MethodologicalMetamorphosisRapid",
}

# ── HTML shell ───────────────────────────────────────────────────────────────
HTML_TOP = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Publications | Julius M. Pfadt</title>
  <link rel="stylesheet" href="/style.css">
  <script src="/assets/js/site-shell.js" defer></script>
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

  <div id="site-header"></div>

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

          <h3>{reviewing_title}</h3>
          <ul>
{reviewing_items}
          </ul>

          <h3>Blog posts</h3>

          <h4>2021</h4>
          <ul>
            <li>A Bayesian Spectacles blog post presenting the preprint of &ldquo;Bayesian estimation of single-test reliability coefficients&rdquo;. <a href="https://www.bayesianspectacles.org/preprint-bayesian-estimation-of-single-test-reliability-coefficients/">https://www.bayesianspectacles.org/preprint-bayesian-estimation-of-single-test-reliability-coefficients/</a></li>
          </ul>
        </div>
      </article>
    </div>
  </main>

  <div id="site-footer"></div>

</body>
</html>
"""


@dataclass(frozen=True)
class Publication:
    key: str
    title: str
    norm_title: str
    year: int
    month: int
    source_order: int
    include_in_html: bool
    include_in_cv: bool
    html_entry: str
    typst_entry: str
    bibtex: str


@dataclass(frozen=True)
class CitationDetails:
    venue: str = ""
    volume: str = ""
    issue: str = ""
    pages: str = ""
    publisher: str = ""


# ── Manual entries missing from ORCID or replacing ORCID works ───────────────
MANUAL_PUBLICATIONS = [
    {
        "key": "Mulder2025TutorialBayesianHypothesisa",
        "year": 2025,
        "month": 10,
        "norm_title": "a tutorial on bayesian hypothesis testing of correlation coefficients using the bfpackmodule in jasp",
        "replace_orcid_norm_titles": [
            "a tutorial on bayesian hypothesis testing of correlation coefficients using the bfpackmodule in jasp"
        ],
        "include_in_html": True,
        "include_in_cv": True,
        "html": (
            '<li>Mulder, J., <strong>Pfadt, J. M.</strong>, &amp; Wagenmakers, E.-J. (2025). '
            'A tutorial on Bayesian hypothesis testing of correlation coefficients '
            'using the BFpack-module in JASP. <em>Behavior Research Methods, 57</em>(11), 311. '
            '<a href="https://doi.org/10.3758/s13428-025-02846-5">'
            'https://doi.org/10.3758/s13428-025-02846-5</a></li>'
        ),
        "bibtex": """@article{Mulder2025TutorialBayesianHypothesisa,
  title = {A tutorial on {{Bayesian}} hypothesis testing of correlation coefficients using the {{BFpack-module}} in {{JASP}}},
  author = {Mulder, Joris and Pfadt, Julius M. and Wagenmakers, Eric-Jan},
  date = {2025-10-13},
  journaltitle = {Behavior Research Methods},
  shortjournal = {Behav Res},
  volume = {57},
  number = {11},
  pages = {311},
  issn = {1554-3528},
  doi = {10.3758/s13428-025-02846-5},
  langid = {english},
  author+an = {2=highlight}
}""",
        "typst": '[Mulder, J., Pfadt, J. M., & Wagenmakers, E.-J. (2025). A tutorial on Bayesian hypothesis testing of correlation coefficients using the BFpack-module in JASP. #emph[Behavior Research Methods, 57] (11), 311. #link("https://doi.org/10.3758/s13428-025-02846-5")[https://doi.org/10.3758/s13428-025-02846-5]]',
    },
    {
        "key": "Pfadt2023PresentFutureReliability",
        "year": 2023,
        "month": 0,
        "norm_title": "dissertation",
        "replace_orcid_norm_titles": [],
        "include_in_html": True,
        "include_in_cv": True,
        "html": (
            '<li><strong>Pfadt, J. M.</strong> (2023), <em>The present and future of reliability '
            'analyis: Advances in theory and practice</em> [Doctoral dissertation, '
            'Ulm University]. <a href="https://doi.org/10.18725/OPARU-49700">'
            'http://dx.doi.org/10.18725/OPARU-49700</a></li>'
        ),
        "bibtex": """@thesis{Pfadt2023PresentFutureReliability,
  title = {The present and future of reliability analysis: {{Advances}} in theory and practice},
  shorttitle = {The present and future of reliability analysis},
  author = {Pfadt, Julius Maria},
  date = {2023},
  institution = {Universit\\"at Ulm},
  doi = {10.18725/OPARU-49700},
  langid = {english},
  keywords = {Bayes-Entscheidungstheorie,Bayesian statistical decision theory,Bayesian statistics,DDC 150 / Psychology,DDC 310 / General statistics,Forschungsmethode,Psychological research methods,Psychologie,Psychology; Research; Methodology,Reliability analysis},
  author+an = {1=highlight}
}""",
        "typst": '[Pfadt, J. M. (2023), #emph[The present and future of reliability analyis: Advances in theory and practice] (Doctoral dissertation, Ulm University). #link("https://doi.org/10.18725/OPARU-49700")[https://doi.org/10.18725/OPARU-49700]]',
    },
    {
        "key": "Sijtsma2023Reliability",
        "year": 2023,
        "month": 0,
        "norm_title": "reliability encyclopedia",
        "replace_orcid_norm_titles": [],
        "include_in_html": True,
        "include_in_cv": True,
        "html": (
            '<li>Sijtsma, K., &amp; <strong>Pfadt, J. M.</strong> (2023). Reliability. In R. '
            'Tierney, F. Rizvi, &amp; K. Ercikan (Eds.), <em>International encyclopedia '
            'of education</em> (4th ed., pp. 21–34). Elsevier. '
            '<a href="https://doi.org/10.1016/B978-0-12-818630-5.10004-1">'
            'https://doi.org/10.1016/B978-0-12-818630-5.10004-1</a></li>'
        ),
        "bibtex": """@incollection{Sijtsma2023Reliability,
  title = {Reliability},
  booktitle = {International encyclopedia of education},
  author = {Sijtsma, Klaas and Pfadt, Julius M.},
  editor = {Tierney, Robert J and Rizvi, Fazal and Ercikan, Kadriye},
  date = {2023},
  edition = {4},
  pages = {21--34},
  publisher = {Elsevier},
  doi = {10.1016/B978-0-12-818630-5.10004-1},
  isbn = {978-0-12-818629-9},
  langid = {english},
  author+an = {2=highlight}
}""",
        "typst": '[Sijtsma, K., & Pfadt, J. M. (2023). Reliability. In R. Tierney, F. Rizvi, & K. Ercikan (Eds.), #emph[International encyclopedia of education] (4th ed., pp. 21-34). Elsevier. #link("https://doi.org/10.1016/B978-0-12-818630-5.10004-1")[https://doi.org/10.1016/B978-0-12-818630-5.10004-1]]',
    },
]

# ── Name overrides for contributors whose names need fixing ─────────────────
NAME_OVERRIDES = {
    "eric-jan wagenmakers": "Wagenmakers, E.-J.",
    "jan peter de ruiter": "De Ruiter, J. P.",
    "giuseppe arena, mr.": "Arena, G.",
    "giuseppe arena": "Arena, G.",
}


# ─── Helpers ────────────────────────────────────────────────────────────────

def html_escape(s: str) -> str:
    """Minimal HTML escaping."""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def replace_inline_markup(text: str, marker: str, tag: str) -> str:
    pattern = re.escape(marker) + r"(.+?)" + re.escape(marker)
    return re.sub(pattern, lambda match: f"<{tag}>{html_escape(match.group(1).strip())}</{tag}>", text)


def typst_inline_to_html(text: str) -> str:
    escaped = html_escape(" ".join(text.split()))
    escaped = replace_inline_markup(escaped, "*", "strong")
    escaped = replace_inline_markup(escaped, "_", "em")
    return escaped


def extract_reviewing_journals(main_typ: str) -> list[str]:
    section_pattern = re.compile(
        rf"(?ms)^= {re.escape(REVIEWING_SECTION_TITLE)}\s*\n+(.*?)(?=^= |\Z)"
    )
    match = section_pattern.search(main_typ)
    if match is None:
        raise RuntimeError(f"Could not find the {REVIEWING_SECTION_TITLE} section in {CV_MAIN_FILE}.")

    section_body = match.group(1).strip()
    if not section_body:
        raise RuntimeError(f"The {REVIEWING_SECTION_TITLE} section in {CV_MAIN_FILE} is empty.")

    section_text = " ".join(
        line.strip() for line in section_body.splitlines() if line.strip()
    )
    if not section_text.startswith("*Ad-hoc reviewer for*:"):
        raise RuntimeError(
            f"Could not find the ad-hoc reviewer entry in the {REVIEWING_SECTION_TITLE} section of {CV_MAIN_FILE}."
        )

    _, journals_text = section_text.split(":", maxsplit=1)
    journals_text = journals_text.strip()
    if journals_text.startswith("_") and journals_text.endswith("_"):
        journals_text = journals_text[1:-1].strip()

    journals = [journal.strip() for journal in journals_text.split(",") if journal.strip()]
    if not journals:
        raise RuntimeError(
            f"Could not extract any journals from the ad-hoc reviewer entry in {CV_MAIN_FILE}."
        )

    return journals


def bib_escape(s: str) -> str:
    """Minimal BibTeX escaping for fallback entries."""
    return (
        s.replace("\\", "\\\\")
        .replace("{", "\\{")
        .replace("}", "\\}")
    )


def strip_bibtex_braces(s: str) -> str:
    """Remove BibTeX brace-protection markers from a plain-text display value."""
    return s.replace("{", "").replace("}", "")


def typst_escape(s: str) -> str:
    """Escape text inserted into Typst content blocks."""
    return (
        s.replace("\\", "\\\\")
        .replace("#", "\\#")
        .replace("[", "\\[")
        .replace("]", "\\]")
    )


def http_get(url: str, accept: str) -> str:
    req = urllib.request.Request(url, headers={"Accept": accept})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def api_get(path: str) -> dict:
    url = f"{ORCID_API}/{path}"
    return json.loads(http_get(url, "application/json"))


def normalize_title(title: str) -> str:
    """Normalize a title for deduplication matching."""
    t = title.lower().strip()
    t = re.sub(r"[^a-z0-9\s]", "", t)
    t = re.sub(r"\s+", " ", t)
    return t


def _is_roman_numeral(word: str) -> bool:
    return bool(re.fullmatch(r"[IVXLCDM]+", word))


def _should_preserve_title_word(word: str) -> bool:
    letters_only = re.sub(r"[^A-Za-z]", "", word)
    if not letters_only:
        return False
    if word.lower() in APA_PROTECTED_TITLE_WORDS:
        return True
    if len(letters_only) > 1 and letters_only.isupper():
        return True
    if _is_roman_numeral(letters_only):
        return True
    segments = re.split(r"[-’']", word)
    return any(any(char.isupper() for char in segment[1:]) for segment in segments if segment)


def format_title_apa(title: str) -> str:
    """Convert imported titles to APA-style sentence case."""
    cleaned = " ".join((title or "Unknown title").strip().split())
    if not cleaned:
        return "Unknown title"

    chars = list(cleaned.lower())
    for match in re.finditer(r"[A-Za-z0-9]+(?:[’'][A-Za-z0-9]+)?(?:-[A-Za-z0-9]+(?:[’'][A-Za-z0-9]+)?)*", cleaned):
        word = match.group(0)
        if _should_preserve_title_word(word):
            chars[match.start() : match.end()] = list(word)

    capitalize_next = True
    for index, char in enumerate(chars):
        if capitalize_next and char.isalpha():
            chars[index] = char.upper()
            capitalize_next = False
        elif char in APA_SUBTITLE_SEPARATORS:
            capitalize_next = True

    return "".join(chars)


def format_bib_title(title: str) -> str:
    sentence_case = format_title_apa(title)

    def protect(match: re.Match[str]) -> str:
        word = match.group(0)
        if _should_preserve_title_word(word):
            return "{" + word + "}"
        return word

    return re.sub(
        r"[A-Za-z0-9]+(?:[’'][A-Za-z0-9]+)?(?:-[A-Za-z0-9]+(?:[’'][A-Za-z0-9]+)?)*",
        protect,
        sentence_case,
    )


def unwrap_bibtex_value(value: str) -> str:
    stripped = value.strip()
    if len(stripped) >= 2 and stripped[0] == stripped[-1] and stripped[0] in {'{', '"'}:
        return stripped[1:-1].strip()
    return stripped


def normalize_pages(pages: str) -> str:
    return pages.replace("--", "–")


def bibtex_fields_lookup(fields: list[tuple[str, str]]) -> dict[str, str]:
    return {name.lower(): unwrap_bibtex_value(value) for name, value in fields}


def extract_citation_details(bibtex: str, fallback_venue: str) -> CitationDetails:
    parsed = parse_bibtex_entry(bibtex)
    if parsed is None:
        return CitationDetails(venue=fallback_venue)

    _, fields = parsed
    lookup = bibtex_fields_lookup(fields)
    venue = (
        lookup.get("journaltitle")
        or lookup.get("journal")
        or lookup.get("booktitle")
        or fallback_venue
    )
    return CitationDetails(
        venue=strip_bibtex_braces(venue),
        volume=strip_bibtex_braces(lookup.get("volume", "")),
        issue=strip_bibtex_braces(lookup.get("number", "")),
        pages=normalize_pages(strip_bibtex_braces(lookup.get("pages", ""))),
        publisher=strip_bibtex_braces(lookup.get("publisher", "")),
    )


def format_html_container(details: CitationDetails, work_type: str) -> str:
    safe_venue = html_escape(details.venue)
    safe_volume = html_escape(details.volume)
    safe_issue = html_escape(details.issue)
    safe_pages = html_escape(details.pages)
    safe_publisher = html_escape(details.publisher)

    if work_type == "journal-article":
        if safe_venue and safe_volume:
            container = f"<em>{safe_venue}, {safe_volume}</em>"
            if safe_issue:
                container += f"({safe_issue})"
            if safe_pages:
                container += f", {safe_pages}"
            return container
        if safe_venue:
            container = f"<em>{safe_venue}</em>"
            if safe_pages:
                container += f", {safe_pages}"
            return container
        return safe_pages

    if work_type in {"book-chapter", "conference-paper"}:
        parts = []
        if safe_venue:
            part = f"In <em>{safe_venue}</em>"
            if safe_pages:
                part += f" (pp. {safe_pages})"
            parts.append(part)
        elif safe_pages:
            parts.append(f"(pp. {safe_pages})")
        if safe_publisher:
            parts.append(safe_publisher)
        return ". ".join(parts)

    if safe_venue:
        return f"<em>{safe_venue}</em>"
    return ""


def format_typst_container(details: CitationDetails, work_type: str) -> str:
    safe_venue = typst_escape(details.venue)
    safe_volume = typst_escape(details.volume)
    safe_issue = typst_escape(details.issue)
    safe_pages = typst_escape(details.pages)
    safe_publisher = typst_escape(details.publisher)

    if work_type == "journal-article":
        if safe_venue and safe_volume:
            container = f"#emph[{safe_venue}, {safe_volume}]"
            if safe_issue:
                container += f" ({safe_issue})"
            if safe_pages:
                container += f", {safe_pages}"
            return container
        if safe_venue:
            container = f"#emph[{safe_venue}]"
            if safe_pages:
                container += f", {safe_pages}"
            return container
        return safe_pages

    if work_type in {"book-chapter", "conference-paper"}:
        parts = []
        if safe_venue:
            part = f"In #emph[{safe_venue}]"
            if safe_pages:
                part += f" (pp. {safe_pages})"
            parts.append(part)
        elif safe_pages:
            parts.append(f"(pp. {safe_pages})")
        if safe_publisher:
            parts.append(safe_publisher)
        return ". ".join(parts)

    if safe_venue:
        return f"#emph[{safe_venue}]"
    return ""


def titles_match(left: str, right: str) -> bool:
    return left.startswith(right) or right.startswith(left)


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
    match = re.search(r"_v(\d+)$", doi)
    if match:
        version = int(match.group(1))

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
    for work in all_works:
        groups[work["norm_title"]].append(work)

    keys = sorted(groups.keys(), key=len)
    merged: dict[str, list[dict]] = {}
    for key in keys:
        canonical = None
        for existing in merged:
            if titles_match(existing, key):
                canonical = existing
                break
        if canonical is None:
            merged[key] = list(groups[key])
        else:
            longer = key if len(key) > len(canonical) else canonical
            if longer != canonical:
                merged[longer] = merged.pop(canonical) + groups[key]
            else:
                merged[canonical].extend(groups[key])

    selected = []
    for works in merged.values():
        published = [work for work in works if work["type"] in PUBLISHED_TYPES]
        preprints = [work for work in works if work["type"] == "preprint"]

        if published:
            best = max(published, key=lambda work: (work["year"], work["month"]))
        elif preprints:
            best = max(
                preprints,
                key=lambda work: (work["version"], work["year"], work["month"]),
            )
        else:
            best = max(works, key=lambda work: (work["year"], work["month"]))

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
        (part[0].upper() + ".") if not part.endswith(".") else part
        for part in first_parts
    )
    last = " ".join(last_parts)
    return f"{last}, {initials}"


def contributor_names(detail: dict) -> list[str]:
    contributors = (detail.get("contributors") or {}).get("contributor", [])
    names = []
    for contributor in contributors:
        credit_name = contributor.get("credit-name") or {}
        name = credit_name.get("value", "").strip()
        if name:
            names.append(name)
    return names


def format_authors_html(raw_names: list[str]) -> str:
    names = []
    for name in raw_names:
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


def format_authors_bib(raw_names: list[str]) -> str:
    return " and ".join(_to_apa_name(name) for name in raw_names)


def format_authors_typst(raw_names: list[str]) -> str:
    names = [typst_escape(_to_apa_name(name)) for name in raw_names]

    if not names:
        return ""
    if len(names) > MAX_AUTHORS_BEFORE_ELLIPSIS:
        return ", ".join(names[:MAX_AUTHORS_BEFORE_ELLIPSIS]) + ", . . . " + names[-1]
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + ", & " + names[-1]


def author_highlight_index(raw_names: list[str]) -> int | None:
    for index, name in enumerate(raw_names, start=1):
        if "pfadt" in name.lower():
            return index
    return None


def title_slug(title: str) -> str:
    stopwords = {"a", "an", "and", "for", "in", "of", "on", "the", "to", "using", "with"}
    words = re.findall(r"[A-Za-z0-9]+", title)
    chosen = [word for word in words if word.lower() not in stopwords]
    if not chosen:
        chosen = words
    return "".join(word[:1].upper() + word[1:] for word in chosen[:4]) or "Work"


def first_author_family(raw_names: list[str]) -> str:
    if not raw_names:
        return "Unknown"
    apa = _to_apa_name(raw_names[0])
    family = apa.split(",", 1)[0].strip()
    family = re.sub(r"[^A-Za-z0-9]", "", family)
    return family or "Unknown"


def make_citation_key(
    doi: str,
    raw_names: list[str],
    year: int,
    title: str,
    used_keys: set[str],
) -> str:
    base = KEY_OVERRIDES_BY_DOI.get(doi) or f"{first_author_family(raw_names)}{year}{title_slug(title)}"
    key = base
    suffix = ord("a")
    while key in used_keys:
        key = f"{base}{chr(suffix)}"
        suffix += 1
    used_keys.add(key)
    return key


def parse_bibtex_entry(bibtex: str) -> tuple[str, list[tuple[str, str]]] | None:
    match = re.match(r"\s*@(\w+)\{[^,]+,(.*)\}\s*$", bibtex, re.DOTALL)
    if not match:
        return None

    entry_type = match.group(1)
    body = match.group(2).strip()
    fields = []
    current = []
    depth = 0
    in_quotes = False
    escape = False

    for char in body:
        if escape:
            current.append(char)
            escape = False
            continue
        if char == "\\":
            current.append(char)
            escape = True
            continue
        if char == '"' and depth == 0:
            in_quotes = not in_quotes
        elif char == "{" and not in_quotes:
            depth += 1
        elif char == "}" and not in_quotes and depth > 0:
            depth -= 1

        if char == "," and depth == 0 and not in_quotes:
            token = "".join(current).strip()
            if token:
                fields.append(token)
            current = []
        else:
            current.append(char)

    tail = "".join(current).strip()
    if tail:
        fields.append(tail)

    parsed_fields = []
    for field in fields:
        if "=" not in field:
            continue
        name, value = field.split("=", 1)
        parsed_fields.append((name.strip(), value.strip()))

    return entry_type, parsed_fields


def render_bibtex_entry(
    entry_type: str,
    key: str,
    fields: list[tuple[str, str]],
    year: int,
    month: int,
    highlight_index: int | None,
) -> str:
    rendered_fields = []
    for name, value in fields:
        if name.lower() in {"year", "month", "date", "author+an"}:
            continue
        if name.lower() == "title":
            formatted_title = format_bib_title(unwrap_bibtex_value(value))
            rendered_fields.append(f"  title = {{{formatted_title}}}")
            continue
        rendered_fields.append(f"  {name} = {value}")

    date_value = f"{year}-{month:02d}" if month else f"{year}"
    rendered_fields.append(f"  date = {{{date_value}}}")
    if highlight_index is not None:
        rendered_fields.append(f"  author+an = {{{highlight_index}=highlight}}")

    return f"@{entry_type}{{{key},\n" + ",\n".join(rendered_fields) + "\n}"


def doi_to_bibtex(
    doi: str,
    key: str,
    highlight_index: int | None,
    year: int,
    month: int,
) -> str | None:
    if not doi:
        return None

    quoted = urllib.parse.quote(doi, safe="/")
    url = f"https://doi.org/{quoted}"
    try:
        bibtex = http_get(url, "application/x-bibtex").strip()
    except (HTTPError, URLError, TimeoutError):
        return None

    parsed = parse_bibtex_entry(bibtex)
    if parsed is None:
        return None
    entry_type, fields = parsed
    return render_bibtex_entry(entry_type, key, fields, year, month, highlight_index)


def fallback_bibtex(
    *,
    key: str,
    title: str,
    raw_names: list[str],
    year: int,
    month: int,
    work_type: str,
    venue: str,
    doi: str,
    highlight_index: int | None,
) -> str:
    entry_type = {
        "journal-article": "article",
        "book-chapter": "incollection",
        "conference-paper": "inproceedings",
        "dissertation-thesis": "thesis",
        "preprint": "online",
    }.get(work_type, "misc")

    lines = [f"@{entry_type}{{{key},"]
    lines.append(f"  title = {{{bib_escape(title)}}},")
    if raw_names:
        lines.append(f"  author = {{{format_authors_bib(raw_names)}}},")
    if month:
        lines.append(f"  date = {{{year}-{month:02d}}},")
    else:
        lines.append(f"  date = {{{year}}},")
    if work_type == "journal-article" and venue:
        lines.append(f"  journaltitle = {{{bib_escape(venue)}}},")
    elif work_type == "book-chapter" and venue:
        lines.append(f"  booktitle = {{{bib_escape(venue)}}},")
    elif venue:
        lines.append(f"  note = {{{bib_escape(venue)}}},")
    if doi:
        lines.append(f"  doi = {{{doi}}},")
        lines.append(f"  url = {{https://doi.org/{doi}}},")
    if highlight_index is not None:
        lines.append(f"  author+an = {{{highlight_index}=highlight}}")
    else:
        lines[-1] = lines[-1].rstrip(",")
    lines.append("}")
    return "\n".join(lines)


def format_html_entry(
    title: str,
    work_type: str,
    year: int,
    details: CitationDetails,
    doi: str,
    raw_names: list[str],
) -> str:
    safe_title = html_escape(title or "Unknown title")
    authors_str = format_authors_html(raw_names)

    if work_type == "preprint":
        line = f"<li>{authors_str} ({year}). <em>{safe_title}</em>."
        line += f" {html_escape(details.venue)}." if details.venue else " PsyArXiv."
    else:
        line = f"<li>{authors_str} ({year}). {safe_title}."
        container = format_html_container(details, work_type)
        if container:
            line += f" {container}."

    if doi:
        doi_url = f"https://doi.org/{doi}"
        line += f' <a href="{doi_url}">{doi_url}</a>'

    line += "</li>"
    return line


def format_typst_entry(
    title: str,
    work_type: str,
    year: int,
    details: CitationDetails,
    doi: str,
    raw_names: list[str],
) -> str:
    safe_title = typst_escape(title or "Unknown title")
    authors_str = format_authors_typst(raw_names)
    doi_url = f"https://doi.org/{doi}" if doi else ""

    parts = [authors_str, f" ({year}). "]
    if work_type == "preprint":
        parts.append(f"#emph[{safe_title}]. ")
        parts.append(f"{typst_escape(details.venue)}. " if details.venue else "PsyArXiv. ")
    else:
        parts.append(f"{safe_title}. ")
        container = format_typst_container(details, work_type)
        if container:
            parts.append(f"{container}. ")
    if doi_url:
        parts.append(f'#link("{doi_url}")[{doi_url}]')

    return "[" + "".join(parts).rstrip() + "]"


def build_orcid_publication(detail: dict, source_order: int, used_keys: set[str]) -> Publication:
    title_obj = detail.get("title", {}).get("title", {})
    raw_title = title_obj.get("value", "Unknown title")
    title = format_title_apa(raw_title)
    work_type = detail.get("type", "")

    pd = detail.get("publication-date") or {}
    year = int((pd.get("year") or {}).get("value", 0))
    month = int((pd.get("month") or {}).get("value", 0))

    journal_obj = detail.get("journal-title") or {}
    venue = journal_obj.get("value", "")

    ext_ids = (detail.get("external-ids") or {}).get("external-id", [])
    doi = ""
    for ext_id in ext_ids:
        if ext_id.get("external-id-type") == "doi":
            doi = ext_id.get("external-id-value", "")
            break

    raw_names = contributor_names(detail)
    highlight_index = author_highlight_index(raw_names)
    key = make_citation_key(doi, raw_names, year, raw_title, used_keys)

    bibtex = doi_to_bibtex(doi, key, highlight_index, year, month)
    if bibtex is None:
        bibtex = fallback_bibtex(
            key=key,
            title=title,
            raw_names=raw_names,
            year=year,
            month=month,
            work_type=work_type,
            venue=venue,
            doi=doi,
            highlight_index=highlight_index,
        )
    citation_details = extract_citation_details(bibtex, venue)

    return Publication(
        key=key,
        title=title,
        norm_title=normalize_title(raw_title),
        year=year,
        month=month,
        source_order=source_order,
        include_in_html=True,
        include_in_cv=True,
        html_entry=format_html_entry(title, work_type, year, citation_details, doi, raw_names),
        typst_entry=format_typst_entry(title, work_type, year, citation_details, doi, raw_names),
        bibtex=bibtex.strip(),
    )


def build_manual_publication(entry: dict, source_order: int, used_keys: set[str]) -> Publication:
    if entry["key"] in used_keys:
        raise RuntimeError(f"Duplicate citation key encountered: {entry['key']}")
    used_keys.add(entry["key"])
    return Publication(
        key=entry["key"],
        title=entry["norm_title"],
        norm_title=entry["norm_title"],
        year=entry["year"],
        month=entry["month"],
        source_order=source_order,
        include_in_html=entry["include_in_html"],
        include_in_cv=entry["include_in_cv"],
        html_entry=entry["html"],
        typst_entry=entry["typst"],
        bibtex=entry["bibtex"].strip(),
    )


def sort_publications(publications: list[Publication]) -> list[Publication]:
    return sorted(
        publications,
        key=lambda pub: (-pub.year, -pub.month, pub.source_order),
    )


def render_html(publications: list[Publication], reviewing_journals: list[str]) -> str:
    by_year: dict[int, list[str]] = defaultdict(list)
    for publication in publications:
        if publication.include_in_html:
            by_year[publication.year].append(publication.html_entry)

    years_desc = sorted(by_year.keys(), reverse=True)

    lines = [HTML_TOP]
    for year in years_desc:
        lines.append(f"          <h4>{year}</h4>")
        lines.append("          <ul>")
        for entry in by_year[year]:
            lines.append(f"            {entry}")
        lines.append("          </ul>")
        lines.append("")

    lines.append(
        HTML_BOTTOM.format(
            reviewing_title=html_escape(REVIEWING_PAGE_TITLE),
            reviewing_items="\n".join(
                f"            <li>{html_escape(journal)}</li>"
                for journal in reviewing_journals
            ),
        )
    )
    return "\n".join(lines)


def render_typst_publications(publications: list[Publication]) -> str:
    lines = [f"  {GENERATED_PUBLICATIONS_START}"]
    current_year = None
    for publication in publications:
        if not publication.include_in_cv:
            continue
        year_label = f"[{publication.year}]" if publication.year != current_year else "[]"
        lines.append(f"  cvitem({year_label}, {publication.typst_entry})")
        current_year = publication.year
    lines.append(f"  {GENERATED_PUBLICATIONS_END}")
    return "\n".join(lines)


def update_main_typ(main_typ: str, generated_block: str) -> str:
    pattern = re.compile(
        rf"^[ \t]*{re.escape(GENERATED_PUBLICATIONS_START)}.*?^[ \t]*{re.escape(GENERATED_PUBLICATIONS_END)}",
        re.MULTILINE | re.DOTALL,
    )
    if not pattern.search(main_typ):
        raise RuntimeError(
            f"Could not find generated publications markers in {CV_MAIN_FILE}."
        )
    return pattern.sub(generated_block, main_typ, count=1)


def build_publications() -> list[Publication]:
    print("Fetching works from ORCID …")
    data = api_get("works")
    groups = data.get("group", [])

    all_works = []
    for group in groups:
        for summary in group.get("work-summary", []):
            all_works.append(extract_summary_info(summary))

    print(f"  Found {len(all_works)} total work entries across {len(groups)} groups.")

    selected = deduplicate(all_works)
    print(f"  After deduplication: {len(selected)} unique works.")
    selected.sort(key=lambda work: (work["year"], work["month"]), reverse=True)

    manual_replacements = [
        norm_title
        for entry in MANUAL_PUBLICATIONS
        for norm_title in entry["replace_orcid_norm_titles"]
    ]

    used_keys: set[str] = set()
    publications: list[Publication] = []
    source_order = 0

    for index, work in enumerate(selected, start=1):
        print(f"  [{index}/{len(selected)}] {work['title'][:70]}…")
        if any(titles_match(work["norm_title"], replacement) for replacement in manual_replacements):
            print("    skipping ORCID item replaced by manual entry")
            continue
        detail = fetch_detail(work["put_code"])
        publications.append(build_orcid_publication(detail, source_order, used_keys))
        source_order += 1

    for entry in MANUAL_PUBLICATIONS:
        publications.append(build_manual_publication(entry, source_order, used_keys))
        source_order += 1

    return sort_publications(publications)


def preview(publications: list[Publication]) -> None:
    html_count = sum(1 for publication in publications if publication.include_in_html)
    cv_count = sum(1 for publication in publications if publication.include_in_cv)
    print("\nPreview:")
    print(f"  Would write {PUBLICATIONS_FILE} with {html_count} scientific entries.")
    print(f"  Would update the generated publications block in {CV_MAIN_FILE}.")
    print("\nCV publication keys:")
    for publication in publications:
        if publication.include_in_cv:
            print(f"  {publication.year}  {publication.key}")


def main() -> None:
    write = "--write" in sys.argv

    publications = build_publications()

    with open(CV_MAIN_FILE, "r", encoding="utf-8") as handle:
        main_typ = handle.read()
    reviewing_journals = extract_reviewing_journals(main_typ)
    html_output = render_html(publications, reviewing_journals)
    typst_output = update_main_typ(main_typ, render_typst_publications(publications))

    if write:
        with open(PUBLICATIONS_FILE, "w", encoding="utf-8") as handle:
            handle.write(html_output)
        with open(CV_MAIN_FILE, "w", encoding="utf-8") as handle:
            handle.write(typst_output)

        print(f"\n✓ Wrote {PUBLICATIONS_FILE}")
        print(f"✓ Updated {CV_MAIN_FILE}")
    else:
        preview(publications)


if __name__ == "__main__":
    main()
