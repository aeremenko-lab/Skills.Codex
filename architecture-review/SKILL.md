---
name: architecture-review
description: Rigorous read-only architecture conformance review for software repositories. Use when Codex is asked to compare existing code against architecture, approach, design, decision, schema, provider, or operations documents; identify material drift; rank each difference as "Substantial diversion", "Moderate drift", or "Minor changes"; and produce an evidence-backed developer handoff report.
---

# Architecture Review

## Purpose

Perform a read-only review of actual code against planned architecture and design documents. Focus on architectural decisions, boundaries, lifecycle rules, data model intent, provider behavior, reliability patterns, observability, security, and failure models.

Do not score implementation against roadmap progress, milestone checklists, or future feature plans unless the user explicitly asks. Roadmaps can help orient scope, but they are not the standard for this review.

## Core Workflow

1. Establish repository state:
   - Run `git status --short --branch`.
   - Run `git log --oneline --decorate -n 10`.
   - Find the latest handoff note for the current branch, usually under `.codex/handoffs/<branch>/`.
   - Do not change code. Only create or edit a report file when the user asks for an artifact.

2. Read orientation sources:
   - Start with `README.md`.
   - Follow README's document order to locate critical docs.
   - Always read `docs/APPROACH.md` and `docs/ARCHITECTURE.md` or similar first when present.
   - Also read architecture-adjacent docs when present: `docs/SCHEMA.md`, `docs/DECISIONS.md`, `docs/PROVIDER_NOTES.md`, `docs/OPERATIONS.md`, provider-specific deep dives, security docs, ADRs, and design specs.
   - Use roadmap/checklist/plan files only to understand current stage or document map. Do not list roadmap gaps as architecture drift.

3. Extract architecture commitments:
   - clone/source-of-truth model;
   - component boundaries and connector contracts;
   - ingestion and sync lifecycle;
   - reconciliation and projection rules;
   - deletion, identity, loop-prevention, and conflict policies;
   - outbox, retry, idempotency, and failure recovery;
   - locks and concurrency model;
   - schema/table/enum intent;
   - observability, audit, security, credential, and retention requirements.

4. Map implementation evidence:
   - Use `rg --files` to inventory code, DB migrations, tests, scripts, config, and docs.
   - Use `rg -n` for precise line anchors.
   - Inspect concrete implementation, not only types.
   - Use tests as behavioral evidence only when they prove the claimed behavior.
   - Treat fixture-only or mock-only behavior as limited evidence; call that out where relevant.

5. Judge drift only when there is evidence:
   - "Substantial diversion": code lacks or contradicts an architecture safety property, lifecycle rule, data model invariant, or failure model in a way that can materially change system behavior.
   - "Moderate drift": code partially supports the architecture but omits orchestration, coverage, observability, or an important edge needed for the intended design.
   - "Minor changes": implementation differs from the docs but is compatible, low-risk, or mostly a documentation alignment issue.

6. Produce a developer-ready report:
   - Include a summary table with columns: `Rank`, `Drift`, `Docs asked`, `Code shows`.
   - Then create one detailed issue per drift case.
   - For each issue, include architecture references, implementation evidence, why it matters, what needs to be done, and a completion checklist.
   - Keep every claim tied to exact `path:line` references.
   - If creating a file, place it in the repo root unless the user names a path. Use a clear name such as `ARCHITECTURE_DRIFT_REVIEW.md`.

## Evidence Rules

- Prefer local files over memory.
- Use exact file and line references for both docs and implementation.
- Explain both sides: what the docs asked for and what the code actually does.
- Do not call missing future roadmap work "drift" unless the architecture docs say it is part of the current design.
- Do not count schema placeholders as implemented behavior unless there is live code or tests proving the behavior.
- Do not infer live-provider safety from mocked connectors unless the architecture only requires mocked behavior.
- Avoid broad phrasing like "coverage is weak"; name the missing architectural behavior.

## Report Structure

Use `references/report-template.md` when a report artifact is requested or when the user asks for a developer handoff document.

Use `references/example-calsync-excerpt.md` as a concrete style reference when you need to see the expected specificity, ranking language, and issue depth. Do not copy its repo-specific findings into another project; copy the structure and evidence standard.

The report must start with repository context, then the summary table, then detailed issues. Each issue should be actionable enough that a development team can turn it into tasks without re-running the whole investigation.

## Useful Commands

```powershell
git status --short --branch
git log --oneline --decorate -n 10
rg --files
rg --files -g "*handoff*" -g "*HANDOFF*" -g "*Handoff*" .codex docs
rg -n "^" README.md docs/APPROACH.md docs/ARCHITECTURE.md
rg -n "Decision|Architecture|Outbox|cursor|lifecycle|identity|deletion|lock|credential|retention|observability" docs README.md
rg -n "<architecture term>" src tests db docs
```

## Output Discipline

If the user says the review is read-only, do not edit source files, config, migrations, or tests. Creating the requested report file is allowed only after the user asks for that artifact.

When handing back the result, mention any pre-existing dirty worktree changes that were not part of the review.
