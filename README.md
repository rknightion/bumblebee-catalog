# bumblebee-catalog

[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/rknightion/bumblebee-catalog/badge)](https://scorecard.dev/viewer/?uri=github.com/rknightion/bumblebee-catalog)

Rolling **OSV exposure catalog** for [Bumblebee](https://github.com/perplexityai/bumblebee),
generated every 4 hours from the [OSSF malicious-packages](https://github.com/ossf/malicious-packages)
feed and published as a release asset that managed endpoints fetch before each scan.

This repo contains **only public threat-intelligence data and the CI to assemble it** — no
secrets, no private data.

## Consume it

| Artifact | URL |
|----------|-----|
| OSSF catalog (`schema_version` 0.1.0) | `https://github.com/rknightion/bumblebee-catalog/releases/latest/download/osv-malicious.json` |
| OSSF provenance / freshness | `https://github.com/rknightion/bumblebee-catalog/releases/latest/download/catalog-meta.json` |
| DataDog catalog (npm / pypi / editor-extension) | `https://github.com/rknightion/bumblebee-catalog/releases/latest/download/datadog-malicious.json` |
| DataDog provenance / freshness | `https://github.com/rknightion/bumblebee-catalog/releases/latest/download/datadog-meta.json` |
| GHSA malware catalog (additive to OSSF) | `https://github.com/rknightion/bumblebee-catalog/releases/latest/download/ghsa-malicious.json` |
| GHSA provenance / freshness | `https://github.com/rknightion/bumblebee-catalog/releases/latest/download/ghsa-meta.json` |

Endpoints combine these catalogs with the binary's bundled curated `threat_intel/*.json`
catalogs in a single `--exposure-catalog` directory — Bumblebee loads every catalog
in the directory and matches against the union. Each `*-meta.json` carries
`generated_at` for a catalog-freshness dead-man's switch (alert if stale).

## ⚠️ `schema_version` is coupled to the deployed binary — do not bump it here first

Bumblebee's directory loader requires **every** catalog in the directory to declare the
**same** `schema_version`. A mismatch is not a warning and not a partial load: it
**exits 2 before the scan starts**, emitting no packages, no findings, and no
`scan_summary`. The run is completely silent, so no freshness or finding alert can fire —
detection is simply off while everything else still looks green.

That makes the version this repo publishes a deployment-coupled decision, not a free one:

| | schema accepted |
|---|---|
| **v0.1.2** — the current release, and what the fleet runs | `0.1.0` only. Hard-rejects `0.2.0`. |
| bumblebee `main` — bundled catalogs already bumped, unreleased | `0.1.0` and `0.2.0` |

**Bumping `CATALOG_SCHEMA_VERSION` here before endpoints run a binary that accepts it
silently drops every catalog in this repo from every scan.** The safe order is:

1. A bumblebee **release** supporting the new schema exists.
2. The deployment's pinned `BUMBLEBEE_VERSION` is raised to it *and has rolled out*.
3. Only then bump `CATALOG_SCHEMA_VERSION` in both workflows.

Two CI guards enforce this so it cannot happen by accident:

- `ci/validate.py --target-schema` fails the build if a generated catalog declares
  anything other than the configured version.
- **`ci/assert_catalog_set.py`** downloads the **released** binary (`BUMBLEBEE_RELEASE`),
  assembles the real directory — every asset this repo publishes *plus* the binary's own
  bundled `threat_intel` — and runs a real scan against it. This is the only check that can
  catch a bad set, because each file is individually valid and only the *combination* is
  illegal.

Note the deliberate split: `BUMBLEBEE_SHA` pins a `main` commit used **only** to build the
`osvcatalog` generator (which postdates the v0.1.1 tag), while `BUMBLEBEE_RELEASE` pins the
released binary used for **all acceptance validation**. Validating against `main` was the
original gap — `main` accepts catalogs the deployed binary rejects, so CI could go green
while every endpoint silently stopped detecting.

## Additional catalogs (`.github/workflows/extra-catalogs.yml`)

Two feeds broaden coverage beyond the OSSF malicious-packages set. Both run daily,
build against the same pinned Bumblebee commit, and go through the same
validate → positive-match self-test → publish path as the OSV catalog.

- **`datadog-malicious.json`** — from the
  [DataDog malicious-software-packages-dataset](https://github.com/DataDog/malicious-software-packages-dataset)
  (Apache-2.0). Additive to OSSF (which does not ingest it) and the only source
  here covering editor extensions. Its `null` (all-versions-malicious) records are
  dropped for exact-match ecosystems since Bumblebee v0.1 matches exact versions
  only — the same reason the OSV importer drops range-only records. The dataset
  also ships an `ai-skills` set that maps to Bumblebee's name-only `agent-skill`
  ecosystem; it is **omitted by default** until `agent-skill` is added to the
  published `exposure-catalog.schema.json` enum (the scanner already matches it at
  runtime — pass `--ecosystems npm,pypi,editor-extension,agent-skill` to
  `ci/datadog_catalog.py` to include it).
- **`ghsa-malicious.json`** — from the
  [GitHub Advisory Database](https://github.com/github/advisory-database) (CC-BY-4.0),
  keeping only CWE-506 ("Embedded Malicious Code") advisories. Strictly additive to
  `osv-malicious.json`: advisories that already alias an OSSF `MAL-` id are skipped.
  This fills a gap Bumblebee's own `osvcatalog` importer cannot — it only treats
  `MAL-` ids as malicious, so GHSA malware advisories that don't alias one are
  otherwise invisible.

## How it works (`.github/workflows/osv-catalog.yml`)

1. Checks out `perplexityai/bumblebee` at a **pinned commit** (`tools/osvcatalog` postdates the
   `v0.1.1` tag) and the OSSF feed (sparse `osv/malicious`).
2. Runs `osvcatalog` → `osv-malicious.json` (malicious-only, enumerated versions, `severity=critical`).
3. **Validates**: JSON parses, `schema_version == 0.1.0`, entry count hasn't dropped >10% vs last-good.
4. **Positive self-test**: builds a fixture from a real catalog entry and asserts a live
   `bumblebee scan --exposure-catalog` actually emits a `finding` — so a structurally-valid but
   non-matching catalog can't silently ship.
5. Publishes `osv-malicious.json` + `catalog-meta.json` to the moving `catalog-latest` release.

A weekly `keepalive` commit prevents GitHub from auto-disabling the scheduled workflow after 60
days of inactivity.

To regenerate on demand: **Actions → Generate OSV exposure catalog → Run workflow**
(`force_publish` overrides the entry-count floor).
