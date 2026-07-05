#!/usr/bin/env python3
"""Convert GitHub Advisory Database *malware* advisories into a Bumblebee
exposure catalog.

Source: https://github.com/github/advisory-database (CC-BY-4.0), OSV JSON
under `advisories/github-reviewed/YYYY/MM/GHSA-.../GHSA-....json`.

GitHub marks a malicious-package advisory with CWE-506 ("Embedded Malicious
Code") in `database_specific.cwe_ids`. Bumblebee's own `osvcatalog` importer
CANNOT surface these directly: it only treats a record as malicious when its
id (or an alias) is an OSSF `MAL-` id, so a GHSA malware advisory that does
not alias a MAL- id is dropped. This converter fills exactly that gap:

  * keep only advisories carrying CWE-506;
  * by default SKIP advisories that already alias a `MAL-` id — those are
    already covered by the OSSF `osv-malicious.json` asset, so this feed is
    strictly additive to it;
  * emit one entry per affected package that maps to a supported ecosystem
    AND enumerates exact versions (range-only advisories are skipped and
    counted, matching v0.1's exact-match constraint).
"""
import argparse
import json
import os
import sys

# OSV ecosystem string -> Bumblebee ecosystem. Mirrors bumblebee's
# internal/osv ecosystemMap; ecosystems with no on-disk inventory
# (crates.io, NuGet, Maven, ...) are intentionally absent and skipped.
ECOSYSTEM_MAP = {
    "npm": "npm",
    "PyPI": "pypi",
    "Go": "go",
    "RubyGems": "rubygems",
    "Packagist": "packagist",
    "VSCode": "editor-extension",
}

MALWARE_CWE = "CWE-506"
SCHEMA_VERSION = "0.1.0"


def cwe_ids(obj):
    ds = (obj or {}).get("database_specific") or {}
    ids = ds.get("cwe_ids") or []
    return ids if isinstance(ids, list) else []


def is_malware(rec):
    if MALWARE_CWE in cwe_ids(rec):
        return True
    # Some advisories carry the CWE only on the affected entry.
    return any(MALWARE_CWE in cwe_ids(a) for a in rec.get("affected", []))


def aliases_mal(rec):
    return any(isinstance(a, str) and a.startswith("MAL-")
               for a in rec.get("aliases", []))


def map_ecosystem(osv_eco):
    base = osv_eco.split(":", 1)[0]  # "Debian:11" -> "Debian"
    return ECOSYSTEM_MAP.get(base)


def record_to_entries(rec, ecosystems, stats):
    if rec.get("withdrawn"):
        stats["skipped_withdrawn"] += 1
        return []
    if not is_malware(rec):
        return []  # ordinary vulnerability advisory, not our concern
    stats["malware_seen"] += 1
    if rec.get("_skip_mal_aliased") and aliases_mal(rec):
        stats["skipped_mal_aliased"] += 1
        return []
    ghsa_id = rec.get("id", "")
    out = []
    for aff in rec.get("affected", []):
        pkg = aff.get("package") or {}
        eco = map_ecosystem(pkg.get("ecosystem", ""))
        name = pkg.get("name", "")
        if not eco or eco not in ecosystems or not name:
            stats["skipped_ecosystem"] += 1
            continue
        versions = aff.get("versions") or []
        versions = sorted({str(v) for v in versions if str(v)})
        if not versions:  # range-only: no exact version to match on
            stats["skipped_no_versions"] += 1
            continue
        out.append({
            "id": f"{ghsa_id}#{eco}:{name}",
            "ecosystem": eco,
            "package": name,
            "versions": versions,
            "severity": "critical",
        })
    return out


def iter_json_files(path):
    if os.path.isfile(path):
        yield path
        return
    for root, _dirs, files in os.walk(path):
        for fn in files:
            if fn.endswith(".json"):
                yield os.path.join(root, fn)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--advisories", required=True,
                    help="path to advisories/github-reviewed (or a single "
                         ".json advisory)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--source", default="")
    ap.add_argument("--ecosystems",
                    default="npm,pypi,go,rubygems,packagist,editor-extension")
    ap.add_argument("--include-mal-aliased", action="store_true",
                    help="also emit advisories that alias an OSSF MAL- id "
                         "(overlaps the osv-malicious.json asset)")
    a = ap.parse_args()

    ecosystems = {e.strip() for e in a.ecosystems.split(",") if e.strip()}
    unknown = ecosystems - set(ECOSYSTEM_MAP.values())
    if unknown:
        sys.exit(f"ghsa_catalog: unknown ecosystem(s): {sorted(unknown)}")

    stats = {"files": 0, "malware_seen": 0, "skipped_mal_aliased": 0,
             "skipped_no_versions": 0, "skipped_ecosystem": 0,
             "skipped_withdrawn": 0, "bad": 0}
    entries = []
    for fp in iter_json_files(a.advisories):
        stats["files"] += 1
        try:
            with open(fp) as f:
                rec = json.load(f)
        except (json.JSONDecodeError, OSError):
            stats["bad"] += 1
            continue
        if not isinstance(rec, dict) or not rec.get("id"):
            stats["bad"] += 1
            continue
        rec["_skip_mal_aliased"] = not a.include_mal_aliased
        entries.extend(record_to_entries(rec, ecosystems, stats))

    # Deduplicate by id (same package can appear once); keep sorted output.
    dedup = {}
    for e in entries:
        dedup.setdefault(e["id"], e)
    entries = sorted(dedup.values(),
                     key=lambda e: (e["ecosystem"], e["package"], e["id"]))
    if not entries:
        sys.exit("ghsa_catalog: produced 0 entries — refusing to write")

    catalog = {
        "schema_version": SCHEMA_VERSION,
        "_comment": {
            "source": a.source or "github/advisory-database (CWE-506)",
            "note": "GHSA malware advisories additive to osv-malicious.json; "
                    "MAL-aliased and range-only records skipped. See "
                    "ci/ghsa_catalog.py.",
            "ecosystems": sorted(ecosystems),
            "malware_advisories_seen": stats["malware_seen"],
            "skipped_mal_aliased": stats["skipped_mal_aliased"],
            "skipped_no_versions": stats["skipped_no_versions"],
        },
        "entries": entries,
    }
    with open(a.out, "w") as f:
        json.dump(catalog, f, indent=2, sort_keys=False)
        f.write("\n")
    print(f"ghsa_catalog: {len(entries)} entries from {stats['malware_seen']} "
          f"malware advisories ({stats['files']} files); skipped "
          f"{stats['skipped_mal_aliased']} mal-aliased, "
          f"{stats['skipped_no_versions']} range-only, "
          f"{stats['skipped_ecosystem']} unsupported-ecosystem",
          file=sys.stderr)


if __name__ == "__main__":
    main()
