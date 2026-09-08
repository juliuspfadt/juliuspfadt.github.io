#!/usr/bin/env python3
"""
Rebuild cv/main.pdf from cv/main.typ.

Usage:
    python3 update_cv.py           # compile if main.typ is newer than main.pdf
    python3 update_cv.py --force   # compile unconditionally
    python3 update_cv.py --check   # report staleness only, exit 1 if stale

The PDF is committed, so it goes stale whenever main.typ changes -- most often
because update_publications.py rewrote the publication list. Run this before
pushing so the published CV matches the source.

Paths are resolved relative to this file, so it works from any directory
(including VS Code's Run button, which does not guarantee the repo root).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
CV_TYP = REPO_ROOT / "cv" / "main.typ"
CV_PDF = REPO_ROOT / "cv" / "main.pdf"


def is_stale() -> bool:
    """True if the PDF is missing or older than the Typst source."""
    if not CV_PDF.exists():
        return True
    return CV_TYP.stat().st_mtime > CV_PDF.stat().st_mtime


def compile_cv() -> None:
    typst = shutil.which("typst")
    if typst is None:
        sys.exit("update_cv: typst not found -- install it with 'brew install typst'")

    print("update_cv: compiling cv/main.pdf")
    result = subprocess.run(
        [typst, "compile", "--root", str(REPO_ROOT), str(CV_TYP), str(CV_PDF)]
    )
    if result.returncode != 0:
        sys.exit(f"update_cv: typst failed (exit {result.returncode})")

    print(f"✓ Wrote {CV_PDF.relative_to(REPO_ROOT)} ({CV_PDF.stat().st_size:,} bytes)")


def main() -> None:
    force = "--force" in sys.argv
    check = "--check" in sys.argv

    if not CV_TYP.exists():
        sys.exit(f"update_cv: missing {CV_TYP}")

    stale = is_stale()

    if check:
        if stale:
            sys.exit("update_cv: cv/main.pdf is STALE (cv/main.typ is newer)")
        print("update_cv: cv/main.pdf is up to date")
        return

    if not stale and not force:
        print("update_cv: cv/main.pdf is up to date (use --force to recompile)")
        return

    compile_cv()


if __name__ == "__main__":
    main()
