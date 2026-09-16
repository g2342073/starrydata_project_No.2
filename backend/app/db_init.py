from pathlib import Path
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
    # DuckDB で Parquet を直接作成（pandas を使わない）
    # ---------------------------------------------------------
    papers_csv_files = sorted(glob.glob(str(PAPERS_PARTS_DIR / "*.csv")))

    con = duckdb.connect(database=":memory:")

    # 空のテーブルを作成（最初の CSV の構造を使う）
    first = papers_csv_files[0]
    con.execute(f"""
        CREATE TABLE papers AS
        SELECT * FROM read_csv_auto('{first}') LIMIT 0
    """)

    # 1ファイルずつ挿入（メモリをほぼ使わない）
    for f in papers_csv_files:
        con.execute(f"""
            INSERT INTO papers
            SELECT * FROM read_csv_auto('{f}')
        """)

    # Parquet に書き出し
    con.execute(f"""
        COPY papers TO '{PAPERS_PARQUET}' (FORMAT PARQUET)
    """)

    # ---------------------------------------------------------
# SQLite DB を /tmp に作成
# ---------------------------------------------------------
print(f"[db_init] SQLite DB を作成します: {SQLITE_PATH}")

sqlite_con = sqlite3.connect(SQLITE_PATH)
cur = sqlite_con.cursor()

# SQLite にテーブルを作成（DuckDB の構造を使う）
schema = con.execute("PRAGMA table_info('papers')").fetchall()

cols = []
for col in schema:
    name = col[1]
    type_ = col[2] or "TEXT"
    cols.append(f"{name} {type_}")

create_sql = f"CREATE TABLE IF NOT EXISTS papers ({', '.join(cols)});"
cur.execute(create_sql)

# DuckDB → SQLite に行を流し込む（numpy/pandas不要）
rows = con.execute("SELECT * FROM papers").fetchall()

placeholders = ",".join(["?"] * len(cols))
insert_sql = f"INSERT INTO papers VALUES ({placeholders})"

cur.executemany(insert_sql, rows)

sqlite_con.commit()
sqlite_con.close()
con.close()

print("[db_init] /tmp に SQLite DB 作成完了")
