# Bug Report: email_intent — unresolved git merge conflicts in 3 files

## Summary

The `email_intent` domain ships with unresolved git merge conflicts in three files: `sop.txt`, `tools.py`, and `test_set_with_outputs.csv`. The conflict markers (`<<<<<<< Updated upstream`, `=======`, `>>>>>>> Stashed changes`) are present in the committed code at `156e9ecd`. The domain cannot be loaded or executed as-is.

## Affected Files

### `test_set_with_outputs.csv` — 1 conflict

The very first line of the CSV is `<<<<<<< Updated upstream`. Pandas loads it as a single-column DataFrame with 195 rows under the column name `<<<<<<< Updated upstream` — no actual data is parsed.

The two versions embedded in the conflict:

- **"Updated upstream"** (lines 2–7): 5 data rows, 21 columns including `seller_id`, `seller_tier`, `account_status`, `intent_confidence_score`, `product_match_confidence`, `pricing_variance_percentage`, etc. Appears to be a prototype with a more complex evaluation schema.
- **"Stashed changes"** (lines 9–195): 186 data rows, 10 columns: `email_id`, `email_body`, `product_id`, `product_description`, `listing_price`, `seller_intent`, `listing_status_details`, `action`, `product_inventory`, `marketplace_id`. Balanced distribution across 4 intent categories (~46 each).

The benchmark loader (`src/amazon_sop_bench/benchmarks/registry.py:192`) would pick up this file but cannot parse it.

### `sop.txt` — 1 conflict (lines 2–180)

The entire SOP is wrapped in a single conflict. The two versions describe the same domain (seller email classification) but with different complexity:

- **"Updated upstream"**: Elaborate multi-dimensional scoring framework (ICS, PMC, PVT, ISI, RPL, CVS), escalation triggers, 116 lines.
- **"Stashed changes"**: Simpler procedure — classify intent into 4 categories, call the relevant tool, determine action. 63 lines.

### `tools.py` — 9 conflicts (lines 352–490)

All 9 conflicts are in the test/validation section at the bottom of the file (after the tool class definition). They differ on parameter names between the two versions — for example, `marketplace_id=""` vs `email_id=""` as the second parameter to `get_product_price`. The tool class itself appears to be conflict-free.

## Impact

The domain is unusable:
- The CSV cannot be parsed by pandas (or any CSV reader) due to conflict markers on line 1.
- The SOP contains two contradictory procedures — an agent would see both versions plus the conflict markers.
- `tools.py` has syntax errors from the conflict markers (though only in the test section, not the class definition).

The `metadata.json` and `toolspecs.json` files are conflict-free.

## Notes

- The README claims 195 tasks. The "Stashed changes" version of the CSV has 186 data rows. The "Updated upstream" version has 5. Neither matches 195.
- The best published baseline is 99% TSR (paper v2, Table 5), but it's unclear which version of the data that was evaluated against — neither version in the committed file can be loaded without manually resolving the conflict.
- The domain would likely be straightforward to evaluate if the conflicts were resolved. The "Stashed changes" version appears to be the more complete dataset (186 tasks, balanced categories, matching the simpler SOP).

## Suggested Fix

Resolve the merge conflicts in all three files. Based on the data completeness, the "Stashed changes" version appears to be the intended one, but the authors would need to confirm.

## Environment

- SOP-Bench commit: `156e9ecd60f42c43e4f3a12824e466afff21e9d8` (2026-02-22, initial release)
- Domain: `email_intent`
- Files affected: `sop.txt`, `tools.py`, `test_set_with_outputs.csv`
