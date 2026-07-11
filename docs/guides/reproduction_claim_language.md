# Reproduction Claim Language Guide

Date: 2026-07-11

Use this guide to keep reports precise. The wrong verb can turn a careful validation into an overclaim.

## Recommended Terms

| Term | Use When |
| --- | --- |
| `internally consistent` | The paper's reported values agree with each other when recomputed from the text. |
| `statically validated` | A claim is checked from paper text, tables, equations, or released static artefacts. |
| `supported by released artefacts` | The required artefacts are available and independently checked. |
| `public-data reconstruction` | Inputs were rebuilt from public sources, not recovered from the original run. |
| `public-data proxy` | Public data is comparable but not the same as the paper's original data. |
| `functional replication` | The described architecture or method was implemented and exercised. |
| `behavioural comparison` | A different model, data source, provider, or runtime was used to compare behaviour. |
| `direct rerun` | Original released code and data were run with minimal changes. |
| `empirical reproduction` | Original or equivalent artefacts and runtime context were used to recover the reported result. |
| `unsupported without artefacts` | Required data, logs, code, prompts, or configuration are missing. |
| `not independently reproducible` | Available materials are insufficient for a third party to reproduce the original empirical result. |
| `contradicted` | Available evidence conflicts with the paper claim or another paper statement. |

## Terms to Avoid Unless Strictly True

| Avoid | Prefer |
| --- | --- |
| `we reproduced the paper` | `we functionally replicated the described method` or `we validated paper-level claims` |
| `confirmed the result` | `the reported arithmetic is internally consistent` |
| `same experiment` | `public-data proxy experiment` or `behavioural comparison` |
| `validated the live system` | `implemented a comparable functional pipeline` |
| `proved the claim` | `supported this claim under the available artefacts` |
| `failed to reproduce, so the paper is false` | `the claim is not independently reproducible from available artefacts` |

## Claim Strength Ladder

Use the lowest accurate claim strength.

1. `The claim is not testable from available materials.`
2. `The claim is unsupported without additional artefacts.`
3. `The paper's arithmetic for this claim is internally consistent.`
4. `The claim is supported by released artefacts.`
5. `The described method was functionally replicated on synthetic or proxy data.`
6. `The released code and data were directly rerun.`
7. `The original empirical result was reproduced with original or equivalent artefacts.`

## Standard Caveat Sentences

Use or adapt these sentences in reports.

```text
This validates paper-level arithmetic, not the original empirical run.
```

```text
This is a functional replication of the described architecture on public/proxy data; it is not evidence that the original live run followed the same decision path.
```

```text
The result is unsupported without the original dataset, runtime logs, configuration, and evaluation artefacts.
```

```text
The fallback dataset is useful for sensitivity analysis but is not equivalent to the paper's original data source.
```

```text
The LLM-backed run is a behavioural comparison because the original prompts, completions, model-serving configuration, and retry/fallback logs are unavailable.
```

```text
This negative finding narrows the reproducibility boundary; it is not evidence of misconduct.
```

## Final Conclusion Pattern

```text
The available evidence supports <narrow supported conclusion>. It does not support <overbroad conclusion> because <missing artefacts or contradiction>. The appropriate classification is <static validation / public-data proxy / functional replication / direct rerun / empirical reproduction / unsupported>.
```
