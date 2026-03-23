# Bug Report: video_annotation — 20 of 26 tools are unimplemented stubs returning None

## Summary

The `video_annotation` domain has 26 tools defined in `toolspecs.json` and `tools.py`, but only 6 are implemented. The remaining 20 methods contain only `pass` (returning `None`), and their corresponding toolspecs define zero input parameters. An agent that calls any of these 20 tools receives `None`, losing information required by the SOP to reach a correct `final status` decision.

## Details

### 6 implemented tools (read from CSV, return correct data)

| Tool | What it returns |
|------|----------------|
| `validateVideoFormat` | format, resolution, frame_rate, bit_depth, channel_count, scene_type, weather, lighting_conditions, camera_position |
| `validateLidarData` | lidar_point_cloud_path, time_offset, object_distance, camera_intrinsics_available, lidar_transform_available |
| `performObjectDetection` | ground_truth_object, predicted_object, confidence_threshold, tracking_enabled, output paths |
| `executeSegmentation` | segmentation_type, predicted_iou, temporal_smoothing, output paths |
| `runAutomatedQC` | temporal_consistency_score, spatial_accuracy_score |
| `performHumanValidation` | inter_annotator_score, min_reviewers |

These 6 tools follow the pattern used in other well-functioning domains: they look up the `video_id` in the CSV and return the precomputed columns. They are correct and deterministic.

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

All 20 stubs also have **zero input parameters** in `toolspecs.json` — their `inputSchema.properties` is an empty object `{}` with no `required` array. This means the toolspecs were never completed either, not just the Python implementations.

For example, `validateWeatherConditions`:

```json
{
  "toolSpec": {
    "name": "validateWeatherConditions",
    "description": "Validates weather conditions for video suitability under specific environmental criteria.",
    "inputSchema": {
      "json": {
        "type": "object",
        "properties": {},
        "required": []
      }
    }
  }
}
```

### Why these are bugs, not intentional design

1. **The paper explicitly promises stable, reproducible mocks**: "To simulate API calls, each dataset includes precomputed inputs and outputs for every tool call, stored as columns. These mocks replace live APIs to enable stable, reproducible evaluation without runtime variability."

2. **The benchmark's own `ADDING_BENCHMARKS.md` guide** lists non-deterministic tools as a "Common Mistake" to avoid, and specifies that tools should be deterministic, returning data from lookups. Stub tools returning `None` are less deterministic than even the `random.random()` case in `content_flagging` — at least that returns a number.

3. **The `ADDING_BENCHMARKS.md` guide** shows every example tool returning a dictionary with meaningful data. No example shows a `pass`-only stub.

4. **These are clearly unfinished placeholders.** The implemented tools follow a consistent pattern (load CSV, filter by video_id, return columns). The stubs follow no pattern — they have docstrings describing expected behavior and return types that are never produced.

5. **The toolspecs have empty parameter schemas.** Tools like `validateWeatherConditions` and `analyzeCameraStability` clearly need a `video_id` parameter to look up the relevant row, but their schemas define zero parameters. This is a second layer of incompleteness beyond the `pass` bodies.

### Impact on benchmark scores

The SOP references several stub tools by name or by implied functionality:

- Section 5.1 mentions "Environmental constraints mandate urban setting contexts with daylight illumination conditions and front-camera positioning." Tools like `validateWeatherConditions`, `validateSceneContext`, and `analyzeCameraStability` are presumably meant to provide this validation, but return `None`.
- Section 5.3 mentions automated QC computing `spatial_accuracy_score` and `temporal_consistency_score`. While `runAutomatedQC` is implemented, `checkSpatialAccuracy` and `validateTemporalConsistency` (which sound like they should provide the same data) are stubs.
- Section 7.1 references bit depth and channel count validation. `adjustBitDepth` and `validateChannelCount` are stubs.

An agent following the SOP will call these tools, receive `None`, and must either:
- **Hallucinate values** (wrong, but might accidentally match)
- **Skip the step** (loses information needed for downstream decisions)
- **Crash or stall** (the 30% ECR failure rate in the paper suggests this happens frequently)

The paper's baseline results for video_annotation:

| Agent | Model | TSR | ECR | C-TSR |
|-------|-------|-----|-----|-------|
| ReAct | Claude 3.5 v2 | 58% | 70% | 99% |
| FC | Claude 3.5 v2 | 49% | 49% | 99% |

The 99% C-TSR (conditional on execution completing) shows that when the agent manages to get through the pipeline without crashing on `None` returns, it almost always gets the right answer. The bottleneck is the 30-51% execution failure rate, which is directly attributable to stub tools.

### Task count mismatch

The README claims 168 tasks for video_annotation. The CSV (`test_set_with_outputs.csv`) contains 125 rows.

### Comparison with other domains

For reference, the other 13 domains have:
- **0 stub tools**: patient_intake, dangerous_goods, customer_service, referral_abuse_v1, referral_abuse_v2, traffic_spoofing_detection, aircraft_inspection, know_your_business, order_fulfillment, email_intent
- **0 stub tools but broken mock logic**: warehouse_package_inspection (hardcoded `po_number % 3`), content_flagging (`random.random()`)
- **5 stub tools**: video_classification (5/11 stubs, but implemented tools have correct CSV lookups)

video_annotation is the most severely affected domain, with 77% of its tools (20/26) being stubs.

## Suggested Fix

Implement the 20 stub tools using the same CSV-lookup pattern as the 6 working tools. Each stub should:

1. Accept `video_id` (and any other relevant parameters) as input — update `toolspecs.json` accordingly
2. Look up the row in `test_set_with_outputs.csv` by `video_id`
3. Return the relevant precomputed columns

For tools whose output columns don't exist in the CSV (e.g., `validateWeatherConditions` might need a `weather_valid` column), the tool should either:
- Return the raw data from existing columns and let the agent apply the SOP logic, or
- Have the expected output added as a new column to the CSV

The CSV task count should also be reconciled with the README's claim of 168 tasks.

## Environment

- SOP-Bench commit: latest as of 2026-03-22
- Domain: `video_annotation`
- Files affected: `tools.py`, `toolspecs.json`
