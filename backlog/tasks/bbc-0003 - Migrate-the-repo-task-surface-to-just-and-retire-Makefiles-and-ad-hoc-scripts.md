---
id: BBC-0003
title: Migrate the repo task surface to just and retire Makefiles and ad-hoc scripts
status: To Do
assignee: []
created_date: '2026-08-28 19:14'
labels: []
dependencies: []
priority: medium
type: chore
ordinal: 3000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
# Migrate bumblebee-catalog's task surface to `just`

## 1. Outcome

`bumblebee-catalog` gets a top-level `justfile` implementing the fleet's seven mandatory recipes
plus thin wrapper recipes for each of the six `ci/*.py` scripts. `ci.yml` calls `just check`
instead of a bare `python3 -m py_compile` line. `osv-catalog.yml` and `extra-catalogs.yml` call
`just <recipe> <same args as today>` instead of `python3 ci/<script>.py <args>` — behavior is
byte-for-byte identical, only the invocation surface changes. `AGENTS.md` gets a "Task interface"
section. `backlog/config.yml`'s `definition_of_done` names `just` recipes instead of a bare
`python3 -m py_compile` line and separate actionlint/zizmor commands.

**This repo has no Makefile and no shell scripts.** `git ls-files | grep -E '\.(sh|bash|zsh|ps1)$'`
returns nothing, and no `Makefile`/`GNUmakefile` exists anywhere in the tree. The "migration" here is
narrower than most fleet repos: introduce the justfile, wrap the existing Python scripts, and switch
three workflow files + two doc files to call it. Nothing is deleted except nothing (there is no dead
file to remove).

**Deliberate scope limit — read before touching `osv-catalog.yml` / `extra-catalogs.yml`:** only the
`python3 ci/*.py ...` invocation lines in these two workflows get converted to `just <recipe> ...`.
The surrounding orchestration (checkout, `go build`, `curl` release downloads + checksum verification,
`git clone`/sparse-checkout, `gh release create/upload`, the floor-check `gh release download`) is
**left exactly as-is** — untouched, not wrapped, not moved into the justfile. See §9 "Traps" for why.

## 2. The complete justfile

Create `justfile` at the repo root:

```just
set shell := ["bash", "-euo", "pipefail", "-c"]

# show the task surface
default:
    @just --list

# nothing to install — ci/*.py is stdlib-only, no lockfile, no venv
setup:
    @echo "python3: {{ require('python3') }}"
    @echo "no dependencies to install (ci/*.py is stdlib-only)"

# format the justfile (no other formatter is configured in this repo)
[group('check')]
fmt:
    @just --fmt

# verify justfile formatting — fails if `just fmt` would change it
[no-exit-message]
[group('check')]
fmt-check:
    just --fmt --check

# syntax-check every CI script — the only static check this repo has today
[no-exit-message]
[group('check')]
lint:
    python3 -m py_compile ci/*.py

# lint and audit GitHub Actions workflows (needs actionlint + zizmor on PATH; not run by `check`)
[no-exit-message]
[group('check')]
lint-workflows:
    actionlint
    zizmor .github/workflows/

# no test suite in this repo — see AGENTS.md ("nothing that runs meaningfully on a laptop")
[group('check')]
test:
    @echo "no tests in this repo"

# the full local gate — exactly what ci.yml enforces
[group('check')]
check: fmt-check lint test

# CI superset: check plus workflow linting (actionlint.yml/zizmor.yml already run these as separate
# GitHub-native workflows; this recipe exists so a dev can reproduce the same gate locally)
[group('check')]
ci: check lint-workflows

# regenerate the DataDog malicious-package catalog — args pass straight through to the script
[group('gen')]
gen-datadog-catalog *args:
    python3 ci/datadog_catalog.py {{ args }}

# regenerate the GHSA (CWE-506) malware catalog — args pass straight through to the script
[group('gen')]
gen-ghsa-catalog *args:
    python3 ci/ghsa_catalog.py {{ args }}

# validate a generated catalog and write its *-meta.json — args pass straight through to the script
[group('gen')]
validate-catalog *args:
    python3 ci/validate.py {{ args }}

# build a fixture package that should trip a given catalog — args pass straight through to the script
[group('gen')]
make-fixture *args:
    python3 ci/make_fixture.py {{ args }}

# assert a bumblebee scan actually flagged the seeded fixture — args pass straight through to the script
[group('gen')]
assert-finding *args:
    python3 ci/assert_finding.py {{ args }}

# assert the full published catalog SET loads in the deployed bumblebee binary — args pass through
[group('gen')]
assert-catalog-set *args:
    python3 ci/assert_catalog_set.py {{ args }}
```

Notes for whoever implements this:
- `require('python3')` halts `setup` with a clear error if `python3` isn't on `PATH`; it otherwise
  prints the resolved path. This is the entire `setup` recipe — there is nothing to install.
- All six `gen-*`/`validate-catalog`/`make-fixture`/`assert-*` recipes use `*args` (variadic,
  zero or more) so they are exact drop-in replacements for the current `python3 ci/<script>.py
  <args...>` workflow lines — see §5 for the exact before/after per call site.
- `lint-workflows` is deliberately **not** a dependency of `check` (only of `ci`) because
  `actionlint`/`zizmor` are not guaranteed to be on a contributor's `PATH`, and `backlog/config.yml`'s
  own `definition_of_done` already gates them separately, conditionally on a workflow file changing.

## 3. Makefile disposition

N/A — confirmed via `find . -iname Makefile -o -iname GNUmakefile` (excluding `vendor/`,
`node_modules/`, `third_party/`, `.venv/`): no Makefile exists anywhere in this repo. No `git rm`
needed for this section.

## 4. Script disposition

| Script | Lines | Disposition | Recipe | Why |
|---|---|---|---|---|
| `ci/assert_catalog_set.py` | 123 | KEEP | `just assert-catalog-set <args>` | Real program: `argparse`, `subprocess`, temp-dir handling, downloads/spawns the bumblebee binary. Not a thin wrapper. |
| `ci/assert_finding.py` | 44 | KEEP | `just assert-finding <args>` | Parses NDJSON scan output and asserts structural content — logic, not sequencing. |
| `ci/datadog_catalog.py` | 125 | KEEP | `just gen-datadog-catalog <args>` | Real catalog-generation program (manifest parsing, ecosystem filtering, null-record dropping). |
| `ci/ghsa_catalog.py` | 182 | KEEP | `just gen-ghsa-catalog <args>` | Real catalog-generation program (advisory parsing, CWE-506 filtering, MAL- alias dedup). |
| `ci/make_fixture.py` | 63 | KEEP | `just make-fixture <args>` | Builds a seeded fixture package on disk — a program, not a sequencing wrapper. |
| `ci/validate.py` | 117 | KEEP | `just validate-catalog <args>` | Schema/entry-count validation + meta-file writer with real branching logic (`--force`, floor check). |

No script in this repo is ABSORB-eligible — there are no thin `cd-and-run-a-tool` shell wrappers at
all, tracked or otherwise. Every "task" in this repo's workflows is either a bare shell one-liner
already (`go build ...`, `curl ...`) or a call into one of the six real Python programs above. Every
KEEP script above gets a `just` recipe as its entry point; nobody should invoke
`python3 ci/<script>.py` directly again outside the recipe body itself.

## 5. CI changes

### `.github/workflows/ci.yml`

Add a `setup-just` step and collapse the syntax-check step to `just check`:

```yaml
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false
      - uses: extractions/setup-just@53165ef7e734c5c07cb06b3c8e7b647c5aa16db3 # v4
        with:
          just-version: '1.58.0'
      - name: Run the check gate
        run: just check
```

This replaces the existing `Syntax-check CI scripts` step (`run: python3 -m py_compile ci/*.py`).
`just check` runs `fmt-check` (new — checks the justfile's own formatting), `lint` (the same
`py_compile` command, unchanged), and `test` (a no-op that prints why). Net effect: strictly more
coverage than today, zero behavior change to the existing check.

**Do not touch**: the `harden-runner` step, the `ci-success` job, its `needs: [validate]`, or the
`if: always()` / `contains(needs.*.result, ...)` logic. `ci-success` is the branch-ruleset gate name.

### `.github/workflows/osv-catalog.yml`

Insert `setup-just` right after the first checkout step (`Checkout this repo (CI scripts)`), before
`Checkout bumblebee (pinned)`:

```yaml
      - name: Checkout this repo (CI scripts)
        uses: actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0 # v7
        with:
          persist-credentials: false

      - uses: extractions/setup-just@53165ef7e734c5c07cb06b3c8e7b647c5aa16db3 # v4
        with:
          just-version: '1.58.0'

      - name: Checkout bumblebee (pinned)
        ...
```

Then three exact line-for-line substitutions further down (everything else in each step —
comments, `set -euo pipefail`, surrounding shell — stays untouched):

1. Step **"Validate + write meta"** — replace the `python3 ci/validate.py \` invocation:
   ```yaml
           python3 ci/validate.py \
             --catalog "$OUTPUT" \
             --old "old/$OUTPUT" \
             --ossf-sha "$OSSF_SHA" \
             --bumblebee-sha "$BUMBLEBEE_SHA" \
             --target-schema "$CATALOG_SCHEMA_VERSION" \
             "${force[@]}"
   ```
   becomes
   ```yaml
           just validate-catalog \
             --catalog "$OUTPUT" \
             --old "old/$OUTPUT" \
             --ossf-sha "$OSSF_SHA" \
             --bumblebee-sha "$BUMBLEBEE_SHA" \
             --target-schema "$CATALOG_SCHEMA_VERSION" \
             "${force[@]}"
   ```
   (the `force=()` array-building `if` above it is untouched — that's step logic, not a script call)

2. Step **"Positive-match self-test (catalog actually matches)"** — replace both invocations:
   - `python3 ci/make_fixture.py --catalog "$OUTPUT" --out fixture` → `just make-fixture --catalog "$OUTPUT" --out fixture`
   - `python3 ci/assert_finding.py --ndjson scan.ndjson --seed-file fixture/seed.json` → `just assert-finding --ndjson scan.ndjson --seed-file fixture/seed.json`

3. Step **"Assert the catalog SET loads in the deployed binary"** — replace:
   ```yaml
           python3 ci/assert_catalog_set.py "${args[@]}"
   ```
   with
   ```yaml
           just assert-catalog-set "${args[@]}"
   ```
   (the `args=(...)` array construction and the `gh release download` peer-fetch above it are
   untouched)

**Do not touch**: `Checkout bumblebee (pinned)`, `Set up Go`, `Build bumblebee (generator only)`,
`Download the DEPLOYED release`, `Sparse-checkout OSSF malicious-packages`, `Download last-good
(floor check)`, `Publish catalog-latest release asset`, the `concurrency:` block, the `permissions:
contents: write`, or any `env:` value (especially `BUMBLEBEE_SHA` / `BUMBLEBEE_RELEASE` /
`CATALOG_SCHEMA_VERSION` — see AGENTS.md's "Hard constraints" section, unrelated to this migration).

### `.github/workflows/extra-catalogs.yml`

Same `setup-just` insertion point (right after `Checkout this repo (CI scripts)`, before `Checkout
bumblebee (pinned)`), same SHA/version pin as above. Then:

1. Step **"Generate datadog-malicious.json"** — replace:
   ```yaml
           python3 ci/datadog_catalog.py \
             --samples dd/samples \
             --source "${DATADOG_REPO}@${DD_SHA}" \
             --out datadog-malicious.json
   ```
   with
   ```yaml
           just gen-datadog-catalog \
             --samples dd/samples \
             --source "${DATADOG_REPO}@${DD_SHA}" \
             --out datadog-malicious.json
   ```

2. Step **"Generate ghsa-malicious.json"** — replace:
   ```yaml
           python3 ci/ghsa_catalog.py \
             --advisories ghsa/advisories/github-reviewed \
             --source "${GHSA_REPO}@${GHSA_SHA}" \
             --out ghsa-malicious.json
   ```
   with
   ```yaml
           just gen-ghsa-catalog \
             --advisories ghsa/advisories/github-reviewed \
             --source "${GHSA_REPO}@${GHSA_SHA}" \
             --out ghsa-malicious.json
   ```

3. Step **"Validate + write meta"** — replace both `python3 ci/validate.py \` invocations with
   `just validate-catalog \`, keeping every arg line under each identical (one call for
   `datadog-malicious.json`/`datadog-meta.json`/`--label datadog`, one for
   `ghsa-malicious.json`/`ghsa-meta.json`/`--label ghsa`). The shared `force=()` block above both
   calls is untouched.

4. Step **"Positive-match self-test (each catalog actually matches)"** — inside the
   `for cat in datadog-malicious.json ghsa-malicious.json; do ... done` loop, replace:
   - `python3 ci/make_fixture.py --catalog "$cat" --out "fixture-$cat"` → `just make-fixture --catalog "$cat" --out "fixture-$cat"`
   - `python3 ci/assert_finding.py --ndjson "scan-$cat.ndjson" --seed-file "fixture-$cat/seed.json"` → `just assert-finding --ndjson "scan-$cat.ndjson" --seed-file "fixture-$cat/seed.json"`

   (the loop itself, the `release/bumblebee scan ...` invocation inside it, and the `PKGVER=$(...)`
   capture stay exactly as-is — the loop's control flow is not being touched, only the two script
   calls inside it)

5. Step **"Assert the catalog SET loads in the deployed binary"** — replace:
   ```yaml
           python3 ci/assert_catalog_set.py "${args[@]}"
   ```
   with
   ```yaml
           just assert-catalog-set "${args[@]}"
   ```

**Do not touch**: `Checkout bumblebee (pinned)`, `Set up Go`, `Build bumblebee (generator only)`,
`Download the DEPLOYED release`, `Fetch DataDog dataset manifests`, `Clone GitHub Advisory Database`,
`Download last-good catalogs (floor check)`, `Publish catalog-latest release assets`, the
`concurrency:` block, `permissions: contents: write`, or any `env:` value.

### Workflows explicitly out of scope for this task

`actionlint.yml`, `codeql.yml`, `dependency-review.yml`, `keepalive.yml`, `scorecard.yml`,
`zizmor.yml` — all six are either GitHub-native reusable-workflow calls (`uses:
rknightion/.github/.github/workflows/...@<sha>`) or a bare `git commit --allow-empty && git push`
housekeeping step. §8 of the fleet standard forbids converting a `uses:` into `run: just`, and none
of these six files contain any build/test/lint/format/generate/validate shell logic to collapse.
**Do not edit any of these six files.**

## 6. Docs and agent-contract changes

### `AGENTS.md`

Add a new `## Task interface` section. Insert it directly after the `## Verifying a change` section
(before `## Commits`), replacing nothing — this is new content:

```markdown
## Task interface

This repo's task surface is a `justfile`. Discover it, don't guess it:

    just --list                        # human-readable
    just --dump --dump-format json     # machine-readable
    just --show <recipe>               # what a recipe actually runs

- `just check` is the full local gate and is exactly what `ci.yml` enforces. It must pass before you
  commit.
- Prefer `just <recipe>` over the underlying tool. If you are typing `python3 ci/validate.py`, you
  want `just validate-catalog` instead.
- Run `just` with stdin from /dev/null. This repo has no `[confirm]`-marked recipes today, but if one
  is added later, stop and ask before running it — never pass `--yes` or `JUST_YES=1`.
- If a task you need does not exist, add a recipe with a `#` doc comment and a `[group(...)]` rather
  than running a bare command.
```

Also update the existing **"Verifying a change"** section's opening paragraph, which currently reads:

> `ci.yml` runs `python3 -m py_compile ci/*.py` and nothing else. It proves the scripts parse. It
> does not run them, does not touch a catalog, and will not fail for most things a change can break.

Change `ci.yml` runs `python3 -m py_compile ci/*.py` and nothing else` to `ci.yml` runs `just check`
and nothing else`. Leave the rest of that paragraph (the "weak claim" point and the three
rising-strength verification levels) unchanged — those levels (run the script locally, actionlint +
zizmor, `workflow_dispatch`) are still accurate and now map onto `just <recipe>` /
`just lint-workflows` naturally, but the prose doesn't need to say so explicitly.

### `CLAUDE.md`

No change — it is a one-line `@AGENTS.md` import already.

### `README.md`

No change — it documents the consumer-facing release-asset contract and the workflow *behavior*
(cadence, schema-version rules), never a `make`/script invocation a human would type. Confirmed via
`grep -n 'make \|\./scripts\|python3 ci/' README.md` returning nothing.

## 7. `backlog/config.yml`

Current:

```yaml
definition_of_done:
  - "python3 -m py_compile ci/*.py"
  - "actionlint (only if a .github/workflows file changed)"
  - "zizmor .github/workflows/ (only if a .github/workflows file changed)"
```

New:

```yaml
definition_of_done:
  - "just check"
  - "just lint-workflows (only if a .github/workflows file changed)"
```

Edit this file by hand — per AGENTS.md, `backlog/config.yml` is the one Backlog.md file edited
directly rather than through the CLI (list-valued keys aren't settable via `backlog config set`).

## 8. Order of work

1. Add the `justfile` (§2) at the repo root. Run `just --fmt --check`, `just --list`, `just check`
   locally to confirm the seven mandatory recipes work and `check` passes.
2. Sanity-check each `gen-*`/`validate-catalog`/`make-fixture`/`assert-*` recipe by hand once, with
   made-up throwaway args, to confirm `*args` pass-through doesn't mangle anything (e.g.
   `just validate-catalog --help` should print the script's own `argparse` help).
3. Edit `ci.yml` (§5) — add `setup-just`, switch to `just check`. Push (this repo commits straight to
   `main`, no PR — see AGENTS.md "Commits"). Watch the next `ci.yml` run go green.
4. Edit `osv-catalog.yml` and `extra-catalogs.yml` (§5) — add `setup-just`, swap the six/five script
   invocations. Push.
5. Verify via `workflow_dispatch`: manually trigger `osv-catalog.yml` and, separately (never both at
   once — same rolling release, separate concurrency groups), `extra-catalogs.yml`. Confirm each
   completes and the release assets update. This is the only way to prove the `just`-wrapped
   invocations still work end to end — per AGENTS.md, `ci.yml` alone is a weak signal.
6. Update `AGENTS.md` (§6) and `backlog/config.yml` (§7). Push.
7. There is no deletion step — no Makefile, no ABSORB scripts. Skip.

Do not skip step 5. These two workflows run on a schedule against real external state (OSSF feed,
DataDog dataset, GHSA advisories, the deployed `bumblebee` release); a broken `*args` pass-through
would silently stop publishing catalog updates with no PR-time signal at all, since neither workflow
runs on push/PR.

## 9. Traps specific to this repo

- **No pyproject.toml, no lockfile, no venv.** `grep -n '^import\|^from' ci/*.py` shows only stdlib
  imports (`argparse`, `json`, `os`, `sys`, `subprocess`, `shutil`, `tempfile`, `datetime`). Do not
  invent a `uv sync` / `pip install` step in `setup` — there is nothing to install. Do not add
  `ruff`/`mypy`/`pytest` config as part of this migration; that's new tooling, out of scope for a
  task-runner migration (raise it separately if wanted).
- **`{{args}}` interpolation loses quoting for values containing spaces** (per fleet standard §10).
  None of the current call sites pass an arg containing a space (paths, flags, commit SHAs, `owner/
  repo@sha` strings), so plain `*args` is safe today — but don't blindly extend these recipes to a
  new call site with a spaced value without checking this.
- **Why the go build / curl / git clone / gh release steps are NOT converted to `just` recipes**: they
  use `$GITHUB_ENV` to pass computed values (`DD_SHA`, `GHSA_SHA`, `OSSF_SHA`) between *separate*
  workflow steps, use `GH_TOKEN`-authenticated `gh` calls, and have real control flow (loops over
  ecosystems, checksum verification, conditional `--force` array building). Per fleet standard §6,
  "anything with non-trivial control flow... belongs in a script (or a `[script('bash')]` recipe if
  genuinely task-shaped)" — forcing this into a recipe would mean re-threading `$GITHUB_ENV` state
  through `just` variables/exports across multiple recipe invocations, which is a real redesign, not
  a migration, and this repo's own AGENTS.md states plainly that "nothing... runs meaningfully on a
  laptop." If a future task wants full local reproducibility of the generate pipeline, that is new
  scope — file it separately, don't fold it into this task.
- **`lint-workflows` needs `actionlint` and `zizmor` on `PATH`.** Neither is installed by `setup`
  (they're not this repo's toolchain — they lint the workflow YAML, and the fleet standard's `setup`
  contract is "toolchain + deps," which for a stdlib-only Python repo is empty). A contributor without
  both binaries gets a bare "command not found" from `lint-workflows` — that's expected; it's why the
  recipe isn't part of `check`.
- **`ci.yml`'s `harden-runner` step runs with `egress-policy: audit`**, not `block`. `setup-just`
  fetches the `extractions/setup-just` action and (transitively) the `just` binary from GitHub
  releases — audit mode logs but does not block this, so no `harden-runner` config change is needed.
  Do not change `egress-policy` as part of this task.
- **Two workflows publish to the same `catalog-latest` release under separate concurrency groups**
  (`osv-catalog` and `extra-catalogs`). When validating step 5 above, check the Actions tab first and
  never dispatch both at once — this is an existing repo rule (AGENTS.md "Verifying a change"),
  restated here because it directly affects how you validate this migration.

## 10. Out of scope

- `actionlint.yml`, `codeql.yml`, `dependency-review.yml`, `keepalive.yml`, `scorecard.yml`,
  `zizmor.yml` — all GitHub-native, untouched (§5).
- The `go build`, `curl`/checksum-verify, `git clone`/sparse-checkout, and `gh release
  create/upload/download` steps in `osv-catalog.yml` and `extra-catalogs.yml` — left exactly as they
  are today (§9).
- `CATALOG_SCHEMA_VERSION`, `BUMBLEBEE_SHA`, `BUMBLEBEE_RELEASE` — untouchable per AGENTS.md's own
  "Hard constraints" section; nothing in this migration should come near these values.
- Adding a Python formatter, linter, or type checker (ruff/mypy/etc.) — not part of a task-runner
  migration; `fmt`/`fmt-check`/`lint` in the justfile reflect the repo's *actual current* toolchain
  (none, beyond `py_compile`), per the fleet standard's "real commands, not placeholders" rule.
- `backlog/docs/*` (the two canonical docs on the fan-out protocol and wave operating model) — no
  `make`/script references in either; not touched.
- `renovate.json` — unrelated to task-runner surface.
- Any `backlog/tasks/*.md` file — never hand-edited (AGENTS.md), and none reference `make` or a
  script path.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Top-level justfile exists implementing all seven mandatory recipes: default, setup, fmt, fmt-check, lint, test, check
- [ ] #2 just check passes locally and runs exactly what ci.yml enforces (fmt-check, lint via py_compile, test no-op)
- [ ] #3 just --fmt --check passes against the committed justfile
- [ ] #4 just --list shows a # doc comment and a [group(...)] for every public recipe, including gen-datadog-catalog, gen-ghsa-catalog, validate-catalog, make-fixture, assert-finding, assert-catalog-set, and lint-workflows
- [ ] #5 Each of the six ci/*.py scripts (assert_catalog_set.py, assert_finding.py, datadog_catalog.py, ghsa_catalog.py, make_fixture.py, validate.py) is reachable only via its wrapping just recipe from ci.yml, osv-catalog.yml, and extra-catalogs.yml
- [ ] #6 ci.yml, osv-catalog.yml, and extra-catalogs.yml invoke just recipes in place of the former python3 ci/*.py and python3 -m py_compile calls, with an extractions/setup-just step added before first use, and the ci-success job, concurrency groups, and permissions blocks unchanged
- [ ] #7 actionlint.yml, codeql.yml, dependency-review.yml, keepalive.yml, scorecard.yml, and zizmor.yml are unmodified
- [ ] #8 AGENTS.md has a Task interface section per the fleet standard and no longer states that ci.yml runs a bare python3 -m py_compile command
- [ ] #9 backlog/config.yml's definition_of_done names just check and just lint-workflows instead of python3 -m py_compile / actionlint / zizmor
- [ ] #10 A workflow_dispatch run of osv-catalog.yml and, separately, extra-catalogs.yml completes successfully after the migration, confirming the just-wrapped script invocations behave identically to the originals
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 python3 -m py_compile ci/*.py
- [ ] #2 actionlint (only if a .github/workflows file changed)
- [ ] #3 zizmor .github/workflows/ (only if a .github/workflows file changed)
<!-- DOD:END -->
