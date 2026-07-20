#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import csv
import math
import os
import re
import tempfile
from typing import Callable, List, Optional

INPUT_PATH = "data/starrydata_curves.csv"
OUTPUT_PATH = "data/starrydata_curves.csv"


def normalize_spaces(text: str) -> str:
    """連続する空白を1つにし，前後の空白を削除する．"""
    return re.sub(r"[ \t]+", " ", text).strip()


def strip_outer_quotes(text: str) -> str:
    """先頭末尾のダブルクォーテーションを1組だけ外す．"""
    text = text.strip()
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        return text[1:-1]
    return text


def comment_equals(cell: str, expected: str) -> bool:
    """16列目のコメント比較用．CSV読み込み後に引用符が外れていても一致できるようにする．"""
    return strip_outer_quotes(cell.strip()) == expected


def split_bracket_list(cell: str) -> List[str]:
    """
    [1, 2, 3] のような文字列を要素列に分解する．
    外側の [] がなくても処理する．
    """
    s = cell.strip()
    if s.startswith("[") and s.endswith("]"):
        s = s[1:-1].strip()

    if s == "":
        return []

    return [part.strip() for part in s.split(",")]


def is_numeric_token(token: str) -> bool:
    """文字列が数値として解釈できるか判定する．"""
    token = token.strip()
    if token == "":
        return False

    # よくある欠損表現を除外
    lower = token.lower()
    if lower in {"nan", "none", "null", "-", "--", "n/a", "na"}:
        return False

    try:
        value = float(token)
        return math.isfinite(value)
    except ValueError:
        return False


def has_any_numeric_value(cell: str) -> bool:
    """[] 内に少なくとも1つ数値があるか判定する．"""
    return any(is_numeric_token(token) for token in split_bracket_list(cell))


def format_number(value: float) -> str:
    """CSVに戻すための数値整形．"""
    if not math.isfinite(value):
        return str(value)

    if value == 0:
        value = 0.0

    text = f"{value:.15g}"

    # -0 のような表現を避ける
    if text in {"-0", "-0.0"}:
        text = "0"

    return text


def transform_numeric_list(cell: str, func: Callable[[float], float]) -> str:
    """
    [] 内の数値トークンだけに変換を適用し，元と同じく [a,b,c] 形式で返す．
    非数値トークンはそのまま残す．
    """
    tokens = split_bracket_list(cell)
    new_tokens: List[str] = []

    for token in tokens:
        if is_numeric_token(token):
            new_value = func(float(token))
            new_tokens.append(format_number(new_value))
        else:
            new_tokens.append(token)

    return "[" + ",".join(new_tokens) + "]"


def replace_includes(text: str, old: str, new: str) -> str:
    """部分文字列を置換する．"""
    return text.replace(old, new)


def ensure_min_columns(row: List[str], min_cols: int = 16) -> List[str]:
    """列数不足に備えて空文字列で埋める．"""
    if len(row) < min_cols:
        row = row + [""] * (min_cols - len(row))
    return row


def process_row(row: List[str]) -> Optional[List[str]]:
    """
    1行を仕様どおりに変換する．
    削除対象なら None を返す．
    """

    row = ensure_min_columns(row, 16)

    # 1-based の列番号
    # 7列目 -> row[6]
    # 8列目 -> row[7]
    # 9列目 -> row[8]
    # 10列目 -> row[9]
    # 11列目 -> row[10]
    # 12列目 -> row[11]
    # 16列目 -> row[15]

    # ------------------------------------------------------------
    # 11列目・12列目に数値が書かれていない行は削除
    # ------------------------------------------------------------
    if not has_any_numeric_value(row[10]):
        return None
    if not has_any_numeric_value(row[11]):
        return None

    # ------------------------------------------------------------
    # 7～10列目の空白正規化
    # ------------------------------------------------------------
    for idx in (6, 7, 8, 9):
        row[idx] = normalize_spaces(row[idx])

    # ------------------------------------------------------------
    # プロパティ名の置換
    # ------------------------------------------------------------
    if row[6] == "thermopower":
        row[6] = "Seebeck coefficient"
    if row[7] == "thermopower":
        row[7] = "Seebeck coefficient"
    if row[7] == "Thermopower":
        row[7] = "Seebeck coefficient"
    if row[7] == "Seebeck coefficient at 550 K":
        row[7] = "Seebeck coefficient"
    if row[6] == "thickness":
        row[6] = "Thickness"
    if row[6] == "Time (h)":
        row[6] = "Time"
    if row[6] == "T":
        row[6] = "Temperature"
    if row[6] == "Inverse temperature":
        row[6] = "T^(-1)"
    if row[6] == "1/T":
        row[6] = "T^(-1)"
    if row[6] == "1/T^(-1/2)":
        row[6] = "T^(1/2)"
    if row[6] == "1/T^(-1/4)":
        row[6] = "T^(1/4)"
    if row[6] == "1000/T.":
        row[6] = "1000/T"
    if row[7] == "T":
        row[7] = "Temperature"
    if row[7] == "1/T":
        row[7] = "T^(-1)"
    if row[6] == "concentrations":
        row[6] = "Concentration"
    if row[6] == "Doping concentration, mol%":
        row[6] = "Doping concentration"
        row[8] = "mol%"
    if row[6] == "magnetic field":
        row[6] = "Magnetic field"
    if row[6] == "Magnetic Field":
        row[6] = "Magnetic field strength"
    if row[7] == "Magnetic Field":
        row[7] = "Magnetic field strength"
    if row[6] == "Magnetic field strength (H)":
        row[6] = "Magnetic field strength"
    if row[7] == "Magnetic field strength (H)":
        row[7] = "Magnetic field strength"

    # ------------------------------------------------------------
    # 単位名の置換
    # ------------------------------------------------------------
    if row[8] == "K^(-1)":
        row[8] = "1/K"
    if row[9] == "K^(-1)":
        row[9] = "1/K"
    if row[8] == "V*K^(-1)":
        row[8] = "V/K"
    if row[9] == "V*K^(-1)":
        row[9] = "V/K"
    if row[8] == "ohm^(-1)*m^(-1)":
        row[8] = "S*m^(-1)"
    if row[9] == "ohm^(-1)*m^(-1)":
        row[9] = "S*m^(-1)"

    row[8] = replace_includes(row[8], "m**2*kg/A/s**3", "V")
    row[9] = replace_includes(row[9], "m**2*kg/A/s**3", "V")
    row[8] = replace_includes(row[8], "kg*m**2/A/s**3", "V")
    row[9] = replace_includes(row[9], "kg*m**2/A/s**3", "V")

    # ------------------------------------------------------------
    # 条件付き単位修正・値変換
    # ------------------------------------------------------------
    if row[6] == "energy":
        row[8] = "eV"

    if row[6] == "T^(1/2)" and row[8] == "K":
        row[8] = "K^(1/2)"
    if row[6] == "T^(1/2)" and row[8] == "1/K^(-1/2)":
        row[8] = "K^(1/2)"
    if row[6] == "T^(1/4)" and row[8] == "T^(-1/4)":
        row[8] = "K^(1/4)"
    if row[6] == "T^(-1/4)" and row[8] == "K^(-1/2)":
        row[8] = "K^(-1/4)"
    if row[6] == "1000/T" and row[8] == "K":
        row[8] = "1/K"

    if row[7] == "Hall mobility":
        row[9] = "cm^2*V^(-1)*s^(-1)"
        row[11] = transform_numeric_list(row[11], lambda x: x * 100.0)

    if row[7] == "Carrier concentration" and row[9] == "m^(-3)":
        row[9] = "cm^(-3)"
        row[11] = transform_numeric_list(row[11], lambda x: x / 1_000_000.0)

    if row[6] == "Carrier concentration" and row[8] == "m^(-3)":
        row[8] = "cm^(-3)"
        row[10] = transform_numeric_list(row[10], lambda x: x / 1_000_000.0)

    if row[7] == "logσT" and row[9] == "S*m^(-1)*K":
        row[9] = "A**2*s**3*K/kg/m**3"

    if row[7] == "Seebeck coefficient" and comment_equals(row[15], "Y-axis unit is muV K^-1"):
        row[9] = "V/K"
        row[11] = transform_numeric_list(row[11], lambda x: x * 1_000_000.0)

    if row[7] == "Seebeck coefficient" and comment_equals(row[15], "y軸単位V/Kですが登録できませんでいた"):
        row[9] = "V/K"

    if row[7] == "Short-circuit current" and comment_equals(row[15], "Short-circuit current unit is mA, "):
        row[9] = "mA"

    if (
        row[7] == "Maximum output power"
        and comment_equals(row[15], "Short-circuit current unit is mA, Maximum output power unit is muW.")
    ):
        row[9] = "muW"

    if row[6] == "frequency" and comment_equals(row[15], "X-axis unit is GHz, Y-axis unit is K."):
        row[8] = "GHz"

    if row[6] == "Concentration" and comment_equals(row[15], "X axis unit is eV. In Fig 5., concentrations unit is cm^-2."):
        row[8] = "eV"

    if row[6] == "diameter" and comment_equals(row[15], "diameter unit is nm."):
        row[8] = "nm"

    if row[6] == "width" and comment_equals(row[15], "X-axis unit is nm"):
        row[8] = "nm"

    if row[6] == "diameter" and comment_equals(row[15], "diameter (nm)"):
        row[8] = "nm"

    if row[6] == "frequency" and comment_equals(row[15], "Frequency (Hz)"):
        row[8] = "Hz"

    if row[6] == "Resistivity" and row[8] == "ohm*m^-1":
        row[8] = "ohm*m"

    if row[7] == "Resistivity" and row[9] == "ohm*m^-1":
        row[9] = "ohm*m"

    if row[6] == "Seebeck coefficient" and row[8] == "V":
        row[8] = "V/K"

    if row[7] == "Seebeck coefficient" and row[9] == "V":
        row[9] = "V/K"

    if row[6] == "Temperature (oC)":
        row[6] = "Temperature"
        row[8] = "K"
        row[10] = transform_numeric_list(row[10], lambda x: x + 273.15)

    if row[6] == "Thickness" and row[8] == "m":
        row[8] = "nm"
        row[10] = transform_numeric_list(row[10], lambda x: x * 1_000_000_000.0)

    if row[7] == "Thickness" and row[9] == "m":
        row[9] = "nm"
        row[11] = transform_numeric_list(row[11], lambda x: x * 1_000_000_000.0)

    if row[6] == "Time (hour)" and row[8] == "-":
        row[6] = "Time"
        row[8] = "s"
        row[10] = transform_numeric_list(row[10], lambda x: x * 3600.0)

    return row


def main() -> None:
    if not os.path.exists(INPUT_PATH):
        raise FileNotFoundError(f"入力ファイルが見つかりません: {INPUT_PATH}")

    os.makedirs(os.path.dirname(os.path.abspath(OUTPUT_PATH)), exist_ok=True)

    # 同一ファイル上書きに対応するため，一時ファイルに書いてから置換する
    with open(INPUT_PATH, "r", encoding="utf-8", newline="") as fin, \
         tempfile.NamedTemporaryFile(
             "w",
             encoding="utf-8",
             newline="\n",
             delete=False,
             dir=os.path.dirname(os.path.abspath(OUTPUT_PATH)),
             suffix=".tmp"
         ) as fout:

        reader = csv.reader(fin)
        writer = csv.writer(fout, lineterminator="\n")

        # 1行目はヘッダーなので，変換せずそのまま書く
        header = next(reader, None)
        if header is not None:
            writer.writerow(header)

        # 2行目以降だけ変換処理する
        for row in reader:
            processed = process_row(row)
            if processed is not None:
                # 元の行を書き込む
                writer.writerow(processed)
                # Temperature(K) → Temperature(oC) の追加行を作る
                if processed[6] == "Temperature" and processed[8] == "K":
                    new_row = processed.copy()
                    # 単位を変更
                    new_row[8] = "oC"
                    # x値を273.15引く
                    new_row[10] = transform_numeric_list(new_row[10], lambda x: x - 273.15)
                    # 追加行を書き込む
                    writer.writerow(new_row)

        temp_path = fout.name

    os.replace(temp_path, OUTPUT_PATH)


if __name__ == "__main__":
    main()
