#!/usr/bin/env python3
"""Prove the published catalog SET loads together in the DEPLOYED binary.

This is the guard for the failure mode that has no other detection.

Endpoints do not consume these catalogs one at a time. They drop every asset
published here into a single directory alongside the binary's own bundled
`threat_intel/*.json` and pass that directory to `--exposure-catalog`.
bumblebee's directory loader (`internal/exposure/exposure.go`, `loadDir`)
requires every file in the directory to declare the SAME `schema_version`, and
a mismatch is fatal:

    exposure catalog <b> declares schema_version "0.1.0" which conflicts
    with "0.2.0" from <a>

`cmd/bumblebee/main.go` turns that into **exit 2 before the scan starts** --
no packages, no findings, and no `scan_summary`. The run is completely silent,
so no freshness or finding alert can fire. Detection is simply off.

Per-file validation cannot catch this: each catalog is individually valid, and
only the COMBINATION is illegal. Nor can validating against `main`: the fleet
runs a pinned RELEASE, and v0.1.2 accepts only "0.1.0" while `main` accepts
both. A catalog that main loads happily can be rejected outright by the binary
that is actually deployed.

So this check does the only thing that settles it: assemble the real directory
and run the real deployed binary against it.

Usage:
    python3 ci/assert_catalog_set.py \
        --binary ./bin/bumblebee-release \
        --bundled ./release/threat_intel \
        --catalog osv-malicious.json --catalog datadog-malicious.json
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile


def schema_of(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh).get("schema_version")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--binary", required=True,
                    help="the DEPLOYED bumblebee binary (a released build, not a main checkout)")
    ap.add_argument("--bundled", default="",
                    help="the binary's bundled threat_intel dir, if the release ships one")
    ap.add_argument("--catalog", action="append", default=[], required=True,
                    help="a catalog this repo publishes (repeatable)")
    a = ap.parse_args()

    # 1. Every published catalog must agree with every other.
    seen = {}
    for c in a.catalog:
        seen.setdefault(schema_of(c), []).append(os.path.basename(c))
    if len(seen) > 1:
        print("FAIL: published catalogs declare conflicting schema_versions.", file=sys.stderr)
        for v, files in sorted(seen.items()):
            print(f"  {v}: {', '.join(files)}", file=sys.stderr)
        print("An endpoint staging these together gets exit 2 and scans nothing.", file=sys.stderr)
        return 1
    published = next(iter(seen))
    print(f"OK: all {len(a.catalog)} published catalogs declare schema_version {published}")

    # 2. They must also agree with the catalogs the binary itself ships,
    #    because the endpoint puts both in the same directory.
    bundled_files = []
    if a.bundled and os.path.isdir(a.bundled):
        bundled_files = [os.path.join(a.bundled, f)
                         for f in sorted(os.listdir(a.bundled)) if f.endswith(".json")]
        bundled_versions = {schema_of(f) for f in bundled_files}
        if bundled_versions and bundled_versions != {published}:
            print(f"FAIL: binary ships threat_intel at {sorted(bundled_versions)} but this repo "
                  f"publishes {published}. Endpoints stage BOTH in one directory, so this "
                  "combination exits 2 and disables detection.", file=sys.stderr)
            return 1
        print(f"OK: {len(bundled_files)} bundled threat_intel catalogs also at {published}")

    # 3. The decisive check: assemble the real directory and run the real
    #    deployed binary against it.
    workdir = tempfile.mkdtemp()
    catdir = os.path.join(workdir, "catalog")
    probe = os.path.join(workdir, "probe")
    os.makedirs(catdir)
    os.makedirs(probe)
    for src in list(a.catalog) + bundled_files:
        shutil.copyfile(src, os.path.join(catdir, os.path.basename(src)))

    proc = subprocess.run(
        [a.binary, "scan", "--profile", "baseline", "--root", probe,
         "--exposure-catalog", catdir, "--max-duration", "60s",
         "--output", "file", "--output-file", os.path.join(workdir, "out.ndjson")],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        print(f"FAIL: the deployed binary rejected the assembled catalog directory "
              f"(exit {proc.returncode}).", file=sys.stderr)
        print(proc.stderr.strip()[:2000], file=sys.stderr)
        return 1

    out_path = os.path.join(workdir, "out.ndjson")
    if not os.path.exists(out_path):
        print("FAIL: binary exited 0 but produced no output file; treating as a load failure.",
              file=sys.stderr)
        return 1

    print(f"OK: deployed binary loaded all {len(a.catalog) + len(bundled_files)} catalogs "
          "from one directory and completed a scan")
    return 0


if __name__ == "__main__":
    sys.exit(main())
