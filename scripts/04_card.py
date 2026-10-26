"""Write data/README.md (the dataset card), data/LICENSE and data/provenance.yaml.

uv run python scripts/04_card.py
"""

import json
import sys
from collections import Counter
from pathlib import Path

import ishikawa as k
import pyarrow.parquet as pq

ROOT = Path(__file__).parents[1]
REPO = "ishikawa-bear-incident"

CARD = """---
license: cc-by-4.0
license_name: cc-by-4.0
license_link: https://creativecommons.org/licenses/by/4.0/legalcode.ja
language:
- ja
tags:
- japan
- ishikawa
- bear
- wildlife
- geospatial
size_categories:
- 1K<n<10K
pretty_name: Bear incidents of Ishikawa Prefecture (石川県クマ出没データ)
---

# {repo}

The bear incident records (sightings, traces, injuries to people) that Ishikawa Prefecture's
nature conservation division published in its open data catalogue as 石川県クマ出没データ: the
R1 to R6 analysis maps (FY2019 to FY2024; five files, each the incidents of one cause) and the R7
sightings (calendar year 2025). {total:,} rows in six tables, each as GeoParquet.

## Source

- Catalogue entry: <{page}> (石川県オープンデータカタログ, 自然環境課), titled 「{title}」, licence
  `{license_id}` (Creative Commons Attribution), update frequency 「随時」, metadata last modified
  {meta_modified}.
- Files: six CSVs as served (UTF-8 with a byte order mark), kept unchanged under `raw/{run}/` with their
  sha256 in `MANIFEST.json`, with the catalogue's `package.json`. Fetched {fetched}; the resources were
  last modified {res_modified} according to the catalogue. The source can change the files; this
  repository holds the state of {fetched}.

## Files

| Table (Parquet) | CSV | Rows | What the source says it is |
|---|---|---|---|
{table_rows}

## Columns

The columns of the source are kept as the strings the source has them (empty is null), under English
names, plus `row`, `date` and `geometry`. Latitude and longitude are numbers.

| Column | Source column | Content |
|---|---|---|
| `row` | | position in the CSV, from 1 |
| `id` | ID | the source's ID, as text (`1.0` in some files, `1` in others) |
| `record_type` | 目撃痕跡種別 | 目撃, 痕跡, 人身被害 |
| `year` | 出没年 | fiscal year as `R1` to `R6` |
| `date_text`, `date` | 出没日 | the text of the source and the date parsed from it |
| `time_text` | 時刻 (R7: 時間) | text such as `18時30分頃` |
| `municipality`, `place` | 市町名, 場所 | |
| `remarks` | 備考 | free text of the report |
| `count_text` | 頭数 | text: `1`, `1頭`, `-` |
| `settlement`, `settlement_code`, `mesh500_code` | 集落, 集落コード, 500mメッシュコード | the codes are as the source has them (see known issues) |
| `latitude`, `longitude` | 緯度, 経度 | |
| `forest`, `river`, `attractant_cause`, `attractant`, `young_bear`, `mass_outbreak` | the last columns of each R1 to R6 file | the flag of the cause that the file is about (`1` or `1.0`); `attractant` is 誘引物と考えられるもの |
| `month_text`, `number` | 月, 番号 | R7 only |
| `geometry` | WKT | the point as WKB (longitude, latitude), WGS84 assumed |

## What was changed

- Column names, the empty fields (null), `row`, and `date` (parsed from the source's date text, whose
  forms are `R4.3.3`, `2019/1/8`, `2025.1.9` and, in {serial} rows, an Excel serial number such as
  `43575`; {nodate} rows have no date) and `geometry` were added. No value of the source was
  changed: the Parquet was checked against the CSV with a second CSV reader, every row and column.
- The WKT of the source equals the latitude and longitude of the same row in all {total:,} rows
  (checked, 1e-6); the geometry is built from them. The source states no datum; WGS84 is assumed.
- Nothing was removed, merged or corrected, and the five R1 to R6 tables were not merged.

## Known issues

- The five R1 to R6 files are extractions by cause of one set of incidents: the same incident can be
  in several tables ({overlap:,} of the {r16:,} rows share the date, place and coordinates with a
  row of another table). `id` restarts every year, so it is not a key (an ID is shared by up to
  {max_dup} rows in a table), and it cannot join the tables. Do not add the tables up as a count of
  incidents.
- The village codes (`settlement_code`) and the mesh codes (`mesh500_code`) were written in scientific
  notation by a spreadsheet in the source. Where the source kept all digits (`1.720204001E9`) the code
  can be read back; in {rounded:,} rows of the codes' columns only three digits are left (`1.72E+09`)
  and the code cannot be recovered. They are kept as text, not repaired.
- The count is text: `1`, `1頭`, `-` or empty; `date_text` mixes forms; one row of the forest table
  has the record type `1`; one row of the river table has the ID `v`.
- The R7 file is a different table (no ID, no codes). Its `number` column is empty in all rows.
- The place and the free text are reports as received; the accuracy of the points is not stated.
- R7 covers calendar year 2025 up to {r7_last}; the files can be updated by the prefecture.

## Licence

The catalogue states Creative Commons Attribution (`cc-by`; the version is not given) for the entry. This
dataset is offered under CC BY 4.0 and the credit is to Ishikawa Prefecture:

> 出典：石川県「石川県クマ出没データ」（{page}）を加工して作成
"""


def main() -> int:
    run = sorted((ROOT / "data" / "raw").glob("*/MANIFEST.json"))[-1].parent
    m = json.loads((run / "MANIFEST.json").read_text())
    cols = json.loads((ROOT / "data/parquet/columns.json").read_text())
    assert cols["run"] == run.name
    total = sum(cols["counts"].values())
    tabs = {
        t: pq.read_table(ROOT / "data/parquet" / f"{t}.parquet").drop(["geometry"]).to_pydict()
        for t in cols["counts"]
    }
    table_rows = "\n".join(
        f"| `{t}.parquet` | `{cols['files'][t]}` | {cols['counts'][t]:,} | {m['files'][cols['files'][t]]['resource_name']} |"
        for t in cols["counts"]
    )
    r16 = [t for t in tabs if t != "sightings_r7"]
    keys = {
        t: [
            (d, la, lo)
            for d, la, lo in zip(
                tabs[t]["date_text"], tabs[t]["latitude"], tabs[t]["longitude"], strict=True
            )
        ]
        for t in r16
    }
    cnt = Counter(k_ for t in r16 for k_ in set(keys[t]))
    overlap = sum(1 for t in r16 for k_ in keys[t] if cnt[k_] > 1)
    max_dup = max(max(Counter(tabs[t]["id"]).values()) for t in r16)
    res_dates = sorted(
        {
            e["resource_last_modified"][:10]
            for n, e in m["files"].items()
            if "resource_last_modified" in e
        }
    )
    r7 = [d for d in tabs["sightings_r7"]["date"] if d]
    card = CARD.format(
        repo=REPO, page=k.PACKAGE_URL, title=m["title"], license_id=m["license_id"], total=total,
        meta_modified=m["metadata_modified"][:10], run=run.name, fetched=run.name,
        res_modified=", ".join(res_dates), table_rows=table_rows,
        serial=sum(1 for t in tabs for d, x in zip(tabs[t]["date_text"], tabs[t]["date"], strict=True) if d and d.isdigit()),
        nodate=sum(1 for t in tabs for d in tabs[t]["date"] if d is None),
        rounded=sum(1 for t in tabs for v in tabs[t].get("settlement_code", []) if v and "E" in v and len(v.split("E")[0]) <= 4),
        overlap=overlap, r16=sum(cols["counts"][t] for t in r16), max_dup=max_dup, r7_last=max(r7),
    )  # fmt: skip
    data = ROOT / "data"
    (data / "README.md").write_text(card, encoding="utf-8")
    (data / "LICENSE").write_text(
        "CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/legalcode)\n\n"
        "The records are from 石川県クマ出没データ, published in the prefecture's open data catalogue\n"
        f"under Creative Commons Attribution ({k.PACKAGE_URL}), processed as described in README.md.\n"
        f"Credit: 出典：石川県「石川県クマ出没データ」（{k.PACKAGE_URL}）を加工して作成\n",
        encoding="utf-8",
    )
    (data / "provenance.yaml").write_text(
        f"source: 石川県クマ出没データ\nurl: {k.PACKAGE_URL}\nlicense: {m['license_id']}\nrun: {run.name}\n"
        f"retrieved: {run.name}\nmetadata_modified: {m['metadata_modified']}\nrows: {total}\n",
        encoding="utf-8",
    )
    print("wrote data/README.md, LICENSE, provenance.yaml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
