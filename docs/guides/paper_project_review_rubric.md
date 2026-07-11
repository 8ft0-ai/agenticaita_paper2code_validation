# Paper Validation Project Review Rubric

Date: 2026-07-11

Grade the validation project, not the paper. Score each applicable category from 0 to 4.

| Score | Meaning |
| ---: | --- |
| 0 | Not attempted or actively misleading. |
| 1 | Attempted but incomplete, unclear, or weakly evidenced. |
| 2 | Adequate for a narrow internal review. |
| 3 | Strong and reviewable, with clear limitations. |
| 4 | Excellent, auditable, reusable, and independently reviewable. |

## Categories

### 1. Scope and gate discipline

0 claims reproduction without boundaries; 2 has a mostly clear scope; 3 records project classification and gate decisions; 4 maintains scope, priorities, stopping rules, and version changes throughout.

### 2. Claim prioritisation and extraction quality

0 has no claim ledger; 2 extracts major quantitative claims; 3 adds importance, priority, locations, and extraction confidence; 4 traces every material conclusion to manually verified extraction and evidence.

### 3. Artefact audit quality

0 ignores missing artefacts; 2 inventories major artefacts; 3 links availability to claim consequences; 4 provides a complete claim-linked inventory and focused author request.

### 4. Data governance and legal fitness

0 uses data without rights or provenance review; 2 records source and licence; 3 covers redistribution, retention, terms, and sensitive-data implications; 4 records owners, expiry, external storage, and enforceable decisions.

### 5. Static and statistical validation

0 has no checks; 2 implements key arithmetic; 3 tests formulas and assumptions; 4 automates all recomputable critical claims and records exact evidence.

### 6. Data reconstruction integrity

0 uses unprovenanced substitutes; 2 checks core coverage; 3 reports gaps, duplicates, failures, and proxy limits; 4 is fully auditable and preserves negative findings and stop decisions.

### 7. Implementation fidelity and value

0 is unrelated to the paper; 2 implements main components with assumptions; 3 maps components to claims and fidelity; 4 is the smallest tested implementation needed to exercise the material claim boundary.

### 8. Metric and stage-accounting correctness

0 reports wrong or unverifiable metrics; 2 documents formulas; 3 is denominator-safe and tested; 4 audits stages, edge cases, benchmark construction, and report consistency.

### 9. LLM or stochastic provenance

Score only when applicable. 0 treats stochastic output as deterministic; 2 logs basic model/configuration; 3 separates valid output, repair, fallback, provider error, and hard gates; 4 also records context, versioning limits, uncertainty, and metrics by provenance.

### 10. Environment, budget, and run reproducibility

0 omits environment and cost; 2 records command and runtime; 3 captures commit, dependencies, seeds, provider versions, and budget; 4 includes deterministic digests, container/hardware details, timezone, and approval/stop thresholds.

### 11. Evidence packaging and reporting honesty

0 cannot be audited or overclaims; 2 includes commands and limitations; 3 has compact evidence, checksums, claim links, and clear proxy boundaries; 4 makes the evidence boundary unmistakable and detects report drift.

### 12. Independent conclusion review

0 has no review; 2 has an informal second pass; 3 records a clean-context review against a fixed commit; 4 resolves discrepancies and independently verifies extraction, calculations, statuses, evidence, and final language.

## Grade mapping

Use the average across applicable categories.

| Average | Grade | Interpretation |
| ---: | --- | --- |
| 3.7–4.0 | A | Excellent, auditable validation project. |
| 3.3–3.69 | A- | Strong project with minor residual limitations or external blockers. |
| 2.8–3.29 | B+ | Useful and mostly honest, with notable gaps. |
| 2.3–2.79 | B | Adequate internal validation with meaningful weaknesses. |
| 1.7–2.29 | C | Partial effort; conclusions require caution. |
| 0–1.69 | D/F | Not reliable for validation or reproduction claims. |

## Final assessment

```text
Average score: <score>
Grade: <grade>
Gate status: <A-F summary>

The project is strongest in <categories> and weakest in <categories>. The evidence supports <narrow conclusion>. It does not support <broader conclusion> because <missing artefacts, material substitutions, contradiction, or review failure>.
```
