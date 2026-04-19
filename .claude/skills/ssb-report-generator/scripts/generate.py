"""Helpers for the ssb-report-generator skill.

CLI:
    python generate.py slugify --question "..."
    python generate.py hash --filters '{"Region":["0301"]}'
    python generate.py render --question ... --type html|dashboard ...

Pure functions; no SSB or Anthropic calls. Claude invokes this from the skill
workflow after collecting all inputs through the SSB MCP.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

STOP_WORDS = {
    "lag", "vis", "make", "show", "for", "om", "the", "a", "an",
    "of", "on", "and", "to", "report", "rapport",
    "dashboard", "oppsummering", "summary", "interaktiv", "interactive",
}

NORWEGIAN_TRANSLITERATION = str.maketrans({
    "æ": "ae", "Æ": "ae",
    "ø": "oe", "Ø": "oe",
    "å": "aa", "Å": "aa",
})

MAX_SLUG_LEN = 60


def slugify(text: str) -> str:
    """Deterministic kebab-case slug from a free-text question.

    1. Lowercase + Norwegian transliteration.
    2. Drop non-ASCII alphanumerics (keep digits + spaces + hyphens).
    3. Tokenize, drop stop words.
    4. Join with hyphens; collapse runs of hyphens.
    5. Truncate at <=MAX_SLUG_LEN at a word boundary; trim trailing hyphens.
    """
    if not text:
        return ""
    text = text.lower().translate(NORWEGIAN_TRANSLITERATION)
    text = re.sub(r"[^a-z0-9\s\-]", " ", text)
    tokens = [t for t in re.split(r"[\s\-]+", text) if t and t not in STOP_WORDS]
    slug = "-".join(tokens)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    if len(slug) <= MAX_SLUG_LEN:
        return slug
    cut = slug[:MAX_SLUG_LEN]
    last_hyphen = cut.rfind("-")
    if last_hyphen > 0:
        cut = cut[:last_hyphen]
    return cut.rstrip("-")


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("slugify")
    s.add_argument("--question", required=True)
    args = parser.parse_args()
    if args.cmd == "slugify":
        print(slugify(args.question))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
