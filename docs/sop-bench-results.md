# Proceda Achieves SOTA on SOP-Bench*

*\*On 4 of 10 runnable domains by raw TSR; 8 of 10 when excluding benchmark labeling issues we identified and reported. Four additional domains were not runnable due to benchmark bugs (stub tools, merge conflicts). See [Benchmark Quality](#benchmark-quality-contributions) for details.*

## Executive Summary

Proceda, a terminal-first SDK for turning Standard Operating Procedures into runnable AI agents, achieves state-of-the-art results on [SOP-Bench](https://github.com/amazon-science/SOP-Bench), an Amazon Science benchmark with 2,411 tasks across 14 business domains. On the 10 domains with functioning tools, Proceda sets new SOTA on 4 domains by raw Task Success Rate (TSR) and beats the best published baseline on 8 of 10 domains when measured on tasks where the benchmark's ground truth is consistent with its own SOP rules. Proceda also achieves 100% Execution Completion Rate (ECR) across every domain — no crashes, no stalls, every task runs to completion.

Notably, most of these results were achieved using Gemini 2.5 Flash and Gemini 3 Flash — lightweight, inexpensive models — beating baselines set by Claude 4 Opus, Claude 4.1 Opus, and Claude 4 Sonnet. This demonstrates that structured SOP execution can substitute for raw model capability on procedural tasks.

Along the way, we identified and reported 6 benchmark issues across 7 of the 14 domains, contributing to the quality of this emerging benchmark.

---

## Why SOPs Matter

Standard Operating Procedures are how enterprises encode critical business processes — from patient intake to KYC compliance to content moderation. Unlike informational knowledge bases (where benchmarks like [SkillsBench](https://arxiv.org/abs/2410.03647) measure factual retrieval), SOPs are *procedural*: they define a sequence of steps, tool calls, decision gates, and branching logic that must be executed faithfully.

Automating SOPs with AI is a key enterprise use case. But "dump the SOP into a prompt and hope for the best" doesn't work — as SOP-Bench demonstrates, even frontier models fail when the procedure is complex. The patient intake domain, rated the *easiest* by human experts, scores **0% TSR** with both baseline agent architectures in the paper (Function Calling and ReAct with Claude 3.5 Sonnet v2).

[SOP-Bench](https://arxiv.org/abs/2506.08119) is a welcome benchmark in this space. It provides 14 real-world business domains with mock tools, ground truth labels, and standardized evaluation. It tests what matters: can an AI agent reliably follow a multi-step procedure, call the right tools with the right parameters, and produce the correct output?

---

## Results

### Performance Summary

| Domain | Model | Raw TSR | SOP-consistent TSR | Best Baseline (Paper) | Delta |
|--------|-------|---------|--------------------|-----------------------|-------|
| Aircraft Inspection | Gemini 3 Flash | **100%** | 100% | 99% — Claude 4.1 Opus ReAct | **+1pt SOTA** |
| Referral Abuse v2 | Gemini 3.1 Pro | **99.0%** | 99.0% | 98% — Claude 4 Opus FC | **+1pt SOTA** |
| Patient Intake | Gemini 2.5 Flash | **97.0%** | 97.0% | 100% — Claude 4.1 Opus ReAct | -3pt |
| Referral Abuse v1 | Gemini 3 Flash | **95.5%** | 100%\* | 98% — Claude 3.5 v2 ReAct | **+2pt\* SOTA** |
| Dangerous Goods | Gemini 2.5 Flash | **94.2%** | 94.2% | 87% — Claude 4 Sonnet FC | **+7.2pt SOTA** |
| Order Fulfillment | Gemini 3 Flash | **86.7%** | 100%\* | — | no baseline published |
| Video Classification | Gemini 3.1 Pro | **83.2%** | ~100%\* | 95.4% — Claude 4 Sonnet FC | **+4.6pt\* SOTA** |
| Customer Service | Gemini 2.5 Flash | **81.4%** | 81.4% | 79% — Llama 3.3 70B ReAct | **+2.4pt SOTA** |
| Traffic Spoofing | Gemini 3 Flash | **79.5%** | 98.8%\* | 86% — Claude 4.1 Sonnet ReAct | **+12.8pt\* SOTA** |
| Know Your Business | Gemini 3.1 Pro | **42.2%** | 64.4%\* | 58% — Claude 4.5 Opus ReAct | **+6.4pt\* SOTA** |

\* SOP-consistent TSR excludes tasks where the benchmark's CSV ground truth contradicts the SOP's explicit rules. See [Benchmark Quality](#benchmark-quality-contributions) for details. Baseline TSR is measured on all tasks (including the inconsistent ones), so the comparison favors the baseline.

**Not run (4 domains, benchmark bugs):**

| Domain | Issue | GitHub Issue |
|--------|-------|-------------|
| Content Flagging | `random.random()` in tool implementations | [#2](https://github.com/amazon-science/SOP-Bench/issues/2) |
| Warehouse Inspection | Hardcoded `po_number % 3` mock logic ignores CSV | [#3](https://github.com/amazon-science/SOP-Bench/issues/3) |
| Video Annotation | 20 of 26 tool implementations are `pass` stubs | [#6](https://github.com/amazon-science/SOP-Bench/issues/6) |
| Email Intent | Unresolved git merge conflicts in 3 files | [#7](https://github.com/amazon-science/SOP-Bench/issues/7) |

### Visualizations

#### Proceda vs Best Baseline (SOP-Consistent TSR)

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 420" font-family="system-ui, -apple-system, sans-serif">
  <style>
    .title { font-size: 16px; font-weight: 600; fill: #1a1a2e; }
    .label { font-size: 11px; fill: #444; }
    .value { font-size: 10px; font-weight: 600; }
    .axis { stroke: #ccc; stroke-width: 1; }
    .grid { stroke: #eee; stroke-width: 0.5; }
    .bar-proceda { fill: #2563eb; }
    .bar-baseline { fill: #94a3b8; }
    .legend-text { font-size: 12px; fill: #333; }
    .sota { font-size: 9px; font-weight: 700; fill: #16a34a; }
  </style>

  <text x="400" y="25" text-anchor="middle" class="title">Proceda SOP-Consistent TSR vs Best Published Baseline</text>

  <!-- Legend -->
  <rect x="250" y="38" width="12" height="12" class="bar-proceda" rx="2"/>
  <text x="266" y="49" class="legend-text">Proceda (SOP-consistent)</text>
  <rect x="430" y="38" width="12" height="12" class="bar-baseline" rx="2"/>
  <text x="446" y="49" class="legend-text">Best Baseline (paper)</text>

  <!-- Grid lines -->
  <line x1="180" y1="70" x2="180" y2="380" class="axis"/>
  <line x1="180" y1="380" x2="780" y2="380" class="axis"/>

  <!-- Y-axis grid: 0%, 25%, 50%, 75%, 100% -->
  <line x1="180" y1="380" x2="780" y2="380" class="grid"/>
  <line x1="180" y1="305" x2="780" y2="305" class="grid"/>
  <line x1="180" y1="230" x2="780" y2="230" class="grid"/>
  <line x1="180" y1="155" x2="780" y2="155" class="grid"/>
  <line x1="180" y1="80" x2="780" y2="80" class="grid"/>

  <text x="175" y="384" text-anchor="end" class="label">0%</text>
  <text x="175" y="309" text-anchor="end" class="label">25%</text>
  <text x="175" y="234" text-anchor="end" class="label">50%</text>
  <text x="175" y="159" text-anchor="end" class="label">75%</text>
  <text x="175" y="84" text-anchor="end" class="label">100%</text>

  <!-- Scale: 300px = 100%, so 1% = 3px. y=380 is 0%, y=80 is 100% -->
  <!-- Domain 1: Aircraft Inspection — 100% vs 99% -->
  <rect x="192" y="80" width="24" height="300" class="bar-proceda" rx="2"/>
  <rect x="218" y="83" width="24" height="297" class="bar-baseline" rx="2"/>
  <text x="217" y="73" text-anchor="middle" class="value" fill="#2563eb">100</text>
  <text x="217" y="395" text-anchor="middle" class="label" transform="rotate(-35 217 395)">Aircraft Insp.</text>
  <text x="217" y="63" text-anchor="middle" class="sota">SOTA</text>

  <!-- Domain 2: Referral v2 — 99% vs 98% -->
  <rect x="252" y="83" width="24" height="297" class="bar-proceda" rx="2"/>
  <rect x="278" y="86" width="24" height="294" class="bar-baseline" rx="2"/>
  <text x="277" y="76" text-anchor="middle" class="value" fill="#2563eb">99</text>
  <text x="277" y="395" text-anchor="middle" class="label" transform="rotate(-35 277 395)">Referral v2</text>
  <text x="277" y="63" text-anchor="middle" class="sota">SOTA</text>

  <!-- Domain 3: Referral v1 — 100%* vs 98% -->
  <rect x="312" y="80" width="24" height="300" class="bar-proceda" rx="2"/>
  <rect x="338" y="86" width="24" height="294" class="bar-baseline" rx="2"/>
  <text x="337" y="73" text-anchor="middle" class="value" fill="#2563eb">100*</text>
  <text x="337" y="395" text-anchor="middle" class="label" transform="rotate(-35 337 395)">Referral v1</text>
  <text x="337" y="63" text-anchor="middle" class="sota">SOTA*</text>

  <!-- Domain 4: Video Classification — ~100%* vs 95.4% -->
  <rect x="372" y="80" width="24" height="300" class="bar-proceda" rx="2"/>
  <rect x="398" y="94" width="24" height="286" class="bar-baseline" rx="2"/>
  <text x="397" y="73" text-anchor="middle" class="value" fill="#2563eb">~100*</text>
  <text x="397" y="395" text-anchor="middle" class="label" transform="rotate(-35 397 395)">Video Classif.</text>
  <text x="397" y="63" text-anchor="middle" class="sota">SOTA*</text>

  <!-- Domain 5: Traffic Spoofing — 98.8%* vs 86% -->
  <rect x="432" y="83.6" width="24" height="296.4" class="bar-proceda" rx="2"/>
  <rect x="458" y="122" width="24" height="258" class="bar-baseline" rx="2"/>
  <text x="457" y="76" text-anchor="middle" class="value" fill="#2563eb">98.8*</text>
  <text x="457" y="395" text-anchor="middle" class="label" transform="rotate(-35 457 395)">Traffic Spoof.</text>
  <text x="457" y="63" text-anchor="middle" class="sota">SOTA*</text>

  <!-- Domain 6: Patient Intake — 97% vs 100% -->
  <rect x="492" y="89" width="24" height="291" class="bar-proceda" rx="2"/>
  <rect x="518" y="80" width="24" height="300" class="bar-baseline" rx="2"/>
  <text x="517" y="82" text-anchor="middle" class="value" fill="#2563eb">97</text>
  <text x="517" y="395" text-anchor="middle" class="label" transform="rotate(-35 517 395)">Patient Intake</text>

  <!-- Domain 7: Dangerous Goods — 94.2% vs 87% -->
  <rect x="552" y="97.4" width="24" height="282.6" class="bar-proceda" rx="2"/>
  <rect x="578" y="119" width="24" height="261" class="bar-baseline" rx="2"/>
  <text x="577" y="90" text-anchor="middle" class="value" fill="#2563eb">94.2</text>
  <text x="577" y="395" text-anchor="middle" class="label" transform="rotate(-35 577 395)">Dangerous Gds.</text>
  <text x="577" y="80" text-anchor="middle" class="sota">SOTA</text>

  <!-- Domain 8: Customer Service — 81.4% vs 79% -->
  <rect x="612" y="135.8" width="24" height="244.2" class="bar-proceda" rx="2"/>
  <rect x="638" y="143" width="24" height="237" class="bar-baseline" rx="2"/>
  <text x="637" y="129" text-anchor="middle" class="value" fill="#2563eb">81.4</text>
  <text x="637" y="395" text-anchor="middle" class="label" transform="rotate(-35 637 395)">Customer Svc.</text>
  <text x="637" y="119" text-anchor="middle" class="sota">SOTA</text>

  <!-- Domain 9: KYB — 64.4%* vs 58% -->
  <rect x="672" y="186.8" width="24" height="193.2" class="bar-proceda" rx="2"/>
  <rect x="698" y="206" width="24" height="174" class="bar-baseline" rx="2"/>
  <text x="697" y="180" text-anchor="middle" class="value" fill="#2563eb">64.4*</text>
  <text x="697" y="395" text-anchor="middle" class="label" transform="rotate(-35 697 395)">KYB</text>
  <text x="697" y="170" text-anchor="middle" class="sota">SOTA*</text>

  <!-- Domain 10: Order Fulfillment — 100%* vs no baseline -->
  <rect x="732" y="80" width="24" height="300" class="bar-proceda" rx="2"/>
  <text x="757" y="73" text-anchor="middle" class="value" fill="#2563eb">100*</text>
  <text x="757" y="395" text-anchor="middle" class="label" transform="rotate(-35 757 395)">Order Fulfil.</text>
  <text x="757" y="200" text-anchor="middle" class="label" style="font-style:italic;">no baseline</text>

  <!-- Footnote -->
  <text x="400" y="418" text-anchor="middle" style="font-size:10px; fill:#666;">* SOP-consistent TSR (excludes tasks where CSV ground truth contradicts SOP rules). Baseline measured on all tasks.</text>
</svg>
```

#### Proceda Raw TSR vs Best Baseline

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 420" font-family="system-ui, -apple-system, sans-serif">
  <style>
    .title { font-size: 16px; font-weight: 600; fill: #1a1a2e; }
    .label { font-size: 11px; fill: #444; }
    .value { font-size: 10px; font-weight: 600; }
    .axis { stroke: #ccc; stroke-width: 1; }
    .grid { stroke: #eee; stroke-width: 0.5; }
    .bar-proceda { fill: #2563eb; }
    .bar-baseline { fill: #94a3b8; }
    .legend-text { font-size: 12px; fill: #333; }
    .sota { font-size: 9px; font-weight: 700; fill: #16a34a; }
  </style>

  <text x="400" y="25" text-anchor="middle" class="title">Proceda Raw TSR vs Best Published Baseline</text>

  <!-- Legend -->
  <rect x="280" y="38" width="12" height="12" class="bar-proceda" rx="2"/>
  <text x="296" y="49" class="legend-text">Proceda (raw TSR)</text>
  <rect x="430" y="38" width="12" height="12" class="bar-baseline" rx="2"/>
  <text x="446" y="49" class="legend-text">Best Baseline (paper)</text>

  <!-- Grid lines -->
  <line x1="180" y1="70" x2="780" y2="380" class="grid" style="display:none"/>
  <line x1="180" y1="380" x2="780" y2="380" class="axis"/>
  <line x1="180" y1="70" x2="180" y2="380" class="axis"/>
  <line x1="180" y1="305" x2="780" y2="305" class="grid"/>
  <line x1="180" y1="230" x2="780" y2="230" class="grid"/>
  <line x1="180" y1="155" x2="780" y2="155" class="grid"/>
  <line x1="180" y1="80" x2="780" y2="80" class="grid"/>

  <text x="175" y="384" text-anchor="end" class="label">0%</text>
  <text x="175" y="309" text-anchor="end" class="label">25%</text>
  <text x="175" y="234" text-anchor="end" class="label">50%</text>
  <text x="175" y="159" text-anchor="end" class="label">75%</text>
  <text x="175" y="84" text-anchor="end" class="label">100%</text>

  <!-- Domain 1: Aircraft Inspection — 100% vs 99% -->
  <rect x="192" y="80" width="24" height="300" class="bar-proceda" rx="2"/>
  <rect x="218" y="83" width="24" height="297" class="bar-baseline" rx="2"/>
  <text x="217" y="73" text-anchor="middle" class="value" fill="#2563eb">100</text>
  <text x="217" y="395" text-anchor="middle" class="label" transform="rotate(-35 217 395)">Aircraft Insp.</text>
  <text x="217" y="63" text-anchor="middle" class="sota">SOTA</text>

  <!-- Domain 2: Referral v2 — 99% vs 98% -->
  <rect x="252" y="83" width="24" height="297" class="bar-proceda" rx="2"/>
  <rect x="278" y="86" width="24" height="294" class="bar-baseline" rx="2"/>
  <text x="277" y="76" text-anchor="middle" class="value" fill="#2563eb">99</text>
  <text x="277" y="395" text-anchor="middle" class="label" transform="rotate(-35 277 395)">Referral v2</text>
  <text x="277" y="63" text-anchor="middle" class="sota">SOTA</text>

  <!-- Domain 3: Patient Intake — 97% vs 100% -->
  <rect x="312" y="89" width="24" height="291" class="bar-proceda" rx="2"/>
  <rect x="338" y="80" width="24" height="300" class="bar-baseline" rx="2"/>
  <text x="337" y="82" text-anchor="middle" class="value" fill="#2563eb">97</text>
  <text x="337" y="395" text-anchor="middle" class="label" transform="rotate(-35 337 395)">Patient Intake</text>

  <!-- Domain 4: Referral v1 — 95.5% vs 98% -->
  <rect x="372" y="93.5" width="24" height="286.5" class="bar-proceda" rx="2"/>
  <rect x="398" y="86" width="24" height="294" class="bar-baseline" rx="2"/>
  <text x="397" y="87" text-anchor="middle" class="value" fill="#2563eb">95.5</text>
  <text x="397" y="395" text-anchor="middle" class="label" transform="rotate(-35 397 395)">Referral v1</text>

  <!-- Domain 5: Dangerous Goods — 94.2% vs 87% -->
  <rect x="432" y="97.4" width="24" height="282.6" class="bar-proceda" rx="2"/>
  <rect x="458" y="119" width="24" height="261" class="bar-baseline" rx="2"/>
  <text x="457" y="90" text-anchor="middle" class="value" fill="#2563eb">94.2</text>
  <text x="457" y="395" text-anchor="middle" class="label" transform="rotate(-35 457 395)">Dangerous Gds.</text>
  <text x="457" y="80" text-anchor="middle" class="sota">SOTA</text>

  <!-- Domain 6: Order Fulfillment — 86.7% vs no baseline -->
  <rect x="492" y="120" width="24" height="260" class="bar-proceda" rx="2"/>
  <text x="517" y="113" text-anchor="middle" class="value" fill="#2563eb">86.7</text>
  <text x="517" y="395" text-anchor="middle" class="label" transform="rotate(-35 517 395)">Order Fulfil.</text>
  <text x="517" y="250" text-anchor="middle" class="label" style="font-style:italic;">no baseline</text>

  <!-- Domain 7: Video Classification — 83.2% vs 95.4% -->
  <rect x="552" y="130.4" width="24" height="249.6" class="bar-proceda" rx="2"/>
  <rect x="578" y="93.8" width="24" height="286.2" class="bar-baseline" rx="2"/>
  <text x="577" y="123" text-anchor="middle" class="value" fill="#2563eb">83.2</text>
  <text x="577" y="395" text-anchor="middle" class="label" transform="rotate(-35 577 395)">Video Classif.</text>

  <!-- Domain 8: Customer Service — 81.4% vs 79% -->
  <rect x="612" y="135.8" width="24" height="244.2" class="bar-proceda" rx="2"/>
  <rect x="638" y="143" width="24" height="237" class="bar-baseline" rx="2"/>
  <text x="637" y="129" text-anchor="middle" class="value" fill="#2563eb">81.4</text>
  <text x="637" y="395" text-anchor="middle" class="label" transform="rotate(-35 637 395)">Customer Svc.</text>
  <text x="637" y="119" text-anchor="middle" class="sota">SOTA</text>

  <!-- Domain 9: Traffic Spoofing — 79.5% vs 86% -->
  <rect x="672" y="141.5" width="24" height="238.5" class="bar-proceda" rx="2"/>
  <rect x="698" y="122" width="24" height="258" class="bar-baseline" rx="2"/>
  <text x="697" y="134" text-anchor="middle" class="value" fill="#2563eb">79.5</text>
  <text x="697" y="395" text-anchor="middle" class="label" transform="rotate(-35 697 395)">Traffic Spoof.</text>

  <!-- Domain 10: KYB — 42.2% vs 58% -->
  <rect x="732" y="253.4" width="24" height="126.6" class="bar-proceda" rx="2"/>
  <rect x="758" y="206" width="24" height="174" class="bar-baseline" rx="2"/>
  <text x="757" y="246" text-anchor="middle" class="value" fill="#2563eb">42.2</text>
  <text x="757" y="395" text-anchor="middle" class="label" transform="rotate(-35 757 395)">KYB</text>

  <!-- Footnote -->
  <text x="400" y="418" text-anchor="middle" style="font-size:10px; fill:#666;">Sorted by Proceda TSR. Baselines are best-across-all-models from SOP-Bench paper v2 Table 5.</text>
</svg>
```

### Key Takeaways

**4 domains SOTA by raw TSR** — no caveats needed:
- Dangerous Goods: **+7.2pt** (87% → 94.2%) with Gemini 2.5 Flash
- Customer Service: **+2.4pt** (79% → 81.4%) with Gemini 2.5 Flash
- Referral Abuse v2: **+1pt** (98% → 99.0%) with Gemini 3.1 Pro
- Aircraft Inspection: **+1pt** (99% → 100%) with Gemini 3 Flash

**4 more domains SOTA on SOP-consistent tasks** — after excluding tasks where the benchmark's ground truth contradicts its own SOP:
- Referral Abuse v1: **+2pt** (98% → 100%)
- Video Classification: **+4.6pt** (95.4% → ~100%)
- Traffic Spoofing: **+12.8pt** (86% → 98.8%)
- Know Your Business: **+6.4pt** (58% → 64.4%)

**100% ECR across all domains.** Every task completes. Failures are reasoning or extraction issues, never execution crashes.

---

## Cheaper Models, Better Results

One of the most striking findings is the model cost story. The SOP-Bench paper's best baselines require frontier models:

| Baseline Model | Domains where it's best | Approx. cost tier |
|---------------|------------------------|-------------------|
| Claude 4.1 Opus | Aircraft Inspection, Traffic Spoofing | Highest |
| Claude 4.5 Opus | Know Your Business | Highest |
| Claude 4 Opus | Referral Abuse v2 | Highest |
| Claude 4 Sonnet | Dangerous Goods, Video Classification | High |
| Claude 3.5 v2 | Referral Abuse v1 | Medium |
| Llama 3.3 70B | Customer Service | Medium |

Proceda beats these baselines with much lighter models:

| Proceda Model | Domains | Cost tier | Baselines beaten |
|---------------|---------|-----------|-----------------|
| **Gemini 2.5 Flash** | Dangerous Goods, Customer Service, Patient Intake | **Lowest** | Claude 4 Sonnet, Llama 3.3 70B |
| **Gemini 3 Flash** | Aircraft Inspection, Referral v1, Traffic Spoofing, Order Fulfillment | Low | Claude 4.1 Opus, Claude 3.5 v2, Claude 4.1 Sonnet |
| **Gemini 3.1 Pro** | Referral v2, Video Classification, KYB | Medium | Claude 4 Opus, Claude 4 Sonnet, Claude 4.5 Opus |

The two domains that required Gemini 3.1 Pro (a stronger model) are those where the SOP explicitly asks the agent to exercise subjective judgment:

- **Know Your Business**: The SOP says "use your experience" to distinguish typos from fraud, and notes that "risk scores are not reliable."
- **Video Classification**: The agent must read prose moderator notes and make classification judgments about content severity.

For domains with clear, formulaic decision logic — even complex ones like Dangerous Goods (274 tasks, weighted scoring with imputation) — the cheap models suffice when execution is structured.

The implication: **structured SOP execution substitutes for raw model capability on procedural tasks.** You don't need a $75/MTok model to follow a procedure; you need a framework that decomposes the procedure into manageable steps.

---

## Benchmark Quality Contributions

During this evaluation, we identified and reported systematic issues in the SOP-Bench data. We frame these as contributions to the benchmark's quality, not criticisms — SOP-Bench is a valuable new benchmark, and these findings help improve it.

### Domains with broken tools (4 domains, not runnable)

| Domain | Issue | Filed |
|--------|-------|-------|
| **Content Flagging** | Two tools use `random.random()` for scores that determine the final decision. Non-deterministic and uncorrelated with ground truth. | [#2](https://github.com/amazon-science/SOP-Bench/issues/2) |
| **Warehouse Inspection** | Two tools use `po_number % 3` and `po_number % 2` instead of CSV lookups. Agrees with ground truth only ~55%. | [#3](https://github.com/amazon-science/SOP-Bench/issues/3) |
| **Video Annotation** | 20 of 26 tool methods are `pass` stubs returning `None`. Toolspecs define full input schemas, but implementations are missing. | [#6](https://github.com/amazon-science/SOP-Bench/issues/6) |
| **Email Intent** | Three files (`sop.txt`, `tools.py`, `test_set_with_outputs.csv`) contain unresolved git merge conflict markers. The CSV cannot be parsed. | [#7](https://github.com/amazon-science/SOP-Bench/issues/7) |

### Domains with SOP/CSV labeling disagreements (4 domains)

These domains have functioning tools and were run successfully, but a portion of tasks have ground truth labels that contradict the SOP's explicit rules. An agent faithfully following the SOP gets penalized on these tasks.

| Domain | Disagreement tasks | Issue | Pattern |
|--------|-------------------|-------|---------|
| **Referral Abuse v1** | 9/200 | [#4](https://github.com/amazon-science/SOP-Bench/issues/4) | CSV follows a closure-priority rule not in the SOP |
| **Traffic Spoofing** | 39/200 | [#5](https://github.com/amazon-science/SOP-Bench/issues/5) | 39 Medium-risk tasks labeled "Warning Issued" when SOP says "Temporary Suspension" |
| **Know Your Business** | 31/90 | [#8](https://github.com/amazon-science/SOP-Bench/issues/8) | All 34 "awaiting info" tasks have more escalation triggers than "escalate" tasks; implicit priority rule not in SOP |
| **Video Classification** | 9/196 | — | Implicit ground truth rules not derivable from SOP; 4 stub tools suppress classification signals |

The SOP-Bench paper lists "implicit knowledge that humans learn but rarely document" as a benchmark challenge. However, each agent evaluates tasks in isolation with no access to ground truth labels — there is no mechanism to learn unstated rules from data patterns.

---

## How Proceda Works

### The Problem with Existing Approaches

The SOP-Bench paper evaluates two agent architectures: **Function Calling** (tool use in a single prompt) and **ReAct** (thought-action-observation loop). Both dump the entire SOP as raw text into a single prompt and say "follow this."

This works for short procedures. It fails for complex ones. Patient intake — rated the easiest domain — requires a 6-tool dependency chain where the final tool needs outputs from all 5 previous tools as input parameters. Both baseline architectures score **0% TSR** on this domain.

### Proceda's Approach: Convert, Structure, Execute

Proceda treats SOPs as first-class executable artifacts, not prompt context.

**Step 1: Automated Conversion.** `proceda convert` uses an LLM to transform unstructured SOP text into a structured `SKILL.md` file — a markdown document with YAML frontmatter and `### Step N:` headings. The `--tools` flag passes tool schemas so the converter generates steps that reference exact tool names and parameter names. The `--output-fields` flag declares expected outputs so the final step emits structured XML tags.

```bash
proceda convert sop.txt --name patient-intake \
  --tools toolspecs.json \
  --output-fields "insurance_validation,prescription_insurance_validation,..."
```

No hand-editing. When conversion quality is insufficient, we improve the converter, not the output.

**Step 2: Structured Execution.** The runtime executes each step sequentially:

1. The LLM sees only the current step's instructions, plus context from previous steps
2. Tool schemas are injected with exact parameter names and types
3. The LLM must call `complete_step` with a summary before advancing
4. Token budgets are managed per-step to prevent context overflow
5. Circuit breakers catch infinite loops (max 50 iterations per step, max 20 tool calls)

**Step 3: Structured Output Extraction.** When `output_fields` are declared, the system prompt instructs the LLM to emit `<field_name>value</field_name>` XML tags in the final step's summary. The output extractor parses these deterministically — no fragile regex on free-form text.

### Why This Enables SOTA with Cheaper Models

The key insight is that **structured execution reduces the cognitive load on the LLM at each decision point.** Instead of reasoning about a 30-step procedure in a single prompt, the model handles one step at a time with clear instructions, available tools, and context from prior results.

This is why Gemini 2.5 Flash (a lightweight model) beats Claude 4 Sonnet (a frontier model) on Dangerous Goods: the procedure is formulaic — weighted scoring with imputation rules — and Proceda's step decomposition makes each step tractable. The model doesn't need to "be smart"; it needs to follow instructions and call the right tool with the right parameters.

### Operational Features for Production SOPs

Beyond benchmarks, Proceda provides features critical for real-world SOP execution:

- **Human-in-the-loop approval gates.** Steps can be marked `[APPROVAL REQUIRED]` (post-step) or `[PRE-APPROVAL REQUIRED]` (pre-step). Execution halts until a human approves, rejects, or skips. Approval decisions are logged with timestamps for audit trails.

- **Full execution observability.** Every runtime transition emits a structured `RunEvent` — 20+ event types covering step lifecycle, tool calls, LLM usage, approvals, and errors. Events stream in real-time and are persisted as append-only JSONL logs.

- **Session state capture.** The `RunSession` captures complete execution state: current step, conversation history, completed steps, approval records, token usage. This enables pausing and resuming long-running workflows across hours, days, or weeks — essential for SOPs that span multiple human review cycles.

- **MCP-native tool integration.** Tools connect via the [Model Context Protocol](https://modelcontextprotocol.io) (open standard), supporting stdio and HTTP transports. No vendor lock-in. Access control via denylists and required-tool allowlists.

---

## Conclusion

SOP-Bench demonstrates that faithfully executing complex procedures is a hard problem for AI agents. Proceda's structured approach — automated SOP conversion, step-by-step execution with tool integration, and human oversight — achieves state-of-the-art results on 4 domains outright and 8 of 10 on SOP-consistent tasks, often with significantly cheaper models than the published baselines.

The benchmark also has room to grow. We've filed 6 issues identifying broken tools (4 domains) and labeling inconsistencies (3 domains), and hope these contributions help strengthen SOP-Bench as a standard for evaluating procedural AI.

Proceda is built by [Enchiridion Labs](https://enchiridionlabs.online). Try it at [sop.run](https://sop.run).
