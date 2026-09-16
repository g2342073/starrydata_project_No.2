from pathlib import Path
import pandas as pd
import duckdb
import sqlite3
import glob

PARQUET_DIR = Path("/tmp/parquet")
PARQUET_DIR.mkdir(parents=True, exist_ok=True)

SQLITE_PATH = Path("/tmp/starrydata.db")

PAPERS_PARTS_DIR = Path("data/csv_parts_papers")
PAPERS_PARQUET = PARQUET_DIR / "papers.parquet"

def ensure_parquet():
    print("[db_init] /tmp に Parquet と SQLite DB を作成します")

    # ---------------------------------------------------------
    # papers（分割 CSV 全部）
    # ---------------------------------------------------------
    papers_csv_files = sorted(glob.glob(str(PAPERS_PARTS_DIR / "*.csv")))
    papers_df = pd.concat([pd.read_csv(f) for f in papers_csv_files], ignore_index=True)

    papers_df.to_parquet(PAPERS_PARQUET, index=False)

    # ---------------------------------------------------------
    # SQLite DB を /tmp に作成
    # ---------------------------------------------------------
    print(f"[db_init] SQLite DB を作成します: {SQLITE_PATH}")

    con = duckdb.connect(database=":memory:")
    con.execute(f"CREATE TABLE papers AS SELECT * FROM read_parquet('{PAPERS_PARQUET}')")

    sqlite_con = sqlite3.connect(SQLITE_PATH)

    df_papers = con.execute("SELECT * FROM papers").fetchdf()
    df_papers.to_sql("papers", sqlite_con, if_exists="replace", index=False)

    sqlite_con.close()
    con.close()

    print("[db_init] /tmp に SQLite DB 作成完了")
