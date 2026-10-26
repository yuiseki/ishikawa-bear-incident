"""Write one GeoParquet per CSV of the 石川県クマ出没データ.

The six CSVs are not one table: the five R1 to R6 files are extractions by cause (forest, river,
attractants, young bears, the mass outbreak year R2) whose ID restarts every year and so is not a key;
the same incident can be in several of them. They are kept apart, one file each, plus the R7
sightings. Every column of the source is kept as the string the source has it (the counts are
"1", "1頭" or "-"; the village codes are in scientific notation, rounded by the source), plus `date`
(the date of 出没日, parsed from `R4.3.3`, `2019/1/8`, `2025.1.9` or an Excel serial number; null when empty) and `geometry`
(WKB Point from the longitude and latitude, WGS84 assumed). `row` is the position in the CSV.

    uv run python scripts/02_export_parquet.py [--version 2026-10-26]
"""

import argparse
import json
import sys
from pathlib import Path

import ishikawa as k
import pyarrow as pa
import pyarrow.parquet as pq
from shapely.geometry import Point

ROOT = Path(__file__).parents[1]
NAMES = {  # CSV column -> Parquet column
    "WKT": None, "ID": "id", "目撃痕跡種別": "record_type", "出没年": "year", "出没日": "date_text",
    "時刻": "time_text", "時間": "time_text", "市町名": "municipality", "場所": "place",
    "備考": "remarks", "頭数": "count_text", "集落": "settlement", "集落コード": "settlement_code",
    "500mメッシュコード": "mesh500_code", "緯度": "latitude", "経度": "longitude",
    "森林からの出没": "forest", "河川からの出没": "river", "誘引物が原因の出没": "attractant_cause",
    "誘引物と考えられるもの": "attractant", "繁殖・分散行動による出没": "young_bear",
    "大量出没年に特有の出没": "mass_outbreak", "月": "month_text", "番号": "number",
}  # fmt: skip


def table_of(rows: list[dict], header: list[str]) -> pa.Table:
    cols = [c for c in header if NAMES[c]]
    data = {"row": list(range(1, len(rows) + 1))}
    for c in cols:
        if c in ("緯度", "経度"):
            data[NAMES[c]] = [float(r[c]) for r in rows]
        else:
            data[NAMES[c]] = [r[c] if r[c] != "" else None for r in rows]
    data["date"] = [k.parse_date(r["出没日"]) for r in rows]
    data["geometry"] = [Point(float(r["経度"]), float(r["緯度"])).wkb for r in rows]
    t = pa.table(data)
    geo = {"version": "1.1.0", "primary_column": "geometry",
           "columns": {"geometry": {"encoding": "WKB", "geometry_types": ["Point"]}}}  # fmt: skip
    return t.replace_schema_metadata({b"geo": json.dumps(geo).encode()})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default=None)
    args = ap.parse_args()
    runs = sorted((ROOT / "data" / "raw").glob("*/MANIFEST.json"))
    raw = runs[-1].parent if args.version is None else ROOT / "data" / "raw" / args.version
    out = ROOT / "data" / "parquet"
    out.mkdir(parents=True, exist_ok=True)
    counts = {}
    specs = {t: (f, k.COMMON + extra) for t, (f, extra) in k.TABLES.items()}
    specs["sightings_r7"] = k.R7
    for name, (fname, header) in specs.items():
        rows = k.parse_csv((raw / fname).read_bytes(), header)
        pq.write_table(table_of(rows, header), out / f"{name}.parquet", compression="zstd")
        counts[name] = len(rows)
        print(name, len(rows))
    (out / "columns.json").write_text(
        json.dumps({"run": raw.name, "counts": counts,
                    "files": {t: s[0] for t, s in specs.items()}}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")  # fmt: skip
    return 0


if __name__ == "__main__":
    sys.exit(main())
