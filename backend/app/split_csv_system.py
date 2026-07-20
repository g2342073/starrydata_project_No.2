import pandas as pd
import os
import sys

def split_csv(input_path, output_folder="data", max_mb=20):
    """
    CSVを自動で分割する
    max_mb: 1ファイルの最大サイズ(MB)
    """

    os.makedirs(output_folder, exist_ok=True)

    df = pd.read_csv(input_path)

    sample = df.head(1000).to_csv(index=False)
    bytes_per_row = len(sample) / 1000

    max_bytes = max_mb * 1024 * 1024
    rows_per_file = int(max_bytes / bytes_per_row)

    print(f"1ファイルあたり最大行数: {rows_per_file}")

    total_rows = len(df)
    part = 1
    start = 0

    while start < total_rows:
        end = min(start + rows_per_file, total_rows)
        part_df = df.iloc[start:end]

        output_path = os.path.join(output_folder, f"part{part}.csv")
        part_df.to_csv(output_path, index=False)

        print(f"Saved {output_path} ({len(part_df)} rows)")
        part += 1
        start = end

    print("=== 分割完了 ===")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("使い方: python split_csv_system.py <input_csv> <output_folder>")
        sys.exit(1)

    input_path = sys.argv[1]
    output_folder = sys.argv[2]

    split_csv(input_path, output_folder)
