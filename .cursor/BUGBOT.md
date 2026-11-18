# Review Bumblebee catalog changes

## Software and operators

Managed endpoints consume the release assets listed in `README.md`. Follow the Python producers
and checks under `ci/`, then the OSV and supplemental workflows that assemble the published set.

## Invariants

The consumer loads every catalog as one set with a shared schema version. Preserve single-file
validation and `ci/assert_catalog_set.py` together. Use the released consumer binary for acceptance
and retain the separately pinned generator revision. Keep the positive-match fixture capable of
proving that a known synthetic entry becomes a real finding.

## Sensitive changes

Review changes to upstream feed handling, normalized identifiers, entry counts and release assets
for downstream scan failures. Keep the count floor meaningful, and require evidence of an upstream
change before using a force-publish path. Preserve the product schedules and weekly keepalive.
Use synthetic entries and aggregate evidence in public fixtures and notes.

## Checks already in CI

`just check` covers Justfile format and Python syntax. Focus review on catalog behavior, release
validation and integration gaps. Preserve the required `ci-success` and the pinned workflow checks.

## Verification

Run `just check </dev/null`. For producer changes, compare output on a controlled fixture and
verify the whole catalog set and the positive-match check against the released consumer. Use
`just lint-workflows` for workflow changes. Scheduled and manually dispatched publishing paths share
release assets, so coordinate any release-path verification through the maintainer.
