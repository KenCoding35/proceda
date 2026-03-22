# SOP-Bench Benchmark Status

Last updated: 2026-03-22

## Overview

Proceda is being evaluated against SOP-Bench, an Amazon Science benchmark with 2,411 tasks
across 14 business domains. We run `proceda convert --tools --output-fields` to convert
each domain's SOP into a SKILL.md, then execute all tasks via the evaluation harness.

**Branch:** `experiment/sop-bench`
**Model:** Gemini 2.5 Flash (`gemini/gemini-2.5-flash`), temperature=0.0
**API key:** `pass soprun/GEMINI_API_KEY`

## Results Summary

| Domain | Tasks | Proceda TSR | Best Baseline | Baseline TSR | Tag |
|--------|-------|-------------|---------------|-------------|-----|
| Patient Intake | 66 | **97.0%** | Claude 4.1 Opus ReAct | 100% | `sop-bench-patient-intake-97pct` |
| Dangerous Goods | 274 | **94.2%** | Claude 4 Sonnet FC | 87% | `sop-bench-dangerous-goods-94pct` |
| Customer Service | 156 | **81.4%** | Llama 3.3 70B ReAct | 79% | `sop-bench-customer-service-81pct` |
| Content Flagging | 168 | 31.0% | DeepSeek R1 ReAct | 60% | `sop-bench-content-flagging-31pct` |
| Know Your Business | 90 | **incomplete** | Claude 4.5 Opus ReAct | 58% | — |

**SOTA on 2 domains** (dangerous_goods, customer_service). Near-SOTA on patient_intake.
Content flagging has non-deterministic tools (benchmark bug). KYB blocked by rate limiting.

## What Was Done

### Infrastructure Built

1. **MCP Tool Bridge** (`benchmarks/sop_bench/mcp_bridge.py`) — Generic stdio MCP server
   wrapping any SOP-Bench domain's Python tool manager. Handles Bedrock→MCP toolspec
   conversion, NaN sanitization, empty value replacement, stdout suppression.

2. **Output Extractor** (`benchmarks/sop_bench/output_extractor.py`) — Extracts structured
   output from Proceda run events. Strategies (in priority order):
   - Tool results (TOOL_COMPLETED events with dict key matching)
   - Bare values from single-column tool results
   - XML tags in summaries/messages (`<field_name>value</field_name>`)
   - `<final_output>{JSON}</final_output>` blocks
   - Bare JSON objects
   - Prose patterns ("status is VALUE")

3. **Evaluation Harness** (`benchmarks/sop_bench/harness.py`) — CLI that loads SOP-Bench
   CSV data, runs Proceda against each task, scores against ground truth, saves traces.
   Features: `--workers N` for parallelism, `--resume` to skip completed tasks, retry
   on LLM API errors (2 retries with exponential backoff).

4. **HTML Report Generator** (`benchmarks/sop_bench/generate_report.py`) — Generates
   interactive HTML reports with per-task expandable traces, field comparisons, and
   tool call details. Dark theme. Filter by pass/fail.

### Proceda Features Added

1. **`output_fields`** — New SKILL.md frontmatter field. When declared, the system prompt
   and final step prompt instruct the LLM to emit XML tags for each output field.
   This was the breakthrough that took customer_service from 30.1% to 81.4%.

2. **`proceda convert --tools`** — Pass tool schemas to the converter for tool-aware
   SKILL.md generation with exact parameter names.

3. **`proceda convert --output-fields`** — Pass expected output field names to the
   converter so it includes them in frontmatter and final step instructions.

4. **Unqualified tool name resolution** — `call_tool()` and `check_required_tools()` now
   fall back to `resolve_tool()` for unqualified names (e.g., `validateInsurance` matches
   `sop-bench__validateInsurance`).

5. **"Don't skip tool calls" rule** — System prompt now says: "If a step instructs you to
   call a specific tool, you MUST call it." Addresses the patient_intake issue where the
   LLM skipped `validatePrescriptionBenefits` because insurance was already invalid.

6. **Empty Gemini response handling** — `_parse_response` returns empty `LLMResponse` when
   `response.choices` is empty instead of crashing.

### Per-Domain Documentation

Each completed domain has a detailed doc in `docs/`:
- `docs/sop-bench-patient-intake.md` — 97% TSR, 2 failures analyzed
- `docs/sop-bench-dangerous-goods.md` — 94.2% TSR (SOTA), 16 failures analyzed
- `docs/sop-bench-content-flagging.md` — 31% TSR, non-deterministic tools explained
- `docs/sop-bench-customer-service.md` — 81.4% TSR (SOTA), output_fields breakthrough

### Process Guide

`docs/sop-bench-guide.md` has the complete step-by-step process for running any domain.
Follow it exactly for new domains.

## What's Next: Know Your Business

KYB (90 tasks, 8 tools, 12 steps) is set up but blocked by Gemini rate limiting.

**Files ready:**
- `benchmarks/sop_bench/domains/know_your_business/SKILL.md` — Converted with output_fields
- `benchmarks/sop_bench/domains/know_your_business/config.yaml` — Gemini 2.5 Flash config

**To run:**
```bash
export GEMINI_API_KEY=$(pass soprun/GEMINI_API_KEY)
uv run python -m benchmarks.sop_bench.harness --domain know_your_business --workers 3
```

**Known issues with KYB:**
- Rate limiting: 12 steps × 90 tasks = ~1,500+ API calls. Hit Gemini rate limits.
- Judgment-heavy: The SOP asks the agent to "use your experience" to detect typos vs
  fabricated data. The boundary between "escalate" and "awaiting information" is subjective.
- The 5-task test run got 60% (3/5), with failures being `escalate` vs `awaiting information`.
- Best baseline is only 58% (Claude 4.5 Opus ReAct) — this is the hardest domain.

**Options to unblock:**
1. Wait for rate limits to reset (usually ~1 hour)
2. Use a different API key
3. Use Claude Haiku (change model in config.yaml to `claude-haiku-4-5-20251001`)
4. Lower parallelism (`--workers 1` or `--workers 3`)

## Remaining Domains (Not Yet Attempted)

From the guide's suggested order:

| Domain | Tasks | Tools | Best Baseline | Notes |
|--------|-------|-------|---------------|-------|
| Order Fulfillment | 30 | 4 | — | Simplest, quick validation |
| Referral Abuse v1 | 200 | 3 | 98% | Boolean scoring, high baseline |
| Referral Abuse v2 | 200 | 6 | 98% | Harder v1 with temporal patterns |
| Traffic Spoofing | 200 | 6 | 86% | Threshold-based |
| Aircraft Inspection | 112 | 7 | 99% | 7 output columns |
| Video Classification | 196 | 10 | 95% | Judgment-heavy |
| Email Intent | 195 | 5 | 99% | SOP has git merge conflict |
| Warehouse Inspection | 150 | 7 | 69% | Needs image understanding |
| Video Annotation | 125 | 26 | 58% | 20 distractor tools |

## Key Learnings

1. **Structured execution works.** Proceda's step-by-step execution with tool schemas beats
   "dump SOP in prompt" agents on execution-focused domains.

2. **`output_fields` is critical.** Without it, extraction is fragile (30% TSR). With it,
   the LLM reliably emits XML tags that the extractor catches (81% TSR). Always use
   `--output-fields` when converting SOPs.

3. **Model quality matters for reasoning.** Gemini 2.5 Flash is cheap but weaker on complex
   branching logic. The 29 remaining customer_service failures are all reasoning errors.

4. **Benchmark quirks exist.** Content flagging has `random.random()` in tools. Some domains
   have NaN values in tool results. Some tools have `print()` statements that corrupt MCP.
   The harness handles all of these.

5. **Extraction is the bottleneck, not execution.** Every domain achieves 100% ECR. Failures
   are either extraction misses or LLM reasoning errors, never execution crashes.

## File Map

```
benchmarks/sop_bench/
├── __init__.py
├── mcp_bridge.py              # Generic MCP stdio server
├── output_extractor.py        # Multi-strategy output extraction
├── harness.py                 # Evaluation runner (parallel, resume, retry)
├── generate_report.py         # HTML report generator
├── domains/
│   ├── patient_intake/        # 97% TSR
│   │   ├── SKILL.md
│   │   └── config.yaml
│   ├── dangerous_goods/       # 94.2% TSR (SOTA)
│   │   ├── SKILL.md
│   │   └── config.yaml
│   ├── content_flagging/      # 31% (non-deterministic tools)
│   │   ├── SKILL.md
│   │   └── config.yaml
│   ├── customer_service/      # 81.4% TSR (SOTA)
│   │   ├── SKILL.md
│   │   └── config.yaml
│   └── know_your_business/    # Incomplete (rate limited)
│       ├── SKILL.md
│       └── config.yaml
└── results/                   # Gitignored - traces, reports, JSON results

docs/
├── sop-bench-guide.md              # Step-by-step process for any domain
├── sop-bench-status.md             # This file
├── sop-bench-patient-intake.md     # Detailed analysis
├── sop-bench-dangerous-goods.md    # Detailed analysis
├── sop-bench-content-flagging.md   # Detailed analysis
└── sop-bench-customer-service.md   # Detailed analysis

tests/test_benchmarks/
├── test_mcp_bridge.py         # 10 tests
└── test_output_extractor.py   # 8 tests
```

## Obsidian Note

Full analysis with baselines from the paper's Table 5 is at:
`~/Obsidian_iCloud/notes.md/SOP-Bench Analysis.md`
