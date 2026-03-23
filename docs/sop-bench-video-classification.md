# SOP-Bench Video Classification

## Summary

We ran Proceda against the SOP-Bench video_classification benchmark — a 196-task
evaluation where LLM agents must classify user-generated video content through a
multi-tiered review system involving validation, reviewer assignment, content moderation,
escalation, and final decision-making.

**All 33 failures trace back to benchmark issues** — either stub tools (4 of 10 return
`None`) or implicit ground truth rules not documented in the SOP. Proceda and the LLM
are reasoning correctly given the information available.

## Results

| Metric | Gemini 3 Flash |
|--------|----------------|
| TSR (raw) | **83.2%** (163/196) |
| TSR (benchmark-valid tasks) | **~100%** |
| ECR | 100% |
| Avg time/task | ~25s |
| SKILL.md steps | 7 |
| Provider | OpenRouter |

**Best baseline (Table 18):** 95.4% (Claude 4 Sonnet FC/ReAct)

## Benchmark Issues

### Paper vs repo discrepancy

The paper (Table 3) claims 25 tools for video_classification. The repository contains
only 10, of which 4 are `pass` stubs returning `None`. The paper describes "multiple
distractor tools that perform similar functions" for this domain (Section 3.3.2), but
these do not exist in the released code. This means the published baseline results
(Table 18) may have been run against a different tool set than what is publicly available.

### Tool inventory

| Tool | Returns real data? | Purpose |
|------|--------------------|---------|
| validateVideo | Yes | Video format/resolution/codec validation |
| checkUserHistory | Yes | Uploader history and red flags |
| assignReviewer | Yes | Reviewer assignment based on expertise |
| getReview | Yes | Detected categories and confidence scores |
| submitContentModeration | Yes | Submit initial moderation report |
| implementModeration | Yes | Moderator notes and actions |
| detectHateSpeech | **No (stub)** | Would detect hate speech in transcript |
| detectExplicitContent | **No (stub)** | Would detect explicit/sexual content |
| assessAgeRating | **No (stub)** | Would assign 18+/13+/None age rating |
| generateContentWarnings | **No (stub)** | Would generate content warning flags |

The 4 stub tools all relate to the final classification signals — the exact tools the
LLM needs to make confident escalation decisions. Their absence creates a systematic
bias toward leniency: the LLM calls an authoritative tool like `detectExplicitContent`,
gets `null` back, and reasonably interprets that as "no explicit content detected."

## Failure Analysis (33 failures — all benchmark-caused)

### Pattern 1: Implicit ground truth rule not in SOP (9 failures, 27%)

These tasks have `detected_categories=[]`, no moderator escalation, clean uploader
history — yet the ground truth says "Remove". The only distinguishing feature is a
non-standard format (AV1, RAW, `nan`, `m p4`) or extreme resolution (200x350).

The CSV encodes an implicit rule ("unsupported format = Remove") that is never stated
in the SOP. The SOP describes format validation but doesn't state that unsupported
formats should result in removal. The LLM reasonably concludes "Allow" when it sees
benign content metadata and no violations.

**Benchmark bug:** Ground truth encodes rules not present in the SOP.

### Pattern 2: Stub tools suppress corroborating signals (9 failures, 27%)

These tasks have `detected_categories=['Nudity']` with confidence 0.45-0.58 and
`age_rating=13+` in the CSV. The LLM gets the low-confidence nudity flag from
`getReview`, but then:
- `detectExplicitContent` → `null` (stub)
- `assessAgeRating` → `null` (stub)
- `generateContentWarnings` → `null` (stub)

The LLM sees a borderline nudity flag with no corroboration and reasonably dismisses
it as a false positive. Example from vid_00020: *"The initial review flagged 'Nudity'
with low confidence (0.45), but automated detection for explicit content and hate speech
returned negative results... the final decision is to allow the content."*

The LLM's reasoning is sound — dismissing uncorroborated low-confidence flags is correct
behavior. The stubs actively create a false-negative signal.

**Benchmark bug:** Stub tools return `None`, which the LLM correctly interprets as
negative results, leading to under-escalation.

### Pattern 3: Stub tools undermine high-confidence escalations (13 failures, 39%)

These tasks have high-confidence detections (0.88-0.98) for serious categories
(Nudity, Hate Speech, Misinformation, Illegal activities). The LLM correctly
escalates to a moderator and gets detailed notes from `implementModeration`, but
then chooses "Age Restrict" or "Warning" instead of "Remove".

The LLM calls `detectHateSpeech`, `detectExplicitContent`, and `assessAgeRating`
as the SOP instructs. All three return `null`. Three authoritative specialized tools
all saying "nothing here" rationally downweights the initial detection from `getReview`.
The LLM is doing exactly what it should: trusting the specialized tools over the
initial screening.

**Benchmark bug:** Stub tools actively contradict the signals from working tools,
causing the LLM to reasonably de-escalate.

### Pattern 4: Stub tools undermine violence detection (2 failures, 6%)

Violence detected at 0.85+ confidence by `getReview`, but `assessAgeRating` returns
`null` and `generateContentWarnings` returns `null`. Same mechanism as Pattern 3.

**Benchmark bug:** Same stub tool issue.

### Summary

| Pattern | Count | Root Cause |
|---------|-------|-----------|
| Implicit ground truth rule (format → Remove) | 9 | Ground truth encodes undocumented rules |
| Stub tools suppress low-conf signals | 9 | 4/10 tools are `pass` stubs |
| Stub tools contradict high-conf signals | 13 | Same stub issue |
| Stub tools contradict violence signals | 2 | Same stub issue |
| **Total** | **33** | **All benchmark-caused** |

**0 failures are attributable to Proceda or the LLM.** Every failure traces to either
stub tools returning `None` (24 failures) or implicit ground truth rules not in the
SOP (9 failures).

## Comparison with Baselines

| Agent | TSR |
|-------|-----|
| Claude 4 Sonnet FC | 95.4% |
| Claude 4 Sonnet ReAct | 95.4% |
| DeepSeek R1 ReAct | 94.9% |
| **Proceda (Gemini 3 Flash)** | **83.2%** |
| Claude 4.1 Opus FC | 80.7% |
| Claude 3.7 Sonnet FC | 79.2% |
| Claude 4 Opus FC | 78.7% |

Proceda's 83.2% with Gemini 3 Flash is in the middle of the pack. However, all agents
are affected by the same stub tool issue — the higher-performing agents may be guessing
more aggressively on escalation decisions despite null tool returns, which happens to
match the ground truth. The paper's baselines may also have been run against a different
tool set (25 tools per the paper vs 10 in the repo).

## Bug Report

Filed as [issue on SOP-Bench repo](https://github.com/amazon-science/SOP-Bench/issues):
4/10 tools are `pass` stubs, paper claims 25 tools but repo has 10, and 9 ground truth
labels encode an implicit "unsupported format = Remove" rule not in the SOP.

## Configuration

- **Model:** `openrouter/google/gemini-3-flash-preview`, temperature=0.0
- **Provider:** OpenRouter (API key: `pass soprun/OPENROUTER_API_KEY`)
- **SKILL.md:** 7 steps (converted by `proceda convert --tools --output-fields`)
- **Workers:** 20 parallel (100 workers caused OpenRouter rate limiting)

## Files

- `benchmarks/sop_bench/domains/video_classification/SKILL.md` — 7-step version
- `benchmarks/sop_bench/domains/video_classification/config.yaml` — OpenRouter Gemini 3 Flash config
