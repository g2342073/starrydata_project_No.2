from pathlib import Path

# 永続フォルダ（Render で消えない）
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

# Parquet の保存先
PARQUET_DIR = DATA_DIR / "parquet_parts_papers"

# SQLite DB の保存先
SQLITE_DB_PATH = DATA_DIR / "starrydata.db"
