# SOP-Bench Benchmark Status

Last updated: 2026-03-23 (video_classification 83.2%, KYB 42.2%, referral_abuse_v2 99.0% SOTA)

## Overview

Proceda is being evaluated against SOP-Bench, an Amazon Science benchmark with 2,411 tasks
across 14 business domains. We run `proceda convert --tools --output-fields` to convert
each domain's SOP into a SKILL.md, then execute all tasks via the evaluation harness.

**Branch:** `experiment/sop-bench`
**Models:** Gemini 2.5 Flash (domains 1-5), Gemini 3 Flash Preview (domain 6+), Gemini 3.1 Pro (referral_abuse_v2 SOTA), temperature=0.0
**API keys:** `pass soprun/GEMINI_API_KEY` (Google AI), `pass soprun/OPENROUTER_API_KEY` (OpenRouter)

## Results Summary

| Domain | Tasks | Proceda TSR | Best Baseline | Baseline TSR | Tag |
|--------|-------|-------------|---------------|-------------|-----|
| Patient Intake | 66 | **97.0%** | Claude 4.1 Opus ReAct | 100% | `sop-bench-patient-intake-97pct` |
| Dangerous Goods | 274 | **94.2%** | Claude 4 Sonnet FC | 87% | `sop-bench-dangerous-goods-94pct` |
| Customer Service | 156 | **81.4%** | Llama 3.3 70B ReAct | 79% | `sop-bench-customer-service-81pct` |
| Referral Abuse v1 | 200 | **95.5%** (100%‡) | Claude 3.5 v2 ReAct | 98% | — |
| Referral Abuse v2 (3.1 Pro) | 200 | **99.0%** | Claude 4 Opus FC | 98% | **SOTA** |
| Referral Abuse v2 (Flash) | 200 | 88.5% | Claude 4 Opus FC | 98% | — |
| Referral Abuse v2 (2.5 Pro) | 55* | 74.5% | Claude 4 Opus FC | 98% | — |
| Order Fulfillment | 30 | **86.7%** (100%‡) | — | — | — |
| Warehouse Inspection | 150 | 53.3%† | Various | 69%† | — |
| Content Flagging | 168 | 31.0%† | DeepSeek R1 ReAct | 60%† | `sop-bench-content-flagging-31pct` |
| Traffic Spoofing | 200 | **79.5%** (98.8%‡) | Claude 4.1 Sonnet ReAct | 86% | — |
| Video Classification | 196 | **83.2%** | Claude 4 Opus FC | 95% | — |
| Aircraft Inspection | 112 | **100%** | Claude 4.1 Opus ReAct | 99% | **SOTA** |
| Know Your Business | 90 | 42.2% | Claude 4.5 Opus ReAct | 58% | — |

† = Domain has broken mock tools (see tool mismatch analysis below), OR partial run due to API rate limits.
‡ = 100% on tasks where tools/CSV agree; remaining failures are tool bugs or CSV errors.
\* = Partial run: 55/200 tasks before daily API quota exhaustion (~1000 req/day for 2.5 Pro).

**SOTA on 4 domains** (dangerous_goods, customer_service, aircraft_inspection, referral_abuse_v2). Near-SOTA on patient_intake.
Three domains have broken tools: content_flagging (random.random()), warehouse_inspection
(mock logic disagrees with CSV ~55%), video_annotation (20/26 tool implementations are `pass` stubs).
KYB completed at 42.2% (below 58% baseline); 31/52 failures are SOP/CSV disagreements where
the CSV expects "awaiting information" for tasks with more escalation triggers than "escalate" tasks.

## What Was Done

### Infrastructure Built

1. **MCP Tool Bridge** (`benchmarks/sop_bench/mcp_bridge.py`) — Generic stdio MCP server
   wrapping any SOP-Bench domain's Python tool manager. Handles Bedrock→MCP toolspec
   conversion, NaN sanitization, empty value replacement, stdout suppression.

2. **Output Extractor** (`benchmarks/sop_bench/output_extractor.py`) — Extracts structured
   output from Proceda run events. Message extraction (agent's deliberate answer) takes
   priority over raw tool results. Strategies:
   - XML tags in summaries/messages (`<field_name>value</field_name>`)
   - `<final_output>{JSON}</final_output>` blocks
   - Bare JSON objects
   - Prose patterns ("status is VALUE")
   - Tool results (TOOL_COMPLETED events, used as fallback)

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
- `docs/sop-bench-referral-abuse-v1.md` — 95.5% TSR, 100% on CSV-consistent tasks
- `docs/sop-bench-referral-abuse-v2.md` — 99.0% TSR (SOTA), 2 failures analyzed
- `docs/sop-bench-order-fulfillment.md` — 86.7% TSR, 100% on tool-matching tasks
- `docs/sop-bench-warehouse-inspection.md` — 53.3% TSR, 100% on tool-matching tasks
- `docs/sop-bench-traffic-spoofing.md` — 79.5% TSR, 98.8% on SOP-consistent tasks
- `docs/sop-bench-aircraft-inspection.md` — 98.2% TSR, 2 empty-response failures
- `docs/sop-bench-know-your-business.md` — 42.2% TSR, 31/52 failures are escalate→awaiting info
- `docs/sop-bench-video-classification.md` — 83.2% TSR, 4 stub tools cause leniency bias
- `docs/sop-bench-tool-csv-mismatch-analysis.md` — Cross-domain tool bug analysis
- `docs/sop-bench-tool-agreement-audit.md` — Tool/CSV agreement rates for all domains

### Process Guide

`docs/sop-bench-guide.md` has the complete step-by-step process for running any domain.
Follow it exactly for new domains.

## What's Next

### Domains to Skip (broken tools)

| Domain | Issue |
|--------|-------|
| Content Flagging | `random.random()` in tools |
| Warehouse Inspection | Mock logic ~55% agreement with CSV |
| Video Annotation | 20/26 tool implementations are `pass` stubs ([issue #6](https://github.com/amazon-science/SOP-Bench/issues/6)) |
| Email Intent | Unresolved git merge conflicts in `sop.txt`, `tools.py`, and `test_set_with_outputs.csv` (see bug report) |

See `docs/sop-bench-tool-csv-mismatch-analysis.md` for details.
Video annotation bug report: `docs/sop-bench-video-annotation-bug-report.md`.
Email intent bug report: `docs/sop-bench-email-intent-bug-report.md`.

## Remaining Domains (Not Yet Attempted)

From the guide's suggested order:

All remaining domains either have broken tools or have been completed:
- ~~Video Classification~~ — **Done** (83.2% TSR)
- ~~Email Intent~~ — **Skipped** — unresolved git merge conflicts in 3 files (see bug report)
- ~~Video Annotation~~ — **Skipped** — 20/26 tool implementations are `pass` stubs ([issue #6](https://github.com/amazon-science/SOP-Bench/issues/6))

## Key Learnings

1. **Structured execution works.** Proceda's step-by-step execution with tool schemas beats
   "dump SOP in prompt" agents on execution-focused domains.

2. **`output_fields` is critical.** Without it, extraction is fragile (30% TSR). With it,
   the LLM reliably emits XML tags that the extractor catches (81% TSR). Always use
   `--output-fields` when converting SOPs.

3. **Model quality matters for reasoning.** Gemini 2.5 Flash is cheap but weaker on complex
   branching logic. The 29 remaining customer_service failures are all reasoning errors.

3b. **Thinking models can be worse for structured scoring.** Gemini 2.5 Pro (thinking model)
   achieves only 74.5% on referral_abuse_v2 vs 88.5% for Gemini 3 Flash and 99.0% for
   Gemini 3.1 Pro (both non-thinking). The thinking mode causes over-analysis on
   straightforward arithmetic tasks.

3c. **OpenRouter bypasses Google AI rate limits.** Gemini 3.1 Pro is limited to 250
   requests/day on Google AI Studio (~15 tasks/day). Using OpenRouter with 20 parallel
   workers, the full 200-task referral_abuse_v2 run completed in ~30 minutes.

4. **Three domains have broken tools.** Content flagging (random.random()), warehouse
   inspection (mock logic ~55% agreement), and video annotation (20/26 `pass` stubs). The
   paper doesn't acknowledge this, attributing low scores to agent reasoning failures. See
   the tool mismatch analysis docs for details.

5. **Extraction is the bottleneck, not execution.** Every domain achieves 100% ECR. Failures
   are either extraction misses or LLM reasoning errors, never execution crashes.

6. **Message extraction should override tool results.** When the agent's final answer (XML
   tags in complete_step) disagrees with a raw tool result, the agent's deliberate answer
   is correct. Fixed in the output extractor after warehouse inspection revealed the issue.

7. **SOP/CSV disagreements are a recurring pattern.** At least 4 domains have CSV ground
   truth that contradicts or extends the SOP's explicit rules: referral_abuse_v1 (9 tasks),
   traffic_spoofing (39 tasks), order_fulfillment (4 tasks), and know_your_business (31
   tasks where "awaiting information" labels have stronger escalation signals than "escalate"
   labels). Agents that faithfully follow the SOP get penalized.

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
│   ├── referral_abuse_detection_v1/  # 95.5% TSR (100% on valid tasks)
│   │   ├── SKILL.md
│   │   └── config.yaml
│   ├── referral_abuse_detection_v2/  # 99.0% TSR (SOTA, 2 reasoning errors)
│   │   ├── SKILL.md
│   │   └── config.yaml
│   ├── order_fulfillment/        # 86.7% TSR (100% on valid tasks)
│   │   ├── SKILL.md
│   │   ├── config.yaml
│   │   └── metadata.json
│   ├── warehouse_package_inspection/  # 53.3% TSR (100% on valid tasks)
│   │   ├── SKILL.md
│   │   ├── config.yaml
│   │   └── metadata.json      # Explicit input_columns override
│   ├── traffic_spoofing_detection/  # 79.5% TSR (98.8% on valid tasks)
│   │   ├── SKILL.md
│   │   └── config.yaml
│   ├── aircraft_inspection/       # 100% TSR (SOTA)
│   │   ├── SKILL.md
│   │   └── config.yaml
│   ├── video_classification/     # 83.2% TSR (4 stub tools)
│   │   ├── SKILL.md
│   │   └── config.yaml
│   └── know_your_business/    # 42.2% TSR (below 58% baseline)
│       ├── SKILL.md
│       └── config.yaml
└── results/                   # Gitignored - traces, reports, JSON results

docs/
├── sop-bench-guide.md              # Step-by-step process for any domain
├── sop-bench-status.md             # This file
├── sop-bench-patient-intake.md     # Detailed analysis
├── sop-bench-dangerous-goods.md    # Detailed analysis
├── sop-bench-content-flagging.md   # Detailed analysis
├── sop-bench-customer-service.md   # Detailed analysis
├── sop-bench-order-fulfillment.md  # Detailed analysis
├── sop-bench-warehouse-inspection.md  # Detailed analysis
├── sop-bench-traffic-spoofing.md      # Detailed analysis
├── sop-bench-aircraft-inspection.md  # Detailed analysis
├── sop-bench-tool-csv-mismatch-analysis.md  # Cross-domain tool bug analysis
└── sop-bench-tool-agreement-audit.md  # Tool/CSV agreement rates

tests/test_benchmarks/
├── test_mcp_bridge.py         # 10 tests
└── test_output_extractor.py   # 8 tests
```

## Obsidian Note

Full analysis with baselines from the paper's Table 5 is at:
`~/Obsidian_iCloud/notes.md/SOP-Bench Analysis.md`
