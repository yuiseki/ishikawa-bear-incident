"""Check every Parquet against its CSV as served, with pyarrow's CSV reader (all columns as strings).

Every row: each column equals the CSV's text (an empty field is null), the latitude and longitude equal
the numbers, the point equals them, the date equals the parsed 出没日, and `row` is the position.
Also: row totals equal the CSV's, the sha256 of each CSV equals the manifest's.

    uv run python scripts/03_verify.py
"""

import datetime as dt
import hashlib
import importlib
import json
import sys
from pathlib import Path

import ishikawa as k
import pyarrow.csv as pacsv
import pyarrow.parquet as pq
from shapely import from_wkb

ROOT = Path(__file__).parents[1]


def main() -> int:
    exp = importlib.import_module("02_export_parquet")
    run = sorted((ROOT / "data" / "raw").glob("*/MANIFEST.json"))[-1].parent
    manifest = json.loads((run / "MANIFEST.json").read_text())
    cols = json.loads((ROOT / "data/parquet/columns.json").read_text())
    total = 0
    for name, fname in cols["files"].items():
        path = run / fname
        assert (
            hashlib.sha256(path.read_bytes()).hexdigest() == manifest["files"][fname]["sha256"]
        ), fname
        header = (k.COMMON + k.TABLES[name][1]) if name in k.TABLES else k.R7[1]
        src = pacsv.read_csv(
            path,
            read_options=pacsv.ReadOptions(encoding="utf-8"),
            parse_options=pacsv.ParseOptions(newlines_in_values=True),
            convert_options=pacsv.ConvertOptions(
                column_types={c: "string" for c in header}, strings_can_be_null=False
            ),
        ).to_pydict()
        t = pq.read_table(ROOT / "data" / "parquet" / f"{name}.parquet")
        d = t.to_pydict()
        n = len(src["WKT"])
        assert t.num_rows == n == cols["counts"][name], (name, t.num_rows, n)
        assert d["row"] == list(range(1, n + 1))
        for c in header:
            col = exp.NAMES[c]
            if col is None:
                continue
            for i in range(n):
                if c in ("緯度", "経度"):
                    assert d[col][i] == float(src[c][i]), (name, c, i)
                else:
                    assert d[col][i] == (src[c][i] or None), (name, c, i)
        for i in range(n):
            g = from_wkb(d["geometry"][i])
            assert (g.x, g.y) == (d["longitude"][i], d["latitude"][i]), (name, i)
            assert d["date"][i] == k.parse_date(src["出没日"][i]), (name, i)
            assert d["date"][i] is None or isinstance(d["date"][i], dt.date)
        total += n
        print(f"{name}: {n} rows equal the CSV")
    print(f"OK: {total} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
