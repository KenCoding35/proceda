# SOP-Bench Video Classification

## Summary

We ran Proceda against the SOP-Bench video_classification benchmark — a 196-task
evaluation where LLM agents must classify user-generated video content through a
multi-tiered review system involving validation, reviewer assignment, content moderation,
escalation, and final decision-making.

This is a **judgment-heavy** domain with 4 of 10 tools returning `None` (stubs).
The LLM must synthesize signals from working tools and make subjective moderation
decisions. The stub tools remove corroborating signals that would help the LLM
make more confident escalation decisions.

## Results

| Metric | Gemini 3 Flash |
|--------|----------------|
| TSR | **83.2%** (163/196) |
| ECR | 100% |
| Failure rate | 16.8% |
| Avg time/task | ~25s |
| SKILL.md steps | 7 |
| Provider | OpenRouter |

**Best baseline (Table 5):** 95% (Claude 4 Opus FC)

## Tool Inventory

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

The 4 stub tools all relate to the final classification signals. Their absence means
the LLM loses corroborating evidence for escalation decisions, creating a systematic
bias toward leniency.

## Failure Analysis (33 real failures)

### Pattern 1: Remove expected from format anomalies (9 failures, 27%)

**Root cause: Benchmark design issue — no signal exists for the LLM.**

These tasks have `detected_categories=[]`, no moderator escalation, clean uploader
history — yet the ground truth says "Remove". The only distinguishing feature is a
non-standard format (AV1, RAW, `nan`, `m p4`) or extreme resolution (200x350).

The benchmark appears to encode an implicit rule ("unsupported format = Remove") that
is never communicated to the LLM. The SOP describes format validation but doesn't
state that unsupported formats should result in removal. The LLM reasonably concludes
"Allow" when it sees benign content metadata and no violations.

**These failures are likely unfixable** without changing the SKILL.md to add an explicit
format-based removal rule, which would be hand-tuning to the ground truth.

### Pattern 2: Age Restrict from low-confidence Nudity (9 failures, 27%)

**Root cause: Stub tools remove corroborating signals.**

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

**These failures would likely be fixed** if the stub tools returned real data. The
LLM's reasoning is sound — dismissing uncorroborated low-confidence flags is correct
behavior. The stubs create a false-negative signal.

### Pattern 3: Remove from high-confidence violations (13 failures, 39%)

**Root cause: Mixed — LLM under-escalation + stub tools.**

These tasks have high-confidence detections (0.88-0.98) for serious categories
(Nudity, Hate Speech, Misinformation, Illegal activities). The LLM correctly
escalates to a moderator and gets detailed notes from `implementModeration`, but
then chooses "Age Restrict" or "Warning" instead of "Remove".

The LLM has sufficient signal to determine "Remove" from the high confidence scores
and moderator notes alone. However, the stub tools removing age rating and content
warning signals contribute to the under-escalation by making the final review step
feel less severe.

**Approximately 60% LLM reasoning error, 40% stub tool contribution.** About 5-6 of
these might be fixed with working tools; the rest require the LLM to reason more
aggressively about escalation thresholds.

### Pattern 4: Age Restrict from violence (2 failures, 6%)

**Root cause: LLM reasoning error.**

Violence detected at 0.85+ confidence, but LLM says "Allow". Clear under-escalation
with sufficient signal available.

### Summary

| Pattern | Count | Root Cause | Fixable? |
|---------|-------|-----------|----------|
| Format anomaly → Remove | 9 | Benchmark design | No (implicit rule) |
| Low-conf Nudity → Age Restrict | 9 | Stub tools | Yes (with working tools) |
| High-conf violations → Remove | 13 | LLM + stub tools | Partially (~5-6) |
| Violence → Age Restrict | 2 | LLM reasoning | With prompt tuning |
| **Total** | **33** | | |

**Estimated TSR with working tools:** ~87-90% (fixing 9 stub-caused + 5-6 mixed-cause failures).
**Estimated ceiling:** ~91-95% (remaining 9 format-anomaly tasks are benchmark noise).

## Comparison with Baselines

| Agent | TSR |
|-------|-----|
| Claude 4 Opus FC | 95% |
| Claude 4.1 Opus ReAct | 93% |
| **Proceda (Gemini 3 Flash)** | **83.2%** |
| Gemini 2.5 Pro ReAct | 81% |
| Llama 3.3 70B FC | 79% |

Proceda's 83.2% with Gemini 3 Flash outperforms Gemini 2.5 Pro ReAct (81%) and
Llama 3.3 70B FC (79%) from the baselines. The gap to Claude 4 Opus (95%) is
attributable to a combination of stub tools, model capability differences, and the
format-anomaly ground truth issue.

## Configuration

- **Model:** `openrouter/google/gemini-3-flash-preview`, temperature=0.0
- **Provider:** OpenRouter (API key: `pass soprun/OPENROUTER_API_KEY`)
- **SKILL.md:** 7 steps (converted by `proceda convert --tools --output-fields`)
- **Workers:** 20 parallel (100 workers caused OpenRouter rate limiting)
- **Rate limiting note:** Initial run with 100 workers failed (195/196 tasks rate-limited).
  Re-run with 20 workers succeeded.

## Files

- `benchmarks/sop_bench/domains/video_classification/SKILL.md` — 7-step version
- `benchmarks/sop_bench/domains/video_classification/config.yaml` — OpenRouter Gemini 3 Flash config
