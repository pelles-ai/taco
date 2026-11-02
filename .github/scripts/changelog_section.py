"""Print the CHANGELOG.md entries for a release.

Usage: python .github/scripts/changelog_section.py VERSION [CHANGELOG.md]

Prints the body of the ``## [VERSION]`` section. When the changelog has no
section for VERSION yet, prints the ``## [Unreleased]`` section instead,
since that holds what the release ships. Exits 1 if both are missing or
empty, so the caller can fall back to other release notes.
"""

from __future__ import annotations

import sys
from pathlib import Path


def sections(text: str) -> dict[str, str]:
    """Map each ``## [name]`` heading's name to the text under it."""
    found: dict[str, str] = {}
    name: str | None = None
    body: list[str] = []
    for line in text.splitlines():
        if line.startswith("## ["):
            if name is not None:
                found.setdefault(name, "\n".join(body).strip())
            name, body = line[4 : line.index("]")], []
        elif name is not None:
            body.append(line)
    if name is not None:
        found.setdefault(name, "\n".join(body).strip())
    return found


def release_notes(version: str, text: str) -> str:
    found = sections(text)
    return found.get(version.removeprefix("v")) or found.get("Unreleased", "")


def main(argv: list[str]) -> int:
    if len(argv) not in (2, 3):
        print(__doc__, file=sys.stderr)
        return 2
    path = Path(argv[2] if len(argv) == 3 else "CHANGELOG.md")
    notes = release_notes(argv[1], path.read_text(encoding="utf-8"))
    if not notes:
        return 1
    print(notes)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
