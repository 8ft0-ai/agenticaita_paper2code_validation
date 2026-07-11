# Reproduction Claim Language Guide

Date: 2026-07-11

Use the lowest claim strength supported by the evidence. Academic communities use “replication” and “reproduction” inconsistently, so every project should publish these local definitions.

## Project classifications

| Term | Use when |
| --- | --- |
| `static validation` | A claim is checked from the paper text, equations, tables, appendices, or released static artefacts. |
| `direct reproduction` | The original released code, data, evaluation path, and materially equivalent runtime context are rerun. |
| `independent replication` | The method is independently implemented using equivalent inputs and evaluation, with differences disclosed. |
| `proxy replication` | Data, model, provider, benchmark, or runtime is materially substituted. |
| `functional replication` | The described architecture or mechanism is implemented and exercised without empirical-equivalence claims. |
| `synthetic replication` | Mechanics are tested under controlled artificial inputs. |
| `diagnostic validation` | One bounded component, formula, claim, or failure mode is tested. |
| `behavioural comparison` | A different model/provider/context is used to compare behaviour rather than reproduce it. |

“Equivalent” artefacts do not automatically justify a direct-reproduction claim. Material equivalence must be established for the inputs, preprocessing, model/runtime, and evaluation path; otherwise use independent or proxy replication.

## Claim statuses

| Status | Meaning |
| --- | --- |
| `supported` | Independently recomputed or observed from available evidence. |
| `partially_supported` | A narrower claim is supported but the full claim needs missing context. |
| `unsupported` | Required artefacts or definitions are absent. |
| `contradicted` | Available evidence conflicts with the claim or another paper statement. |
| `not_testable` | The assertion cannot be operationalised from the available description. |
| `unresolved` | A material ambiguity remains, often pending author clarification. |

## Terms to avoid unless strictly true

| Avoid | Prefer |
| --- | --- |
| `we reproduced the paper` | `we directly reproduced the released experiment` or `we functionally replicated the method` |
| `confirmed the result` | `the reported arithmetic is internally consistent` or `the claim is supported by released artefacts` |
| `same experiment` | `independent replication` or `proxy experiment` |
| `validated the live system` | `implemented a comparable functional pipeline` |
| `proved the claim` | `supported the claim under the available evidence` |
| `failed to reproduce, so the paper is false` | `the result is not independently reproducible from available materials` |

## Claim-strength ladder

1. The claim is not testable from available materials.
2. The claim is unsupported without additional artefacts.
3. The paper’s arithmetic is internally consistent.
4. The claim is supported by released artefacts.
5. A bounded component was diagnostically validated.
6. The method was functionally or synthetically replicated.
7. An independent or proxy replication produced a stated result under disclosed differences.
8. The original released experiment was directly reproduced.

## Standard caveats

```text
This validates paper-level arithmetic, not the original empirical run.
```

```text
This is a functional replication on public or proxy data; it is not evidence that the original run followed the same decision path.
```

```text
This model run is a behavioural comparison because the original prompts, model-serving version, context, completions, and retry/fallback logs are unavailable.
```

```text
This negative finding narrows the reproducibility boundary; it is not evidence of misconduct.
```

## Final conclusion pattern

```text
The available evidence supports <narrow conclusion>. The project classification is <classification>. It does not support <broader conclusion> because <missing artefacts, material substitutions, or contradiction>. The remaining uncertainty is <unresolved dependency>.
```
