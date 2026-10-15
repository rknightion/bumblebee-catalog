# Loop: bumblebee-catalog
tier: guarded
gate: just check
ci-required: ci-success
grafana-stack: none

Public repository: no host, endpoint, tenant or account identifier and no fleet inventory in any
tracked file or loop artifact. `just check` only proves the scripts parse, so a green gate says
almost nothing here: a lane reports which evidence level it reached (a local run diffed against a
real input, `just lint-workflows`, or a `workflow_dispatch` run). The failure this repo exists to
prevent is silent: a bad catalog makes Bumblebee exit 2 before scanning and no alert can fire.

## Credentials

- None held by the loop. Anything that mutates GitHub state (a `workflow_dispatch`, the
  `catalog-latest` release or its assets, any `gh` call that is not a read) is root-only.

## Traps

- The positive-match self-test (`ci/make_fixture.py` seeding, `ci/assert_finding.py` asserting a
  live scan emits a `finding`) must stay meaningful through any change to entry shape, id format,
  ecosystem naming or version handling; a self-test that would pass against an empty catalog is
  broken without failing.
- `ci/validate.py` checks one catalog; only `ci/assert_catalog_set.py` catches a set that cannot
  load together.
- The two catalog workflows publish to one release under separate concurrency groups, and each
  downloads the other's assets: a manual dispatch during a scheduled run (osv every 4h, extra daily
  at 05:30 UTC) can assert against a half-updated set. Check the Actions tab; never dispatch both.
- Generated catalogs, metas and workflow scratch directories are gitignored and never staged.
- The weekly keepalive empty commit is load-bearing: do not tidy it away.
- A branch-protection bypass message on a push is the expected mechanism, not an incident.

## Mutexes

- The `catalog-latest` release is a moving tag with live consumers: root only, one at a time.
- Upstream feeds (OSSF malicious-packages, the DataDog dataset, the GitHub Advisory Database) are
  rate-limited and read-only: clone once and share the checkout path.
- Single owner, one commit, both files: `CATALOG_SCHEMA_VERSION`, `BUMBLEBEE_SHA`,
  `BUMBLEBEE_RELEASE` (read by `ci/validate.py`). `ci/validate.py` and `README.md`'s consumer table
  move together. Never change `CATALOG_SCHEMA_VERSION` outside `BBC-0001`.
- `osv-catalog.yml` and `extra-catalogs.yml` share a deliberate shape: a change to the shape is one
  lane touching both.

## Lane brief

Local edits and dry-runs only. A decision the brief does not cover (a version, pin, schema value
or threshold) stops the lane and returns the question; never invent one.
