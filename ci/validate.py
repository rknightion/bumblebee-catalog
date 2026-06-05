#!/usr/bin/env python3
"""Validate a generated OSV exposure catalog and emit catalog-meta.json.

Checks: parses as JSON, schema_version == 0.1.0, entries is a non-empty list,
and (unless --force) the entry count hasn't dropped >10% vs the last-good
catalog. Writes catalog-meta.json (generated_at + provenance) which endpoints
fetch for a catalog-freshness dead-man's switch.
"""
import argparse
import json
import sys
from datetime import datetime, timezone

EXPECTED_SCHEMA = "0.1.0"


def load(path):
    with open(path) as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", required=True)
    ap.add_argument("--old", default="")
    ap.add_argument("--ossf-sha", default="")
    ap.add_argument("--bumblebee-sha", default="")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    try:
        cat = load(a.catalog)
    except Exception as e:
        sys.exit(f"FAIL: catalog does not parse as JSON: {e}")

    sv = cat.get("schema_version")
    if sv != EXPECTED_SCHEMA:
        sys.exit(f"FAIL: schema_version={sv!r}, expected {EXPECTED_SCHEMA!r} "
                 "(deployed binary would fail-closed on a mismatched catalog)")

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
    with open("catalog-meta.json", "w") as f:
        json.dump(meta, f, indent=2)
    print(f"OK: {n} entries (prev {old_n}), schema {sv}")


if __name__ == "__main__":
    main()
