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

# CSV の場所
CURVES_PARTS_DIR = Path("data/csv_parts_curves")
SAMPLES_PARTS_DIR = Path("data/csv_parts_samples")
PAPERS_PARTS_DIR = Path("data/csv_parts_papers")

SAMPLE_PARQUET = PARQUET_DIR / "sample.parquet"
PAPERS_PARQUET = PARQUET_DIR / "papers.parquet"


# ============================
# 安全な clean_df
# ============================
def clean_df(df):
    """Ellipsis を除去。DataFrame 以外はそのまま返す。"""
    if not isinstance(df, pd.DataFrame):
        return df

    # 値の中の Ellipsis を除去
    df = df.applymap(lambda v: None if v is ... else v)

    # 列名に Ellipsis が入っている場合も除去
    df.columns = [(None if c is ... else c) for c in df.columns]

    return df



# ============================
# メイン処理
# ============================
def ensure_parquet():
    print("[db_init] /tmp に Parquet と SQLite DB を作成します")

    # ---------------------------------------------------------
    # 1) curves
    # ---------------------------------------------------------
    curve_csv_files = sorted(glob.glob(str(CURVES_PARTS_DIR / "*.csv")))
    temp_curves_parquet = PARQUET_DIR / "curves_long_tmp.parquet"

    writer = None
    fixed_schema = pa.schema([
        ("SID", pa.string()),
        ("prop_x", pa.string()),
        ("prop_y", pa.string()),
        ("unit_x", pa.string()),
        ("unit_y", pa.string()),
        ("x", pa.float64()),
        ("y", pa.float64()),
        ("composition", pa.string()),
        ("sample_info", pa.string()),
    ])

    for csv_path in curve_csv_files:
        for chunk_idx, chunk in enumerate(pd.read_csv(csv_path, chunksize=5000)):
            chunk = clean_df(chunk)  # ← DataFrame のときだけ動く

            table = pa.Table.from_pandas(chunk, schema=fixed_schema, preserve_index=False)

            if writer is None:
                writer = pq.ParquetWriter(temp_curves_parquet, fixed_schema)

            writer.write_table(table)

    if writer:
        writer.close()

    # ---------------------------------------------------------
    # 2) samples
    # ---------------------------------------------------------
    sample_csv_files = sorted(glob.glob(str(SAMPLES_PARTS_DIR / "*.csv")))
    samples_df = pd.concat([pd.read_csv(f) for f in sample_csv_files], ignore_index=True)
    samples_df = clean_df(samples_df)

    temp_samples_parquet = PARQUET_DIR / "samples_tmp.parquet"
    samples_df.to_parquet(temp_samples_parquet, index=False)

    # ---------------------------------------------------------
    # 3) DuckDB 結合
    # ---------------------------------------------------------
    con = duckdb.connect(database=":memory:")
    con.execute(f"CREATE TABLE long_curves AS SELECT * FROM read_parquet('{temp_curves_parquet}')")
    con.execute(f"CREATE TABLE samples AS SELECT * FROM read_parquet('{temp_samples_parquet}')")

    con.execute(
        f"""
        COPY (
            SELECT *
            FROM samples
        )
        TO '{SAMPLE_PARQUET}' (FORMAT PARQUET)
        """
    )
    con.close()

    # ---------------------------------------------------------
    # 4) papers
    # ---------------------------------------------------------
    papers_csv_files = sorted(glob.glob(str(PAPERS_PARTS_DIR / "*.csv")))
    papers_df = pd.concat([pd.read_csv(f) for f in papers_csv_files], ignore_index=True)
    papers_df = clean_df(papers_df)
    papers_df.to_parquet(PAPERS_PARQUET, index=False)

    # ---------------------------------------------------------
    # 5) SQLite
    # ---------------------------------------------------------
    print(f"[db_init] SQLite DB を作成します: {SQLITE_PATH}")

    con = duckdb.connect(database=":memory:")
    con.execute(f"CREATE TABLE sample AS SELECT * FROM read_parquet('{SAMPLE_PARQUET}')")
    con.execute(f"CREATE TABLE papers AS SELECT * FROM read_parquet('{PAPERS_PARQUET}')")

    sqlite_con = sqlite3.connect(SQLITE_PATH)

    df_sample = con.execute("SELECT * FROM sample").fetchdf()
    df_sample = clean_df(df_sample)
    df_sample.to_sql("sample", sqlite_con, if_exists="replace", index=False)

    df_papers = con.execute("SELECT * FROM papers").fetchdf()
    df_papers = clean_df(df_papers)
    df_papers.to_sql("papers", sqlite_con, if_exists="replace", index=False)

    sqlite_con.close()
    con.close()

    print("[db_init] /tmp に SQLite DB 作成完了")
