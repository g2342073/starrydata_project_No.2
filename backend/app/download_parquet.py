import requests
from pathlib import Path

# Parquet を保存するフォルダ
PARQUET_DIR = Path("/tmp/parquet_parts_papers")
PARQUET_DIR.mkdir(parents=True, exist_ok=True)

# Supabase の URL を貼る（あなたがコピーしたやつ）
URLS = [
    "https://mmcfbpjelndhpmiaftny.supabase.co/storage/v1/object/public/starrydata/part1.parquet",
    "https://mmcfbpjelndhpmiaftny.supabase.co/storage/v1/object/public/starrydata/part2.parquet",
    "https://mmcfbpjelndhpmiaftny.supabase.co/storage/v1/object/public/starrydata/part3.parquet",
    "https://mmcfbpjelndhpmiaftny.supabase.co/storage/v1/object/public/starrydata/part4.parquet",
    "https://mmcfbpjelndhpmiaftny.supabase.co/storage/v1/object/public/starrydata/part5.parquet",
]

def download_parquet_files():
    for url in URLS:
        filename = url.split("/")[-1]
        save_path = PARQUET_DIR / filename

        # 既にあるならスキップ（Render の再起動時に無駄なダウンロードを防ぐ）
        if save_path.exists():
            print(f"[skip] {filename} は既に存在します")
            continue

        print(f"[download] {filename} をダウンロード中…")
        r = requests.get(url)
        r.raise_for_status()

        with open(save_path, "wb") as f:
            f.write(r.content)

        print(f"[done] {filename} を保存しました")
