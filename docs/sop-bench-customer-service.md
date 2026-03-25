# SOP-Bench Customer Service: 81.4% TSR (SOTA)

## Summary

Proceda achieves **81.4% TSR** (127/156) on customer_service, beating the 79% baseline
(Llama 3.3 70B ReAct) with Gemini 2.5 Flash. This was achieved after adding the
`output_fields` feature to Proceda — the initial run scored only 30.1%.

| Agent | Model | TSR |
|-------|-------|-----|
| **Proceda (with output_fields)** | **Gemini 2.5 Flash** | **81.4% (127/156)** |
| ReAct (best baseline, Table 5) | Llama 3.3 70B | 79% |
| FC (2nd best, Table 5) | Claude 4.5 Sonnet | 71% |
| Proceda (before output_fields) | Gemini 2.5 Flash | 30.1% (47/156) |

## The output_fields Feature

The initial 30.1% TSR was caused by extraction failures, not reasoning failures. Deep trace
analysis revealed:

- **44 tasks (28%)**: LLM computed correct answer but output in prose → extractor found nothing
- **26 tasks (17%)**: Prose extractor matched "account status is ACTIVE" instead of resolution
- **16 tasks (10%)**: Genuine RESOLVED→ESCALATED reasoning errors
- **23 tasks (15%)**: Other extraction noise

The fix: add `output_fields` to Proceda's SKILL.md format. When declared:

```yaml
---
name: customer-service
output_fields:
  - final_resolution_status
---
```

The system prompt tells the LLM: "When completing the FINAL step, include each output field
using XML tags: `<final_resolution_status>value</final_resolution_status>`"

The final step prompt reinforces this: "IMPORTANT: This is the final step. Your complete_step
summary MUST include these output fields as XML tags."

This eliminated ALL extraction failures. The 29 remaining failures are genuine LLM reasoning
errors where the XML tags are present but contain the wrong value.

## Remaining Failures (29/156)

| Predicted | Expected | Count | Pattern |
|-----------|----------|-------|---------|
| FAILED | RESOLVED | 12 | LLM too pessimistic about auth/account issues |
| PENDING_ACTION | FAILED | 7 | LLM treats early termination as pending rather than failed |
| PENDING_ACTION | RESOLVED | 4 | Outage detection overrides successful troubleshooting |
| ESCALATED | RESOLVED | 3 | LLM escalates when troubleshooting actually worked |
| ESCALATED | PENDING_ACTION | 2 | Escalates when should wait |
| ESCALATED | FAILED | 1 | Edge case |

All 29 are LLM reasoning errors — the output_fields XML tags are present and parseable in
every case. These would require a stronger model or more explicit decision criteria in the SOP.

## Domain Characteristics

- 10 tools, 10 steps (reduced from 11 in second conversion)
- 4 possible outcomes: RESOLVED, PENDING_ACTION, ESCALATED, FAILED
- Heavy branching: invalid account → FAILED, terminated → FAILED, outage → PENDING_ACTION,
  troubleshooting works → RESOLVED, troubleshooting fails → ESCALATED
- Most complex tool chaining of any domain run so far
- NaN values in diagnostic timestamps (handled by MCP bridge sanitization)

## Iteration History

| Run | TSR | Key Change |
|-----|-----|------------|
| Initial (5 tasks) | 0% | Extraction failures — no prose pattern matched |
| With prose extractor | 20% | Prose extractor too greedy (ACTIVE false positives) |
| Full run (156 tasks) | 30.1% | ~70% of failures are extraction, not reasoning |
| **Deep failure analysis** | — | Identified 3 failure categories, proposed output_fields |
| **With output_fields** (5 tasks) | **100%** | XML tags eliminate all extraction failures |
| **Full run with output_fields** | **81.4%** | **SOTA** — remaining 29 are reasoning errors |

## Proceda Changes Made

- `output_fields: list[str] | None` added to `Skill` dataclass and parser
- System prompt includes output field instructions when `output_fields` is declared
- Final step prompt reinforces XML tag requirement
- System prompt adds "don't skip tool calls" rule
- `proceda convert` gains `--output-fields` CLI flag
- Converter instructs final step to emit XML tags when output_fields provided
