import numpy as np
import glob

def clean_df(df: pd.DataFrame) -> pd.DataFrame:
    """Ellipsis（...）を含む値や列名を除去して None に変換する"""
    # 値の中の Ellipsis を除去
    df = df.applymap(lambda v: None if v is ... else v)

    # 列名に Ellipsis が入っている場合も除去
    df.columns = [(None if c is ... else c) for c in df.columns]

    return df


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

            # ★ Ellipsis を除去
            chunk = clean_df(chunk)

            # あなたの元コードそのまま
            ...

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

    # ★ Ellipsis を除去
    samples_df = clean_df(samples_df)

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

    # ★ Ellipsis を除去
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
    df_sample = clean_df(df_sample)  # ★ 念のためもう一度除去
    df_sample.to_sql("sample", sqlite_con, if_exists="replace", index=False)

    df_papers = con.execute("SELECT * FROM papers").fetchdf()
    df_papers = clean_df(df_papers)
    df_papers.to_sql("papers", sqlite_con, if_exists="replace", index=False)

    sqlite_con.close()
    con.close()

    print("[db_init] /tmp に SQLite DB 作成完了")
