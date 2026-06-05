#!/usr/bin/env python3
"""Assert a scan NDJSON contains a finding for the expected package@version."""
import argparse
import json
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ndjson", required=True)
    ap.add_argument("--seed-file", required=True)  # {"package":..., "version":...}
    a = ap.parse_args()
    with open(a.seed_file) as f:
        seed = json.load(f)
    name, ver = seed["package"], seed["version"]
    expect = f"{name}@{ver}"

    findings = []
    with open(a.ndjson) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("record_type") == "finding":
                findings.append(rec)

    for rec in findings:
        if rec.get("version") == ver and name in (
            rec.get("package_name"),
            rec.get("normalized_name"),
        ):
            print(f"OK: finding emitted for {expect} "
                  f"(catalog_id={rec.get('catalog_id')}, severity={rec.get('severity')})")
            return
    seen = [f"{f.get('package_name')}@{f.get('version', '')}" for f in findings][:5]
    sys.exit(f"FAIL: no finding for {expect}; saw {len(findings)} finding record(s): {seen}")


if __name__ == "__main__":
    main()
