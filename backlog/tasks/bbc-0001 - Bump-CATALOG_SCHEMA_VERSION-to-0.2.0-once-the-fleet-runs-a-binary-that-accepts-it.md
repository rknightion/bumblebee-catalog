---
id: BBC-0001
title: >-
  Bump CATALOG_SCHEMA_VERSION to 0.2.0 once the fleet runs a binary that accepts
  it
status: In Progress
assignee: []
created_date: '2026-08-14 16:37'
labels:
  - blocked-external
  - catalog-schema
dependencies: []
references:
  - 'https://github.com/rknightion/bumblebee-catalog/blob/main/ci/validate.py'
documentation:
  - doc-0002
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The schema_version this repo publishes is deployment-coupled, not a free choice. Bumblebee's directory loader requires every catalog in the --exposure-catalog directory to declare the SAME schema_version; a mismatch exits 2 before the scan starts, emitting no packages, no findings and no scan_summary. Detection is off while every alert stays green, because there is nothing left to alert on.

State today: the deployed release accepts 0.1.0 only and hard-rejects 0.2.0. Bumblebee main accepts both and its bundled threat_intel catalogs are already bumped, but no release carries it. So this repo publishes 0.1.0.

BLOCKED ON TWO FACTS OUTSIDE THIS REPO, IN ORDER:
1. a Bumblebee release supporting 0.2.0 exists;
2. the deployment's pinned BUMBLEBEE_VERSION has been raised to it AND HAS ROLLED OUT.

Only then does this task become actionable. Bumping ahead of the rollout silently drops every catalog in this repo from every scan. Do not do it to 'stay current'.

The change itself is small and touches three surfaces that must move together: CATALOG_SCHEMA_VERSION in .github/workflows/osv-catalog.yml and .github/workflows/extra-catalogs.yml, BUMBLEBEE_RELEASE in both (the validation target must be the release that accepts the new schema), and the docstring in ci/validate.py plus the table in README.md, which both state the current coupling as fact.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A Bumblebee release accepting schema_version 0.2.0 exists, and the fleet's pinned BUMBLEBEE_VERSION has been confirmed rolled out to it — evidence recorded in the task before any edit
- [ ] #2 CATALOG_SCHEMA_VERSION and BUMBLEBEE_RELEASE updated in BOTH osv-catalog.yml and extra-catalogs.yml in one commit — neither file left on the old value
- [ ] #3 ci/validate.py docstring and the README schema_version section updated to state the new coupling; no sentence left claiming 0.1.0 is what the fleet accepts
- [ ] #4 A workflow_dispatch run of BOTH catalog workflows completed, with ci/assert_catalog_set.py passing against the new release binary — the only check that proves the real directory combination loads
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 python3 -m py_compile ci/*.py
- [ ] #2 actionlint (only if a .github/workflows file changed)
- [ ] #3 zizmor .github/workflows/ (only if a .github/workflows file changed)
<!-- DOD:END -->
