from pathlib import Path

# backend/app/config.py から見て 3階層上がるとプロジェクトルート
BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = BASE_DIR / "data"
PARQUET_DIR = DATA_DIR / "parquet_parts_papers"
SQLITE_DB_PATH = DATA_DIR / "papers.db"
