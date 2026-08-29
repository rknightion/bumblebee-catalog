---
id: BBC-0004
title: Decide how to handle GitHub scheduled-workflow drift on the catalog crons
status: To Do
assignee: []
created_date: '2026-08-29 12:35'
labels: []
dependencies: []
priority: medium
type: chore
ordinal: 4000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
GitHub deprioritises `schedule` triggers under load, and both catalog workflows are drifting far enough that their documented cadence is no longer what endpoints actually receive. This was found while diagnosing a BumblebeeCatalogStale page; the alert thresholds have since been widened to absorb the drift, so this task is about whether the underlying publish cadence should be made reliable rather than merely tolerated.

Observed on 2026-08-29 via `gh run list`:

- `osv-catalog.yml` declares `cron: '0 */4 * * *'` (nominal 4h). Real gaps skip whole slots -- 2026-08-28T03:59Z to 2026-08-28T16:30Z is 12.5h against a nominal 4h.
- `extra-catalogs.yml` declares `cron: '30 5 * * *'` (nominal 24h). Real gaps of 25h, 19h and 18h, with fire times wandering from 05:5x to 17:30.

Why it matters: endpoints refresh their local copy before each scan, so publish cadence is the ceiling on catalog freshness fleet-wide. A skipped slot is not visible anywhere except the age metric -- scans keep succeeding and keep reporting clean against an older catalog, which is the blind-detector failure mode the staleness alerts exist to catch. The alert thresholds (30h all-source, 18h OSV-only) currently absorb the observed drift, so drift getting worse is silent until it crosses those.

Options to weigh, no decision made yet:

1. Accept the drift and treat the alert thresholds as the real contract. Zero work; documents the true guarantee rather than the nominal one.
2. Add a second, offset schedule entry to each workflow so a skipped slot has a nearby retry. Cheap, stays on GitHub-hosted runners, but doubles nominal runs and GitHub may deprioritise both together.
3. Trigger from something that is not GitHub's scheduler (an external cron calling `workflow_dispatch`, or a self-hosted runner). Reliable, but adds an external dependency and a credential, and `rknightion` is a User account so it has no runner groups or org-level Actions policy -- see the github-actions-oss rule.

Constraints that must hold whichever way this goes: the two workflows publish to the same `catalog-latest` release under separate concurrency groups, so they must never be dispatched concurrently. `BUMBLEBEE_SHA` and `BUMBLEBEE_RELEASE` live in both files and must stay in step. Do not touch `CATALOG_SCHEMA_VERSION`.

References:
- `.github/workflows/extra-catalogs.yml` header comment records the cron-to-alert-threshold coupling.
- Grafana rules `bumblebee-catalog-stale` (>30h, all sources) and `bumblebee-osv-catalog-stale` (>18h, catalog_age_by_source.osv) in folder `bumblebee-alerts`.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Measured real inter-run gaps for both catalog workflows over at least 30 days and recorded the distribution in this task, not just the worst case
- [ ] #2 Chose one of the three options with the reason written down, so the decision is not re-litigated later
- [ ] #3 If the cadence changed, the alert thresholds and the coupling comment in extra-catalogs.yml were updated in the same change
- [ ] #4 If the cadence did not change, the workflow header comments state the real observed cadence rather than the nominal cron
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 python3 -m py_compile ci/*.py
- [ ] #2 actionlint (only if a .github/workflows file changed)
- [ ] #3 zizmor .github/workflows/ (only if a .github/workflows file changed)
<!-- DOD:END -->
