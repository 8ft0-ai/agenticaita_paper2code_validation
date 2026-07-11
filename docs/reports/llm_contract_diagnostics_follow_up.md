# LLM Contract and Diagnostics Follow-Up

Date: 2026-07-11

## Status

The LLM-backed replication path now distinguishes valid model behaviour from response-contract repair, deterministic fallback, hard-gate rejection, and Analyst abstention.

The original OpenRouter run is not reinterpreted as a clean measure of model conservatism. Its 17 Analyst fallbacks were integration-quality events, and the original pipeline did not preserve enough per-invocation provenance to reconstruct every category after the fact. A fresh live run is required for the new diagnostics.

## Contract Changes

### Analyst wait

A `wait` response now requires only:

```json
{
  "signal": "wait",
  "confidence": 0.0,
  "reasoning": "..."
}
```

Action fields may be absent or null because no order is proposed. The harness normalises entry, stop, and take-profit to the trigger price and size to zero for its internal typed contract. The Risk Manager is not evaluated.

### Analyst long or short

A directional response requires non-null, numeric confidence, entry price, stop loss, take profit, positive size, and reasoning. Directional levels are validated before the deterministic hard gates:

```text
long:  stop_loss < entry_price < take_profit
short: take_profit < entry_price < stop_loss
```

Missing, null, non-numeric, out-of-range, zero-size, and directionally invalid values are explicit contract errors.

### Risk Manager

An approval requires a positive size and non-empty negotiation summary. A rejection requires only `approved: false` and a non-empty summary.

## Bounded Repair and Fallback

A schema-validity failure triggers exactly one repair request. The repair request contains the validation error, invalid JSON response, and original structured context. It cannot loop.

Each decision is classified as one of:

- `llm_valid`;
- `llm_repaired`;
- `deterministic_fallback`;
- `deterministic_hard_gate` for Risk Manager stage-A rejection;
- `not_evaluated` after an Analyst wait;
- `deterministic` for the non-LLM control path.

Network/provider errors fall back directly rather than being misclassified as schema-repair attempts.

## Pipeline and Summary Diagnostics

New pipeline columns record:

- Analyst and Risk Manager provenance;
- original contract error text;
- whether a repair was attempted;
- risk-stage evaluation status;
- existing fallback warnings and rejection reasons.

Summary JSON now includes:

- Analyst provenance counts;
- Analyst signal mix by provenance;
- Analyst and Risk Manager contract-error histograms;
- repair-attempt counts;
- Risk Manager provenance and rejection-reason counts;
- approvals by Analyst and Risk Manager provenance.

These aggregates permit a report to distinguish genuine abstention from malformed outputs and deterministic safety controls.

## Context Supplied to the Model

The Analyst currently receives:

- the AZTE trigger event;
- CBD components and composite score;
- a derived volatility regime;
- current asset, timestamp, price, signed return, and absolute return;
- up to five episodic-memory reasoning entries;
- explicit statements that historical L2 order-book snapshots and funding context are unavailable.

This remains materially thinner than the paper-described context. The paper's exact prompt, full recent-bar context, historical L2 snapshot, model-serving configuration, and original agent messages are unavailable. The additional diagnostics improve integration validity but do not make this the paper's exact Qwen/Ollama experiment.

## Fresh Live Run

A fresh live run is intentionally not performed in repository CI because it requires both the gitignored 76-symbol market input and an `OPENROUTER_API_KEY`. From a workstation retaining those inputs:

```bash
python replication/replicate.py \
  --config replication/config.yaml \
  --input-csv data/binanceusdm_ohlcv_large_76/replication_input_ohlcv.csv \
  --out replication/results_real_binanceusdm_large_76_llm_contract_v2 \
  --agents llm \
  --model qwen/qwen-2.5-7b-instruct \
  --audit-log replication/results_real_binanceusdm_large_76_llm_contract_v2/llm_audit.jsonl
```

The resulting `summary.json` and `pipeline_log.csv` will contain the new provenance and reason histograms. Credentials, raw audit records, market data, and full run outputs remain outside git.

## Interpretation Rule

Future reports should use terms such as *more conservative* only after separating:

1. valid model `wait` decisions;
2. valid model directional decisions rejected by deterministic gates;
3. valid LLM Risk Manager rejections;
4. repaired responses;
5. deterministic fallbacks caused by unrepaired contract failures;
6. provider/network failures.

Without that separation, trade-count reduction is an integration outcome, not a reliable behavioural claim about the model.
