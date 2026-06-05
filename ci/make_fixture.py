#!/usr/bin/env python3
"""Build a minimal npm project fixture from the first npm catalog entry.

Writes <out>/package-lock.json (lockfileVersion 3) containing the exact
(name, version) of a real catalog entry, so a scan against the catalog MUST
yield a finding. Prints "<package>@<version>" for the assertion step. This is a
self-derived positive test: it proves the freshly generated catalog both loads
and matches end-to-end, without hardcoding any package that might age out.
"""
import argparse
import json
import os
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    with open(a.catalog) as f:
        entries = json.load(f).get("entries", [])

    pick = None
    for e in entries:
        if e.get("ecosystem") == "npm" and e.get("package") and e.get("versions"):
            pick = (e["package"], e["versions"][0])
            break
    if not pick:
        sys.exit("FAIL: no npm entry with an enumerated version found in catalog")
    name, ver = pick

    os.makedirs(a.out, exist_ok=True)
    lock = {
        "name": "bumblebee-ci-fixture",
        "version": "1.0.0",
        "lockfileVersion": 3,
        "requires": True,
        "packages": {
            "": {
                "name": "bumblebee-ci-fixture",
                "version": "1.0.0",
                "dependencies": {name: ver},
            },
            f"node_modules/{name}": {
                "version": ver,
                "resolved": f"https://registry.npmjs.org/{name}/-/ci-{ver}.tgz",
                "integrity": "sha512-ci",
            },
        },
    }
    with open(os.path.join(a.out, "package-lock.json"), "w") as f:
        json.dump(lock, f, indent=2)
    print(f"{name}@{ver}")


if __name__ == "__main__":
    main()
