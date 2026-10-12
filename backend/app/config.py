from pathlib import Path

# Render では /tmp が書き込み可能
SQLITE_DB_PATH = Path("/tmp/papers.db")

# Parquet は /tmp に置くのが安全
PARQUET_DIR = Path("/tmp/parquet_parts_papers")
