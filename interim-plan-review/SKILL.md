---
name: interim-plan-review
description: Rigorous interim implementation review for a software repo. Use when Codex is asked to assess where a project stands, compare real code/tests/schema against roadmap, milestones, implementation plans, architecture docs, handoff notes, or checklists, identify implementation gaps versus the planned architecture, and produce a developer-ready Markdown checklist before the next phase of work.
---

# Interim Plan Review

## Purpose

Produce a read-only, evidence-backed audit of a codebase against its own plan and architecture docs. The output should help developers see exactly what is implemented, what is missing, what is out of scope, and what must be fixed before moving to the next planned phase.

## Core Workflow

1. Start read-only unless the user asks you to create the final report file.
2. Find project orientation sources:
   - `git status --short --branch`
   - recent commits with `git log --oneline --decorate -n 10`
   - latest handoff notes, usually under `.codex/handoffs/<branch>/`
   - `README.md`
   - roadmap, execution plan, architecture, schema, operations, decisions, provider notes, and checklists under `docs/`
3. Establish the review scope before judging gaps:
   - Use the milestone/version range named by the user.
   - If the user asks for specific Milestones from the implementation plan (e.g. Milestones 1-4), do not list what's beyond that (eg Milestone 5, V2 architecture, etc.) as gaps. Instead, mark them "out of scope" and only flag missing items that are explicitly required by the current milestone range.
   - If docs mention future architecture, mark it "out of scope" unless it is explicitly required by the current milestone range.
4. Extract source-of-truth requirements:
   - milestone outcomes and tasks
   - exit criteria
   - architecture decisions
   - schema/table/enum requirements
   - provider behavior requirements
   - test expectations
5. Map implementation evidence:
   - repo structure with `rg --files`
   - package scripts and config
   - DB migrations and seeds
   - src modules and public interfaces
   - tests and fixtures
   - any generated artifacts or prior prototype references only when docs say they matter
6. Verify when practical:
   - run typecheck and default tests if they are local and safe
   - run DB tests only when a safe test database is configured
   - record exact commands and pass/fail results
7. Separate findings into:
   - implemented
   - missing or incomplete in current scope
   - intentionally deferred or out of scope
   - unclear scope needing developer confirmation

## Evidence Rules

- Use specific file and line references for every meaningful claim.
- Prefer `rg -n` to collect line anchors.
- Reference local files as `path:line` inside generated Markdown checklists.
- Do not rely on memory when a repo document or code file can be read.
- Do not count a type/interface as full implementation if no concrete implementation or test proves behavior.
- Do not count fixture-only coverage as live-provider coverage.
- Do not treat future roadmap items as current gaps unless the requested review scope includes them.

## Output File

When asked to create an artifact, write a Markdown file in the repo root unless the user names a path. Use a clear filename such as:

- `INTERIM_REVIEW_CHECKLIST.md`
- `PRE_SMOKE_TEST_REVIEW_CHECKLIST.md`
- `MILESTONES_1_4_REVIEW_CHECKLIST.md`

Use the project/user language preferences from repo instructions.

## Report Format

Use this structure for the Markdown output:

```markdown
# <Scope> Review Checklist

Review date: <date>
Branch observed: `<branch>`
Observed latest local commits:

- `<hash> <message>`

Verification run during review:

- `<command>`: <passed/failed/skipped and reason>

Scope of this checklist:

- <milestone/version/task in scope>

Out of scope here:

- <explicitly deferred/future items>

## Milestone Coverage Summary

### <Milestone/Area Name>

Status: <covered / mostly covered / partial / not covered>, with <short caveat>.

Implemented:

- <implemented item>: `path:line`

Missing or incomplete:

- <gap in current scope>: `path:line` where relevant

## Detailed Issue Checklist

### 1. <Issue Title>

Milestone: <number/name or area>
Severity: <Critical/High/Medium/Low>

References:

- <requirement reference>: `docs/...:line`
- <implementation evidence>: `src/...:line`

What is missing:

- <specific missing behavior/test/code>

Checklist:

- [ ] <developer action>
- [ ] <developer action>

## Recommended Developer Order For <Scope>

1. <highest-value next action>
2. <next action>

## <Scope> Completion Gate

- [ ] <objective completion condition>
```

## Issue-Writing Standards

Write every issue separately. Each issue should explain:

- which milestone or area it belongs to
- why it matters in the current scope
- what the docs expected
- what the code actually contains
- what is missing
- how a developer can close it

Keep issues concrete. Prefer "No reconciliation DB test proves an eligible Yandex one-off event creates a Google outbox operation" over "Yandex coverage is weak."

When referencing docs, use exact file and line anchors. When referencing code, do the same. This allows developers to quickly verify and understand the issue without ambiguity.

## Scope Discipline Examples

- If Milestone 4 says "Outbox execution with mocked providers first", do not flag missing live API clients as a Milestone 4 gap. Flag only missing mocked outbox paths or adapter-through-outbox coverage.
- If Milestone 5 says "Live-provider smoke tests", do not include live smoke harness requirements in a Milestones 1-4 checklist.
- If architecture docs describe V1.0/V2 capabilities, list them as out of scope unless current milestone docs make them mandatory.
- If a future item is risky but out of scope, mention it briefly in "Out of scope here" rather than in the detailed issue checklist.

## Useful Commands

Use these as starting points and adapt to the repo:

```powershell
git status --short --branch
git log --oneline --decorate -n 10
rg --files
rg --files -g "*handoff*" -g "*HANDOFF*" -g "*Handoff*"
rg -n "Milestone|Exit criteria|Must have|Tasks|Decision|Outbox|cursor|connector" docs README.md
rg -n "<term>" src tests db docs
npm run typecheck
npm test
```
