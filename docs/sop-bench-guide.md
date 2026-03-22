# SOP-Bench Evaluation Guide

How to run Proceda against any SOP-Bench domain. Follow this guide step by step for each new
domain. Lessons learned from patient_intake are baked in.

## Prerequisites

- SOP-Bench repo cloned at `~/repos/3p/sop-bench`
- Proceda on the `experiment/sop-bench` branch
- API key available via `pass soprun/GEMINI_API_KEY` (or whatever model you're using)
- pandas installed: `uv add --dev pandas` (already done)

## Domain Data Layout

Each SOP-Bench domain lives at:
```
~/repos/3p/sop-bench/src/amazon_sop_bench/benchmarks/data/{domain}/
├── sop.txt              # The raw SOP text
├── toolspecs.json       # Bedrock-format tool schemas
├── tools.py             # Python tool manager (*Manager class)
├── metadata.json        # input_columns, output_columns
├── test_set_with_outputs.csv   # Tasks + ground truth
└── data.csv             # (some domains have this instead)
```

## Step 1: Understand the Domain

Before running anything, read the domain's files:

1. **Read `sop.txt`** — Understand the procedure, decision logic, step dependencies
2. **Read `metadata.json`** — Note the `input_columns` and `output_columns`
3. **Read `toolspecs.json`** — Count the tools, note their parameter names and types
4. **Read first 5 rows of the CSV** — Check for data quirks (empty fields, list-as-string
   values like `"['Surgery 2017']"`, unusual formatting)
5. **Read `tools.py`** — Check the `process_tool_call` dispatch and any validation logic
   that might reject valid-looking inputs (e.g., `if not all([...])` guards)

### Things to Watch For

- **Empty fields**: SOP-Bench CSVs have empty values for some rows. The MCP bridge replaces
  empty strings with "N/A" but this may not work for all tools. Check the tool's validation.
- **List-as-string fields**: Columns like `previous_surgeries` store Python list reprs as
  strings (e.g., `"['Back Surgery 2017']"`). The LLM needs to parse these as JSON arrays.
- **Tool count**: Domains with many tools (Video Annotation has 26, only 6 relevant) will
  challenge the LLM's tool selection. Note which tools are actually needed.
- **Multi-output domains**: Some domains have multiple output columns (patient_intake has 6,
  aircraft_inspection has 7). All must be correct for TSR.
- **Single-output domains**: Most domains have one output column (e.g., `final_decision`).
  Simpler to evaluate.
- **Merge conflicts**: email_intent's sop.txt has a git merge conflict in it. Check for this.

## Step 2: Create the Domain Directory

```bash
mkdir -p benchmarks/sop_bench/domains/{domain}/
```

## Step 3: Convert the SOP

Set up a temporary proceda.yaml for the converter (the repo's proceda.yaml is gitignored):

```bash
export GEMINI_API_KEY=$(pass soprun/GEMINI_API_KEY)

# Temporarily swap proceda.yaml for the converter
cat > /tmp/proceda_convert.yaml << 'EOF'
llm:
  model: gemini/gemini-2.5-flash
  temperature: 0.7
  max_tokens: 16384
  api_key_env: GEMINI_API_KEY
EOF

cp proceda.yaml proceda.yaml.bak
cp /tmp/proceda_convert.yaml proceda.yaml

uv run proceda convert \
  ~/repos/3p/sop-bench/src/amazon_sop_bench/benchmarks/data/{domain}/sop.txt \
  --name {domain-kebab-case} \
  --tools ~/repos/3p/sop-bench/src/amazon_sop_bench/benchmarks/data/{domain}/toolspecs.json \
  --output benchmarks/sop_bench/domains/{domain}/SKILL.md

mv proceda.yaml.bak proceda.yaml
```

### Verify the Converted SKILL.md

Check the output for:

1. **Correct tool names** — The `required_tools` list should match tool names from toolspecs.json
2. **Exact parameter names** — Step instructions should reference the exact parameter names
   from the tool schemas, not invented/paraphrased names
3. **Step-tool mapping** — Ideally each step maps to one tool call
4. **Dependency references** — Later steps should explicitly reference results from earlier
   steps (e.g., "use the `life_style_risk_level` from Step 3")
5. **Step count** — Should be reasonable (roughly one per tool call, not excessively split)

**Do NOT hand-edit the SKILL.md.** If it's wrong, fix `proceda convert` (the converter prompt
in `src/proceda/skills/converter.py` or the `--tools` context formatting). Benchmark integrity
requires automated conversion.

If the conversion is truncated (too few steps), increase `max_tokens` in the converter config.

## Step 4: Create the Domain Config

```bash
cat > benchmarks/sop_bench/domains/{domain}/config.yaml << 'EOF'
llm:
  model: gemini/gemini-2.5-flash
  temperature: 0.0
  max_tokens: 4096
  api_key_env: GEMINI_API_KEY

apps:
  - name: sop-bench
    description: SOP-Bench {domain} tools
    transport: stdio
    command:
      - uv
      - --directory
      - /Users/haldar/repos/gh/proceda
      - run
      - python
      - benchmarks/sop_bench/mcp_bridge.py
      - --domain
      - {domain}
      - --data-dir
      - /Users/haldar/repos/3p/sop-bench/src/amazon_sop_bench/benchmarks/data
EOF
```

Key settings:
- `temperature: 0.0` for reproducibility
- The `--directory` flag ensures uv resolves from the proceda repo root
- `config.yaml` (not `proceda.yaml`) to avoid gitignore conflicts

## Step 5: Test the MCP Bridge

Verify tools load and respond correctly for the domain:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}
{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' | \
  uv run python benchmarks/sop_bench/mcp_bridge.py \
    --domain {domain} \
    --data-dir ~/repos/3p/sop-bench/src/amazon_sop_bench/benchmarks/data
```

Check that:
- `initialize` returns a valid response
- `tools/list` returns the expected number of tools
- Tool names match what the SKILL.md references

### Test a Tool Call

Pick a task from the CSV and test a single tool:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"toolName","arguments":{"key":"value"}}}' | \
  uv run python benchmarks/sop_bench/mcp_bridge.py \
    --domain {domain} \
    --data-dir ~/repos/3p/sop-bench/src/amazon_sop_bench/benchmarks/data
```

## Step 6: Run a Single Task

```bash
export GEMINI_API_KEY=$(pass soprun/GEMINI_API_KEY)

uv run python -m benchmarks.sop_bench.harness \
  --domain {domain} \
  --max-tasks 1
```

Expected output: `PASS` or `FAIL` with field-level diff.

If it fails, check the trace at `benchmarks/sop_bench/results/traces/{domain}_*_fail.jsonl`:

```bash
# See all tool calls and their results/errors
cat benchmarks/sop_bench/results/traces/{domain}_*_fail.jsonl | python3 -c "
import json, sys
for line in sys.stdin:
    e = json.loads(line)
    if '_meta' in e:
        print('PREDICTED:', json.dumps(e.get('predicted', {})))
        print('EXPECTED:', json.dumps(e.get('expected', {})))
        continue
    t = e.get('type', '')
    if t in ('tool.called', 'tool.completed', 'tool.failed'):
        payload = e.get('payload', {})
        print(f\"{t}: {payload.get('tool_name')}\")
        if 'arguments' in payload:
            print(f'  args: {json.dumps(payload[\"arguments\"])}')
        if 'result' in payload:
            print(f'  result: {payload[\"result\"][:200]}')
        if 'error' in payload:
            print(f'  error: {payload[\"error\"][:200]}')
"
```

### Common Failure Patterns

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Tool not found: toolName` | Unqualified name not resolving | Should be fixed already; check `resolve_tool` |
| `got an unexpected keyword argument` | LLM using wrong param name | Converter needs better param name instructions |
| `Missing required input fields` | Empty value in CSV | Bridge already replaces `""` with `"N/A"` — check if tool needs different handling |
| `Step N exhausted 50 iterations` | LLM stuck in retry loop | Check what tool call is failing; may need converter prompt fix |
| All fields `<missing>` | Output extractor found nothing | Check if tool results use expected column names |

## Step 7: Run 5 Tasks

```bash
uv run python -m benchmarks.sop_bench.harness \
  --domain {domain} \
  --max-tasks 5
```

If ≥4/5 pass, proceed to full run. If <4/5 pass, debug using traces and iterate.

## Step 8: Full Run

```bash
uv run python -m benchmarks.sop_bench.harness --domain {domain}
```

Results are saved to:
- `benchmarks/sop_bench/results/{domain}_results.json` — metrics + per-task details
- `benchmarks/sop_bench/results/{domain}_detailed.csv` — one row per task
- `benchmarks/sop_bench/results/traces/` — full event traces for every task

## Step 9: Record Results

After each domain run, update the Obsidian note at
`~/Obsidian_iCloud/notes.md/SOP-Bench Analysis.md` with the results table.

Commit the SKILL.md and config.yaml (results/ is gitignored). Tag significant milestones:

```bash
git tag -a sop-bench-{domain}-{pct}pct -m "SOP-Bench {domain}: {pct}% TSR ({correct}/{total})"
```

## Troubleshooting

### MCP Bridge Won't Start

- Check `pandas` is installed: `uv add --dev pandas`
- Check the domain's `tools.py` doesn't import other SOP-Bench modules that need additional
  dependencies
- Test with `echo '...' | uv run python benchmarks/sop_bench/mcp_bridge.py ...` to see errors

### Converter Produces Bad SKILL.md

- **Too few steps**: Increase `max_tokens` in the converter config
- **Wrong tool names**: Check that `--tools` flag points to the right toolspecs.json
- **Invented parameter names**: The converter prompt in `src/proceda/skills/converter.py`
  tells the LLM to use exact names. If it still invents names, add more explicit examples
  to the prompt for the specific pattern.
- **Missing dependencies**: Some SOPs reference results from earlier steps. If the converter
  doesn't capture these, the prompt may need domain-specific guidance.

### Tool Calls Fail with Wrong Parameters

The LLM sees two sources of parameter info:
1. The SKILL.md step instructions (from the converter)
2. The tool schemas (from MCP `tools/list`)

If these conflict, the LLM may follow either one. Fix the converter to match the tool schemas
exactly. The LLM should prefer the tool schemas since they're the formal API contract, but
misleading step instructions can override this.

### Low TSR Despite Tools Succeeding

If tools all return valid results but the final output is wrong:
- Check the output extractor: does it map tool result keys to expected column names?
- Some domains return results in unexpected formats — check the tool's `process_tool_call`
  return value
- The extractor looks for keys matching `expected_columns` — if the tool returns
  `{"status": "approved"}` but the column is `final_decision`, it won't match

### Domains with Distractor Tools

Video Annotation has 26 tools (only 6 relevant). The converter's `required_tools` should list
only the needed ones. If the LLM calls wrong tools:
- Check if `required_tools` in the SKILL.md is correct
- Proceda's `required_tools` acts as an allowlist — only listed tools are available to the LLM
- This should prevent distractor tool confusion automatically

## Reference: All 14 Domains

| Domain | Tasks | Tools | Output Cols | Notes |
|--------|-------|-------|-------------|-------|
| aircraft_inspection | 112 | 7 | 7 | Multi-output |
| content_flagging | 168 | 4 | 1 | Weighted scoring |
| customer_service | 156 | 10 | 1 | Heavy branching, 7+ sequential calls |
| dangerous_goods | 274 | 4 | 1 | Score aggregation + imputation |
| email_intent | 195 | 5 | 2 | SOP has git merge conflict |
| know_your_business | 90 | 8 | 1 | Judgment-heavy, noisy signals |
| order_fulfillment | 30 | 4 | 1 | Simplest domain |
| patient_intake | 66 | 6 | 6 | **Done: 97% TSR** |
| referral_abuse_detection_v1 | 200 | 3 | 1 | Boolean scoring |
| referral_abuse_detection_v2 | 200 | 6 | 1 | v1 + temporal + risk severity |
| traffic_spoofing_detection | 200 | 6 | 1 | Threshold-based |
| video_annotation | 125 | 26 | 1 | 20 distractor tools |
| video_classification | 196 | 10 | 1 | Judgment-heavy |
| warehouse_package_inspection | 150 | 7 | 1 | Short-circuit logic |

### Suggested Order (easiest first)

1. **order_fulfillment** (30 tasks, 4 tools, simple pipeline) — quick validation
2. **dangerous_goods** (274 tasks, 4 tools, formulaic) — high task count, clear logic
3. **referral_abuse_detection_v1** (200 tasks, 3 tools) — boolean scoring, simple
4. **warehouse_package_inspection** (150 tasks, 7 tools) — short-circuit logic
5. **aircraft_inspection** (112 tasks, 7 tools, 7 outputs) — tests multi-output extraction
6. **traffic_spoofing_detection** (200 tasks, 6 tools) — threshold-based
7. **referral_abuse_detection_v2** (200 tasks, 6 tools) — harder version of v1
8. **email_intent** (195 tasks, 5 tools) — fix the merge conflict in sop.txt first
9. **customer_service** (156 tasks, 10 tools) — heavy branching, many sequential calls
10. **content_flagging** (168 tasks, 4 tools) — weighted scoring with formulas
11. **video_classification** (196 tasks, 10 tools) — judgment-heavy
12. **know_your_business** (90 tasks, 8 tools) — judgment + noisy signals
13. **video_annotation** (125 tasks, 26 tools) — distractor tools, longest SOP
