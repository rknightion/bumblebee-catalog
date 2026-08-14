# bumblebee-catalog — contributor and agent instructions

Read this before changing anything. `CLAUDE.md` imports this file, so Claude Code and Codex read the
same contract and cannot drift apart.

## What this repo is

Nine GitHub Actions workflows and six Python scripts. Their only output is a set of **release assets
on the moving `catalog-latest` release**, fetched by managed endpoints before every Bumblebee scan.
No binary, no service, no test suite, nothing that runs meaningfully on a laptop. `README.md` is the
consumer-facing contract — the asset table there is what downstream reads.

Public threat-intelligence data and the CI to assemble it. **No secrets, no private data, ever** —
including in `backlog/`. No host names, endpoint names, tenant or account identifiers, no fleet
inventory. Write the shape, not the instance. Counts, timings and structural findings are fine.

## Hard constraints

**Do not change `CATALOG_SCHEMA_VERSION`.** It is a deployment-coupled decision, not a free one:
Bumblebee's directory loader requires every catalog in the `--exposure-catalog` directory to declare
the same `schema_version`, and a mismatch **exits 2 before the scan starts** — no packages, no
findings, no `scan_summary`, so no alert can fire. Detection is off while everything looks green.
The safe ordering and the current state are in the `ci/validate.py` docstring and in `README.md`;
`BBC-0001` is the only place the bump may happen.

**`BUMBLEBEE_SHA` and `BUMBLEBEE_RELEASE` do different jobs — never conflate them.** `BUMBLEBEE_SHA`
pins a `main` commit used *only* to build the `osvcatalog` generator (which postdates the `v0.1.1`
tag). `BUMBLEBEE_RELEASE` pins the released binary the fleet runs and is used for **all acceptance
validation**. Validating against `main` was the original gap: `main` accepts catalogs the deployed
binary rejects, so CI went green while endpoints would have silently stopped detecting. Both values
live in `osv-catalog.yml` *and* `extra-catalogs.yml`; changing one file only is drift.

**`ci/assert_catalog_set.py` is the only check that can catch a bad catalog set.** `ci/validate.py`
checks one file in isolation, and every file in an unloadable set is individually valid — only the
*combination* is illegal. Anything that adds a catalog or changes what one declares must keep the
set assertion meaningful.

**`force_publish` / `--force` discards the >10% entry-count floor**, which is the only guard against
an upstream feed regression publishing a gutted catalog to the whole fleet. Use it for a legitimate
large upstream change, never to turn a red run green before establishing why the count dropped.

**The weekly `keepalive` empty commit is load-bearing.** GitHub auto-disables scheduled workflows
after 60 days of repository inactivity and this repo can be quiet for months. It looks like junk in
`git log`; do not tidy it away.

**Every `uses:` is pinned to a 40-character commit SHA** with the version in a trailing comment.
Renovate keeps them current, `zizmor` fails the build otherwise.

## Verifying a change

`ci.yml` runs `python3 -m py_compile ci/*.py` and nothing else. It proves the scripts parse. It does
not run them, does not touch a catalog, and will not fail for most things a change can break. **"The
gate passed" is a weak claim here.** Evidence, in rising order of strength:

1. run the changed script locally against a real input and diff the output;
2. `actionlint` and `zizmor .github/workflows/` for any workflow edit;
3. a `workflow_dispatch` run of the affected workflow — the only thing that proves the publish path
   still works end to end. Both catalog workflows publish to the same release under *separate*
   concurrency groups, so check the Actions tab first and never dispatch both at once.

Say which level you actually reached.

## Commits

Work lands on `main` — no PR flow for this repo's own changes (Renovate's PRs are separate). One
commit per change, Conventional Commits (`type(scope): subject`), because Renovate parses it. A push
reporting bypassed branch-protection rules is the expected mechanism here, not an incident. Generated
catalogs and their metas are gitignored and never staged; stage explicit pathspecs rather than
`git add -A`.

## Task tracking — Backlog.md

Open work lives in `backlog/`, driven **only** through the `backlog` CLI. `backlog task list --plain`
is the queue; `backlog doc list --plain` lists the durable docs. GitHub Issues was never used for
this repo's own work and is not the queue — the tracker stays enabled for external contributors and
for Renovate's dependency dashboard, and anything arriving that way becomes a `BBC-NNNN` task.

Read the **Agent fan-out protocol (canonical)** doc before designing a wave, and the **Wave operating
model** doc for this project's own rules. Docs load on demand via `backlog doc view <id> --plain`, so
neither costs context until something reads it. The protocol is harness-neutral — it routes lanes by
**role**, and its Appendix A (Codex) or Appendix B (Claude Code) resolves a role into a concrete
model and reasoning depth. Name the harness in the run contract and resolve every lane from that
profile.

- **`backlog/` is committed, so no real identifiers in tasks or docs** — same rule as the repo's own
  no-private-data contract above. A tracker *feels* private, which is exactly why this breaks by
  accident.
- **Never use `--notes` or `--plan` bare** — they *silently replace* the whole section, destroying
  another session's writes with no warning and exit 0. Use `--append-notes` and `--append-plan`.
  `.claude/hooks/backlog-guard.py` denies the bare forms rather than trusting anyone to remember.
- **Finalize in one call**, so an interrupted run cannot leave finished work looking unfinished:
  `backlog task edit BBC-0001 --check-ac 1 --check-ac 2 -s Done`. Checking criteria at one step and
  setting status several steps later leaves the task inconsistent if anything interrupts between.
- **Never hand-edit task, draft, doc, decision or milestone markdown.** Section boundaries are
  HTML-comment markers; break one and the section is *silently dropped* at exit 0 — the data is still
  in the file but invisible, until the next write destroys it for real. There is no repair command;
  `backlog doctor` only fixes duplicate task IDs. `backlog/config.yml` is the one file edited by
  hand, because list-valued keys cannot be set through `backlog config set`.
- **Never let two agents edit the same task.** The v1.50 concurrency fix covers the edit funnel but
  *not* reorder, draft saves, the TUI edit path, `doc update` or decision updates.
- **`Parked` is a real status**, not a synonym for To Do: attempted, blocked, and left with a concrete
  resume boundary. Both current tasks are blocked on facts outside this repo, so `Parked` is a normal
  terminal state here.
- **Do not build on decisions, and do not use the MCP surface.** Decisions are half-built upstream —
  no `edit`, `view` or `update`, no supersede mechanism, no validation — so durable reference goes in
  **docs** and tasks stay the unit. MCP is frozen upstream and costs 10-50k tokens of permanent
  context against 1-2k for the CLI.

<!-- BACKLOG.MD GUIDELINES START -->
<!-- backlog.md-instructions-version: 1.50.1 -->
<CRITICAL_INSTRUCTION>

## Backlog.md Workflow

This project uses Backlog.md for task and project management.

**For every user request in this project, run `backlog instructions overview` before answering or taking action.**

Use the overview to decide whether to search, read, create, or update Backlog tasks.

Before task lifecycle actions, read the matching detailed guide:
- `backlog instructions task-creation` before creating or splitting tasks
- `backlog instructions task-execution` before planning, changing status or assignee, adding a plan or implementation notes, or implementing task work
- `backlog instructions task-finalization` before checking acceptance criteria, writing final summaries, or moving tasks to terminal statuses

Use `backlog <command> --help` before running unfamiliar commands. Help shows options, fields, and examples.

Do not edit Backlog task, draft, document, decision, or milestone markdown files directly. Use the `backlog` CLI so metadata, relationships, and history stay consistent.

</CRITICAL_INSTRUCTION>
<!-- BACKLOG.MD GUIDELINES END -->
