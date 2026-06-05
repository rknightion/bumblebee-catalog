# bumblebee-catalog

Rolling **OSV exposure catalog** for [Bumblebee](https://github.com/perplexityai/bumblebee),
generated every 4 hours from the [OSSF malicious-packages](https://github.com/ossf/malicious-packages)
feed and published as a release asset that managed endpoints fetch before each scan.

This repo contains **only public threat-intelligence data and the CI to assemble it** — no
secrets, no private data.

## Consume it

| Artifact | URL |
|----------|-----|
| Catalog (NDJSON-of-one-object, `schema_version` 0.1.0) | `https://github.com/rknightion/bumblebee-catalog/releases/latest/download/osv-malicious.json` |
| Provenance / freshness | `https://github.com/rknightion/bumblebee-catalog/releases/latest/download/catalog-meta.json` |

Endpoints combine this OSV catalog with the brew-bundled curated `threat_intel/*.json`
catalogs in a single `--exposure-catalog` directory. `catalog-meta.json` carries
`generated_at` for a catalog-freshness dead-man's switch (alert if stale).

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
