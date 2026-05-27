"""Secret-scan utility for auto-docs.

Per CLAUDE.md rule 13: tracked-file content must be publish-safe. Before writing
any auto-generated line to a tracked file, redact recognized secret shapes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

PATTERNS: dict[str, re.Pattern[str]] = {
    "aws-access-key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "postgres-url-with-password": re.compile(r"postgres(?:ql)?://[^/\s:]+:[^@\s]+@"),
    "hex40-api-secret": re.compile(r"\b[a-f0-9]{40}\b"),
}


@dataclass
class ScanResult:
    safe: str
    hits: list[tuple[str, str]]


def scan(text: str) -> ScanResult:
    hits: list[tuple[str, str]] = []
    safe = text
    for name, pat in PATTERNS.items():
        for match in pat.finditer(text):
            hits.append((name, match.group(0)))
        safe = pat.sub(f"<REDACTED-{name}>", safe)
    return ScanResult(safe=safe, hits=hits)


def has_secrets(text: str) -> bool:
    return bool(scan(text).hits)
