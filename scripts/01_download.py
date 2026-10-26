"""Download the 石川県クマ出没データ from the open data catalogue of Ishikawa Prefecture.

Saves the catalogue's metadata (package_show) and the six CSV resources as served, with sha256 and
the Last-Modified, in data/raw/<version>/MANIFEST.json. Stops when the catalogue does not say
`cc-by` or a CSV is not one of those the scripts know. The version is the UTC date of the run.

    uv run python scripts/01_download.py [--version 2026-10-26]
"""

import argparse
import datetime as dt
import hashlib
import json
import sys
import time
import urllib.request
from pathlib import Path

import ishikawa as k

ROOT = Path(__file__).parents[1]
UA = "ishikawa-bear-incident/0.1 (+https://github.com/yuiseki/ishikawa-bear-incident)"


def get(url: str) -> tuple[bytes, dict]:
    with urllib.request.urlopen(
        urllib.request.Request(url, headers={"User-Agent": UA}), timeout=120
    ) as r:
        return r.read(), {h.lower(): v for h, v in r.headers.items()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default=dt.datetime.now(dt.UTC).strftime("%Y-%m-%d"))
    args = ap.parse_args()
    raw = ROOT / "data" / "raw" / args.version
    raw.mkdir(parents=True, exist_ok=True)
    body, _ = get(k.API_PACKAGE)
    pkg = json.loads(body)["result"]
    if pkg["license_id"] != k.LICENSE_ID:
        raise SystemExit(f"license_id is {pkg['license_id']!r}, not {k.LICENSE_ID}: stopping")
    (raw / "package.json").write_bytes(body)
    known = {f for f, _ in k.TABLES.values()} | {k.R7[0]}
    files = {
        "package.json": {
            "url": k.API_PACKAGE,
            "bytes": len(body),
            "sha256": hashlib.sha256(body).hexdigest(),
        }
    }
    csvs = [r for r in pkg["resources"] if r["format"] == "CSV"]
    names = {r["url"].rsplit("/", 1)[1] for r in csvs}
    if names != known:
        raise SystemExit(f"CSV resources changed: {sorted(names ^ known)}")
    for r in csvs:
        name = r["url"].rsplit("/", 1)[1]
        time.sleep(1)
        data, h = get(r["url"])
        (raw / name).write_bytes(data)
        files[name] = {
            "url": r["url"], "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "last_modified": h.get("last-modified"), "resource_name": r["name"],
            "resource_last_modified": r["last_modified"],
        }  # fmt: skip
        print(name, len(data))
    manifest = {
        "retrieved": args.version, "page": k.PACKAGE_URL, "title": pkg["title"],
        "license_id": pkg["license_id"], "metadata_modified": pkg["metadata_modified"], "files": files,
    }  # fmt: skip
    (raw / "MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
