"""Turn exported owner feedback into routing-corpus candidates.

Usage: python feedback_to_corpus.py golge-export.json   (export from /api/export)
Prints lines to review by hand and paste into skill_routing_corpus.CASES with the right label.
"""
import json
import sys

import feedback_skills


def main(path: str) -> int:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    lines = feedback_skills.corpus_lines(data.get("feedback", []))
    print("\n".join(lines) if lines else "# no negative feedback to review")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]) if len(sys.argv) == 2 else print(__doc__) or 2)
