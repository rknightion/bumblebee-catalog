## What changed

The change in a few sentences, naming the files or areas it touches.

## Why

The problem it solves, with a link to the issue or bug report.

## Verified

Which evidence level you reached: a local run diffed against a real input, `just lint-workflows`, or
a `workflow_dispatch` run. `just check` only proves the scripts parse, so say what it did not cover.

## Not verified

What you did not run or could not observe. Write "nothing" only if that is true.

## Checklist

- [ ] `just check` passes
- [ ] The title is a [Conventional Commit](https://www.conventionalcommits.org/) subject
- [ ] No host, endpoint, tenant or account identifier and no fleet inventory in the change
- [ ] `README.md` consumer table updated if an asset changed

## Issue

<!-- Closes #<number> on a line of its own for each issue of this repository this change completes (Closes owner/repo#<number> means the same). Refs #<number> when it only relates to one. A change with no issue says "Task: none, <reason>" on a line of its own. -->

## Acceptance evidence

<!-- One row per acceptance criterion of every issue this change closes, copied exactly from the issue's "- [ ] ACn" list. Evidence class is code, live or browser. In Proof, put repository paths in backticks, and write anything else (a command, a read-back, a run) without them. Delete the example row. Leave the table out only when the change closes no issue. -->

| Issue | AC | AC text | Evidence class | Proof |
| --- | --- | --- | --- | --- |
| #N | AC1 | The acceptance criterion, word for word | code | `path/to/the_test.go` TestWhatItProves |
