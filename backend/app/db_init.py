from pathlib import Path
import json
import re
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import duckdb
import sqlite3
import glob

# ============================
# 出力先を /tmp に変更
# ============================
PARQUET_DIR = Path("/tmp/parquet")
PARQUET_DIR.mkdir(parents=True, exist_ok=True)

SQLITE_PATH = Path("/tmp/starrydata.db")

# CSV の場所は GitHub の data/ を使う
CURVES_PARTS_DIR = Path("data/csv_parts_curves")
SAMPLES_PARTS_DIR = Path("data/csv_parts_samples")
PAPERS_PARTS_DIR = Path("data/csv_parts_papers")

SAMPLE_PARQUET = PARQUET_DIR / "sample.parquet"
PAPERS_PARQUET = PARQUET_DIR / "papers.parquet"


# ============================
# ここからあなたの既存処理
# ============================

def parse_number_array(value):
    ...
    # （あなたの元コードそのまま）


def parse_sample_info_to_map(value):
    ...
    # （あなたの元コードそのまま）


def ensure_parquet():
    print("[db_init] /tmp に Parquet と SQLite DB を作成します")

    # ---------------------------------------------------------
    # 1) curves（分割 CSV 全部）
    # ---------------------------------------------------------
    curve_csv_files = sorted(glob.glob(str(CURVES_PARTS_DIR / "*.csv")))
    temp_curves_parquet = PARQUET_DIR / "curves_long_tmp.parquet"

    writer = None
    fixed_schema = pa.schema([...])  # あなたの元コードそのまま

    for csv_path in curve_csv_files:
        for chunk_idx, chunk in enumerate(pd.read_csv(csv_path, chunksize=5000)):
            ...
            # あなたの元コードそのまま
            if writer is None:
                writer = pq.ParquetWriter(temp_curves_parquet, fixed_schema)
            writer.write_table(table)

    if writer:
        writer.close()

    # ---------------------------------------------------------
    # 2) samples（分割 CSV 全部）
    # ---------------------------------------------------------
    sample_csv_files = sorted(glob.glob(str(SAMPLES_PARTS_DIR / "*.csv")))
    samples_df = pd.concat([pd.read_csv(f) for f in sample_csv_files], ignore_index=True)
    ...
    temp_samples_parquet = PARQUET_DIR / "samples_tmp.parquet"
    samples_df.to_parquet(temp_samples_parquet, index=False)

    # ---------------------------------------------------------
    # 3) DuckDB 結合 → sample.parquet
    # ---------------------------------------------------------
    con = duckdb.connect(database=":memory:")
    con.execute(f"CREATE TABLE long_curves AS SELECT * FROM read_parquet('{temp_curves_parquet}')")
    con.execute(f"CREATE TABLE samples AS SELECT * FROM read_parquet('{temp_samples_parquet}')")

    con.execute(
        f"""
        COPY (
            SELECT ...
        )
        TO '{SAMPLE_PARQUET}' (FORMAT PARQUET)
        """
    )
    con.close()

    # ---------------------------------------------------------
    # 4) papers（分割 CSV 全部）
    # ---------------------------------------------------------
    papers_csv_files = sorted(glob.glob(str(PAPERS_PARTS_DIR / "*.csv")))
    papers_df = pd.concat([pd.read_csv(f) for f in papers_csv_files], ignore_index=True)
    papers_df.to_parquet(PAPERS_PARQUET, index=False)

    # ---------------------------------------------------------
    # 5) SQLite DB を /tmp に作成
    # ---------------------------------------------------------
    print(f"[db_init] SQLite DB を作成します: {SQLITE_PATH}")

    con = duckdb.connect(database=":memory:")
    con.execute(f"CREATE TABLE sample AS SELECT * FROM read_parquet('{SAMPLE_PARQUET}')")
    con.execute(f"CREATE TABLE papers AS SELECT * FROM read_parquet('{PAPERS_PARQUET}')")

    sqlite_con = sqlite3.connect(SQLITE_PATH)

    df_sample = con.execute("SELECT * FROM sample").fetchdf()
    df_sample.to_sql("sample", sqlite_con, if_exists="replace", index=False)

    df_papers = con.execute("SELECT * FROM papers").fetchdf()
    df_papers.to_sql("papers", sqlite_con, if_exists="replace", index=False)

    sqlite_con.close()
    con.close()

    print("[db_init] /tmp に SQLite DB 作成完了")
