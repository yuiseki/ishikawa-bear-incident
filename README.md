# ishikawa-bear-incident

Reproducible collection of the 石川県クマ出没データ (bear incidents, six CSVs) of Ishikawa Prefecture.
The dataset card is generated into `data/README.md` (not tracked; the data is published at
https://huggingface.co/datasets/yuiseki/ishikawa-bear-incident).

```
uv run python scripts/01_download.py      # six CSVs and the catalogue metadata (data/raw/<date>)
uv run python scripts/02_export_parquet.py
uv run python scripts/03_verify.py        # each Parquet vs its CSV, with a second reader
uv run python scripts/04_card.py
uv run python src/publish.py [--push]     # dry run by default
```

Code: MIT. Data: CC BY 4.0, see the card.
