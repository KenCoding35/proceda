# How We Achieved SOTA on SOP-Bench in 48 Hours with Claude Code

*A solo founder's account of benchmarking an AI agent framework against Amazon's SOP-Bench — the bugs we found, the breakthroughs we stumbled into, and what it taught us about building reliable AI agents.*

---

I'm building [Proceda](https://github.com/vivekhaldar/proceda), an open-source SDK that turns Standard Operating Procedures into executable AI agents. When Amazon released [SOP-Bench](https://arxiv.org/abs/2506.08119) — a benchmark with 2,411 tasks across 14 business domains — I had to run it. This is the kind of benchmark Proceda was built for.

What I didn't expect: we'd achieve state-of-the-art on 4 domains, find bugs in 7 of the 14 domains, and do the entire thing in about 48 hours of Claude Code sessions. Here's how it went.

## Day 0: Building the Infrastructure

Before running a single benchmark task, we needed three pieces of infrastructure.

**The MCP Bridge.** SOP-Bench's tools are Python classes with a `process_tool_call` method. Proceda expects tools via the Model Context Protocol (MCP). So we built a generic stdio MCP server that wraps any SOP-Bench domain's tools — handling the Bedrock-to-MCP toolspec conversion, NaN sanitization, empty value replacement, and stdout suppression that SOP-Bench's tools throw at you.

**The Output Extractor.** SOP-Bench grades you on exact field matches. The agent's answer might be in a tool result, an XML tag in a summary, a bare JSON blob, or buried in prose ("the status is APPROVED"). We built a multi-strategy extractor that tries them all, with message extraction (the agent's deliberate answer) taking priority over raw tool results. This ordering turned out to be critical.

**The Evaluation Harness.** Load CSV tasks, run Proceda against each one, score against ground truth, save traces. Later we added parallel execution (`--workers N`), resume (skip completed tasks), and retry with exponential backoff for API rate limits.

## The Patient Intake Breakthrough: 0% to 97%

Patient intake was our first domain and our proving ground. It's rated the *easiest* by human experts — and both baseline agent architectures in the SOP-Bench repo score 0% on it with Claude 3.5 Sonnet v2.

The SOP requires a strict 6-tool dependency chain where the final tool needs outputs from all 5 previous tools. When you dump the whole SOP into a single prompt, the model can't manage the sequencing.

Our first 4 runs also scored 0%. But each failure taught us something specific:

| Run | TSR | What We Learned |
|-----|-----|-----------------|
| 1 | 0% | MCP bridge was missing pandas |
| 2 | 0% | Tools not found — needed unqualified name resolution |
| 3 | 0% | Converter used wrong parameter names |
| 4 | 0% | Converter needed tool schemas for exact param names |
| 5 | **100%** (1 task) | First PASS after adding `--tools` flag |
| 6 | 100% (5 tasks) | Scaled up, all pass |
| 7 | 83% (55/66) | Empty CSV values breaking tools |
| 8 | **97%** (64/66) | Bridge replaces empty strings with "N/A" |

The key insight from runs 3-5: the converter was *inventing* parameter names. The SOP says "validate insurance" and the converter would generate a step saying `validateInsurance(patient_insurance_data=...)` — but the actual tool parameter is `insurance_provider`. Adding `--tools` to `proceda convert` fixed this by giving the converter the exact tool schemas.

The 2 remaining failures? The LLM skips prescription benefit validation when primary insurance is already invalid. A clinically reasonable judgment call — but SOPs don't care about your judgment. You do every step.

## The Extraction Crisis: 30% to 81%

Customer service hit us with a different problem. The run completed fine — 100% ECR, every task ran to completion. But only 30.1% TSR. We were getting the right answers but couldn't extract them.

Trace analysis showed the pattern: the LLM would compute the correct `final_resolution_status` and express it in prose ("Based on my analysis, the resolution status should be RESOLVED"), but the output extractor was matching "account status is ACTIVE" instead — a field from a tool result, not the agent's answer.

The fix was a new Proceda feature: `output_fields`. Declare the expected output fields in the SKILL.md frontmatter, and the system prompt instructs the LLM to emit them as XML tags: `<final_resolution_status>RESOLVED</final_resolution_status>`. The extractor parses these deterministically.

Before `output_fields`: 30.1%. After: **81.4%**. SOTA on customer service, beating Llama 3.3 70B ReAct at 79%.

This was the single most impactful change in the entire benchmark run.

## The Benchmark Bug Saga

As we ran more domains, a pattern emerged: some failures weren't ours.

**Content flagging** was the first red flag. Two tools use `random.random()` to generate scores that determine the final decision. The benchmark claims to provide "stable, reproducible evaluation without runtime variability." `random.random()` is the opposite of that. We filed [issue #2](https://github.com/amazon-science/SOP-Bench/issues/2) and moved on.

**Warehouse inspection** was more subtle. Two tools use `po_number % 3` and `po_number % 2` — hardcoded arithmetic that agrees with the CSV ground truth only ~55% of the time. An agent following the SOP perfectly still gets the wrong answer 45% of the time because the *tools* are wrong. [Issue #3](https://github.com/amazon-science/SOP-Bench/issues/3).

**Video annotation** was the worst. 20 of 26 tool methods are literally `pass` — they return `None`. The toolspecs define full input schemas, but the Python implementations are empty stubs. [Issue #6](https://github.com/amazon-science/SOP-Bench/issues/6).

**Email intent** has unresolved git merge conflict markers *in the committed code*. The CSV starts with `<<<<<<< Updated upstream`. You can't even parse it. [Issue #7](https://github.com/amazon-science/SOP-Bench/issues/7).

Four of 14 domains — nearly a third of the benchmark — weren't runnable. The paper doesn't mention any of this.

## The SOP/CSV Disagreement Pattern

Even on runnable domains, we found a subtler problem. In several domains, the CSV ground truth follows labeling rules that aren't in the SOP.

**Referral abuse v1**: The SOP says to select the violation with the highest score. But 9 tasks in the CSV pick the violation with the highest-priority *closure action* — a tiebreaking rule not mentioned in the SOP. [Issue #4](https://github.com/amazon-science/SOP-Bench/issues/4).

**Traffic spoofing**: The SOP says Medium risk = "Temporary Suspension." The CSV labels 39 Medium-risk tasks as "Warning Issued." [Issue #5](https://github.com/amazon-science/SOP-Bench/issues/5).

**Know Your Business** was the most dramatic. Every single "awaiting information" task (34/34) has sanctions matches, shell company flags, offshore jurisdictions, and risk scores above 0.85. The "escalate" tasks have *fewer* flags and *lower* risk scores. The SOP says to escalate on these triggers. The CSV follows an unstated rule: profile irregularities in Step 1 override everything downstream. [Issue #8](https://github.com/amazon-science/SOP-Bench/issues/8).

The paper frames this as testing "implicit knowledge that humans learn but rarely document." But the agent evaluates each task in isolation with no access to ground truth — there's no mechanism to learn unstated rules.

## The Model Comparison Surprise

We started with Gemini 2.5 Flash — the cheapest model available — and kept winning. Dangerous goods: **94.2%** (vs 87% Claude 4 Sonnet baseline). Customer service: **81.4%** (vs 79% Llama 3.3 70B). Aircraft inspection: **100%** (vs 99% Claude 3.7 Sonnet).

For referral abuse v2, we ran three models head-to-head:
- Gemini 3 Flash: 88.5%
- Gemini 2.5 Pro (thinking model): 74.5%
- Gemini 3.1 Pro: **99.0%** — SOTA, beating Claude 4 Opus at 98%

The thinking model was the *worst*. It over-analyzed straightforward arithmetic tasks. Meanwhile, the non-thinking models just followed the steps.

This is the key insight: **structured execution reduces cognitive load at each decision point.** Instead of reasoning about a 30-step procedure in a single prompt, the model handles one step at a time. It doesn't need to "be smart" — it needs to follow instructions. That's what a harness gives you.

## The Rate Limit Dance

Google AI Studio limits Gemini 3.1 Pro to 250 requests per day. Each SOP-Bench task requires 10-65 LLM calls. At that rate, we could run maybe 15 tasks per day.

We switched to OpenRouter. Same model, no daily cap. The full 200-task referral abuse v2 run completed in ~30 minutes with 20 parallel workers. The KYB run (90 tasks, 50 workers, ~65 LLM calls per task) ran in about 25 minutes.

The other fun rate-limit story: KYB was "blocked by rate limiting" for days. The original run hit the limit on the very first LLM call of every task — 90 tasks, 0% TSR, every `predicted` field empty. We didn't realize this until we actually looked at the traces instead of just the score.

## The Worktree Lesson (Learned the Hard Way)

We ran multiple benchmark sessions in parallel using git worktrees — one session per domain to avoid stepping on each other. This worked great until we deleted a worktree and realized the traces (which live in `results/`, which is gitignored) went with it.

Lost traces mean you can't re-score with an updated extractor, can't do failure analysis, can't verify anything. We added a rule to the guide in bold: **"CRITICAL: Save traces before cleaning up."** And a memory note so future sessions wouldn't repeat the mistake.

## The Fact-Check Gauntlet

Writing up the results, I ran every claim through a fact-check. Some of what I found:

- Our report said aircraft inspection used Gemini 3 Flash. The config file says Gemini 2.5 Flash. (The cost story actually got *stronger* — SOTA with an even cheaper model.)
- Our report said the baseline was Claude 4.1 Opus. The paper says Claude 3.7 Sonnet. (Different model, same 99%.)
- Our report said "both baseline architectures score 0% on patient intake." True for Claude 3.5 Sonnet v2, but the paper reports 100% with Claude 4.1 Opus. Had to qualify the claim.

Every error we caught made the report more defensible. The final version cites specific tables, commits, and file paths for every claim.

## The Final Scorecard

After 48 hours, 10 domains run, 6 issues filed:

- **4 domains SOTA by raw TSR**: Dangerous Goods (+7.2pt), Customer Service (+2.4pt), Referral Abuse v2 (+1pt), Aircraft Inspection (+1pt)
- **8 of 10 SOTA on SOP-consistent tasks** (excluding benchmark labeling issues)
- **100% ECR across every domain** — zero crashes
- **4 domains skipped** due to benchmark bugs (stub tools, merge conflicts, random.random())
- **6 GitHub issues filed** improving the benchmark

Most of this with Gemini Flash models costing a fraction of the Claude Opus baselines.

## What I Learned

**The harness matters more than the model.** This was the central finding. Structured step-by-step execution with tool schema injection lets cheap models outperform expensive ones on procedural tasks. The model doesn't need to hold a 30-step procedure in its head — it just needs to handle one step at a time.

**Extraction is the hidden bottleneck.** Before `output_fields`, we had 100% execution completion but terrible scores because we couldn't reliably extract the agent's answer from its output. The model knew the answer. We just couldn't hear it.

**Benchmarks have bugs.** Four of 14 domains weren't runnable. Four more had labeling issues. This isn't a criticism — SOP-Bench is new and valuable. But if you evaluate against a benchmark and your scores look bad, check the data before blaming your system.

**Traces are gold.** Every task gets a full JSONL event trace. When something fails, the trace tells you exactly why: wrong tool call, extraction miss, reasoning error, or benchmark bug. Without traces, you're guessing. With traces, you're debugging.

**AI-assisted benchmarking is a superpower.** I ran this entire evaluation — infrastructure, 10 domains, failure analysis, bug reports, writeup — in 48 hours as a solo founder. Claude Code was my co-pilot for the whole thing: writing the MCP bridge, debugging extraction failures, analyzing traces, drafting bug reports, fact-checking claims. The speed wasn't "move fast and break things." It was "move fast and catch things" — including bugs in the benchmark itself.

---

Proceda is open source at [github.com/vivekhaldar/proceda](https://github.com/vivekhaldar/proceda). The full results report is at [enchiridionlabs.online/sop-bench-results.html](https://enchiridionlabs.online/sop-bench-results.html). Built by [Enchiridion Labs](https://enchiridionlabs.online).

Try it at [sop.run](https://sop.run).
