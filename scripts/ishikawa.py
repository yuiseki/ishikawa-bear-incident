"""Shared helpers: the 石川県クマ出没データ (CKAN open data catalogue of Ishikawa) and how to read the CSVs."""

import csv
import datetime as dt
import io
import re

CKAN = "https://ckan.opendata.pref.ishikawa.lg.jp"
PACKAGE = "bear_incidents_data"
PACKAGE_URL = f"{CKAN}/dataset/{PACKAGE}"
API_PACKAGE = f"{CKAN}/api/3/action/package_show?id={PACKAGE}"
LICENSE_ID = "cc-by"

COMMON = [
    "WKT", "ID", "目撃痕跡種別", "出没年", "出没日", "時刻", "市町名", "場所", "備考", "頭数",
    "集落", "集落コード", "500mメッシュコード", "緯度", "経度",
]  # fmt: skip
# table -> (the CSV file name in the catalogue, the columns of the CSV after COMMON)
TABLES = {
    "forest_r1_r6": ("bear_incidents_forest_r1-r6.csv", ["森林からの出没"]),
    "river_r1_r6": ("bear_incidents_river_r1-r6.csv", ["河川からの出没"]),
    "attractants_r1_r6": (
        "bear_incidents_attractants_r1-r6.csv", ["誘引物が原因の出没", "誘引物と考えられるもの"],
    ),
    "young_bears_r1_r6": ("bear_incidents_young_bears_r1-r6.csv", ["繁殖・分散行動による出没"]),
    "mass_outbreak_r2": ("bear_incidents_mass_outbreak_r2.csv", ["大量出没年に特有の出没"]),
}  # fmt: skip
R7 = (
    "bear_sightings_r7.csv",
    ["WKT", "緯度", "経度", "出没日", "時間", "市町名", "場所", "備考", "頭数", "月", "番号"],
)
BBOX = (135.9, 36.0, 137.5, 37.6)  # lon min, lat min, lon max, lat max: Ishikawa with a margin

_ERA = re.compile(r"^R(\d+)\.(\d+)\.(\d+)$")
_SLASH = re.compile(r"^(\d{4})[/.](\d+)[/.](\d+)$")


def parse_date(s: str) -> dt.date | None:
    """`R4.3.3` (Reiwa 4), `2019/1/8`, `2025.1.9` or an Excel serial number such as `43575`; None for an empty string; ValueError otherwise."""
    if not s:
        return None
    m = _ERA.match(s)
    if m:
        return dt.date(int(m.group(1)) + 2018, int(m.group(2)), int(m.group(3)))
    m = _SLASH.match(s)
    if m:
        return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    if (
        re.fullmatch(r"\d{5}", s) and 40000 <= int(s) < 50000
    ):  # an Excel serial day number, left in by the source
        return dt.date(1899, 12, 30) + dt.timedelta(days=int(s))
    raise ValueError(f"unknown date {s!r}")


def point_of(wkt: str) -> tuple[float, float]:
    m = re.fullmatch(r"POINT \(([\d.]+) ([\d.]+)\)", wkt)
    if m is None:
        raise ValueError(f"unexpected WKT {wkt!r}")
    return float(m.group(1)), float(m.group(2))


def parse_csv(data: bytes, header: list[str]) -> list[dict]:
    """Every row as a dict of the source's own columns, as strings; checks the header, the points and the dates."""
    rows = list(csv.DictReader(io.StringIO(data.decode("utf-8-sig"), newline="")))
    if not rows or list(rows[0]) != header:
        raise ValueError(f"unexpected header {list(rows[0]) if rows else None}")
    for i, r in enumerate(rows):
        if None in r or None in r.values():
            raise ValueError(f"row {i}: ragged")
        x, y = point_of(r["WKT"])
        lon, lat = float(r["経度"]), float(r["緯度"])
        if abs(x - lon) > 1e-6 or abs(y - lat) > 1e-6:
            raise ValueError(f"row {i}: WKT and the latitude and longitude differ")
        if not (BBOX[0] <= lon <= BBOX[2] and BBOX[1] <= lat <= BBOX[3]):
            raise ValueError(f"row {i}: point outside Ishikawa ({lat}, {lon})")
        parse_date(r["出没日"])
    return rows
