# Paper Validation Project Review Rubric

Date: 2026-07-11

Use this rubric at milestone reviews and final retrospectives. It grades the validation project, not the paper itself.

## Scoring

Score each category from 0 to 4.

| Score | Meaning |
| ---: | --- |
| 0 | Not attempted or actively misleading. |
| 1 | Attempted but incomplete, unclear, or weakly evidenced. |
| 2 | Adequate for a narrow internal review. |
| 3 | Strong and reviewable, with clear limitations. |
| 4 | Excellent, auditable, and reusable. |

## Categories

### 1. Scope Discipline

| Score | Criteria |
| ---: | --- |
| 0 | Claims reproduction without defining artefacts or boundaries. |
| 1 | Scope exists but validation, replication, and reproduction are blurred. |
| 2 | Scope is mostly clear, with some ambiguous language. |
| 3 | Scope cleanly separates validation, proxy replication, functional replication, and reproduction. |
| 4 | Scope is precise, maintained across all reports, and updated when new evidence appears. |

### 2. Artefact Audit Quality

| Score | Criteria |
| ---: | --- |
| 0 | Missing artefacts are ignored. |
| 1 | Some missing artefacts are mentioned but not tied to claims. |
| 2 | Major artefacts are inventoried. |
| 3 | Artefacts are classified by availability and reproduction impact. |
| 4 | Artefact inventory is complete, claim-linked, and includes a clear author request. |

### 3. Claim-Ledger Coverage

| Score | Criteria |
| ---: | --- |
| 0 | No claim ledger or equivalent. |
| 1 | Only headline claims extracted. |
| 2 | Most quantitative claims extracted. |
| 3 | Quantitative, benchmark, dataset, and operational claims extracted with statuses. |
| 4 | Claim ledger is comprehensive, statused, and traceable to final conclusions. |

### 4. Static Validation Strength

| Score | Criteria |
| ---: | --- |
| 0 | No static checks. |
| 1 | Manual spot checks only. |
| 2 | Key arithmetic checks implemented. |
| 3 | Arithmetic/statistical checks are tested and reported. |
| 4 | Static validation is automated, tested, documented, and covers all recomputable claims. |

### 5. Data Reconstruction Integrity

| Score | Criteria |
| ---: | --- |
| 0 | Uses data without provenance. |
| 1 | Data source named but coverage not checked. |
| 2 | Coverage checked for core inputs. |
| 3 | Coverage, gaps, duplicates, failures, and fallback limits are reported. |
| 4 | Data reconstruction is fully auditable and preserves negative findings. |

### 6. Implementation Fidelity

| Score | Criteria |
| ---: | --- |
| 0 | Implementation is unrelated to paper method. |
| 1 | Implements a rough demo with undocumented assumptions. |
| 2 | Implements main components with some fidelity notes. |
| 3 | Component mapping is explicit and assumptions are documented. |
| 4 | Implementation is modular, tested, traceable to paper components, and honest about missing details. |

### 7. Metric and Accounting Correctness

| Score | Criteria |
| ---: | --- |
| 0 | Metrics are wrong or unverifiable. |
| 1 | Metrics are reported without denominator clarity. |
| 2 | Major metrics have formulas. |
| 3 | Metrics are tested, denominator-safe, and comparable to paper claims. |
| 4 | Metric accounting is audited across stages, edge cases, and reports. |

### 8. LLM or Stochastic Provenance

Score this category only when applicable.

| Score | Criteria |
| ---: | --- |
| 0 | Stochastic/LLM outputs are treated as deterministic or unexplained. |
| 1 | Model/provider named but prompts, parameters, and failures are unclear. |
| 2 | Basic configuration and outputs are logged. |
| 3 | Prompt/model/configuration/fallback provenance is reported. |
| 4 | Valid decisions, repairs, fallbacks, provider errors, and hard gates are separated in logs and metrics. |

### 9. Evidence Packaging

| Score | Criteria |
| ---: | --- |
| 0 | Results cannot be audited. |
| 1 | Large local artefacts are referenced but no compact evidence exists. |
| 2 | Reports include commands and selected outputs. |
| 3 | Compact evidence bundles include summaries, checksums, and limitations. |
| 4 | Evidence is complete, small, non-secret, reproducible, and linked from reports. |

### 10. Reporting Honesty

| Score | Criteria |
| ---: | --- |
| 0 | Overclaims reproduction or hides failures. |
| 1 | Limitations exist but are buried. |
| 2 | Main limitations are stated. |
| 3 | Reports clearly separate supported, unsupported, proxy, and contradicted findings. |
| 4 | Reports make the reproducibility boundary unmistakable and preserve negative findings. |

## Grade Mapping

Use the average score across applicable categories.

| Average | Grade | Interpretation |
| ---: | --- | --- |
| 3.7 to 4.0 | A | Excellent, auditable validation project. |
| 3.3 to 3.69 | A- | Strong project with minor residual limits or external blockers. |
| 2.8 to 3.29 | B+ | Useful and mostly honest, but with notable gaps. |
| 2.3 to 2.79 | B | Adequate internal validation with meaningful weaknesses. |
| 1.7 to 2.29 | C | Partial effort; conclusions require caution. |
| 0 to 1.69 | D/F | Not reliable for reproduction or validation claims. |

## Final Assessment Template

```text
Average score: <score>
Grade: <grade>

The project is strongest in <categories>. It is weakest in <categories>. The final conclusion is <supported / partially supported / unsupported / contradicted / not reproducible from available artefacts> because <reason>.
```
