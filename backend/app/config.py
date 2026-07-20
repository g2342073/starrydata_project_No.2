import os
from pathlib import Path

# GitHub に置く CSV の場所（固定）
DATA_DIR = Path("data")

# Render の /tmp に Parquet を作る
PARQUET_DIR = Path("/tmp/parquet")

# 分割CSVの場所
CURVES_PARTS_DIR = DATA_DIR / "csv_parts_curves"
SAMPLES_PARTS_DIR = DATA_DIR / "csv_parts_samples"
PAPERS_PARTS_DIR = DATA_DIR / "csv_parts_papers"

# Parquet 出力先（/tmp）
SAMPLE_PARQUET = PARQUET_DIR / "sample.parquet"
PAPERS_PARQUET = PARQUET_DIR / "papers.parquet"

# SQLite DB の出力先（最重要）
SQLITE_DB_PATH = "/tmp/starrydata.db"
