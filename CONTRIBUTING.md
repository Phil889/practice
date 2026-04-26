# Contributing to practice

Thanks for opening this file — most projects don't, and that already puts you ahead.

`practice` is the harness extracted from a real project that ships audited compliance work daily. The contribution standards mirror the harness's own quality bar: **evidence-grounded, audit-trail-complete, no vibes-based changes.**

If that sounds heavy, it is — and it's the point. The harness is only as trustworthy as its own development process.

---

## What we accept

| Type | How likely we merge | Notes |
|------|--------------------|-------|
| **Bug fixes** | high | with a `verifiable_outcome` probe in the PR description |
| **New domain templates** (e.g. a `tax-specialist` archetype for accounting projects) | high | one PR per domain; include a sample audit run |
| **New workflows** (multi-skill chains with a gate) | medium | only after the chain has been used ≥3 times in a real project; include the rationale |
| **New universal agents** (additions to the four — qa-engineer, audit-verifier, implementer, tester) | low | the four are load-bearing; new universals raise the maintenance bar for every project |
| **Re-architecture** (changes to the four-tier USER ↔ SUPERVISOR ↔ ORCHESTRATORS ↔ AGENTS split) | very low | propose as an HSI in an issue first; we'll discuss before any code |
| **Documentation polish** | high | typo fixes, broken-link fixes, clarification PRs always welcome |
| **New language refresh.{js,go,rb}** | high | one per ecosystem; must produce equivalent inventories to the Python version |

---

## How to propose a change

### Small fixes (typo, broken link, one-line clarification)

PR directly. Include:

- The change
- A one-sentence rationale in the PR body

That's it. We'll merge the same day if it's clean.

### Substantive changes (new template, workflow, behavioural change)

Open an issue first as an **HSI proposal** — same shape `practice` uses internally:

```
HSI proposal — <one-line headline>

Trigger evidence: <what observation made this worth proposing? Cite a real run, a community report, or a specific gap>
Hypothesis: <if we change X, outcome Y improves, measurable as Z>
Proposed change: <concrete spec — what file, what shape>
Verification probe: <how would we know this works after merge>
PASS condition: <quantitative threshold>
REFUTE condition: <what metric value disconfirms>
```

We'll discuss the hypothesis before any code. **It's faster.** A PR that arrives without an HSI typically gets the HSI questions in the review and the cycle takes longer.

---

## What we reject (gently, with reasoning)

These aren't bad ideas — they're just not a fit for `practice`:

- **Generic improvements without an HSI hypothesis.** "This makes the code cleaner" — maybe, but if there's no measurable outcome, we can't tell whether it actually helps. Frame the change as a hypothesis with a probe.
- **Adding a fifth tier to the architecture.** The four-tier split (User ↔ Supervisor ↔ Orchestrators ↔ Agents) is structurally enforced by Claude Code's runtime. Extending it usually masks the right answer (a new mode on an existing skill, or a new workflow).
- **Domain templates with no source codebase.** A `kyc-specialist` template generated from a real fintech project ships immediately. A `kyc-specialist` template designed in a vacuum doesn't — we won't know what failure modes it should hunt.
- **Renames that touch every template.** The `audit-orchestrator` skill name, `_findings-status/` directory, `verifiable_outcome` field — these are referenced thousands of places by users in the wild. Renames are technically free but cost the community.

---

## Development setup

```bash
git clone https://github.com/Phil889/practice.git
cd practice
# Run the test harness (work in progress)
./scripts/test.sh
```

When testing changes that affect `/init` behaviour, run against at least two test projects of different stacks (one Python, one TypeScript). The `examples/` directory has anonymised real runs you can use as fixtures.

---

## The contribution review loop

Every PR goes through the same loop the harness uses for findings:

1. **You file the PR with an HSI-style description.** Hypothesis, probe, PASS condition.
2. **A maintainer reviews against the quality bar in `templates/planning/quality-bar.md`** — citations, severity calibration, concreteness, etc. The same R1–R5 rules.
3. **The probe runs.** If the probe doesn't reproduce, we ask for evidence — not "trust me."
4. **We merge or iterate.** If the probe passes, we merge with the verification result attached. If it doesn't, we iterate or close.

This is slower than "send PR, get LGTM." It's also why the harness compounds. **Every merged change is a verified hypothesis, not a vibe.**

---

## Code of conduct

The harness's working ethos: *honest > optimistic, evidence > opinion, audit-trail > convenience.* The same applies to the community.

- **Be specific.** *"This doesn't work"* is hard to action. *"The `mode: hygiene` run failed because `_archive/findings/2026-04/` already existed and the script crashed on `mkdir`"* is reproducible.
- **Cite your sources.** When proposing a change, link the run, the artefact, the line of code. Same standard the audit team holds itself to.
- **Critique kindly.** A friendly verifier is a useless verifier — but a hostile one is also useless. Be clear, be specific, assume good faith.

---

## What you'll learn by contributing

The harness's design embeds opinions about evidence, verification, and audit trails that took a real production project to develop. Contributing to it — even a small fix — is a fast way to internalise those opinions for your own work.

If you ship a non-trivial contribution that gets merged, **we'll add you to the project's** [`AUTHORS.md`](AUTHORS.md) **and reach out to learn what `practice` is helping you build.** We genuinely want to hear what domains the harness reaches.
