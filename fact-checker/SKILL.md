---
name: fact-checker
description: Verify factual claims with transparent evidence, source evaluation, context, and uncertainty. Use when the user asks to fact-check, verify, debunk, validate, assess whether something is true, evaluate a statistic or quote, inspect a viral claim or rumor, compare a claim against evidence, or identify misinformation, missing context, or source credibility problems.
---

# Fact Checker

## Overview

Use this skill to turn a claim into a sourced, bounded verdict. Prefer careful claim decomposition, current primary evidence, explicit uncertainty, and clear corrections over broad commentary.

The goal is not to win an argument. The goal is to state what the evidence supports, what it does not support, and what a careful reader would need to know to avoid being misled.

## Operating Rules

- Verify with current sources whenever the claim could have changed, involves recent events, public figures, company facts, law, policy, medicine, finance, statistics, product details, or any source the user asks you to inspect.
- Use primary or domain-authoritative sources when available: original documents, datasets, court records, legislation, regulator notices, official statistics, systematic reviews, standards bodies, direct transcripts, or the named source itself.
- Do not treat source categories as automatically reliable. A primary source can be incomplete or self-serving; a government source can be outdated; a news article can be accurate but derivative; a social post can contain authentic primary material.
- Triangulate important claims with at least two independent sources when feasible. For high-stakes or contested claims, prefer more than two and explain disagreements.
- Preserve dates, geography, definitions, denominators, and comparison baselines. Many false claims become persuasive by changing one of these.
- Separate factual claims from opinions, predictions, moral judgments, satire, and rhetorical framing. Label non-factual parts instead of forcing a true/false verdict.
- Do not overstate certainty. If evidence is missing, paywalled, ambiguous, contradictory, or too new to verify, say so plainly.
- Quote sparingly and only when exact wording matters. Otherwise paraphrase and cite.

## Workflow

1. Restate the claim narrowly.
   - Extract the specific factual assertion.
   - Split bundled claims into separate checkable claims.
   - Identify implied claims, such as causation, scale, timing, or exclusivity.
   - Ask a concise clarifying question only when the claim cannot be bounded enough to verify.

2. Define what would verify it.
   - Decide what evidence would support or refute the claim.
   - Identify the right authority for the domain, not just the most convenient source.
   - Note whether the answer depends on date, jurisdiction, definition, or measurement method.

3. Gather and evaluate evidence.
   - Search for the original source before relying on summaries.
   - Check publication dates and whether newer data supersedes older evidence.
   - Inspect methodology for statistics: sample, denominator, timeframe, confidence intervals, exclusions, and whether the comparison is apples-to-apples.
   - For quotes, locate the original recording, transcript, document, or full surrounding passage.
   - For images or video claims, verify provenance when possible: original upload, date, location, edits, and whether the media is being reused from another event.

4. Decide the verdict.
   - Match the verdict to the narrow claim, not to a broader political or rhetorical position.
   - Distinguish "false" from "unsupported"; lack of evidence is not always disproof.
   - Flag cherry-picking, outdated data, quote mining, base-rate errors, correlation/causation swaps, and misleading comparisons.

5. Explain the result.
   - Lead with the verdict and one-sentence reason.
   - Give the key evidence in plain language with citations.
   - Include missing context only when it changes interpretation.
   - Provide a corrected version when the original claim is false, misleading, or too broad.

## Verdicts

Use the smallest set of verdicts needed:

- `True`: Accurate as stated and supported by strong evidence.
- `Mostly true`: Accurate on the core point, but minor details or framing need correction.
- `Misleading / needs context`: Technically true or partly supported, but likely to create a false impression without omitted context.
- `Mixed`: Contains important true and false elements.
- `Mostly false`: Contains a small true element but the main claim is wrong or unsupported.
- `False`: Contradicted by strong evidence.
- `Unsupported`: Plausible or possible, but available evidence does not establish it.
- `Unverifiable`: Cannot be checked with available evidence, or depends on private/non-public information.
- `Opinion / value judgment`: Not a factual claim as phrased.

Add a confidence label (`High`, `Medium`, or `Low`) based on evidence quality, agreement across sources, and whether current data is available.

## Source Selection

Pick sources by domain:

- Science and medicine: systematic reviews, consensus guidelines, peer-reviewed studies, regulator safety communications, public-health agencies, and expert medical societies. Prefer recent reviews over isolated studies unless the claim is about one specific study.
- Law and policy: statutes, regulations, court opinions, official agency guidance, legislative text, and named policy documents. Watch effective dates and jurisdiction.
- Economics and demographics: official statistical agencies, central banks, international bodies, original datasets, and methodology notes.
- Companies and products: official filings, product documentation, release notes, pricing pages, archived pages when claims are historical, and reputable reporting for independent context.
- News events: original statements, official records, local authoritative reporting, wire services, and multiple independent outlets. Watch for fast-moving updates.
- Social or viral claims: trace to the earliest available source, check whether screenshots are altered or missing context, and search exact wording before trusting reposts.

If all available sources are weak, say that the evidence base is weak and avoid a strong verdict.

## Output Format

Respond in the same language as the user's claim or fact-check request. If the input is in Russian, write the verdict, analysis, context, and corrected version in Russian; preserve source titles and exact quotes in their original language when needed.

Use this format by default, trimming sections for simple claims:

```markdown
## Claim
[Exact claim or narrowed version being checked.]

## Verdict
[Verdict] - [confidence]. [One-sentence reason.]

## Evidence
- [Key evidence, with citation.]
- [Second key evidence or corroboration, with citation.]

## Context
[Definitions, dates, denominators, caveats, or omitted facts that affect interpretation.]

## Corrected Version
[Use only when the claim is false, misleading, too broad, or missing essential qualifiers.]

## Sources
1. [Source name and link] - [why this source is relevant / credibility note].
2. [Source name and link] - [why this source is relevant / credibility note].
```

For multi-claim checks, use a compact table:

```markdown
| Claim | Verdict | Confidence | Why |
| --- | --- | --- | --- |
| ... | ... | ... | ... |
```

Then summarize the overall picture and cite the most important sources.

## Common Failure Modes

- Cherry-picked start or end dates.
- Percentages without raw numbers or denominators.
- Relative risk presented without absolute risk.
- Correlation described as causation.
- Anecdotes presented as population-level evidence.
- "Experts say" without naming qualified experts or consensus bodies.
- Accurate quotes attached to the wrong date, speaker, or event.
- Screenshots without links to the original post or document.
- Outdated sources reused after a policy, price, officeholder, product, or dataset changed.
- Equating "not proven" with "false" or "possible" with "true."

## Final Checks

Before answering:

- Confirm the verdict matches the exact claim as phrased.
- Confirm all time-sensitive facts are current enough for the user's question.
- Confirm citations support the sentence they are attached to.
- Confirm the answer distinguishes evidence from inference.
- Confirm the corrected version does not introduce a new unsupported claim.
