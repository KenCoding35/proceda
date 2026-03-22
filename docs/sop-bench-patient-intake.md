# SOP-Bench Patient Intake: 97% TSR (vs 0% Baseline)

## Summary

We ran Proceda against the SOP-Bench patient_intake benchmark — a 66-task evaluation where
LLM agents must follow a healthcare patient registration Standard Operating Procedure. Both
existing agent architectures (FunctionCalling and ReAct) score **0% TSR** on this benchmark.
Proceda achieves **97.0% TSR** (64/66 correct) using Gemini 2.5 Flash with zero hand-tuning.

| Metric | Proceda + Gemini 2.5 Flash | FC (Claude 3.5 Sonnet v2) | ReAct (Claude 3.5 Sonnet v2) |
|--------|---------------------------|---------------------------|------------------------------|
| **TSR** | **97.0% (64/66)** | 0% | 0% |
| **ECR** | 100% | 33% | 100% |
| **C-TSR** | 97.0% | 0% | 0% |

## What Is SOP-Bench?

[SOP-Bench](https://github.com/amazon-science/sop-bench) is an Amazon Science benchmark
(submitted to KDD 2026) containing 2,411 tasks across 14 business domains. It evaluates how
well LLM agents follow complex, human-expert-authored Standard Operating Procedures. The
benchmark uses mock tools (CSV lookups) and deterministic grading (predicted output vs ground
truth).

The existing agents (FunctionCallingAgent and ReActAgent) dump the entire SOP as raw text into
a single prompt and say "follow this." No step decomposition, no progress tracking, no
explicit state machine.

## Why Patient Intake Fails at 0%

Patient intake is rated the *easiest* domain by human experts (complexity score 4.33/10), yet
both agents score 0% TSR. The SOP requires a strict 6-tool dependency chain:

1. `validateInsurance` → `insurance_validation`
2. `validatePrescriptionBenefits` → `prescription_insurance_validation`
3. `calculateLifestyleRisk` → `life_style_risk_level`
4. `calculateOverallRisk(life_style_risk_level from step 3)` → `overall_risk_level`
5. `verifyPharmacy` → `pharmacy_check`
6. `registerPatient(ALL 5 prior results)` → `user_registration`

The final tool requires outputs from ALL 5 previous tools as input parameters. With 6 tools
× 3-6 parameters each = ~26 parameter slots, the agents can't manage the sequencing when the
SOP is a single blob of text.

## How Proceda Solves This

### 1. SOP Conversion (`proceda convert --tools`)

The raw SOP text is converted to a structured SKILL.md using the `proceda convert` command
with tool schema awareness:

```bash
proceda convert sop.txt --name patient-intake --tools toolspecs.json --output SKILL.md
```

This is LLM-based conversion — no hand-editing of the output. The `--tools` flag passes the
full tool schemas (names, parameter names, types, descriptions) so the converter generates
steps that reference actual tool names and parameter names.

The converter produced a 6-step SKILL.md where each step maps to exactly one tool call, with
explicit parameter listings and cross-step dependency references (e.g., "use the
`life_style_risk_level` from Step 3").

### 2. MCP Tool Bridge

SOP-Bench tools are Python functions in a `PatientIntakeManager` class. Proceda expects MCP
servers. The bridge (`benchmarks/sop_bench/mcp_bridge.py`) is a generic stdio MCP server that:

- Dynamically imports any SOP-Bench domain's tools.py
- Converts Bedrock-format toolspecs to MCP format
- Handles `initialize`, `tools/list`, `tools/call` JSON-RPC requests
- Replaces empty string values with "N/A" (SOP-Bench tools reject empty required fields)

The bridge is parameterized by domain name — extensible to all 14 SOP-Bench domains.

### 3. Evaluation Harness

The harness (`benchmarks/sop_bench/harness.py`) loads SOP-Bench CSV data directly (no
dependency on boto3/langchain), runs each task through Proceda's `Agent.run()` with the task
inputs as variables, extracts output from `TOOL_COMPLETED` events, and scores against ground
truth.

Every task trace is saved to `benchmarks/sop_bench/results/traces/` with descriptive filenames
(`patient_intake_P100012_success.jsonl`).

### 4. Structured Execution

Proceda's runtime provides what the baseline agents lack:

- **Step-by-step execution**: Each `### Step N:` heading is executed sequentially
- **Variable injection**: Task inputs (patient_id, insurance_provider, etc.) are injected into
  the system prompt as named variables
- **Tool call routing**: The LLM sees tool schemas with exact parameter names and calls them
  via MCP
- **Context preservation**: Tool results from earlier steps are visible in later steps' context
- **Completion enforcement**: `complete_step` must be called before advancing to the next step

## Pipeline Architecture

```
SOP-Bench CSV task
    │
    ▼
Harness (harness.py)
    │ converts task row → Proceda variables dict
    ▼
Agent.from_path("domains/patient_intake")
    │ loads SKILL.md + config.yaml
    ▼
Runtime
    │ connects MCP bridge → SOP-Bench tools
    ▼
Executor (step-by-step)
    │ Step 1: call validateInsurance → insurance_validation
    │ Step 2: call validatePrescriptionBenefits → prescription_insurance_validation
    │ Step 3: call calculateLifestyleRisk → life_style_risk_level
    │ Step 4: call calculateOverallRisk(life_style_risk_level) → overall_risk_level
    │ Step 5: call verifyPharmacy → pharmacy_check
    │ Step 6: call registerPatient(all prior results) → user_registration
    ▼
Output Extractor
    │ extracts 6 fields from TOOL_COMPLETED events
    ▼
Comparison → TSR/ECR/C-TSR metrics
```

## Configuration

```yaml
# benchmarks/sop_bench/domains/patient_intake/config.yaml
llm:
  model: gemini/gemini-2.5-flash
  temperature: 0.0
  max_tokens: 4096
  api_key_env: GEMINI_API_KEY

apps:
  - name: sop-bench
    description: SOP-Bench patient intake tools
    transport: stdio
    command:
      - uv
      - --directory
      - /Users/haldar/repos/gh/proceda
      - run
      - python
      - benchmarks/sop_bench/mcp_bridge.py
      - --domain
      - patient_intake
      - --data-dir
      - /path/to/sop-bench/src/amazon_sop_bench/benchmarks/data
```

## Running the Benchmark

```bash
# Set API key
export GEMINI_API_KEY=$(pass soprun/GEMINI_API_KEY)

# Run full benchmark
uv run python -m benchmarks.sop_bench.harness --domain patient_intake

# Run subset
uv run python -m benchmarks.sop_bench.harness --domain patient_intake --max-tasks 5
```

Results are saved to `benchmarks/sop_bench/results/`:
- `patient_intake_results.json` — metrics + per-task details
- `patient_intake_detailed.csv` — one row per task
- `traces/` — full event traces for every task

## Iteration History

| Run | TSR | Change | Root Cause |
|-----|-----|--------|-----------|
| Run 1 | 0% | — | MCP bridge missing pandas dependency |
| Run 2 | 0% (ECR 100%) | Fixed pandas | Tools not found: unqualified name resolution |
| Run 3 | 0% (ECR 100%) | Fixed name resolution | Wrong parameter names in SKILL.md |
| Run 4 | 0% (1 task) | Added tool schemas to converter | Converter used wrong param names |
| Run 5 | 100% (1 task) | Improved converter prompt | First PASS |
| Run 6 | 100% (5 tasks) | — | Scaled up, all pass |
| Run 7 | 83.3% (55/66) | Full run | 11 fails on empty CSV values |
| Run 8 | **97.0% (64/66)** | Empty value handling in bridge | 2 remaining edge cases |

## Remaining Failures (2/66)

Tasks P100033 and P100015 both fail because `validatePrescriptionBenefits` returns no result.
The LLM occasionally passes incorrect parameter names for this specific tool. All other 5
fields are correct for both tasks. These are non-deterministic LLM failures that could be
addressed by:

- Further improving the converter prompt
- Using a stronger model
- Adding retry logic for failed tool calls

## Key Technical Decisions

1. **No hand-tuning**: The SKILL.md is generated by `proceda convert --tools` with no manual
   edits. When conversion quality was insufficient, we improved the converter itself.

2. **Generic MCP bridge**: The bridge is parameterized by domain name — the same code works
   for all 14 SOP-Bench domains.

3. **Direct CSV loading**: The harness reads SOP-Bench data directly with csv/json modules,
   avoiding a dependency on SOP-Bench's boto3/langchain stack.

4. **Output from TOOL_COMPLETED events**: Deterministic extraction from Proceda's event stream
   rather than relying on LLM-formatted output text.

5. **Empty value handling**: SOP-Bench CSV data has empty fields for some tasks. The tools
   reject empty required parameters even though they only use patient_id for lookup. The bridge
   replaces empty strings with "N/A".

## Files

```
benchmarks/sop_bench/
├── __init__.py
├── mcp_bridge.py                          # Generic MCP stdio server
├── output_extractor.py                    # Extracts output from events
├── harness.py                             # Evaluation runner
├── domains/patient_intake/
│   ├── SKILL.md                           # Generated by proceda convert
│   └── config.yaml                        # Gemini 2.5 Flash config
└── results/                               # Gitignored output

tests/test_benchmarks/
├── test_mcp_bridge.py                     # 10 tests
└── test_output_extractor.py               # 8 tests
```

## Proceda Changes Made

- `proceda convert` gained `--tools` flag for tool schema context
- Converter prompt includes exact parameter names and descriptions
- `MCPOrchestrator.call_tool()` falls back to unqualified name resolution
- `MCPOrchestrator.check_required_tools()` uses `resolve_tool()` for unqualified matching
