import sqlite3
import json
from pathlib import Path
import pyarrow.parquet as pq

from .config import SAMPLE_PARQUET, PAPERS_PARQUET, SQLITE_DB_PATH

def ensure_parquet():
    """
    Parquet → SQLite を初期化する。
    DuckDB を使わず、pyarrow で直接読み込む。
    """

    print("[db_init] SQLite DB を作成します:", SQLITE_DB_PATH)

    # DB ファイル削除（毎回クリーンに）
    if SQLITE_DB_PATH.exists():
        SQLITE_DB_PATH.unlink()

    con = sqlite3.connect(SQLITE_DB_PATH)
    cur = con.cursor()

    # sample テーブル作成
    cur.execute("""
        CREATE TABLE sample (
            SID TEXT,
            prop_x TEXT,
            prop_y TEXT,
            unit_x TEXT,
            unit_y TEXT,
            x REAL,
            y REAL,
            composition TEXT,
            sample_info TEXT
        )
    """)

    # papers テーブル作成
    cur.execute("""
        CREATE TABLE papers (
            SID TEXT,
            DOI TEXT,
            URL TEXT,
            issued TEXT,
            author TEXT,
            title TEXT,
            container_title TEXT,
            container_title_short TEXT,
            volume TEXT,
            issue TEXT,
            page TEXT,
            ISSN TEXT,
            publisher TEXT,
            project_names TEXT,
            created_at TEXT
        )
    """)

    # ---- sample.parquet を読み込む ----
    print("[db_init] sample.parquet を読み込みます:", SAMPLE_PARQUET)
    table = pq.read_table(SAMPLE_PARQUET)
    df = table.to_pandas()

    rows = []
    for _, row in df.iterrows():
        rows.append((
            row.get("SID"),
            row.get("prop_x"),
            row.get("prop_y"),
            row.get("unit_x"),
            row.get("unit_y"),
            row.get("x"),
            row.get("y"),
            row.get("composition"),
            json.dumps(row.get("sample_info"))
        ))

    cur.executemany("""
        INSERT INTO sample VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)

    # ---- papers.parquet を読み込む ----
    print("[db_init] papers.parquet を読み込みます:", PAPERS_PARQUET)
    table2 = pq.read_table(PAPERS_PARQUET)
    df2 = table2.to_pandas()

    rows2 = []
    for _, row in df2.iterrows():
        rows2.append(tuple(row.values))

    cur.executemany("""
        INSERT INTO papers VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rows2)

    con.commit()
    con.close()

    print("[db_init] SQLite DB 初期化完了")
