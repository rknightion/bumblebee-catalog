---
id: doc-0002
title: Wave operating model
type: guide
created_date: '2026-08-14 16:37'
updated_date: '2026-08-14 16:37'
---
This document carries **only what is true of bumblebee-catalog**. The campaign model itself — run
contract and run modes, the routing contract, authority and the thread pool, child lane briefs,
external-contract freezing, the blocker contract, the goal-file template, the run-end protocol and
the pre-flight checklist — is the *Agent fan-out protocol (canonical)* doc, and that doc wins on any
specific. Nothing here restates it. If a section below could be pasted into another repo unchanged,
it is in the wrong document.

That protocol is harness-neutral and names no model: it describes lanes by **role**, and its
Appendix A (Codex) or Appendix B (Claude Code) resolves a role into a concrete route. **Name the
harness in the run contract and resolve every lane's route from that harness's profile** — a lane
brief carrying a role name alone is not routed.

Every rule here exists because of something specific about this repo. The reason is kept with the
rule; a rule without its reason gets argued away by the next session.

---

## 0. What this repo actually is, and why that changes how waves run here

This is not an application. It is **nine GitHub Actions workflows and six Python scripts whose only
output is a set of release assets** on the moving `catalog-latest` release, fetched by managed
endpoints before every Bumblebee scan. There is no binary, no service, no test suite, and nothing
here runs on a developer's machine in anger.

Three consequences that shape every wave:

- **The gate is weak by construction.** `ci.yml` runs `python3 -m py_compile ci/*.py` and nothing
  else. It proves the scripts parse. It does not run them, does not touch a catalog, and cannot
  fail for any reason a wave is likely to introduce. A lane reporting "gate green" here has said
  almost nothing — see §2.
- **The real gate is a `workflow_dispatch` run**, and it takes minutes, downloads a release binary
  and clones two upstream feeds. It is not free and it is not local.
- **The failure mode this repo exists to prevent is silent.** A bad catalog does not error at the
  endpoint. It makes Bumblebee exit 2 before scanning — no packages, no findings, no
  `scan_summary` — so no freshness alert and no finding alert can fire. Detection is simply off
  while every dashboard stays green. **Assume any change you cannot prove is safe fails this way.**

---

## 1. Rules this project added

### `CATALOG_SCHEMA_VERSION` is frozen for the duration of any wave

No lane may change it, in either workflow or in `ci/validate.py`'s default, for any reason —
including "the value looks stale" or "main already moved". It is a **deployment-coupled** decision
that depends on a fact outside this repo: whether the fleet's pinned `BUMBLEBEE_VERSION` has
*rolled out* to a release accepting the new schema. Raising it first drops every catalog in this
repo from every scan, silently. The ordering is in `README.md` and in the `ci/validate.py`
docstring; there is a seeded task for the bump, and it is the only place the change may happen.

### The two Bumblebee pins do different jobs and must never be conflated

- `BUMBLEBEE_SHA` — a `main` commit, used **only** to build the `osvcatalog` generator, because
  `tools/osvcatalog` postdates the `v0.1.1` tag.
- `BUMBLEBEE_RELEASE` — the released binary the fleet runs, used for **all acceptance validation**.

Validating against `main` was the original gap and is the reason the split exists: `main` accepts
catalogs the deployed binary rejects, so CI went green while endpoints would have stopped detecting.
A lane that "simplifies" the workflow by reusing one pin for both reopens that gap and the
consequence is invisible. Both pins appear in `osv-catalog.yml` **and** `extra-catalogs.yml`;
bumping one file only is drift.

### Work lands on `main`, and only the root agent pushes

No PR flow for this repo's own work (Renovate's PRs are separate and are left alone). Lanes commit
to the shared checkout; the root agent owns the push, squashing checkpoint commits into one commit
per change with `git reset --soft origin/main`. Conventional Commits is not a style preference —
Renovate parses it. A push that reports **bypassed branch-protection rules is the expected
mechanism here**, not an incident, and is not worth reporting as one.

### Anything that mutates GitHub state stays on the root agent

Lanes do read-only investigation, script and workflow edits, and local dry-runs. **Triggering a
`workflow_dispatch`, touching the `catalog-latest` release or its assets, deleting or re-uploading
anything, and any `gh` call that is not a read stay with the root agent.** Besides blast radius,
a dispatched lane inherits the parent's permission mode and cannot clear a soft block — clearing
one needs a message from the user, and a lane's transcript contains none. A blocked lane is run by
the root agent, never re-dispatched.

### A lane that hits a decision its brief does not cover stops and returns the question

It does not invent an answer, and on this repo it especially does not invent a *version*, a *pin*,
a *schema value* or a *threshold*. One round trip is cheaper than a silently-undetecting fleet.

### Nothing private ever enters this repo — it is the repo's own stated contract

`README.md` promises "only public threat-intelligence data and the CI to assemble it — no secrets,
no private data". That covers `backlog/` too: no host names, endpoint names, tenant or account
identifiers, no fleet inventory, no deployment specifics. Write the shape, not the instance ("the
deployment's pinned version", not where it is pinned). Counts, timings and structural findings are
fine.

---

## 2. Recurring defects in this codebase

### "The gate passed" is not a claim about anything here

`py_compile` catches a syntax error. It does not catch: a wrong ecosystem mapping, a dropped
entry class, a broken `jq`/shell pipeline in a workflow, a mis-set env var, an unpinned action, or
any change in what actually gets published. **A lane whose only evidence is the CI gate has not
verified its work.** Acceptable evidence, in rising order of strength:

1. running the changed script locally against a real input and diffing the output;
2. `actionlint` + `zizmor .github/workflows/` for any workflow edit;
3. a `workflow_dispatch` run of the affected workflow (root agent only) — the only thing that
   proves the publish path still works end to end.

### Each file is individually valid and only the *combination* is illegal

`ci/validate.py` checks one catalog in isolation and will happily pass every file in a set that
cannot load together. `ci/assert_catalog_set.py` is the **only** check that can catch a bad set: it
downloads the released binary, assembles the real directory — every asset this repo publishes plus
the binary's own bundled `threat_intel` — and runs a real scan. A change that adds a catalog, or
changes what a catalog declares, is not covered by the per-file validator no matter how green it
looks.

### A structurally valid catalog that matches nothing looks identical to a working one

That is why the positive-match self-test exists: `ci/make_fixture.py` seeds a fixture from a real
entry and `ci/assert_finding.py` asserts a live scan actually emits a `finding`. Any change to
entry shape, id format, ecosystem naming or version handling must keep that test meaningful — a
self-test that would pass against an empty catalog is a test that has been broken without failing.

### `force_publish` discards the only guard against an upstream feed regression

The >10% entry-count floor is what stops a bad upstream ingest from publishing a gutted catalog to
the whole fleet. `--force` exists for legitimate large upstream changes. Using it to make a red run
go green, without first establishing *why* the count dropped, ships exactly the regression the floor
was added for.

### Both catalog workflows publish to the same release under *separate* concurrency groups

`osv-catalog` (`group: osv-catalog`, every 4h) and `extra-catalogs` (`group: extra-catalogs`, daily
05:30 UTC) each guard themselves and neither guards the other. They upload to the same
`catalog-latest` release, and each downloads the *other's* assets to assert the set loads. Their
scheduled times do not collide; **a manual dispatch during a scheduled run can**, and the loser
asserts against a half-updated set. Do not dispatch both at once, and check the Actions tab before
dispatching either.

### The keepalive commit is load-bearing, not noise

GitHub auto-disables scheduled workflows after 60 days of repository inactivity, and this repo can
be quiet for months. The weekly empty commit exists to keep the catalog cron alive. It looks like
junk in `git log` and it is not; do not tidy it away.

### Actions are pinned to commit SHAs, and zizmor enforces it

Every `uses:` carries a 40-character SHA with the version in a trailing comment. Renovate keeps them
current. A lane that adds a tag-pinned action fails `zizmor` in CI, not in the local gate.

---

## 3. Lane conventions

### Single-owner surfaces — never two lanes, never concurrently

- **`CATALOG_SCHEMA_VERSION`, `BUMBLEBEE_SHA`, `BUMBLEBEE_RELEASE`** — the same values live in both
  workflows and are read by `ci/validate.py`. One owner, one commit, both files.
- **`.github/workflows/osv-catalog.yml` and `.github/workflows/extra-catalogs.yml`** — they share
  the validate → assert-set → positive-self-test → publish shape deliberately. A change to that
  *shape* is one lane touching both; a change confined to one feed's generation step is not.
- **`ci/validate.py`** — consumed by both workflows and by both catalog families. Its docstring is
  the canonical statement of the schema-version rule; it and `README.md` must move together.
- **`README.md`'s consumer table** — the published URL contract. Anything that renames or adds an
  asset changes it, and it is the only place downstream consumers read.

### Exclusive resources — root agent only, one at a time

- **The `catalog-latest` release.** A moving tag with live consumers. It is not a build artefact
  store; every asset on it is being fetched by endpoints right now.
- **`workflow_dispatch` runs.** See the concurrency defect above.
- **Upstream feeds** (OSSF malicious-packages, the DataDog dataset, the GitHub Advisory Database)
  are read-only and rate-limited. A wave that clones them repeatedly from lanes will get throttled;
  clone once and share the checkout path in the run contract.

### Generated files are never committed

`osv-malicious.json`, `catalog-meta.json`, the DataDog and GHSA catalogs and their metas, and every
scratch directory the workflows use are gitignored and produced only in the runner. A lane that
finds one in the working tree has run a generator locally — that is fine, but it never gets staged.
Stage explicit pathspecs; never `git add -A` in this checkout.

---

## 4. Run-end against this tracker

The tracker *is* the report. There is no run-end file.

- Landed work: `backlog task edit <id> --check-ac N -s Done` **in one call**, with the commit SHA in
  the final summary. Splitting the criteria check from the status change lets an interrupted run
  leave finished work looking unfinished.
- Attempted and blocked: `-s Parked` with a concrete resume boundary — what was tried, what the next
  action is, what would unblock it. Both seeded tasks on this board are blocked on facts outside the
  repo, so `Parked` is the normal terminal state here, not a failure state.
- Untouched work needs no action; it is still `To Do` and self-evidently so.
- Discovered work: a new task labelled `needs-triage`. Never a note in a summary nobody queries.
- Notes and plans are appended (`--append-notes`, `--append-plan`), never set.

Before any task goes to `Done`, the `definition_of_done` gate in `backlog/config.yml` must have been
run and its output seen — and, per §2, for anything touching a workflow or a generator, that gate is
the floor and not the proof. Say in the task's final summary which of the three evidence levels the
work actually reached.

The run's closing terminal message carries only what no single task can: what this run learned as a
whole. Nothing durable may live only there.
