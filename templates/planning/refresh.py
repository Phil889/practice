#!/usr/bin/env python3
"""
practice harness — context-inventory refresh

Scans the project and regenerates `.planning/audits/_context/` inventory files
that every specialist reads at the start of an audit. Runs before any
heavy playbook so specialists work against current state, not stale state.

Usage:
    python .planning/audits/_context/refresh.py [--check]

Flags:
    --check    Don't write; just verify inventories are up-to-date with
               the current commit. Exit 0 if fresh, 1 if stale. CI-friendly.

The inventory files generated:
    SUMMARY.md           — one-line index of every other inventory
    modules.md           — top-level module/directory list
    routes.md            — frontend routes (if applicable)
    api-routes.md        — backend API endpoints (if applicable)
    db-tables.md         — database tables + columns (if applicable)
    ai-agents.md         — AI agent inventory (if applicable)
    debugging-tools.md   — live-verification tooling available

Detection is best-effort and graceful. Missing categories produce
"N/A — not applicable to this project" stub files instead of crashing.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent.parent.parent.parent
CONTEXT_DIR = ROOT / ".planning" / "audits" / "_context"


def git_rev() -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
            text=True,
        ).strip()
    except subprocess.CalledProcessError:
        return "unknown"


def git_root_clean() -> bool:
    try:
        out = subprocess.check_output(
            ["git", "-C", str(ROOT), "status", "--porcelain"],
            text=True,
        )
        return out.strip() == ""
    except subprocess.CalledProcessError:
        return False


def detect_stack() -> dict[str, str | bool]:
    """Detect primary stack signals from common manifest files."""
    signals: dict[str, str | bool] = {
        "primary_lang": "unknown",
        "web_framework": "unknown",
        "test_framework": "unknown",
        "db_layer": "unknown",
        "has_python_backend": False,
        "has_js_frontend": False,
        "has_rust": False,
        "has_go": False,
        "has_ruby": False,
    }

    if (ROOT / "package.json").exists():
        signals["has_js_frontend"] = True
        try:
            pkg = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            for fw in ("next", "remix", "astro", "vite", "react"):
                if fw in deps:
                    signals["web_framework"] = fw
                    break
            for tf in ("jest", "vitest", "playwright", "cypress"):
                if tf in deps:
                    signals["test_framework"] = tf
                    break
            for db in ("@supabase/supabase-js", "prisma", "drizzle-orm", "kysely"):
                if db in deps:
                    signals["db_layer"] = db.split("/")[-1]
                    break
        except (json.JSONDecodeError, OSError):
            pass

    if (ROOT / "requirements.txt").exists() or (ROOT / "pyproject.toml").exists():
        signals["has_python_backend"] = True
        signals["primary_lang"] = "python"
        py_text = ""
        for p in ("requirements.txt", "pyproject.toml"):
            f = ROOT / p
            if f.exists():
                try:
                    py_text += f.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    pass
        if "fastapi" in py_text.lower():
            signals["web_framework"] = "fastapi"
        elif "django" in py_text.lower():
            signals["web_framework"] = "django"
        elif "flask" in py_text.lower():
            signals["web_framework"] = "flask"
        if "pytest" in py_text.lower():
            signals["test_framework"] = "pytest"

    if signals["primary_lang"] == "unknown" and signals["has_js_frontend"]:
        signals["primary_lang"] = "typescript" if (ROOT / "tsconfig.json").exists() else "javascript"

    if (ROOT / "go.mod").exists():
        signals["has_go"] = True
        if signals["primary_lang"] == "unknown":
            signals["primary_lang"] = "go"
    if (ROOT / "Cargo.toml").exists():
        signals["has_rust"] = True
        if signals["primary_lang"] == "unknown":
            signals["primary_lang"] = "rust"
    if (ROOT / "Gemfile").exists():
        signals["has_ruby"] = True
        if signals["primary_lang"] == "unknown":
            signals["primary_lang"] = "ruby"

    return signals


def list_modules(stack: dict) -> list[tuple[str, int]]:
    """List top-level module directories with file count."""
    candidates: list[Path] = []
    for parent in ("src", "app", "backend", "frontend", "internal", "lib", "modules"):
        p = ROOT / parent
        if p.is_dir():
            for child in sorted(p.iterdir()):
                if child.is_dir() and not child.name.startswith("."):
                    candidates.append(child)
    if not candidates:
        for child in sorted(ROOT.iterdir()):
            if child.is_dir() and not child.name.startswith(".") and child.name not in (
                "node_modules", "venv", ".venv", "target", "dist", "build", "out",
            ):
                candidates.append(child)

    out: list[tuple[str, int]] = []
    for c in candidates:
        n = sum(1 for _ in c.rglob("*") if _.is_file())
        if n > 0:
            rel = c.relative_to(ROOT)
            out.append((str(rel).replace("\\", "/"), n))
    return out


def list_routes(stack: dict) -> list[str]:
    """Frontend routes — Next.js app/[locale]/... or pages/... patterns."""
    routes: list[str] = []
    for app_dir in (ROOT / "app", ROOT / "frontend" / "app", ROOT / "src" / "app"):
        if app_dir.is_dir():
            for p in app_dir.rglob("page.*"):
                if p.suffix in (".tsx", ".jsx", ".ts", ".js"):
                    rel = p.relative_to(app_dir).parent
                    routes.append("/" + str(rel).replace("\\", "/"))
    for pages_dir in (ROOT / "pages", ROOT / "frontend" / "pages"):
        if pages_dir.is_dir():
            for p in pages_dir.rglob("*.*"):
                if p.suffix in (".tsx", ".jsx", ".ts", ".js") and p.name not in ("_app.tsx", "_document.tsx"):
                    rel = p.relative_to(pages_dir).with_suffix("")
                    routes.append("/" + str(rel).replace("\\", "/").replace("/index", ""))
    return sorted(set(routes))


def list_api_routes(stack: dict) -> list[str]:
    """Backend API routes — best-effort grep for FastAPI/Django/Express decorators."""
    endpoints: list[str] = []
    for backend_dir in (ROOT / "backend", ROOT / "api", ROOT / "src" / "api", ROOT):
        if not backend_dir.is_dir():
            continue
        for ext in ("*.py",):
            for p in backend_dir.rglob(ext):
                try:
                    content = p.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                for m in re.finditer(r'@\w+\.(get|post|put|delete|patch)\(\s*["\']([^"\']+)["\']', content):
                    endpoints.append(f"{m.group(1).upper()} {m.group(2)}")
    return sorted(set(endpoints))


def list_db_tables(stack: dict) -> list[str]:
    """DB tables from migrations — pattern-match CREATE TABLE statements."""
    tables: set[str] = set()
    for migrations_dir in (
        ROOT / "supabase" / "migrations",
        ROOT / "db" / "migrate",
        ROOT / "migrations",
        ROOT / "alembic" / "versions",
        ROOT / "prisma" / "migrations",
    ):
        if not migrations_dir.is_dir():
            continue
        for p in migrations_dir.rglob("*"):
            if p.is_file() and p.suffix in (".sql", ".py"):
                try:
                    content = p.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                for m in re.finditer(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?["`]?(\w+)["`]?', content, re.IGNORECASE):
                    tables.add(m.group(1))
    return sorted(tables)


def list_ai_agents(stack: dict) -> list[str]:
    """AI agent files — pattern-match common agent SDK imports."""
    agents: list[str] = []
    for ai_dir in (ROOT / "backend" / "app" / "ai", ROOT / "src" / "ai", ROOT / "ai"):
        if ai_dir.is_dir():
            for p in ai_dir.rglob("*_agent.py"):
                rel = p.relative_to(ROOT)
                agents.append(str(rel).replace("\\", "/"))
            for p in ai_dir.rglob("*_agent.ts"):
                rel = p.relative_to(ROOT)
                agents.append(str(rel).replace("\\", "/"))
    return sorted(agents)


def detect_debugging_tools() -> list[str]:
    """List of live-verification tools available in this project."""
    tools: list[str] = []
    if (ROOT / "supabase").is_dir():
        tools.append("Supabase MCP — `mcp__supabase__execute_sql` for live DB queries")
    if (ROOT / "vercel.json").exists() or (ROOT / ".vercel").is_dir():
        tools.append("Vercel CLI / MCP — `vercel logs`, deploy inspection")
    if (ROOT / "render.yaml").exists():
        tools.append("Render CLI — `rnd services events`, log streaming")
    if (ROOT / ".github" / "workflows").is_dir():
        tools.append("GitHub CLI — `gh run list`, `gh pr view` for CI state")
    if (ROOT / "playwright.config.ts").exists() or (ROOT / "playwright.config.js").exists():
        tools.append("Playwright — `playwriter` CLI for UI verification")
    return tools


def write_inventory(name: str, content: str) -> None:
    target = CONTEXT_DIR / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def render_summary(stack: dict, modules_count: int, routes_count: int, api_routes_count: int,
                   tables_count: int, agents_count: int) -> str:
    rev = git_rev()
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"""# Context Inventory — Summary

**Refreshed:** {ts}
**Git rev:** {rev}
**Stack:** {stack['primary_lang']} · {stack['web_framework']} · {stack['db_layer']} · tests via {stack['test_framework']}

## Inventory files in this directory

- `SUMMARY.md` — this file
- `modules.md` — {modules_count} modules
- `routes.md` — {routes_count} frontend routes
- `api-routes.md` — {api_routes_count} backend endpoints
- `db-tables.md` — {tables_count} DB tables
- `ai-agents.md` — {agents_count} AI agents
- `debugging-tools.md` — live verification tooling
- `quality-bar.md` — non-negotiable rules every report must meet

## How specialists use these

Every specialist's working method begins with reading this SUMMARY.md plus the inventory file(s) relevant to its domain. Without these files, specialists work against grep-only state — slower and more error-prone.

## Refresh

Run before any heavy playbook:

```bash
python .planning/audits/_context/refresh.py
```

Or check freshness in CI:

```bash
python .planning/audits/_context/refresh.py --check
```
"""


def render_modules(modules: list[tuple[str, int]]) -> str:
    rows = "\n".join(f"| `{name}` | {n} |" for name, n in modules) or "| — | 0 |"
    return f"""# Modules Inventory

**Refreshed:** {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}
**Git rev:** {git_rev()}

| Module | File count |
|--------|-----------|
{rows}
"""


def render_list(title: str, items: list[str], empty: str = "(none detected)") -> str:
    body = "\n".join(f"- `{i}`" for i in items) if items else empty
    return f"""# {title}

**Refreshed:** {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}
**Git rev:** {git_rev()}

{body}
"""


def render_debugging_tools(tools: list[str]) -> str:
    body = "\n".join(f"- {t}" for t in tools) if tools else "(no automated detection — add tools your specialists should use here)"
    return f"""# Debugging & Live-Verification Tools

**Refreshed:** {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}
**Git rev:** {git_rev()}

When static analysis is inconclusive, specialists escape to live tools to reproduce findings. The harness detected the following:

{body}

## How specialists use these

A finding backed by a live probe (DB query, browser screenshot, CI log) is **stronger** than one backed by static reading alone. Specialists are encouraged to escape to live tools whenever a finding's reproduction is non-obvious from code.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="practice harness — context-inventory refresh")
    parser.add_argument("--check", action="store_true", help="Verify inventories are fresh; don't write.")
    args = parser.parse_args()

    if not (ROOT / ".git").exists():
        print("ERR: not a git repository. practice requires a git project.", file=sys.stderr)
        return 2

    stack = detect_stack()
    modules = list_modules(stack)
    routes = list_routes(stack)
    api_routes = list_api_routes(stack)
    tables = list_db_tables(stack)
    agents = list_ai_agents(stack)
    tools = detect_debugging_tools()

    inventories = {
        "SUMMARY.md": render_summary(stack, len(modules), len(routes), len(api_routes), len(tables), len(agents)),
        "modules.md": render_modules(modules),
        "routes.md": render_list("Frontend Routes", routes, "(no frontend routes detected — N/A for this project)"),
        "api-routes.md": render_list("API Endpoints", api_routes, "(no API endpoints detected — N/A for this project)"),
        "db-tables.md": render_list("Database Tables", tables, "(no DB migrations detected — N/A for this project)"),
        "ai-agents.md": render_list("AI Agents", agents, "(no AI agent files detected — N/A for this project)"),
        "debugging-tools.md": render_debugging_tools(tools),
    }

    if args.check:
        stale: list[str] = []
        for name, expected in inventories.items():
            target = CONTEXT_DIR / name
            if not target.exists():
                stale.append(f"{name} (missing)")
                continue
            actual = target.read_text(encoding="utf-8")
            actual_no_ts = re.sub(r"\*\*Refreshed:\*\* [^\n]+\n", "", actual)
            actual_no_ts = re.sub(r"\*\*Git rev:\*\* [^\n]+\n", "", actual_no_ts)
            expected_no_ts = re.sub(r"\*\*Refreshed:\*\* [^\n]+\n", "", expected)
            expected_no_ts = re.sub(r"\*\*Git rev:\*\* [^\n]+\n", "", expected_no_ts)
            if actual_no_ts != expected_no_ts:
                stale.append(f"{name} (content drift)")
        if stale:
            print("STALE: " + ", ".join(stale), file=sys.stderr)
            return 1
        print("FRESH: all inventories match current state.")
        return 0

    for name, content in inventories.items():
        write_inventory(name, content)

    print(f"refreshed {len(inventories)} inventories at {git_rev()}")
    print(f"  modules: {len(modules)} | routes: {len(routes)} | api: {len(api_routes)} | tables: {len(tables)} | agents: {len(agents)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
