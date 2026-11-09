# bumblebee-catalog

## What this repo is

CI that assembles public threat-intelligence catalogs. The only output is a set of release assets on
the moving `catalog-latest` release, fetched by managed endpoints before every Bumblebee scan. No
binary, no service, no test suite, nothing that runs meaningfully on a laptop. `README.md` is the
consumer-facing contract - its asset table is what downstream reads.

**No secrets and no private data, ever - including in issues, pull request bodies and `.github/tracker/`.** No host names, endpoint names,
tenant or account identifiers, no fleet inventory. Write the shape, not the instance. Counts, timings
and structural findings are fine.

## Task interface

`just check` is the gate and must pass before you commit. It only proves the scripts parse (fmt
check, lint, a no-op test) - it does not run them or touch a catalog, so a green run here is a weak
claim; see "Verifying a change" below for what actually proves a change works. There is no `just ci`
recipe.

## Hard constraints

**Do not change `CATALOG_SCHEMA_VERSION`.** Endpoints point `--exposure-catalog` at a directory, and
Bumblebee's directory loader requires every catalog in it to declare the same `schema_version`. A
mismatch exits 2 before the scan starts - no packages, no findings, no `scan_summary`, so no alert
can fire. Detection is off while everything looks green. The safe ordering and the current state are
in the `ci/validate.py` docstring; `BBC-0001` is the only place the bump may happen.

**`BUMBLEBEE_SHA` and `BUMBLEBEE_RELEASE` do different jobs - never conflate them.** `BUMBLEBEE_SHA`
pins a `main` commit used only to build the `osvcatalog` generator. `BUMBLEBEE_RELEASE` pins the
released binary the fleet runs and is used for all acceptance validation. Validating against `main`
was the original gap: `main` accepts catalogs the deployed binary rejects, so CI goes green while
endpoints silently stop detecting. Both values live in `osv-catalog.yml` and `extra-catalogs.yml`;
changing one file only is drift.

**`ci/assert_catalog_set.py` is the only check that can catch a bad catalog set.** `ci/validate.py`
checks one file in isolation, and every file in an unloadable set is individually valid - only the
combination is illegal. Anything that adds a catalog or changes what one declares must keep the set
assertion meaningful.

**`force_publish` / `--force` discards the >10% entry-count floor**, the only guard against an
upstream feed regression publishing a gutted catalog to the whole fleet. Use it for a legitimate
large upstream change, never to turn a red run green before establishing why the count dropped.

**The weekly `keepalive` empty commit is load-bearing.** GitHub auto-disables scheduled workflows
after 60 days of repository inactivity and this repo can be quiet for months. It looks like junk in
`git log`; do not tidy it away.

Every `uses:` is pinned to a 40-character commit SHA with the version in a trailing comment.
`zizmor` fails the build otherwise.

## Verifying a change

`ci.yml` runs `just check` and nothing else. It proves the scripts parse. It does not run them, does
not touch a catalog, and will not fail for most things a change can break. **"The gate passed" is a
weak claim here.** Evidence, in rising order of strength:

1. run the changed script locally against a real input and diff the output;
2. `just lint-workflows` (actionlint + zizmor) for any workflow edit;
3. a `workflow_dispatch` run of the affected workflow - the only thing that proves the publish path
   still works end to end. Both catalog workflows publish to the same release under separate
   concurrency groups (`osv-catalog`, `extra-catalogs`), so check the Actions tab first and never
   dispatch both at once.

Say which level you actually reached.

## Commits

Conventional Commits (`type(scope): subject`), because Renovate parses it. Generated catalogs and
their metas are gitignored and never staged; stage explicit pathspecs.

## Tracking work

Work is tracked in this repository's GitHub issues; they are the only queue. Do not add a checklist
file such as `ROADMAP.md` beside them. Renovate's Dependency Dashboard is bot-owned: leave it alone.

- A pull request body says how it relates to an issue, on a line of its own: `Closes #N` with the
  `Acceptance evidence` table from `.github/pull_request_template.md` (one row for each acceptance
  criterion of that issue), `Refs #N` when it only relates to one, or `Task: none, <reason>`.
- A pull request that changes `.github/workflows/` or `.github/actions/` carries no closing keyword:
  write `Task: none, <reason>`, with `Refs #N` beside it if you like.
- Contributors never need the project board or the tracker tooling; a maintainer handles both.
- Issues and pull requests are public, so they carry no host, endpoint, tenant or account
  identifier and no fleet inventory. Write the shape, not the instance.
- Older commits and docs cite legacy board ids such as `BBC-0001`. `just issue <ID>` prints the
  issue each one became; `.github/tracker/id-map.json` is the map, and the retired board's document
  is kept under `.github/tracker/history/`.
