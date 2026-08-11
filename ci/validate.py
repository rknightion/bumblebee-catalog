#!/usr/bin/env python3
"""Validate a generated exposure catalog and emit its *-meta.json.

Checks: parses as JSON, schema_version matches the target, entries is a
non-empty list, and (unless --force) the entry count hasn't dropped >10% vs
the last-good catalog. Writes the meta file (generated_at + provenance) which
endpoints fetch for a catalog-freshness dead-man's switch.

WHY THE SCHEMA VERSION IS LOAD-BEARING
--------------------------------------
Endpoints point `--exposure-catalog` at a DIRECTORY holding every catalog:
the binary's own bundled `threat_intel/*.json` plus each asset published here.
bumblebee's directory loader requires every file in that directory to declare
the SAME schema_version, and a mismatch is fatal -- it exits 2 BEFORE scanning,
emitting no records at all, not even a scan_summary. There is nothing left to
alert on.

So the version this repo publishes is not a free choice. It must equal the
schema the DEPLOYED binary ships and accepts:

  * v0.1.2 (the current release, and what the fleet runs) supports ONLY
    "0.1.0" and hard-rejects "0.2.0" with
    `unsupported exposure catalog schema_version "0.2.0"`.
  * bumblebee `main` has moved to "0.2.0" (adds any-version "*" entries) and
    its bundled threat_intel catalogs are already bumped, but no release
    carries it yet.

Therefore: do NOT bump --target-schema ahead of the endpoints. The order is
(1) a bumblebee release supporting the new schema exists, (2) the deployment's
pinned BUMBLEBEE_VERSION is raised to it and has rolled out, (3) only then
bump here. Bumping here first silently drops this repo's catalogs from every
endpoint's scan.
"""
import argparse
import json
import sys
from datetime import datetime, timezone


def load(path):
    with open(path) as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", required=True)
    ap.add_argument("--old", default="")
    ap.add_argument("--ossf-sha", default="")
    ap.add_argument("--bumblebee-sha", default="")
    ap.add_argument("--meta-out", default="catalog-meta.json",
                    help="path to write the freshness/provenance metadata")
    ap.add_argument("--label", default="",
                    help="human label identifying which catalog this is")
    ap.add_argument("--provenance", action="append", default=[],
                    metavar="KEY=VALUE",
                    help="extra provenance pairs to stamp into the metadata "
                         "(repeatable)")
    ap.add_argument("--target-schema", default="0.1.0",
                    help="schema_version the DEPLOYED binary supports; the catalog must "
                         "declare exactly this (see module docstring before changing it)")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    try:
        cat = load(a.catalog)
    except Exception as e:
        sys.exit(f"FAIL: catalog does not parse as JSON: {e}")

    sv = cat.get("schema_version")
    if sv != a.target_schema:
        sys.exit(f"FAIL: schema_version={sv!r}, expected {a.target_schema!r}. "
                 "Endpoints load every catalog from ONE directory and bumblebee refuses a "
                 "directory that mixes schema versions -- it exits 2 before scanning, with no "
                 "records and nothing to alert on. Publishing this would silently disable "
                 "detection fleet-wide.")

    entries = cat.get("entries")
    if not isinstance(entries, list) or not entries:
        sys.exit(f"FAIL: entries missing or empty (got {type(entries).__name__})")
    n = len(entries)

    old_n = None
    if a.old:
        try:
            old_n = len(load(a.old).get("entries", []))
        except Exception:
            old_n = None  # first run / no previous asset
    if old_n and not a.force:
        floor = int(old_n * 0.9)
        if n < floor:
            sys.exit(f"FAIL: entry count dropped {old_n} -> {n} (< floor {floor}); "
                     "refusing to publish. Re-run with force_publish=true to override.")

    meta = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "schema_version": sv,
        "entry_count": n,
        "previous_entry_count": old_n,
        "ossf_sha": a.ossf_sha,
        "bumblebee_sha": a.bumblebee_sha,
    }
    if a.label:
        meta["catalog"] = a.label
    for pair in a.provenance:
        key, sep, value = pair.partition("=")
        if not sep:
            sys.exit(f"FAIL: --provenance expects KEY=VALUE, got {pair!r}")
        meta[key.strip()] = value.strip()
    with open(a.meta_out, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"OK: {n} entries (prev {old_n}), schema {sv}"
          + (f" [{a.label}]" if a.label else ""))


if __name__ == "__main__":
    main()
