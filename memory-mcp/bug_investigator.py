"""Deterministic engine behind the /investigate skill.

Parses pasted logs/tracebacks/kernel panics into structured reports, and
gates investigation claims so none ship without a resolvable proof anchor
(the /karpathy-bar refuse-criteria, as code).

Stdlib only — mirrors whats_new_check.py / self_audit.py zero-deps stance.

Public API:
    InputKind                                  — enum
    PanicReport, Frame, TraceReport, Claim,
        Anchor, Verdict                        — dataclasses
    classify_input, parse_panic,
        parse_traceback, karpathy_gate, main
"""

from __future__ import annotations

import argparse
import enum
import json
import os
import re
import shlex
import shutil
import sys
from dataclasses import dataclass, field, asdict
from typing import Optional

# ---------------------------------------------------------------------------
# Input kinds
# ---------------------------------------------------------------------------


class InputKind(enum.Enum):
    TRACEBACK = "traceback"
    TEST_FAILURE = "test_failure"
    BUILD_ERROR = "build_error"
    KERNEL_PANIC = "kernel_panic"
    OS_LOG = "os_log"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class PanicReport:
    panic_string: str = ""
    fault_site: Optional[str] = None
    faulting_cpu: Optional[int] = None
    panicked_task: Optional[str] = None
    panicked_pid: Optional[int] = None
    loaded_kexts: list = field(default_factory=list)
    third_party_kexts: list = field(default_factory=list)
    repeated_class: Optional[str] = None
    termination_queue_depth: Optional[int] = None
    darwin_version: Optional[str] = None
    macos_name: Optional[str] = None
    hardware_model: Optional[str] = None
    backtrace_lrs: list = field(default_factory=list)


@dataclass
class Frame:
    file: Optional[str] = None
    line: Optional[int] = None
    func: Optional[str] = None
    raw: str = ""


@dataclass
class TraceReport:
    exception_type: Optional[str] = None
    exception_message: str = ""
    frames: list = field(default_factory=list)
    crash_frame: Optional[Frame] = None
    root_frame: Optional[Frame] = None


@dataclass
class Anchor:
    kind: str  # "file" | "command"
    value: str  # "path" | "path:line" | shell command


@dataclass
class Claim:
    text: str
    anchor: Optional[Anchor] = None


@dataclass
class Verdict:
    status: str  # "PASS" | "FAIL"
    unproven: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# Lookup tables — Darwin major → marketing name, Apple SoC code → model
# ---------------------------------------------------------------------------

_DARWIN_TO_MACOS = {
    25: "macOS 26 (Tahoe)",
    24: "macOS 15 (Sequoia)",
    23: "macOS 14 (Sonoma)",
    22: "macOS 13 (Ventura)",
    21: "macOS 12 (Monterey)",
}

_SOC_TO_MODEL = {
    "T8103": "Apple M1",
    "T6000": "Apple M1 Pro",
    "T6001": "Apple M1 Max",
    "T6002": "Apple M1 Ultra",
    "T8112": "Apple M2",
    "T6020": "Apple M2 Pro",
    "T6021": "Apple M2 Max",
    "T6022": "Apple M2 Ultra",
    "T8122": "Apple M3",
    "T6030": "Apple M3 Pro",
    "T6031": "Apple M3 Max",
    "T8132": "Apple M4",
    "T6041": "Apple M4 Pro",
    "T6042": "Apple M4 Max",
}


# ---------------------------------------------------------------------------
# classify_input
# ---------------------------------------------------------------------------


def classify_input(raw: str) -> InputKind:
    """Route raw pasted text to an investigation track. Order matters."""
    text = raw or ""

    if "panic(" in text and (
        re.search(r"@[\w.]+:\d+", text)
        or "Kernel version: Darwin" in text
        or "loaded kexts:" in text
        or "Debugger message: panic" in text
    ):
        return InputKind.KERNEL_PANIC

    is_test = (
        bool(re.search(r"\bRan \d+ tests?\b", text))
        or "FAILED (" in text
        or "=== FAILURES ===" in text
        or re.search(r"^FAILED \S+\.py::", text, re.M) is not None
    )
    if is_test and (
        "AssertionError" in text
        or "FAIL:" in text
        or "ERROR:" in text
        or "assert " in text
    ):
        return InputKind.TEST_FAILURE

    if "Traceback (most recent call last):" in text:
        return InputKind.TRACEBACK

    if (
        "npm ERR!" in text
        or "make: ***" in text
        or "cargo error" in text
        or re.search(r"error\[E\d+\]", text)
        or "ld: symbol(s) not found" in text
    ):
        return InputKind.BUILD_ERROR

    # syslog / `log show` style lines with no traceback or panic
    if re.search(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}", text, re.M):
        return InputKind.OS_LOG

    return InputKind.UNKNOWN


# ---------------------------------------------------------------------------
# parse_panic
# ---------------------------------------------------------------------------


def parse_panic(raw: str) -> PanicReport:
    text = raw or ""
    r = PanicReport()

    m = re.search(r"^(panic\([^\n]*)", text, re.M)
    if m:
        r.panic_string = m.group(1).strip()

    m = re.search(r"panic\(cpu (\d+)", text)
    if m:
        r.faulting_cpu = int(m.group(1))

    m = re.search(r"@([\w.]+:\d+)", text)
    if m:
        r.fault_site = m.group(1)

    m = re.search(r"termination queue depth (\d+):\s*'([^']+)'", text)
    if m:
        r.termination_queue_depth = int(m.group(1))
        r.repeated_class = m.group(2)

    m = re.search(
        r"Panicked task \S+: \d+ pages, \d+ threads: pid (\d+):\s*(\S+)", text
    )
    if m:
        r.panicked_pid = int(m.group(1))
        r.panicked_task = m.group(2)

    m = re.search(r"Darwin Kernel Version (\d+\.\d+(?:\.\d+)?)", text)
    if m:
        r.darwin_version = m.group(1)
        major = int(m.group(1).split(".")[0])
        r.macos_name = _DARWIN_TO_MACOS.get(major)

    m = re.search(r"RELEASE_\w*?_(T\d+)", text)
    if m:
        code = m.group(1)
        r.hardware_model = _SOC_TO_MODEL.get(code, f"Apple Silicon ({code})")

    r.backtrace_lrs = re.findall(r"\blr:\s*(0x[0-9a-fA-F]+)", text)

    r.loaded_kexts = _extract_kexts(text)
    r.third_party_kexts = [
        k for k in r.loaded_kexts if not k.startswith("com.apple.")
    ]
    return r


def _extract_kexts(text: str) -> list:
    lines = text.splitlines()
    out: list = []
    started = False
    for line in lines:
        if not started:
            if line.strip().startswith("loaded kexts:"):
                started = True
            continue
        # kext id = reverse-DNS (≥1 dot), followed by a digit-leading version
        m = re.match(r"\s*([A-Za-z][\w]*(?:\.[\w]+)+)\s+\d\S*", line)
        if m:
            out.append(m.group(1))
        elif line.strip():
            break  # non-blank, non-kext line → section ended
        # blank line: tolerate a gap within the section, keep scanning
    return out


# ---------------------------------------------------------------------------
# parse_traceback (Python-style)
# ---------------------------------------------------------------------------

_FRAME_RE = re.compile(r'File "(.+?)", line (\d+), in (\S+)')


def parse_traceback(raw: str) -> TraceReport:
    text = raw or ""
    t = TraceReport()

    for m in _FRAME_RE.finditer(text):
        t.frames.append(
            Frame(
                file=m.group(1),
                line=int(m.group(2)),
                func=m.group(3),
                raw=m.group(0),
            )
        )

    if t.frames:
        t.root_frame = t.frames[0]
        t.crash_frame = t.frames[-1]

    # Exception line: last non-empty line shaped `Name: message` or `Name`,
    # where Name is a capitalised (possibly dotted) identifier. No suffix
    # whitelist — covers stdlib, custom, and PEP-654 ExceptionGroup names.
    for line in reversed([ln for ln in text.splitlines() if ln.strip()]):
        em = re.match(r"^([A-Z][\w.]*)(?::[ ]?(.*))?$", line.strip())
        if em:
            t.exception_type = em.group(1)
            t.exception_message = (em.group(2) or "").strip()
            break

    return t


# ---------------------------------------------------------------------------
# karpathy_gate — a claim ships only with a resolvable proof anchor
# ---------------------------------------------------------------------------


def karpathy_gate(claims, *, repo_root: Optional[str] = None) -> Verdict:
    """FAIL if any claim lacks a resolvable proof anchor.

    file anchor      "path" or "path:line" — file must exist; line in range.
    command anchor   shell string — must pass `bash -n` (syntax check only).
    """
    unproven: list = []
    for c in claims:
        if not _anchor_resolves(c.anchor, repo_root):
            unproven.append(c.text)
    return Verdict(status="FAIL" if unproven else "PASS", unproven=unproven)


def _anchor_resolves(anchor: Optional[Anchor], repo_root: Optional[str]) -> bool:
    if anchor is None:
        return False

    if anchor.kind == "file":
        path, _, line_s = anchor.value.partition(":")
        if repo_root and not os.path.isabs(path):
            path = os.path.join(repo_root, path)
        if not os.path.isfile(path):
            return False
        if line_s:
            if not line_s.isdigit():
                return False
            want = int(line_s)
            try:
                with open(path, "r", errors="replace") as fh:
                    n = sum(1 for _ in fh)
            except OSError:
                return False
            return 1 <= want <= n
        return True

    if anchor.kind == "command":
        # No subprocess. `bash -n` is not reliably non-executing (command
        # substitution can fire at parse time, version-dependent). Validate
        # in pure Python instead: reject shell metaprogramming, then confirm
        # the executable exists — same "is this a real command" signal.
        cmd = anchor.value or ""
        if re.search(r"\$\(|`|<\(|>\(", cmd):
            return False  # command/process substitution → refuse
        try:
            tokens = shlex.split(cmd)
        except ValueError:
            return False  # unbalanced quoting = syntax error
        if not tokens:
            return False
        return shutil.which(tokens[0]) is not None

    return False  # unknown anchor kind → conservative


# ---------------------------------------------------------------------------
# redact_secrets — scrub credentials before any persistence of log-derived text
# ---------------------------------------------------------------------------

_REDACTIONS = [
    (re.compile(r"(\w+://[^:/\s]+:)[^@\s]+(@)"), r"\1[REDACTED]\2"),
    (re.compile(r"(?i)\bBearer\s+\S+"), "Bearer [REDACTED]"),
    (re.compile(r"\bsk-[A-Za-z0-9]{6,}"), "[REDACTED]"),
    (re.compile(r"\bAKIA[0-9A-Z]{8,}"), "[REDACTED]"),
    (re.compile(r"(?i)(password=)\S+"), r"\1[REDACTED]"),
]


def redact_secrets(text: str) -> str:
    """Strip common credential shapes from log-derived text.

    Call this before writing any [LEARNING]/bridge entry that paraphrases a
    pasted log — logs routinely carry connection strings, bearer tokens, and
    cloud keys. Structure (e.g. ``scheme://user:``) is preserved; the secret
    is replaced with ``[REDACTED]``.
    """
    out = text or ""
    for pat, repl in _REDACTIONS:
        out = pat.sub(repl, out)
    return out


# ---------------------------------------------------------------------------
# CLI — read stdin (or a file arg), classify, emit JSON summary
# ---------------------------------------------------------------------------


def _to_jsonable(obj):
    d = asdict(obj)
    return d


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Classify + parse a pasted log/panic/traceback.")
    p.add_argument("path", nargs="?", help="file to read; omit to read stdin")
    args = p.parse_args(argv)

    if args.path is not None:
        if not os.path.isfile(args.path):
            print(f"investigate: not a regular file: {args.path!r}", file=sys.stderr)
            return 1
        try:
            with open(args.path, errors="replace") as fh:
                raw = fh.read()
        except OSError as exc:
            print(f"investigate: cannot read {args.path!r}: {exc}", file=sys.stderr)
            return 1
    else:
        raw = sys.stdin.read()

    kind = classify_input(raw)
    out = {"kind": kind.value}
    if kind is InputKind.KERNEL_PANIC:
        out["panic"] = _to_jsonable(parse_panic(raw))
    elif kind in (InputKind.TRACEBACK, InputKind.TEST_FAILURE):
        out["traceback"] = _to_jsonable(parse_traceback(raw))
    json.dump(out, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
