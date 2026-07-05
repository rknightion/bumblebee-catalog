#!/usr/bin/env python3
"""Convert the DataDog malicious-software-packages-dataset into a Bumblebee
exposure catalog.

Source: https://github.com/DataDog/malicious-software-packages-dataset
(Apache-2.0). Each `samples/<ecosystem>/manifest.json` maps a package name
to either `null` (every published version is malicious — a purpose-built
malicious package) or an explicit list of compromised version strings.

Bumblebee v0.1 matches EXACT versions only, so:
  * entries with an explicit version list are emitted verbatim;
  * `null` entries are emitted ONLY for name-only ecosystems (agent-skill,
    where the documented convention is `versions: [""]` to match every
    install regardless of ref) and otherwise SKIPPED and counted — we have
    no exact version to match on, exactly as the OSV importer skips
    range-only records.

This dataset is additive to the OSSF feed already published here: OSSF does
not ingest DataDog's data, and DataDog uniquely covers editor extensions and
AI agent skills. Output validates against
docs/schema/v0.1.0/exposure-catalog.schema.json in the pinned bumblebee.
"""
import argparse
import json
import os
import sys

# DataDog sample folder -> Bumblebee ecosystem. `agent-skill` is matched on
# name only (version intentionally empty) per bumblebee's inventory docs.
FOLDER_TO_ECOSYSTEM = {
    "npm": "npm",
    "pypi": "pypi",
    "ide_extensions": "editor-extension",
    "ai-skills": "agent-skill",
}

# Ecosystems whose entries match on name alone; a `null` (all-versions)
# record is representable here via the `versions: [""]` wildcard.
NAME_ONLY = {"agent-skill"}

SCHEMA_VERSION = "0.1.0"


def build_entries(samples_dir, ecosystems, stats):
    entries = []
    for folder, ecosystem in FOLDER_TO_ECOSYSTEM.items():
        if ecosystem not in ecosystems:
            continue
        manifest = os.path.join(samples_dir, folder, "manifest.json")
        if not os.path.isfile(manifest):
            print(f"datadog_catalog: no manifest for {folder} at {manifest}",
                  file=sys.stderr)
            continue
        with open(manifest) as f:
            data = json.load(f)
        for package, versions in sorted(data.items()):
            stats["seen"] += 1
            if versions:  # explicit list of compromised versions
                vers = sorted({str(v) for v in versions})
            elif ecosystem in NAME_ONLY:
                vers = [""]  # match every install of this name
            else:
                stats["skipped_no_versions"] += 1
                continue
            entries.append({
                "id": f"DATADOG-{ecosystem}:{package}",
                "ecosystem": ecosystem,
                "package": package,
                "versions": vers,
                "severity": "critical",
            })
            stats["by_ecosystem"][ecosystem] = \
                stats["by_ecosystem"].get(ecosystem, 0) + 1
    entries.sort(key=lambda e: (e["ecosystem"], e["package"], e["id"]))
    return entries


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", required=True,
                    help="path to the dataset's samples/ directory")
    ap.add_argument("--out", required=True)
    ap.add_argument("--source", default="",
                    help="provenance label (e.g. repo URL @ commit)")
    ap.add_argument("--ecosystems", default="npm,pypi,editor-extension",
                    help="comma-separated Bumblebee ecosystems to emit. "
                         "agent-skill is omitted by default until it is added "
                         "to the published exposure-catalog schema enum.")
    a = ap.parse_args()

    ecosystems = {e.strip() for e in a.ecosystems.split(",") if e.strip()}
    unknown = ecosystems - set(FOLDER_TO_ECOSYSTEM.values())
    if unknown:
        sys.exit(f"datadog_catalog: unknown ecosystem(s): {sorted(unknown)}")

    stats = {"seen": 0, "skipped_no_versions": 0, "by_ecosystem": {}}
    entries = build_entries(a.samples, ecosystems, stats)
    if not entries:
        sys.exit("datadog_catalog: produced 0 entries — refusing to write")

    catalog = {
        "schema_version": SCHEMA_VERSION,
        "_comment": {
            "source": a.source or "DataDog/malicious-software-packages-dataset",
            "note": "Malicious-package dataset (Apache-2.0). null "
                    "(all-versions) records are skipped for exact-match "
                    "ecosystems; see ci/datadog_catalog.py.",
            "ecosystems": sorted(ecosystems),
            "records_seen": stats["seen"],
            "skipped_no_versions": stats["skipped_no_versions"],
            "entries_by_ecosystem": stats["by_ecosystem"],
        },
        "entries": entries,
    }
    with open(a.out, "w") as f:
        json.dump(catalog, f, indent=2, sort_keys=False)
        f.write("\n")
    print(f"datadog_catalog: {len(entries)} entries "
          f"({stats['by_ecosystem']}) from {stats['seen']} records; "
          f"skipped {stats['skipped_no_versions']} no-version records",
          file=sys.stderr)


if __name__ == "__main__":
    main()
