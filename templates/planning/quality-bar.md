# Audit Quality Bar

This document defines the **non-negotiable quality bar** every audit-team report must meet. The orchestrator dispatches `audit-verifier` after every synthesis to enforce these rules. Failing a rule means a re-dispatch with the verifier's specific complaints — not "good enough".

Every specialist receives this file as required reading in their dispatch prompt. **Read it before scoring.**

---

## Universal rules (every specialist + the orchestrator)

### R1 — Citations are mechanical

Every finding must include a citation a reader can mechanically reproduce:

- **Code findings:** `path/to/file.ext:LINE` or `path/to/file.ext:LINE-LINE` (exact, copy-pasteable)
- **DB findings:** `table_name.column_name` + migration filename if relevant
- **Domain findings:** the exact domain reference, NOT paraphrase (e.g. clause/section/case-id/study-id)
- **Workflow findings:** trigger event + the breaking step (or step number in a flow diagram)
- **Competitive findings:** vendor URL or "{vendor} demo, {date}" — NEVER vague "competitors do X"

If a finding has no citable source, it is a vibes-finding. **Vibes-findings fail verification.**

**Live verification:** when static analysis is inconclusive, escape to live tools — the project's database MCP, browser-driver / playwriter, deploy-platform CLI, etc. A finding backed by a live screenshot or query result is stronger than one backed by static reading alone.

### R2 — Severity is calibrated

Severity tags map to **business consequence**, not author opinion:

| Tag | Threshold |
|-----|-----------|
| 🔴 **P0** | Blocks a sale, blocks a certification, leaks data, crashes prod, violates a hard regulatory line without workaround |
| 🟠 **P1** | Loses a deal in procurement bake-off, fails an audit Major, breaks an integration the user paid for |
| 🟡 **P2** | Hinweis-level finding, slows users, degrades UX but not a blocker |
| 🟢 **OK** | Fully covered, no action needed |

Stylistic improvements that don't fit P0–P2 go in a **Nits** section, not the main findings.

**Common dishonest patterns the verifier catches:**
- All findings tagged 🔴 — author lacks calibration
- 🔴 with no actual deal-breaker consequence — fail
- 🟢 OK with no evidence — fail (unsubstantiated praise)
- 🟡 P2 used as a dumping ground — fail (either it matters, or it's a Nit)

### R3 — Recommendations are concrete

Every recommendation must include:

- **Effort:** S (<4h), M (1–3 days), L (>3 days, often involves migration / spec work)
- **Driver:** which specialist's finding(s) made this priority — cited by finding ID or section heading
- **Sequencing:** what blocks/unblocks
- **Verifiable outcome:** what state would prove "done" — re-runnable probe (SQL, test, citation lookup, etc.)

**Vague:** *"Improve audit module"* — fails.

**Concrete:** *"Add `audit_program_cycle` field on `audit_plans` table (migration 00146); UI displays in /audits header; verified by Lead-Auditor walkthrough — Effort M; Driver regulatory-officer F-003 + competitive-analyst gap-7"* — passes.

### R4 — Self-check section is required

Every report must end with:

```markdown
## Self-Check

- [ ] All required sections present (per agent spec)
- [ ] All findings have R1-compliant citations
- [ ] Severity tags applied per R2
- [ ] Recommendations meet R3 (effort + driver + sequencing + verifiable outcome)
- [ ] Confidence: high | medium | low — {reason}
- [ ] What would lift confidence to high: {if not high}
- [ ] Cross-agent contradictions flagged: yes | no | n/a
```

The specialist signs off by checking each box. The verifier checks the boxes are honest.

### R5 — Cross-agent contradictions surface

If a peer's report contradicts your finding, do not paper over it. Flag it:

```markdown
**Contradicts:** workflow-architect/{date}-{slug}.md §W3 says hazard→risk is wired; my reading
of `hazard_service.py:88` shows the FK is nullable and the form doesn't enforce it.
Resolution proposed: re-trace with workflow-architect to confirm whether "wired" means
schema-present or actually-required.
```

The verifier double-checks contradiction handling. **Surfaced contradictions strengthen a report; suppressed contradictions sink it.**

---

## Specialist-specific minima

The orchestrator's `/init` skill writes specialist-specific minima here when generating the team. Each domain specialist has rules like *"≥1 finding per <domain-axis> in scope"* or *"coverage matrix has ≥10 rows"*. The audit-verifier enforces these.

Universal minima (every project, regardless of domain):

| Specialist | Minimum bar |
|-----------|-------------|
| qa-engineer | ≥1 finding per pattern checked OR explicit "no findings — verified by query X"; file:line on every code finding |
| audit-verifier | re-dispatch instructions copy-pasteable for every FAIL; sampled ≥5 findings/specialist for Q2 calibration |
| audit-orchestrator | TL;DR ≤3 sentences; top-N actions cite ≥2 specialists per action; "if you do these N things in <horizon>" closing |

(Domain specialists' minima get appended below by `/init`.)

<!-- DOMAIN-SPECIALIST-MINIMA-START -->
<!-- DOMAIN-SPECIALIST-MINIMA-END -->

---

## What the verifier checks

Two layers:

### Deterministic (fast, free) — `verify_audit.py`

- File exists at expected path
- Required sections present (regex on `^## `)
- Severity tags present (emoji match)
- Citations present (regex match for file:line, §clause, vendor URL)
- Self-check section present
- Sampled file:line citations resolve (file exists + line range valid)

### Qualitative (LLM, audit-verifier agent)

- Recommendations meet R3 (concrete? effort? driver?)
- Synthesis is cross-cutting (top-N actions cite multiple specialists per action, not just one)
- Severity calibration looks honest (not all 🔴 to look thorough)
- Contradictions flagged or genuinely absent
- Confidence statement is honest (low confidence with no remediation plan = fail)

---

## Verifier verdict

| Verdict | Trigger | Orchestrator action |
|---------|---------|--------------------|
| **PASS** | All deterministic + qualitative checks green | proceed to delivery |
| **PASS-WITH-WARNINGS** | All deterministic green; ≤2 qualitative warnings | proceed; warnings noted in strategic report |
| **FAIL** | Any deterministic FAIL OR ≥3 qualitative warnings | re-dispatch failing specialist with verifier's specific complaints |
| **HARD-FAIL** | ≥1 specialist file missing entirely OR synthesis lacks specialist cites | full re-run of failing specialist + synthesis re-do |

Re-dispatches are capped at 2 retries per specialist per audit run. After 2, escalate to user.

---

## Maintenance

This file is owned by `audit-orchestrator` and `/init`. When new specialists are added:

- Update the minima table (add row)
- Update `verify_audit.py` PATTERNS dict (add specialist's required sections)

**Keep this file under 200 lines.** Concision matters more than coverage when every agent has to read it.
