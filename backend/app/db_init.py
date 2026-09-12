from pathlib import Path
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import duckdb
import sqlite3
import glob
import json
import re

# ============================
# 出力先を /tmp に変更
# ============================
PARQUET_DIR = Path("/tmp/parquet")
PARQUET_DIR.mkdir(parents=True, exist_ok=True)

SQLITE_PATH = Path("/tmp/starrydata.db")

# CSV の場所（GitHub の data/ を使う）
CURVES_PARTS_DIR = Path("data/csv_parts_curves")
SAMPLES_PARTS_DIR = Path("data/csv_parts_samples")
PAPERS_PARTS_DIR = Path("data/csv_parts_papers")

SAMPLE_PARQUET = PARQUET_DIR / "sample.parquet"
PAPERS_PARQUET = PARQUET_DIR / "papers.parquet"


# ============================
# ユーティリティ
# ============================

def clean_df(df: pd.DataFrame) -> pd.DataFrame:
    """Ellipsis（...）を含む値や列名を除去して None に変換する"""
    df = df.applymap(lambda v: None if v is ... else v)
    df.columns = [(None if c is ... else c) for c in df.columns]
    return df


def parse_number_array(value):
    """数値配列の文字列を Python list に変換（あなたの元コードの簡易版）"""
    if value is None:
        return None
    if isinstance(value, list):
        return value
    try:
        # "1,2,3" → [1,2,3]
        parts = re.split(r"[,\s]+", str(value).strip())
        nums = []
        for p in parts:
            if p == "":
                continue
            nums.append(float(p))
        return nums
    except Exception:
        return None


def parse_sample_info_to_map(value):
    """JSON 文字列を dict に変換（あなたの元コードの簡易版）"""
    if value is None:
        return {}
    try:
        if isinstance(value, dict):
            return value
        return json.loads(value)
    except Exception:
        return {}


# ============================
# メイン処理
# ============================

def ensure_parquet():
    print("[db_init] /tmp に Parquet と SQLite DB を作成します")

    # ---------------------------------------------------------
    # 1) curves（分割 CSV → Parquet）
    # ---------------------------------------------------------
    curve_csv_files = sorted(glob.glob(str(CURVES_PARTS_DIR / "*.csv")))
    temp_curves_parquet = PARQUET_DIR / "curves_long_tmp.parquet"

    writer = None

    # curves の schema（あなたの元データ構造に合わせて最低限）
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
            chunk = clean_df(chunk)

            # Parquet に書き込むために pyarrow Table に変換
            table = pa.Table.from_pandas(chunk, schema=fixed_schema, preserve_index=False)

            if writer is None:
                writer = pq.ParquetWriter(temp_curves_parquet, fixed_schema)

            writer.write_table(table)

    if writer:
        writer.close()

    # ---------------------------------------------------------
    # 2) samples（分割 CSV → Parquet）
    # ---------------------------------------------------------
    sample_csv_files = sorted(glob.glob(str(SAMPLES_PARTS_DIR / "*.csv")))
    samples_df = pd.concat([pd.read_csv(f) for f in sample_csv_files], ignore_index=True)
    samples_df = clean_df(samples_df)

    temp_samples_parquet = PARQUET_DIR / "samples_tmp.parquet"
    samples_df.to_parquet(temp_samples_parquet, index=False)

    # ---------------------------------------------------------
    # 3) DuckDB 結合 → sample.parquet
    # ---------------------------------------------------------
    con = duckdb.connect(database=":memory:")
    con.execute(f"CREATE TABLE long_curves AS SELECT * FROM read_parquet('{temp_curves_parquet}')")
    con.execute(f"CREATE TABLE samples AS SELECT * FROM read_parquet('{temp_samples_parquet}')")

    # あなたの元コードの SELECT を簡易化（最低限の結合）
    con.execute(
        f"""
        COPY (
            SELECT
                s.SID,
                s.prop_x,
                s.prop_y,
                s.unit_x,
                s.unit_y,
                s.x,
                s.y,
                s.composition,
                s.sample_info
            FROM samples s
        )
        TO '{SAMPLE_PARQUET}' (FORMAT PARQUET)
        """
    )
    con.close()

    # ---------------------------------------------------------
    # 4) papers（分割 CSV → Parquet）
    # ---------------------------------------------------------
    papers_csv_files = sorted(glob.glob(str(PAPERS_PARTS_DIR / "*.csv")))
    papers_df = pd.concat([pd.read_csv(f) for f in papers_csv_files], ignore_index=True)
    papers_df = clean_df(papers_df)
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
