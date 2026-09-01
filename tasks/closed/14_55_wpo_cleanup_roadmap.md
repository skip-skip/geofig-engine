# WP-O: Cleanup + ROADMAP + commit (reversal series)

**Status**: complete
**Phase**: 14.55
**Dependencies**: `14_55_wpi_reverse_flag_model.md`, `14_55_wpj_cartesian_normalize_range.md`, `14_55_wpk_cartesian_reverse_arrows.md`, `14_55_wpl_piper_template_reverse.md`, `14_55_wpm_tests.md`, `14_55_wpn_verify_render.md`

## Description

Close out the reversal work-package series: update the ROADMAP 14.55 entry
(strip the now-outdated "there is no `reverse` handedness flag" claim), move the
task files to `tasks/closed/`, and commit the uncommitted working-tree changes
plus the new code on the `mapping-refactor` branch.

## Changes

### `ROADMAP.md` — Phase 14.55 entry (lines ~227-267)

- Update the section to describe the new `x_reversed`/`y_reversed` fields, the
  always-normalized cartesian range, and the rule that arrows always point toward
  increasing data (so reversal flips arrows + tick labels together).
- Update the test count in the section header if the suite grew.

### `tasks/closed/`

- Move `14_55_wpi_reverse_flag_model.md` … `14_55_wpo_cleanup_roadmap.md` from
  `tasks/open/` to `tasks/closed/`, setting `**Status**: complete` on each.

### Commit

- On branch `mapping-refactor`, style `Phase 14.55 <desc>`.
- Include the uncommitted `piper.py` and `test_piper.py` changes **plus** the new
  reversal work (axis.py, renderer.py, task files, ROADMAP).

## Acceptance criteria

- [ ] ROADMAP 14.55 entry updated (reversal documented; stale "no reverse flag" claim removed)
- [ ] All reversal WPs in `tasks/closed/` with `**Status**: complete`
- [ ] `git status` shows a staged set matching the intended files
- [ ] Commit created on `mapping-refactor` with a `Phase 14.55` message; no secrets/stray files

## Files

- `ROADMAP.md`
- `tasks/open/` → `tasks/closed/`
- commit on `mapping-refactor`
