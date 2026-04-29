#!/usr/bin/env python3
"""
practice harness — deterministic audit verifier

Runs structural checks on a completed audit run before the audit-verifier
agent does the qualitative review. Catches the cheap failures: missing
files, missing required sections, missing severity tags, broken citations.
The agent only spends LLM tokens on findings that pass these checks.

Usage:
    python .planning/audits/_context/verify_audit.py <date> [--slug <slug>]
    python .planning/audits/_context/verify_audit.py latest
    python .planning/audits/_context/verify_audit.py --refresh-patterns  # auto-validate vocabulary vs agent specs

Outputs:
    .planning/audits/_context/verification/<date>-<slug>.json   — machine-readable
    .planning/audits/_context/verification/<date>-<slug>.md     — human-readable

Exit codes:
    0 — PASS or PASS-WITH-WARNINGS
    1 — FAIL
    2 — HARD-FAIL (≥1 specialist file missing)
    3 — invocation error

The audit-verifier agent reads both outputs as input to its qualitative pass.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent
AUDITS_DIR = ROOT / ".planning" / "audits"
VERIFICATION_DIR = AUDITS_DIR / "_context" / "verification"
AGENTS_DIR = ROOT / ".claude" / "agents"


# ---------------------------------------------------------------------------
# Auto-vocabulary extraction from agent spec files.
# Eliminates false-positive FAILs caused by heading-name mismatches between
# what specialists write and what REQUIRED_SECTIONS expects.
# Extracts `## ` headings from each agent's output template section,
# deduplicates against existing patterns, and reports gaps.
# ---------------------------------------------------------------------------
def extract_sections_from_agent_spec(agent_name: str) -> list[str]:
    """Parse an agent's .md spec and extract required section names from output templates.

    Looks for fenced code blocks after '# Output' or '## Output' headings
    and extracts `## Section Name` patterns from them. Also extracts any
    headings mentioned in 'required_sections' lists within the spec.
    """
    spec_path = AGENTS_DIR / f"{agent_name}.md"
    if not spec_path.exists():
        return []
    text = spec_path.read_text(encoding="utf-8", errors="ignore")
    sections: list[str] = []

    # Strategy 1: Extract ## headings from fenced code blocks in Output sections
    in_output = False
    in_fence = False
    for line in text.splitlines():
        if re.match(r"^#{1,3}\s+Output", line, re.IGNORECASE):
            in_output = True
            continue
        if in_output and re.match(r"^#{1,2}\s+[A-Z]", line) and "output" not in line.lower():
            in_output = False
            continue
        if in_output:
            if line.strip().startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                m = re.match(r"^#{2,4}\s+(.+?)\s*$", line)
                if m:
                    heading = m.group(1).strip()
                    # Strip template variables like {Scope}, {date}, etc.
                    heading = re.sub(r"\{[^}]+\}", "", heading).strip(" —-")
                    if heading and heading not in sections:
                        sections.append(heading)

    # Strategy 2: Extract from explicit section lists in the spec
    for m in re.finditer(r"required.sections?.*?:\s*\[([^\]]+)\]", text, re.IGNORECASE):
        for name in re.findall(r'"([^"]+)"', m.group(1)):
            if name not in sections:
                sections.append(name)

    return sections


def discover_specialist_agents() -> list[str]:
    """Find all specialist agent .md files (excluding universal agents)."""
    universal = {"implementer", "tester", "audit-verifier", "_specialist-template"}
    if not AGENTS_DIR.is_dir():
        return []
    return [
        p.stem for p in AGENTS_DIR.glob("*.md")
        if p.stem not in universal and not p.name.startswith(".")
    ]


def merge_extracted_vocabulary() -> dict[str, list[str]]:
    """Extract vocabulary from all agent specs and report new headings not in REQUIRED_SECTIONS.

    Returns a dict of specialist -> list of new section names found in the spec
    that aren't already covered by the specialist pattern set.
    """
    novelties: dict[str, list[str]] = {}
    specialists = discover_specialist_agents()
    existing_specialist_flat: set[str] = set()
    for pattern in REQUIRED_SECTIONS.get("specialist", []):
        # Extract the human-readable part from the regex
        cleaned = pattern.replace(r"^## ", "").replace(r"\s*", " ").strip()
        existing_specialist_flat.add(cleaned.lower())

    for spec_name in specialists:
        extracted = extract_sections_from_agent_spec(spec_name)
        if not extracted:
            continue
        new = [s for s in extracted if s.lower() not in existing_specialist_flat]
        if new:
            novelties[spec_name] = new
    return novelties


def refresh_patterns_report() -> str:
    """Generate a human-readable report of vocabulary gaps between agent specs and REQUIRED_SECTIONS."""
    novelties = merge_extracted_vocabulary()
    if not novelties:
        return "[refresh-patterns] All agent spec headings are covered by REQUIRED_SECTIONS. No gaps."
    lines = ["[refresh-patterns] Vocabulary gaps detected:"]
    for specialist, new_sections in novelties.items():
        lines.append(f"  {specialist}:")
        for sec in new_sections:
            lines.append(f'    + "{sec}" (found in agent spec, not in REQUIRED_SECTIONS)')
        lines.append(f"    → Consider adding to REQUIRED_SECTIONS['specialist'] or as a per-specialist override.")
    return "\n".join(lines)


REQUIRED_SECTIONS = {
    "orchestrator": [
        r"^## TL;DR",
        r"^## Strategic narrative",
        r"^## Top-?N?\s*(prioritised actions|actions)",
        r"^## Self-Check",
    ],
    "specialist": [
        r"^## Executive Summary",
        r"^## Findings",
        r"^## Self-Check",
    ],
}

CITATION_PATTERNS = [
    re.compile(r"`([^`]+\.\w+):(\d+)(?:-(\d+))?`"),
    re.compile(r"\b([\w/.-]+\.\w+):(\d+)(?:-(\d+))?\b"),
]

SEVERITY_PATTERN = re.compile(r"🔴|🟠|🟡|🟢|P0|P1|P2")


def find_audit_runs(date: str | None, slug: str | None = None) -> list[Path]:
    """Resolve which run(s) to verify. Returns list of orchestrator synthesis paths."""
    orch_dir = AUDITS_DIR / "orchestrator"
    if not orch_dir.is_dir():
        return []

    candidates = sorted(orch_dir.glob("*.md"))
    candidates = [c for c in candidates if not c.name.endswith("-PLAN.md")]
    candidates = [c for c in candidates if "build-" not in c.name]

    if date == "latest":
        return [candidates[-1]] if candidates else []

    if date:
        prefix = f"{date}-"
        candidates = [c for c in candidates if c.name.startswith(prefix)]
        if slug:
            candidates = [c for c in candidates if slug in c.name]
        return candidates

    return candidates[-1:] if candidates else []


def find_specialist_reports(date: str, slug: str) -> dict[str, Path]:
    """Locate every specialist report referenced by an audit slug."""
    specialists: dict[str, Path] = {}
    for d in AUDITS_DIR.iterdir():
        if not d.is_dir() or d.name.startswith("_") or d.name in ("orchestrator", "audit-verifier"):
            continue
        candidate = d / f"{date}-{slug}.md"
        if candidate.exists():
            specialists[d.name] = candidate
    return specialists


def check_required_sections(content: str, kind: str) -> list[str]:
    """Return list of missing required sections."""
    missing: list[str] = []
    for pattern in REQUIRED_SECTIONS[kind]:
        if not re.search(pattern, content, re.MULTILINE | re.IGNORECASE):
            missing.append(pattern)
    return missing


def check_severity_tags(content: str) -> int:
    """Return count of severity-tag uses."""
    return len(SEVERITY_PATTERN.findall(content))


def extract_citations(content: str) -> list[tuple[str, int, int | None]]:
    """Extract (file, line, end_line) tuples from the report."""
    citations: list[tuple[str, int, int | None]] = []
    for pattern in CITATION_PATTERNS:
        for m in pattern.finditer(content):
            file = m.group(1)
            line = int(m.group(2))
            end = int(m.group(3)) if m.group(3) else None
            citations.append((file, line, end))
    return citations


def verify_citation(file: str, line: int, end_line: int | None) -> str | None:
    """Return None if citation resolves; error string if not."""
    p = ROOT / file
    if not p.exists():
        return f"file does not exist: {file}"
    try:
        line_count = sum(1 for _ in p.open())
    except OSError as e:
        return f"cannot read {file}: {e}"
    target = end_line or line
    if line < 1 or target > line_count:
        return f"line {line}{'-'+str(end_line) if end_line else ''} out of range (file has {line_count} lines)"
    return None


def verify_run(synthesis_path: Path) -> dict:
    """Run all deterministic checks on one audit run. Return result dict."""
    name = synthesis_path.stem
    m = re.match(r"^(\d{4}-\d{2}-\d{2})-(.+)$", name)
    if not m:
        return {"verdict": "HARD-FAIL", "error": f"cannot parse date+slug from {name}"}

    date, slug = m.group(1), m.group(2)
    result: dict = {
        "synthesis": str(synthesis_path.relative_to(ROOT)).replace("\\", "/"),
        "date": date,
        "slug": slug,
        "checks": {},
        "warnings": [],
        "failures": [],
        "verdict": "PASS",
    }

    try:
        synth_content = synthesis_path.read_text(encoding="utf-8")
    except OSError as e:
        result["failures"].append(f"cannot read synthesis: {e}")
        result["verdict"] = "HARD-FAIL"
        return result

    missing = check_required_sections(synth_content, "orchestrator")
    if missing:
        result["failures"].append(f"orchestrator missing sections: {missing}")
        result["verdict"] = "FAIL"
    result["checks"]["orchestrator_sections"] = "PASS" if not missing else "FAIL"

    sev_count = check_severity_tags(synth_content)
    result["checks"]["orchestrator_severity_tags"] = sev_count
    if sev_count == 0:
        result["warnings"].append("orchestrator has 0 severity tags")

    specialists = find_specialist_reports(date, slug)
    result["specialists_found"] = list(specialists.keys())

    if not specialists:
        result["failures"].append("no specialist reports found for this audit slug")
        result["verdict"] = "HARD-FAIL"
        return result

    for spec_name, spec_path in specialists.items():
        try:
            spec_content = spec_path.read_text(encoding="utf-8")
        except OSError as e:
            result["failures"].append(f"{spec_name}: cannot read ({e})")
            result["verdict"] = "HARD-FAIL"
            continue

        missing = check_required_sections(spec_content, "specialist")
        if missing:
            result["failures"].append(f"{spec_name} missing sections: {missing}")
            if result["verdict"] != "HARD-FAIL":
                result["verdict"] = "FAIL"

        sev = check_severity_tags(spec_content)
        if sev == 0:
            result["warnings"].append(f"{spec_name} has 0 severity tags")

        citations = extract_citations(spec_content)
        sample = citations[: min(5, len(citations))]
        bad: list[str] = []
        for file, line, end in sample:
            err = verify_citation(file, line, end)
            if err:
                bad.append(f"{file}:{line} → {err}")
        if bad:
            result["warnings"].append(f"{spec_name} broken citations: {bad}")

        result["checks"][f"{spec_name}_sections"] = "PASS" if not missing else "FAIL"
        result["checks"][f"{spec_name}_citations_sampled"] = len(sample)
        result["checks"][f"{spec_name}_citations_broken"] = len(bad)

    if result["verdict"] == "PASS" and result["warnings"]:
        result["verdict"] = "PASS-WITH-WARNINGS"

    return result


def write_outputs(result: dict) -> tuple[Path, Path]:
    """Write JSON + Markdown reports. Return both paths."""
    VERIFICATION_DIR.mkdir(parents=True, exist_ok=True)
    base = f"{result['date']}-{result['slug']}"
    json_path = VERIFICATION_DIR / f"{base}.json"
    md_path = VERIFICATION_DIR / f"{base}.md"

    json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    md = [f"# Audit Verification — {result['date']} {result['slug']}", ""]
    md.append(f"**Verifier:** `verify_audit.py` (deterministic)")
    md.append(f"**Run at:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    md.append(f"**Synthesis:** `{result['synthesis']}`")
    md.append("")
    md.append(f"## Verdict: **{result['verdict']}**")
    md.append("")

    if result.get("failures"):
        md.append("### Failures")
        for f in result["failures"]:
            md.append(f"- ❌ {f}")
        md.append("")
    if result.get("warnings"):
        md.append("### Warnings")
        for w in result["warnings"]:
            md.append(f"- ⚠️ {w}")
        md.append("")

    md.append("### Specialists found")
    for s in result.get("specialists_found", []):
        md.append(f"- `{s}`")
    md.append("")

    md.append("### Checks")
    md.append("")
    md.append("| Check | Result |")
    md.append("|-------|--------|")
    for k, v in result.get("checks", {}).items():
        md.append(f"| `{k}` | {v} |")
    md.append("")

    md.append("### Next step")
    if result["verdict"] == "PASS":
        md.append("Audit-verifier agent runs the qualitative pass.")
    elif result["verdict"] == "PASS-WITH-WARNINGS":
        md.append("Audit-verifier agent runs the qualitative pass; warnings noted.")
    elif result["verdict"] == "FAIL":
        md.append("Orchestrator re-dispatches failing specialists with the failure list above.")
    else:
        md.append("**HARD-FAIL** — full re-run required. Likely orchestrator bug, not specialist bug.")

    md_path.write_text("\n".join(md), encoding="utf-8")
    return json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(description="practice harness — deterministic audit verifier")
    parser.add_argument("date", nargs="?", default=None, help="YYYY-MM-DD or 'latest'")
    parser.add_argument("--slug", default=None, help="optional slug filter (e.g. 'foundation-audit')")
    parser.add_argument(
        "--refresh-patterns",
        action="store_true",
        help="auto-extract vocabulary from agent specs and report gaps vs REQUIRED_SECTIONS",
    )
    args = parser.parse_args()

    # --refresh-patterns mode: report vocabulary gaps and exit
    if args.refresh_patterns:
        report = refresh_patterns_report()
        print(report)
        return 0

    if not args.date:
        parser.error("date is required (YYYY-MM-DD or 'latest') unless --refresh-patterns is used")

    # Auto-validate vocabulary on every run (non-blocking warning)
    novelties = merge_extracted_vocabulary()
    if novelties:
        print("⚠️  Vocabulary gaps detected (run --refresh-patterns for details):", file=sys.stderr)
        for specialist, new in novelties.items():
            print(f"  {specialist}: {len(new)} new heading(s) in agent spec not in REQUIRED_SECTIONS", file=sys.stderr)

    runs = find_audit_runs(args.date, args.slug)
    if not runs:
        print(f"ERR: no audit runs found for date={args.date} slug={args.slug}", file=sys.stderr)
        return 3

    exit_code = 0
    for run in runs:
        result = verify_run(run)
        json_path, md_path = write_outputs(result)
        print(f"{result['verdict']}: {run.name}")
        print(f"  -> {str(md_path.relative_to(ROOT)).replace(chr(92), '/')}")
        print(f"  -> {str(json_path.relative_to(ROOT)).replace(chr(92), '/')}")
        verdict_to_exit = {"PASS": 0, "PASS-WITH-WARNINGS": 0, "FAIL": 1, "HARD-FAIL": 2}
        exit_code = max(exit_code, verdict_to_exit.get(result["verdict"], 1))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
