import sqlite3
import pyarrow.parquet as pq
from pathlib import Path

from .config import PARQUET_DIR, SQLITE_DB_PATH

DB_PATH = SQLITE_DB_PATH

def init_db():
    # Parquet フォルダが無ければ作る
    PARQUET_DIR.mkdir(parents=True, exist_ok=True)

    print("[db_init] SQLite DB を新規作成:", DB_PATH)

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    # papers テーブル
    cur.execute("""
        CREATE TABLE papers (
            SID TEXT,
            DOI TEXT,
            composition TEXT,
            sample_id TEXT,
            figure_id TEXT,
            prop_x TEXT,
            prop_y TEXT,
            unit_x TEXT,
            unit_y TEXT,
            x REAL,
            y REAL,
            created_at TEXT,
            updated_at TEXT,
            project_names TEXT,
            comments TEXT
        )
    """)

    # Parquet を読み込んで papers に挿入
    for pq_file in PARQUET_DIR.glob("*.parquet"):
        print(f"[load] {pq_file.name} を読み込み中…")
        table = pq.read_table(pq_file)
        df = table.to_pandas()
        df.to_sql("papers", con, if_exists="append", index=False)
        print(f"[done] {pq_file.name} を挿入しました")

    # sample テーブル
    cur.execute("""
        CREATE TABLE sample (
            SID TEXT,
            composition TEXT,
            prop_x TEXT,
            prop_y TEXT,
            unit_x TEXT,
            unit_y TEXT,
            x REAL,
            y REAL,
            sample_info TEXT
        )
    """)

    # papers → sample にコピー
    cur.execute("""
        INSERT INTO sample (SID, composition, prop_x, prop_y, unit_x, unit_y, x, y, sample_info)
        SELECT
            SID,
            composition,
            prop_x,
            prop_y,
            unit_x,
            unit_y,
            x,
            y,
            '{}'
        FROM papers
    """)

    con.commit()
    con.close()

    print("\n=== SQLite DB 初期化完了 ===")
