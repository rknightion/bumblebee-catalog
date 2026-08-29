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
[group('check')]
[no-exit-message]
fmt-check:
    just --fmt --check

# syntax-check every CI script — the only static check this repo has today
[group('check')]
[no-exit-message]
lint:
    python3 -m py_compile ci/*.py

# lint and audit GitHub Actions workflows (needs actionlint + zizmor on PATH)
[group('check')]
[no-exit-message]
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
