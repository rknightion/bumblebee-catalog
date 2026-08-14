---
id: BBC-0002
title: >-
  Include the agent-skill ecosystem in datadog-malicious.json once it is in the
  published catalog schema enum
status: To Do
assignee: []
created_date: '2026-08-14 16:37'
labels:
  - blocked-external
  - coverage
dependencies: []
references:
  - >-
    https://github.com/rknightion/bumblebee-catalog/blob/main/ci/datadog_catalog.py
documentation:
  - doc-0002
ordinal: 2000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The DataDog malicious-software-packages-dataset ships an ai-skills sample set that ci/datadog_catalog.py already maps to Bumblebee's name-only agent-skill ecosystem (FOLDER_TO_ECOSYSTEM, NAME_ONLY). It is omitted from the published catalog by default: --ecosystems defaults to npm,pypi,editor-extension.

The omission is deliberate, not an oversight. The scanner already matches agent-skill at runtime, but agent-skill is not yet in the enum of the published exposure-catalog.schema.json. Emitting entries for an ecosystem the published schema does not list makes the catalog fail schema validation for anyone validating against it, and this repo's whole contract is that its assets load cleanly in the directory the fleet assembles.

BLOCKED ON: agent-skill being added to the published exposure-catalog.schema.json ecosystem enum upstream.

Once unblocked, including it is one flag on one invocation in .github/workflows/extra-catalogs.yml (pass --ecosystems npm,pypi,editor-extension,agent-skill to ci/datadog_catalog.py) plus the doc updates. Note agent-skill is in NAME_ONLY, so its null / all-versions-malicious records are KEPT rather than dropped — the opposite of the exact-match ecosystems — which means the entry count will jump, and the >10% floor in ci/validate.py compares against the last-good catalog in the other direction only, so a large increase will not trip it.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 agent-skill confirmed present in the published exposure-catalog.schema.json ecosystem enum, with the source and date recorded in the task
- [ ] #2 extra-catalogs.yml passes --ecosystems npm,pypi,editor-extension,agent-skill to ci/datadog_catalog.py
- [ ] #3 README.md's additional-catalogs section no longer says agent-skill is omitted, and the --ecosystems help text in ci/datadog_catalog.py is updated to match
- [ ] #4 A workflow_dispatch run of extra-catalogs completed: ci/assert_catalog_set.py passes and the positive-match self-test still emits a finding with the larger catalog
- [ ] #5 The new entry count and per-ecosystem breakdown recorded in the task, so a later unexplained drop has a baseline to compare against
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 python3 -m py_compile ci/*.py
- [ ] #2 actionlint (only if a .github/workflows file changed)
- [ ] #3 zizmor .github/workflows/ (only if a .github/workflows file changed)
<!-- DOD:END -->
