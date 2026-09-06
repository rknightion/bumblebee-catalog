# bumblebee-catalog

## What this repo is

CI that assembles public threat-intelligence catalogs. The only output is a set of release assets on
the moving `catalog-latest` release, fetched by managed endpoints before every Bumblebee scan. No
binary, no service, no test suite, nothing that runs meaningfully on a laptop. `README.md` is the
consumer-facing contract - its asset table is what downstream reads.

**No secrets and no private data, ever - including in `backlog/`.** No host names, endpoint names,
tenant or account identifiers, no fleet inventory. Write the shape, not the instance. Counts, timings
and structural findings are fine.

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

## Task tracking

Tasks are `BBC-NNNN`. GitHub Issues is not the queue - the tracker stays enabled for external
contributors and for Renovate's dependency dashboard, and anything arriving that way becomes a task.
`backlog/` is committed, so the no-private-data rule above applies to tasks and docs too; a tracker
feels private, which is exactly why this breaks by accident.

Read the **Agent fan-out protocol (canonical)** doc before designing a wave, and the **Wave operating
model** doc for this project's own rules (`backlog doc view <id> --plain`).

`Parked` is a real status, not a synonym for To Do: attempted, blocked, and left with a concrete
resume boundary. Do not build on decisions and do not use the MCP surface - decisions are half-built
upstream, so durable reference goes in docs and tasks stay the unit, and MCP is frozen upstream and
costs 10-50k tokens of permanent context against 1-2k for the CLI.

Backlog CLI traps, each of which loses data silently at exit 0:

- **Never `--notes`, `--plan` or `--final-summary` bare.** Each REPLACES its whole section, wiping
  another session's writes with no warning. Use `--append-notes`, `--append-plan`,
  `--append-final-summary`. A hook in the agent config denies the bare forms.
- **Never hand-edit task, draft, doc, decision or milestone markdown.** Section boundaries are
  HTML-comment markers; break one and the section is dropped silently - still in the file, invisible
  to the CLI, until the next write destroys it for real. There is no repair command; `backlog doctor`
  only fixes duplicate task IDs. `backlog/config.yml` is the one deliberate exemption, because
  list-valued keys cannot be set through `backlog config set`.
- **Never let two agents edit the same task.** The concurrent-edit fix covers the edit funnel but not
  reorder, draft saves, the TUI edit path, `doc update` or decision updates.
- **Finalize in one call**, so an interrupted run cannot leave finished work looking unfinished:
  `backlog task edit BBC-0001 --check-ac 1 --check-ac 2 -s Done`.
