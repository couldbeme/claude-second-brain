"""Deterministic toolkit health checker — finds underused Claude Code platform features.

Audits commands/, agents/, skills/, and CLAUDE.md.template against a static feature
catalog. Every rule is a regex or structural check. No LLM calls. No .jsonl body reads.

Public API:
    Finding, ArtifactFile, CatalogEntry, AuditReport — dataclasses
    load_catalog, collect_corpus, run_rules, _parse_frontmatter,
    _parse_tools_list, _format_report, main

v0.1 — 12 rules across CMD, AGENT, SKILL, TMPL, SESSION categories.

Design: SELF-AUDIT-DESIGN-2026-04-28.md
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Sibling toolkit import — matches existing test convention (Q5)
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from context_estimator import estimate_from_transcript, ContextEstimate
    _CONTEXT_ESTIMATOR_AVAILABLE = True
except ImportError:
    _CONTEXT_ESTIMATOR_AVAILABLE = False

# ---------------------------------------------------------------------------
# Defaults (Q2: script-relative target, falls back to ~/Dev/claude-second-brain)
# ---------------------------------------------------------------------------

def _default_target() -> Path:
    candidate = Path(__file__).resolve().parent.parent
    if (candidate / "commands").is_dir():
        return candidate
    fallback = Path.home() / "Dev" / "claude-second-brain"
    return fallback


DEFAULT_TARGET = _default_target()
DEFAULT_CATALOG = Path(__file__).resolve().parent / "self_audit_catalog.json"

# ---------------------------------------------------------------------------
# Regex
# ---------------------------------------------------------------------------

_BASH_PATTERN = re.compile(
    r"(?:`[^`]*`|\brun\b|\bexecute\b|\$\(|\bshell\b|\bgit\s|\bnpm\s|\bpython3?\s)",
    re.IGNORECASE,
)
_WEB_PATTERN = re.compile(
    r"(?:\bsearch\b.*\bweb\b|\bweb\b.*\bsearch\b|\bfetch\b.*https?://|https?://\S+\bfetch\b|\bWebSearch\b|\bWebFetch\b)",
    re.IGNORECASE,
)
_MCP_TOOL_PATTERN = re.compile(r"\b(memory|context7|deepwiki)\b", re.IGNORECASE)
_REASONING_KEYWORDS = re.compile(
    r"\b(architect(?:ure)?|research|analyz[ei]|design|deep.think|reason|synthesiz[ei])\b",
    re.IGNORECASE,
)
_LIGHTWEIGHT_KEYWORDS = re.compile(
    r"\b(verify|lint|check|validate|format|count|summariz[ei])\b",
    re.IGNORECASE,
)
_SCRIPT_PATH_RE = re.compile(
    r"(?:python3?\s+|bash\s+|sh\s+|run:\s*`?)(~?/[\w./\-_~]+\.py)\b"
)
_PLAN_RE = re.compile(r"\bplan\b", re.IGNORECASE)
_PLAN_MODE_RE = re.compile(r"plan.mode|/plan\b", re.IGNORECASE)
_AGENT_SPAWN_RE = re.compile(r"\b(Agent|Task|subagent|sub-agent|spawn)\b", re.IGNORECASE)
_PHASE_RE = re.compile(r"\bPhase\s+\d+\b|\bphase\b\s*\d+", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class CatalogEntry:
    id: str
    category: str
    name: str
    description: str
    docs_url: str | None
    detection_rule_id: str | None
    status: str  # "verified" | "unverified"


@dataclass
class ArtifactFile:
    path: Path
    artifact_type: str        # "command" | "agent" | "skill" | "template"
    frontmatter: dict[str, str]
    body: str
    tools: list[str]          # parsed tools list (empty if no tools: key)


@dataclass
class Finding:
    target: str
    rule_id: str
    feature_underused: str
    suggestion: str
    effort: str
    impact: str
    severity: str             # "warn" | "info"
    evidence: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AuditReport:
    generated_at: str
    catalog_version: str
    catalog_age_days: int
    corpus_stats: dict[str, int]
    findings: list[Finding]
    summary: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["findings"] = [f.as_dict() for f in self.findings]
        return d


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------

def load_catalog(catalog_path: Path = DEFAULT_CATALOG) -> list[CatalogEntry]:
    """Load feature catalog from JSON. Raises FileNotFoundError if missing."""
    raw = json.loads(catalog_path.read_text(encoding="utf-8"))
    return [CatalogEntry(**f) for f in raw["features"]]


def _catalog_meta(catalog_path: Path = DEFAULT_CATALOG) -> tuple[str, int]:
    """Return (catalog_version, age_in_days)."""
    raw = json.loads(catalog_path.read_text(encoding="utf-8"))
    version = raw.get("catalog_version", "unknown")
    try:
        version_date = datetime.strptime(version, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        age = (datetime.now(tz=timezone.utc) - version_date).days
    except ValueError:
        age = 0
    return version, age


# ---------------------------------------------------------------------------
# Frontmatter parser (hand-rolled, no yaml dep)
# ---------------------------------------------------------------------------

def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Parse YAML-ish frontmatter fenced by '---' lines.

    Returns (frontmatter_dict, body_text).
    - No frontmatter → ({}, full text).
    - Incomplete (no closing ---) → ({}, full text) — tolerates silently.
    - Multi-line values not supported (single-key-value per line only).
    """
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip() != "---":
        return {}, text

    # Find closing fence
    close_idx = None
    for i, line in enumerate(lines[1:], start=1):
        if line.rstrip() == "---":
            close_idx = i
            break

    if close_idx is None:
        return {}, text

    fm: dict[str, str] = {}
    for line in lines[1:close_idx]:
        if ":" in line:
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip()

    body = "".join(lines[close_idx + 1:])
    return fm, body


def _parse_tools_list(raw: str) -> list[str]:
    """Parse a comma-separated tools string, stripping parenthesized args.

    'Glob, Read, Bash(git log:*), WebFetch(url)' → ['Glob', 'Read', 'Bash', 'WebFetch']
    """
    if not raw or not raw.strip():
        return []
    result = []
    for part in raw.split(","):
        part = part.strip()
        # Strip anything from '(' onward
        paren_idx = part.find("(")
        if paren_idx != -1:
            part = part[:paren_idx].strip()
        if part:
            result.append(part)
    return result


# ---------------------------------------------------------------------------
# Corpus collection
# ---------------------------------------------------------------------------

def collect_corpus(target: Path) -> list[ArtifactFile]:
    """Collect all toolkit artifact files. Skips unreadable files silently."""
    artifacts: list[ArtifactFile] = []

    def _load(path: Path, artifact_type: str) -> ArtifactFile | None:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None
        fm, body = _parse_frontmatter(text)
        tools = _parse_tools_list(fm.get("tools", ""))
        return ArtifactFile(path=path, artifact_type=artifact_type,
                            frontmatter=fm, body=body, tools=tools)

    # commands/*.md
    cmd_dir = target / "commands"
    if cmd_dir.is_dir():
        for p in sorted(cmd_dir.glob("*.md")):
            a = _load(p, "command")
            if a:
                artifacts.append(a)

    # agents/*.md
    agent_dir = target / "agents"
    if agent_dir.is_dir():
        for p in sorted(agent_dir.glob("*.md")):
            a = _load(p, "agent")
            if a:
                artifacts.append(a)

    # skills/*/SKILL.md
    skills_dir = target / "skills"
    if skills_dir.is_dir():
        for p in sorted(skills_dir.glob("*/SKILL.md")):
            a = _load(p, "skill")
            if a:
                artifacts.append(a)

    # CLAUDE.md.template (optional)
    tmpl = target / "CLAUDE.md.template"
    if tmpl.exists():
        a = _load(tmpl, "template")
        if a:
            artifacts.append(a)

    return artifacts


def _corpus_stats(corpus: list[ArtifactFile]) -> dict[str, int]:
    stats: dict[str, int] = {"commands": 0, "agents": 0, "skills": 0, "template": 0}
    for a in corpus:
        if a.artifact_type == "command":
            stats["commands"] += 1
        elif a.artifact_type == "agent":
            stats["agents"] += 1
        elif a.artifact_type == "skill":
            stats["skills"] += 1
        elif a.artifact_type == "template":
            stats["template"] += 1
    return stats


# ---------------------------------------------------------------------------
# Settings.json reader (Q4: grace-fail)
# ---------------------------------------------------------------------------

def _read_settings_json() -> tuple[dict, str | None]:
    """Return (parsed_settings, error_reason). error_reason is None on success."""
    settings_path = Path.home() / ".claude" / "settings.json"
    try:
        return json.loads(settings_path.read_text(encoding="utf-8")), None
    except FileNotFoundError:
        return {}, f"settings.json not readable: file not found at {settings_path}"
    except PermissionError:
        return {}, f"settings.json not readable: permission denied"
    except json.JSONDecodeError as e:
        return {}, f"settings.json not readable: JSON parse error — {e}"


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------

def _rel(path: Path, base: Path | None = None) -> str:
    """Relative path string for display, or absolute if base unknown."""
    if base and path.is_absolute():
        try:
            return str(path.relative_to(base))
        except ValueError:
            pass
    return path.name


def _finding(
    artifact: ArtifactFile,
    rule_id: str,
    feature_underused: str,
    suggestion: str,
    effort: str,
    impact: str,
    severity: str,
    evidence: str,
    base: Path | None = None,
) -> Finding:
    return Finding(
        target=_rel(artifact.path, base),
        rule_id=rule_id,
        feature_underused=feature_underused,
        suggestion=suggestion,
        effort=effort,
        impact=impact,
        severity=severity,
        evidence=evidence,
    )


def _rule_cmd1(a: ArtifactFile, base: Path | None) -> Finding | None:
    """R-CMD-1: argument-hint present but $ARGUMENTS absent from body."""
    has_hint = "argument-hint" in a.frontmatter
    has_placeholder = "$ARGUMENTS" in a.body
    if has_hint and not has_placeholder:
        return _finding(
            a, "R-CMD-1", "argument-hint (CMD-1)",
            "Use $ARGUMENTS in body or remove argument-hint from frontmatter",
            "S", "S", "warn",
            f"{_rel(a.path, base)}: argument-hint present but no $ARGUMENTS in body",
            base,
        )
    return None


def _rule_cmd2(a: ArtifactFile, base: Path | None) -> Finding | None:
    """R-CMD-2: body spawns agents but no phase structure."""
    if not _AGENT_SPAWN_RE.search(a.body):
        return None
    if _PHASE_RE.search(a.body):
        return None
    return _finding(
        a, "R-CMD-2", "orchestration layering (AGENT-1)",
        "Add Phase structure to command body for multi-agent orchestration clarity",
        "M", "M", "info",
        f"{_rel(a.path, base)}: agent/Task keyword found but no Phase structure",
        base,
    )


def _rule_cmd3(a: ArtifactFile, base: Path | None) -> Finding | None:
    """R-CMD-3: $ARGUMENTS in body but no argument-hint in frontmatter."""
    has_hint = "argument-hint" in a.frontmatter
    has_placeholder = "$ARGUMENTS" in a.body
    if has_placeholder and not has_hint:
        return _finding(
            a, "R-CMD-3", "argument-hint (SKILL-1)",
            "Add 'argument-hint' to frontmatter for /guide discoverability",
            "S", "S", "warn",
            f"{_rel(a.path, base)}: $ARGUMENTS at body but no argument-hint in frontmatter",
            base,
        )
    return None


def _rule_cmd4(a: ArtifactFile, base: Path | None) -> Finding | None:
    """R-CMD-4: command teaches settings.json but no hooks examples."""
    body_lower = a.body.lower()
    mentions_settings = "settings.json" in body_lower
    has_hook_example = "hook" in body_lower
    if mentions_settings and not has_hook_example:
        return _finding(
            a, "R-CMD-4", "hooks examples (HOOK-1/HOOK-2)",
            "Include hook configuration examples alongside settings.json guidance",
            "S", "S", "info",
            f"{_rel(a.path, base)}: settings.json mentioned but no hook examples",
            base,
        )
    return None


def _rule_cmd5(a: ArtifactFile, base: Path | None) -> Finding | None:
    """R-CMD-5: body mentions 'plan' without plan-mode reference."""
    if _PLAN_RE.search(a.body) and not _PLAN_MODE_RE.search(a.body):
        return _finding(
            a, "R-CMD-5", "plan-mode (PLAN-1)",
            "Link to plan-mode pattern where 'plan' is mentioned",
            "S", "S", "info",
            f"{_rel(a.path, base)}: 'plan' mentioned but no plan-mode reference",
            base,
        )
    return None


def _rule_agent1(a: ArtifactFile, base: Path | None) -> Finding | None:
    """R-AGENT-1: model:sonnet + reasoning keywords → suggest opus."""
    model = a.frontmatter.get("model", "").lower()
    if "sonnet" not in model:
        return None
    if _REASONING_KEYWORDS.search(a.body):
        return _finding(
            a, "R-AGENT-1", "model selection (MODEL-1)",
            "Consider model: opus for architecture/research/analysis agents",
            "S", "S", "info",
            f"{_rel(a.path, base)}: model=sonnet with reasoning keyword; opus may perform better",
            base,
        )
    return None


def _rule_agent2(a: ArtifactFile, base: Path | None) -> Finding | None:
    """R-AGENT-2: model:sonnet + lightweight keywords → suggest haiku."""
    model = a.frontmatter.get("model", "").lower()
    if "sonnet" not in model:
        return None
    if _LIGHTWEIGHT_KEYWORDS.search(a.body):
        return _finding(
            a, "R-AGENT-2", "model selection (MODEL-2)",
            "Consider model: haiku for verify/lint/check agents (cost + speed)",
            "S", "S", "info",
            f"{_rel(a.path, base)}: model=sonnet with lightweight keyword; haiku may be faster/cheaper",
            base,
        )
    return None


def _rule_agent3(a: ArtifactFile, base: Path | None) -> Finding | None:
    """R-AGENT-3: Bash patterns in body but Bash not in tools list."""
    if "Bash" in a.tools:
        return None
    if _BASH_PATTERN.search(a.body):
        return _finding(
            a, "R-AGENT-3", "Bash tool (TOOLS-1)",
            "Add Bash to tools: list or remove shell examples from body",
            "S", "S", "warn",
            f"{_rel(a.path, base)}: shell patterns in body but Bash not in tools list",
            base,
        )
    return None


def _rule_agent4(a: ArtifactFile, base: Path | None) -> Finding | None:
    """R-AGENT-4: web search/fetch in body but not in tools list."""
    has_web_tool = any(t in ("WebSearch", "WebFetch") for t in a.tools)
    if has_web_tool:
        return None
    if _WEB_PATTERN.search(a.body):
        return _finding(
            a, "R-AGENT-4", "WebSearch/WebFetch (TOOLS-2)",
            "Add WebSearch or WebFetch to tools: list",
            "S", "S", "warn",
            f"{_rel(a.path, base)}: web search/fetch in body but not in tools list",
            base,
        )
    return None


def _rule_agent5(a: ArtifactFile, base: Path | None) -> Finding | None:
    """R-AGENT-5: MCP tool referenced in body but server not in tools list."""
    mcp_tools = {"memory", "context7", "deepwiki"}
    body_lower = a.body.lower()
    fm_lower = " ".join(a.frontmatter.values()).lower()
    mcp_in_body = any(t in body_lower for t in mcp_tools)
    mcp_in_tools = any(t.lower() in mcp_tools for t in a.tools)
    # Also check if any mcp tool name appears in tools list as-is
    tools_lower = {t.lower() for t in a.tools}
    if mcp_in_body and not mcp_in_tools and not any(t in tools_lower for t in mcp_tools):
        return _finding(
            a, "R-AGENT-5", "MCP tool wiring (MCP-1/MCP-2)",
            "Add MCP server tool to tools: list or document inheritance",
            "S", "M", "warn",
            f"{_rel(a.path, base)}: MCP tool referenced in body but not declared in tools",
            base,
        )
    return None


def _rule_skill1(a: ArtifactFile, base: Path | None) -> Finding | None:
    """R-SKILL-1: SKILL.md has no argument-hint."""
    if "argument-hint" not in a.frontmatter:
        return _finding(
            a, "R-SKILL-1", "argument-hint (SKILL-1)",
            "Add argument-hint to SKILL.md frontmatter for /guide discoverability",
            "S", "S", "warn",
            f"{_rel(a.path, base)}: no argument-hint in SKILL.md frontmatter",
            base,
        )
    return None


def _rule_skill2(a: ArtifactFile, base: Path | None) -> Finding | None:
    """R-SKILL-2: SKILL.md references a script path that doesn't exist."""
    full_body = a.body
    for match in _SCRIPT_PATH_RE.finditer(full_body):
        raw_path = match.group(1)
        resolved = Path(os.path.expanduser(raw_path))
        if not resolved.exists():
            return _finding(
                a, "R-SKILL-2", "script path validity",
                f"Fix path {raw_path!r} or update after rename",
                "S", "S", "warn",
                f"{_rel(a.path, base)}: referenced script missing: {raw_path}",
                base,
            )
    return None


def _rule_skill3(a: ArtifactFile, base: Path | None) -> Finding | None:
    """R-SKILL-3: SKILL.md describes hook but hook not in settings.json."""
    if "hook" not in a.body.lower():
        return None
    settings, err = _read_settings_json()
    if err:
        return _finding(
            a, "R-SKILL-3", "hook in settings.json (SETTINGS-1)",
            "Add hook setup note to SKILL.md or verify settings.json",
            "M", "S", "info",
            f"{_rel(a.path, base)}: {err}",
            base,
        )
    hooks = settings.get("hooks", {})
    if not hooks:
        return _finding(
            a, "R-SKILL-3", "hook in settings.json (SETTINGS-1)",
            "Add hook to settings.json or add setup note to SKILL.md",
            "M", "S", "info",
            f"{_rel(a.path, base)}: SKILL mentions hook but settings.json has no hooks configured",
            base,
        )
    return None


def _rule_tmpl1(a: ArtifactFile, base: Path | None) -> Finding | None:
    """R-TMPL-1: CLAUDE.md.template missing PostToolUse mention."""
    if "PostToolUse" not in a.body:
        return _finding(
            a, "R-TMPL-1", "PostToolUse hook (HOOK-3)",
            "Add PostToolUse hook example to template if relevant",
            "M", "M", "info",
            f"{_rel(a.path, base)}: PostToolUse not mentioned in template",
            base,
        )
    return None


def _rule_tmpl2(a: ArtifactFile, base: Path | None) -> Finding | None:
    """R-TMPL-2: template references MCP tool not in settings.json.template."""
    mcp_tools = {"memory", "context7", "deepwiki"}
    body_lower = a.body.lower()
    mentioned = [t for t in mcp_tools if t in body_lower]
    if not mentioned:
        return None
    # Check if settings.json.template exists alongside template
    settings_tmpl = a.path.parent / "memory-mcp" / "settings.json.template"
    if not settings_tmpl.exists():
        # Also check same dir
        settings_tmpl = a.path.parent / "settings.json.template"
    if settings_tmpl.exists():
        tmpl_text = settings_tmpl.read_text(encoding="utf-8").lower()
        undocumented = [t for t in mentioned if t not in tmpl_text]
    else:
        undocumented = mentioned
    if undocumented:
        return _finding(
            a, "R-TMPL-2", "MCP dependency documentation (MCP-1/MCP-2)",
            f"Document MCP dependency {undocumented} in settings.json.template explicitly",
            "S", "S", "warn",
            f"{_rel(a.path, base)}: MCP tool(s) {undocumented} referenced but not in settings template",
            base,
        )
    return None


def _rule_session1(
    base: Path | None, no_session: bool
) -> Finding | None:
    """R-SESSION-1: percent_used > 0.75 on sonnet → suggest opus."""
    if no_session or not _CONTEXT_ESTIMATOR_AVAILABLE:
        return None
    # Find most recent .jsonl transcript
    transcript_dir = Path.home() / ".claude" / "projects"
    if not transcript_dir.is_dir():
        return None
    transcripts = sorted(transcript_dir.rglob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not transcripts:
        return None
    transcript = transcripts[0]
    try:
        est: ContextEstimate = estimate_from_transcript(transcript)
    except Exception:
        return None
    if est.percent_used > 0.75 and "sonnet" in est.model.lower():
        return Finding(
            target="session",
            rule_id="R-SESSION-1",
            feature_underused="model selection (MODEL-1)",
            suggestion="Consider model: opus for long-context reasoning sessions",
            effort="S",
            impact="S",
            severity="info",
            evidence=f"session {est.session_id}: {est.percent_used:.0%} of {est.model} context used",
        )
    return None


# ---------------------------------------------------------------------------
# Rule dispatch
# ---------------------------------------------------------------------------

_CMD_RULES = [_rule_cmd1, _rule_cmd2, _rule_cmd3, _rule_cmd4, _rule_cmd5]
_AGENT_RULES = [_rule_agent1, _rule_agent2, _rule_agent3, _rule_agent4, _rule_agent5]
_SKILL_RULES = [_rule_skill1, _rule_skill2, _rule_skill3]
_TMPL_RULES = [_rule_tmpl1, _rule_tmpl2]


def run_rules(
    corpus: list[ArtifactFile],
    catalog: list[CatalogEntry],
    base: Path | None = None,
    rule_ids: list[str] | None = None,
    no_session: bool = False,
) -> list[Finding]:
    """Run all applicable rules over corpus. Returns sorted findings list.

    Sorting: severity desc (warn before info), then effort asc (S before M before L).
    """
    findings: list[Finding] = []

    def _add(f: Finding | None) -> None:
        if f and (rule_ids is None or f.rule_id in rule_ids):
            findings.append(f)

    for a in corpus:
        if a.artifact_type == "command":
            for rule in _CMD_RULES:
                _add(rule(a, base))
        elif a.artifact_type == "agent":
            for rule in _AGENT_RULES:
                _add(rule(a, base))
        elif a.artifact_type == "skill":
            for rule in _SKILL_RULES:
                _add(rule(a, base))
        elif a.artifact_type == "template":
            for rule in _TMPL_RULES:
                _add(rule(a, base))

    # R-SESSION-1 (global, not per-file)
    _add(_rule_session1(base, no_session))

    # Sort: warn first, then info; within each, S effort before M before L
    effort_order = {"S": 0, "M": 1, "L": 2}
    sev_order = {"warn": 0, "info": 1}
    findings.sort(key=lambda f: (sev_order.get(f.severity, 99), effort_order.get(f.effort, 99)))
    return findings


# ---------------------------------------------------------------------------
# Report formatting
# ---------------------------------------------------------------------------

_SEV_PREFIX = {"warn": "[WARN]", "info": "[INFO]"}


def _format_report(report: AuditReport, fmt: str = "text") -> str:
    findings = report.findings
    stats = report.corpus_stats

    if fmt == "json":
        return json.dumps(report.as_dict(), indent=2)

    if fmt == "markdown":
        lines = [
            f"# /self-audit Report — {report.generated_at}",
            f"",
            f"**Catalog:** {report.catalog_version} ({report.catalog_age_days} days old)",
            f"**Corpus:** {stats['commands']} commands, {stats['agents']} agents, "
            f"{stats['skills']} skills, {stats['template']} template(s)",
            f"**Findings:** {report.summary['total']} total",
            f"",
        ]
        if not findings:
            lines.append("All rules passed — no findings.")
        else:
            by_sev: dict[str, list[Finding]] = {}
            for f in findings:
                by_sev.setdefault(f.severity, []).append(f)
            for sev in ("warn", "info"):
                group = by_sev.get(sev, [])
                if not group:
                    continue
                lines.append(f"## {sev.upper()} ({len(group)})")
                for f in group:
                    lines.append(f"- **{f.rule_id}** `{f.target}` — {f.suggestion}")
                    lines.append(f"  *{f.evidence}*")
                lines.append("")
        return "\n".join(lines)

    # text (default)
    if not findings:
        corpus_total = sum(stats.values())
        return f"self-audit clean: {corpus_total} artifacts, 0 findings\n"

    lines = [
        f"self-audit — {report.summary['total']} finding(s) "
        f"[catalog: {report.catalog_version}]",
        "",
    ]
    for f in findings:
        prefix = _SEV_PREFIX.get(f.severity, f.severity.upper())
        lines.append(f"{prefix} [{f.rule_id}] {f.target}")
        lines.append(f"  suggestion: {f.suggestion}")
        lines.append(f"  effort: {f.effort}  impact: {f.impact}")
        lines.append(f"  evidence: {f.evidence}")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Deterministic toolkit health checker — finds underused Claude Code features."
    )
    p.add_argument(
        "--target", default=str(DEFAULT_TARGET),
        help=f"Root of toolkit to audit (default: {DEFAULT_TARGET})",
    )
    p.add_argument(
        "--json", action="store_true",
        help="Output JSON report (implies --format json)",
    )
    p.add_argument(
        "--format", choices=["text", "markdown", "json"], default="text",
        help="Output format (default: text)",
    )
    p.add_argument(
        "--no-session", action="store_true",
        help="Disable session transcript reads (skip R-SESSION-1)",
    )
    p.add_argument(
        "--catalog", default=str(DEFAULT_CATALOG),
        help=f"Path to feature catalog JSON (default: {DEFAULT_CATALOG})",
    )
    p.add_argument(
        "--rules", default=None,
        help="Comma-separated list of rule IDs to run (default: all)",
    )
    p.add_argument(
        "--exit-on-finding", action="store_true",
        help="Exit 1 if any findings present",
    )
    p.add_argument(
        "--quiet", action="store_true",
        help="Print nothing if no findings",
    )
    args = p.parse_args(argv)

    target = Path(os.path.expanduser(args.target))
    catalog_path = Path(os.path.expanduser(args.catalog))
    fmt = "json" if args.json else args.format
    rule_ids: list[str] | None = None
    if args.rules:
        rule_ids = [r.strip() for r in args.rules.split(",") if r.strip()]

    catalog = load_catalog(catalog_path)
    catalog_version, catalog_age_days = _catalog_meta(catalog_path)

    corpus = collect_corpus(target)
    stats = _corpus_stats(corpus)

    findings = run_rules(corpus, catalog, base=target, rule_ids=rule_ids,
                         no_session=args.no_session)

    by_sev: dict[str, int] = {}
    by_effort: dict[str, int] = {}
    for f in findings:
        by_sev[f.severity] = by_sev.get(f.severity, 0) + 1
        by_effort[f.effort] = by_effort.get(f.effort, 0) + 1

    report = AuditReport(
        generated_at=datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        catalog_version=catalog_version,
        catalog_age_days=catalog_age_days,
        corpus_stats=stats,
        findings=findings,
        summary={"total": len(findings), "by_severity": by_sev, "by_effort": by_effort},
    )

    if catalog_age_days > 90:
        print(f"[WARN] catalog is {catalog_age_days} days old — run /whats-new to refresh",
              file=sys.stderr)

    output = _format_report(report, fmt)

    if findings or not args.quiet:
        print(output, end="" if output.endswith("\n") else "\n")

    if findings and args.exit_on_finding:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
