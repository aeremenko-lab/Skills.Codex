# Architecture Drift Report Template

Use this template for a developer handoff artifact produced by the `architecture-review` skill.

```markdown
# Architecture Drift Review

Review date: <YYYY-MM-DD>

Branch observed: `<branch>`

Observed commit: `<hash> <message>`

Latest handoff note observed: `<path>`

Scope: this review compares existing code only against architectural decisions and design documents. It does not evaluate roadmap or milestone completion.

Primary docs reviewed:

- `README.md`
- `docs/APPROACH.md`
- `docs/ARCHITECTURE.md`
- <other architecture-adjacent docs>

## Summary Table

| Rank | Drift | Docs asked | Code shows |
|---|---|---|---|
| Substantial diversion | <short drift title> | <doc requirement with `path:line` references> | <implementation evidence with `path:line` references> |
| Moderate drift | <short drift title> | <doc requirement with `path:line` references> | <implementation evidence with `path:line` references> |
| Minor changes | <short drift title> | <doc requirement with `path:line` references> | <implementation evidence with `path:line` references> |

## Issue 1. <Issue Title>

Rank: <Substantial diversion / Moderate drift / Minor changes>

### Architecture references

- `<path>:<line>` <what this doc requires>
- `<path>:<line>` <related architecture decision>

### Implementation evidence

- `<path>:<line>` <what the code actually does>
- `<path>:<line>` <additional evidence or lack of implementation>

### Why this matters

<Explain behavioral, operational, data-integrity, safety, or support impact in plain language.>

### What needs to be done

<Describe the implementation direction without over-prescribing internals unless the architecture docs require them.>

### Completion checklist

- [ ] <developer action>
- [ ] <developer action>
- [ ] <test or verification action>

## Overall Assessment

<Short synthesis of what aligns with the architecture and where the most important drift is concentrated.>
```

## Ranking Guide

Use `Substantial diversion` when the implementation can violate a core architectural safety property, such as source-of-truth boundaries, deletion safety, durable outbox guarantees, cursor commit rules, identity rules, or failure recovery.

Use `Moderate drift` when the architecture is partially present but missing orchestration, edge handling, auditability, or operational behavior needed to make the design work reliably.

Use `Minor changes` when implementation differs from the docs but remains compatible and low risk, or when the main fix is documenting an accepted implementation detail.

## Style Notes

- Keep the summary table concise.
- Make detailed issues self-contained.
- Avoid roadmap language such as "Milestone missing" unless the user requested a roadmap review.
- Use exact `path:line` references.
- State "Docs asked" and "Code shows" explicitly for every drift case.
