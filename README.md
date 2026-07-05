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

Endpoints combine these catalogs with the brew-bundled curated `threat_intel/*.json`
catalogs in a single `--exposure-catalog` directory — Bumblebee loads every catalog
in the directory and matches against the union. Each `*-meta.json` carries
`generated_at` for a catalog-freshness dead-man's switch (alert if stale).

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
