import requests
from pathlib import Path
from .config import PARQUET_DIR

# Parquet フォルダを作る
PARQUET_DIR.mkdir(parents=True, exist_ok=True)

URLS = [
    "https://mmcfbpjelndhpmiaftny.supabase.co/storage/v1/object/public/starrydata/part1.parquet",
    "https://mmcfbpjelndhpmiaftny.supabase.co/storage/v1/object/public/starrydata/part2.parquet",
    "https://mmcfbpjelndhpmiaftny.supabase.co/storage/v1/object/public/starrydata/part3.parquet",
    "https://mmcfbpjelndhpmiaftny.supabase.co/storage/v1/object/public/starrydata/part4.parquet",
    "https://mmcfbpjelndhpmiaftny.supabase.co/storage/v1/object/public/starrydata/part5.parquet",

    #論文データ
    "https://mmcfbpjelndhpmiaftny.supabase.co/storage/v1/object/public/starrydata/papers_part1.parquet",
    "https://mmcfbpjelndhpmiaftny.supabase.co/storage/v1/object/public/starrydata/papers_part2.parquet",
]

def download_parquet_files():
    for url in URLS:
        filename = url.split("/")[-1]
        save_path = PARQUET_DIR / filename

        if save_path.exists():
            print(f"[skip] {filename} は既に存在します")
            continue

        print(f"[download] {filename} をダウンロード中…")
        r = requests.get(url)
        r.raise_for_status()

        with open(save_path, "wb") as f:
            f.write(r.content)

        print(f"[done] {filename} を保存しました")
