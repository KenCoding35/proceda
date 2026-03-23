# Bug Report: video_annotation — 20 of 26 tool implementations are `pass`-only stubs

## Summary

In the `video_annotation` domain, 20 of the 26 tool methods in `VideoProcessingManager` (`tools.py:29`) contain only `pass` and return `None`. The remaining 6 tools are properly implemented as CSV lookups and return correct data. The toolspecs (`toolspecs.json`) define complete input schemas for all 26 tools, so the issue is limited to the Python implementations.

When an agent calls a stub tool it receives `null` (serialized via `json.dumps(None)`), which is marked `success=True` by the tool manager (`src/amazon_sop_bench/tools/manager.py:141`). The agent does not crash or error — it simply loses information needed for downstream decisions.

## Details

### 6 implemented tools (CSV lookups, return correct data)

| Tool | What it returns |
|------|----------------|
| `validateVideoFormat` | format, resolution, frame_rate, bit_depth, channel_count, scene_type, weather, lighting_conditions, camera_position |
| `validateLidarData` | lidar_point_cloud_path, time_offset, object_distance, camera_intrinsics_available, lidar_transform_available |
| `performObjectDetection` | ground_truth_object, predicted_object, confidence_threshold, tracking_enabled, output paths |
| `executeSegmentation` | segmentation_type, predicted_iou, temporal_smoothing, output paths |
| `runAutomatedQC` | temporal_consistency_score, spatial_accuracy_score |
| `performHumanValidation` | inter_annotator_score, min_reviewers |

These 6 tools follow the pattern used in other well-functioning domains: load the CSV, filter by `video_id`, return precomputed columns as a dict.

### 20 stub tools (method body is `pass`, return `None`)

```
processHighResolution       validateOutputFormat        checkProcessingStatus
optimizeTrackingSettings    calibrateCameraSensors      synchronizeLidarTimestamp
generateDepthMap            validateWeatherConditions   optimizeFrameRate
enhanceLowLightFootage      trackObjectMotion           validateCameraIntrinsics
processNightTimeFootage     analyzeCameraStability      validateSceneContext
adjustBitDepth              validateChannelCount        validateTemporalConsistency
checkSpatialAccuracy        validateAnnotatorScores
```

The toolspecs for these 20 tools are fully populated — they have input parameters, required fields, descriptions, and type constraints. For example, `validateWeatherConditions` (`toolspecs.json:311`) requires `video_id` and `weather`; `validateTemporalConsistency` (`toolspecs.json:636`) requires `video_id` and `temporal_consistency_score`. The schemas look complete. Only the Python implementations are missing.

### Why these are bugs

The SOP-Bench paper (v2, 2026-02-23; [ar5iv](https://ar5iv.labs.arxiv.org/html/2506.08119)) explicitly says redundant tools are intentionally added to stress tool selection — that is a valid benchmark design choice. The bug is not that extra tools exist; the bug is that these tools are shipped as `pass`-only stubs that return `None` instead of meaningful data.

Evidence that the stubs are unfinished, not intentional:

1. **The paper promises stable, reproducible mocks**: "To simulate API calls, each dataset includes precomputed inputs and outputs for every tool call, stored as columns. These mocks replace live APIs to enable stable, reproducible evaluation without runtime variability." A `pass` body returning `None` is deterministic but semantically useless as a mock — it does not simulate an API call.

2. **`docs/ADDING_BENCHMARKS.md:115`** says tools must be "deterministic mock implementations that return consistent results for the same inputs," and the "Common Mistakes" section (`ADDING_BENCHMARKS.md:576`) shows `random.random()` as an anti-pattern. Every example tool returns a dict with real data. No example uses `pass`.

3. **The toolspecs are complete.** If the tools were meant to be non-functional distractors, there would be no reason to define input schemas with specific parameters, types, and required fields. The schemas describe tools that are meant to work.

4. **The 6 implemented tools follow a consistent pattern** (load CSV → filter by `video_id` → return columns). The stubs have docstrings describing the same kind of return values but never produce them.

### Impact on benchmark scores

The paper (v2) reports the following baselines for video_annotation (Claude 3.5 Sonnet v2):

| Agent | ECR | C-TSR | TSR |
|-------|-----|-------|-----|
| FC | 100% | 49% | 49% |
| ReAct | 70% | 99% | 69% |

(Source: SOP-Bench paper v2, Table 4; confirmed by `docs/AGENTS.md:319`.)

When an agent calls a stub tool, it receives `null`. The framework does not raise an error (`tools/manager.py:141` returns `success=True`), and both agents serialize the result as JSON null (`function_calling.py:280`, `react.py:377`). The failure mode is not a crash — it is missing information leading to bad branching and incorrect final decisions. The agent must either skip the step (losing data) or hallucinate a value.

The 99% C-TSR for ReAct shows that when agents complete execution, they almost always reach the correct `final status`. The 30% ECR gap for ReAct suggests that `None` returns disrupt the agent's ability to complete the workflow in many cases, though we cannot attribute this entirely to stubs without deeper trace analysis.

### Task count mismatch

`README.md:296` claims 168 tasks. The packaged data contains:

- `test_set_with_outputs.csv`: 125 rows
- `test_set_without_outputs.csv`: 42 rows
- Total: 167 (off by 1 from the README's claim of 168)

## Suggested Fix

Implement the 20 stub methods in `tools.py` using the same CSV-lookup pattern as the 6 working tools. The toolspecs already define the correct input schemas, so no changes to `toolspecs.json` are needed.

For each stub:
1. Accept the parameters defined in the existing toolspec
2. Look up the row in `test_set_with_outputs.csv` by `video_id`
3. Return a dict with relevant precomputed columns

For tools whose advertised outputs cannot be derived from existing CSV columns, new columns would need to be added to the CSV.

The task count in the README should also be reconciled (167 vs 168).

## Environment

- SOP-Bench commit: `156e9ecd60f42c43e4f3a12824e466afff21e9d8` (2026-02-22, initial release)
- Domain: `video_annotation`
- File affected: `src/amazon_sop_bench/benchmarks/data/video_annotation/tools.py`
- Paper: SOP-Bench v2 (2026-02-23), https://ar5iv.labs.arxiv.org/html/2506.08119
