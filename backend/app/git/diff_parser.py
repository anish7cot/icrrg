"""Unified diff parser – converts raw diff text into structured Pydantic models."""

from __future__ import annotations

import re
from pydantic import BaseModel

# Matches hunk headers: @@ -a,b +c,d @@ optional section heading
_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


class DiffLine(BaseModel):
    """A single added or removed line inside a hunk."""

    line_number: int  # 1-indexed in the *new* file (for adds) or *old* file (for removes)
    content: str  # line text without the leading +/- character
    change_type: str  # "add" or "remove"


class FileDiff(BaseModel):
    """Parsed diff for one file."""

    old_path: str | None = None  # path from --- header (None for new files)
    new_path: str | None = None  # path from +++ header (None for deleted files)
    is_binary: bool = False
    lines: list[DiffLine] = []

    @property
    def added_lines(self) -> list[DiffLine]:
        return [l for l in self.lines if l.change_type == "add"]

    @property
    def removed_lines(self) -> list[DiffLine]:
        return [l for l in self.lines if l.change_type == "remove"]


class ParsedDiff(BaseModel):
    """Top-level result of parsing a unified diff."""

    files: list[FileDiff] = []

    @property
    def total_additions(self) -> int:
        return sum(len(f.added_lines) for f in self.files)

    @property
    def total_deletions(self) -> int:
        return sum(len(f.removed_lines) for f in self.files)


def _strip_prefix(path: str) -> str:
    """Remove the a/ or b/ prefix git adds to paths."""
    if path.startswith(("a/", "b/")):
        return path[2:]
    return path


def parse_unified_diff(raw_diff: str) -> ParsedDiff:
    """Parse a raw unified diff string into structured data.

    Focuses on text file additions and removals.  Binary diffs are recorded
    but their contents are not parsed.
    """
    files: list[FileDiff] = []
    current_file: FileDiff | None = None
    old_line = 0
    new_line = 0

    for line in raw_diff.splitlines():
        # --- Start of a new file diff ---
        if line.startswith("diff --git"):
            if current_file is not None:
                files.append(current_file)
            current_file = FileDiff()
            continue

        if current_file is None:
            continue

        # Binary file marker
        if line.startswith("Binary files") or line.startswith("GIT binary patch"):
            current_file.is_binary = True
            continue

        # Old file path
        if line.startswith("--- "):
            path = line[4:].strip()
            current_file.old_path = None if path == "/dev/null" else _strip_prefix(path)
            continue

        # New file path
        if line.startswith("+++ "):
            path = line[4:].strip()
            current_file.new_path = None if path == "/dev/null" else _strip_prefix(path)
            continue

        # Hunk header
        m = _HUNK_RE.match(line)
        if m:
            old_line = int(m.group(1))
            new_line = int(m.group(3))
            continue

        # Skip binary files content
        if current_file.is_binary:
            continue

        # Added line
        if line.startswith("+"):
            current_file.lines.append(
                DiffLine(line_number=new_line, content=line[1:], change_type="add")
            )
            new_line += 1
            continue

        # Removed line
        if line.startswith("-"):
            current_file.lines.append(
                DiffLine(line_number=old_line, content=line[1:], change_type="remove")
            )
            old_line += 1
            continue

        # Context line (unchanged) – advance both counters
        if line.startswith(" "):
            old_line += 1
            new_line += 1
            continue

        # "\ No newline at end of file" and other noise – skip
    
    if current_file is not None:
        files.append(current_file)

    return ParsedDiff(files=files)
