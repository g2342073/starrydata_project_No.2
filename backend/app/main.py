from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Literal
import duckdb
import json
from .config import SAMPLE_PARQUET, PAPERS_PARQUET
from . import db_init

app = FastAPI(title="Starry Sample Viewer")

# CORS 設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://starrydata-project-no-2-frontend.onrender.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



class SearchRequest(BaseModel):
    # 既存互換
    components: List[str] = []

    # 追加：単一入力文字列
    query: Optional[str] = None

    # 追加：検索モード
    mode: Literal["all_terms", "exact"] = "all_terms"

class AxisOption(BaseModel):
    prop_x: str
    prop_y: str
    unit_x_list: List[str]
    unit_y_list: List[str]


class SearchResponse(BaseModel):
    axis_options: List[AxisOption]
    form_category_options: List[str]


class Point(BaseModel):
    SID: str
    x: float
    y: float
    composition: str

    form_category: Optional[str] = None
    form_comment: Optional[str] = None

    purity_category: Optional[str] = None
    purity_comment: Optional[str] = None

class FilterResponse(BaseModel):
    axis_x: str
    axis_y: str
    points: List[Point]


class Paper(BaseModel):
    SID: str
    DOI: Optional[str] = None
    URL: Optional[str] = None
    issued: Optional[str] = None
    author: Optional[str] = None
    title: Optional[str] = None
    container_title: Optional[str] = None
    container_title_short: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    page: Optional[str] = None
    ISSN: Optional[str] = None
    publisher: Optional[str] = None
    project_names: Optional[str] = None
    created_at: Optional[str] = None


import sqlite3
from .config import SQLITE_DB_PATH   

con = sqlite3.connect(SQLITE_DB_PATH, check_same_thread=False)


@app.on_event("startup")
def startup_event():
    print("[startup] SQLite DB を開きます")

    try:
        con.execute("SELECT 1")
        print("[startup] SQLite DB 接続 OK")
    except Exception as e:
        print("[startup] SQLite DB 接続エラー:", e)
    # ★ ここで Parquet → SQLite の初期化を実行する
    try:
        print("[startup] Parquet → SQLite 初期化開始")
        db_init.ensure_parquet()   # ← これが超重要
        print("[startup] Parquet → SQLite 初期化完了")
    except Exception as e:
        print("[startup] 初期化エラー:", e)
        
    print("[startup] アプリケーション起動処理完了")


import re

def build_components_filter_sql(components: List[str], query: Optional[str], mode: str) -> str:
    """
    composition に対する検索条件を SQL 文字列で返す．
    mode:
      - "all_terms": 空白区切り語をすべて含む（AND，部分一致）
      - "exact": 入力文字列と完全一致（大文字小文字を無視）
    """
    # query が与えられていて components が空なら，query を空白分割して components を作る
    if (not components) and query is not None:
        q = query.strip()
        if q:
            components = [t for t in re.split(r"\s+", q) if t]

    if mode == "exact":
        # 完全一致．components ではなく query を使う．
        if query is None:
            return "1=1"
        q = query.strip()
        if not q:
            return "1=1"
        q_escaped = q.replace("'", "''")
        # 大文字小文字を無視して一致
        return f"lower(composition) = lower('{q_escaped}')"

    # デフォルト：all_terms（従来互換）
    if not components:
        return "1=1"

    clauses = []
    for c in components:
        c = (c or "").strip()
        if not c:
            continue
        c_escaped = c.replace("'", "''")
        clauses.append(f"lower(composition) LIKE '%' || lower('{c_escaped}') || '%'")

    return " AND ".join(clauses) if clauses else "1=1"


@app.post("/api/search", response_model=SearchResponse)
def search_axis(request: SearchRequest):
    condition = build_components_filter_sql(request.components, request.query, request.mode)

    # prop_x, prop_y ごとに unit_x / unit_y のユニークリストを集計
    sql = f"""
        SELECT
            prop_x,
            prop_y,
            GROUP_CONCAT(DISTINCT unit_x) AS unit_x_list,
            GROUP_CONCAT(DISTINCT unit_y) AS unit_y_list
        FROM sample
        WHERE {condition}
        GROUP BY prop_x, prop_y
        ORDER BY prop_x, prop_y
    """
    try:
        rows = con.execute(sql).fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"search_axis error: {e}")

    axis_options: List[AxisOption] = []
    for r in rows:
        prop_x = r[0]
        prop_y = r[1]
        # DuckDB の list() 集計結果は Python の list で返ってきます
        raw_unit_x = r[2] or ""
        raw_unit_y = r[3] or ""

        # None を除去して文字列だけにする
        unit_x_list = [u.strip() for u in raw_unit_x.split(",") if u.strip()]
        unit_y_list = [u.strip() for u in raw_unit_y.split(",") if u.strip()]
        axis_options.append(
            AxisOption(
                prop_x=prop_x,
                prop_y=prop_y,
                unit_x_list=unit_x_list,
                unit_y_list=unit_y_list,
            )
        )

        form_sql = f"""
            SELECT DISTINCT sample_info
            FROM sample
            WHERE {condition}
        """

        form_categories = set()

        try:
            form_rows = con.execute(form_sql).fetchall()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"form_category search error: {e}")

        for fr in form_rows:
            raw = fr[0]
            if not raw:
                continue

            try:
                info = json.loads(raw)
            except Exception:
                continue

            form = info.get("Form")
            if isinstance(form, dict):
                cat = form.get("category")
            elif isinstance(form, str):
                cat = form
            else:
                cat = None

            if cat is not None:
                cat = str(cat).strip()
                if cat:
                    form_categories.add(cat)

    return SearchResponse(
        axis_options=axis_options,
        form_category_options=sorted(form_categories)
    )


def _to_float_or_none(v) -> Optional[float]:
    """空欄や変な値を安全に None / float に変換."""
    if v is None:
        return None
    s = str(v).strip()
    if s == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None


@app.post("/api/filter", response_model=FilterResponse)
def filter_points(payload: dict = Body(...)):
    try:
        components = payload.get("components") or []

        # 追加：単一入力文字列とモード
        query = payload.get("query")
        mode = payload.get("mode") or "all_terms"

        prop_x = str(payload.get("prop_x", "") or "")
        prop_y = str(payload.get("prop_y", "") or "")

        unit_x = str(payload.get("unit_x", "") or "")
        unit_y = str(payload.get("unit_y", "") or "")

        form_category_filter = str(payload.get("form_category", "") or "")

        if not prop_x or not prop_y:
            raise HTTPException(status_code=400, detail="prop_x / prop_y が指定されていません。")

        x_min = _to_float_or_none(payload.get("x_min"))
        x_max = _to_float_or_none(payload.get("x_max"))
        y_min = _to_float_or_none(payload.get("y_min"))
        y_max = _to_float_or_none(payload.get("y_max"))

        # ここが重要：query と mode を渡す
        condition = build_components_filter_sql(components, query, mode)

        prop_x_escaped = prop_x.replace("'", "''")
        prop_y_escaped = prop_y.replace("'", "''")

        axis_conditions = [
            f"prop_x = '{prop_x_escaped}'",
            f"prop_y = '{prop_y_escaped}'",
        ]

        if unit_x:
            unit_x_escaped = unit_x.replace("'", "''")
            axis_conditions.append(f"unit_x = '{unit_x_escaped}'")

        if unit_y:
            unit_y_escaped = unit_y.replace("'", "''")
            axis_conditions.append(f"unit_y = '{unit_y_escaped}'")

        axis_cond = " AND ".join(axis_conditions)

        range_conditions = []
        if x_min is not None:
            range_conditions.append(f"x >= {x_min}")
        if x_max is not None:
            range_conditions.append(f"x <= {x_max}")
        if y_min is not None:
            range_conditions.append(f"y >= {y_min}")
        if y_max is not None:
            range_conditions.append(f"y <= {y_max}")

        where_clauses = [condition, axis_cond]
        if range_conditions:
            where_clauses.extend(range_conditions)

        where_sql = " AND ".join(where_clauses)

        sql = f"""
            SELECT SID, x, y, composition, sample_info
            FROM sample
            WHERE {where_sql}
            ORDER BY SID
        """
        rows = con.execute(sql).fetchall()

        points = []

        for r in rows:
            info = {}

            if r[4]:
                try:
                    info = json.loads(r[4])
                except Exception:
                    info = {}

            form = info.get("Form", {})
            purity = info.get("Purity", {})

            if not isinstance(form, dict):
                form = {"category": str(form), "comment": ""}

            if not isinstance(purity, dict):
                purity = {"category": str(purity), "comment": ""}

            form_category = form.get("category")
            form_comment = form.get("comment")
            purity_category = purity.get("category")
            purity_comment = purity.get("comment")

            # ★ Form category で絞り込み
            if form_category_filter and form_category != form_category_filter:
                continue

            points.append(
                Point(
                    SID=str(r[0]),
                    x=float(r[1]),
                    y=float(r[2]),
                    composition=r[3],
                    form_category=form_category,
                    form_comment=form_comment,
                    purity_category=purity_category,
                    purity_comment=purity_comment,
                )
            )

        return FilterResponse(axis_x=prop_x, axis_y=prop_y, points=points)

    except HTTPException:
        # 上で自分で投げた HTTPException はそのまま
        raise
    except Exception as e:
        # それ以外は 500 にまとめる
        raise HTTPException(status_code=500, detail=f"filter_points error: {e}")

@app.get("/api/paper/{sid}", response_model=Paper)
def get_paper(sid: str):
    sid_escaped = sid.replace("'", "''")
    sql = f"""
        SELECT *
        FROM papers
        WHERE SID = '{sid_escaped}'
        LIMIT 1
    """
    try:
        row = con.execute(sql).fetchone()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"get_paper error: {e}")

    if not row:
        raise HTTPException(status_code=404, detail="Paper not found")

    col_names = [d[0] for d in con.description]
    data = dict(zip(col_names, row))

    return Paper(
        SID=str(data.get("SID", "")),
        DOI=data.get("DOI"),
        URL=data.get("URL"),
        issued=str(data.get("issued")) if data.get("issued") is not None else None,
        author=data.get("author"),
        title=data.get("title"),
        container_title=data.get("container_title"),
        container_title_short=data.get("container_title_short"),
        volume=str(data.get("volume")) if data.get("volume") is not None else None,
        issue=str(data.get("issue")) if data.get("issue") is not None else None,
        page=data.get("page"),
        ISSN=data.get("ISSN"),
        publisher=data.get("publisher"),
        project_names=data.get("project_names"),
        created_at=str(data.get("created_at")) if data.get("created_at") is not None else None,
    )
@app.post("/api/search")
def search_papers(req: SearchRequest):
    con = sqlite3.connect(SQLITE_PATH)
    con.row_factory = sqlite3.Row

    q = f"%{req.query.lower()}%"

    rows = con.execute(
        """
        SELECT *
        FROM papers
        WHERE
            lower(DOI) LIKE ?
            OR lower(composition) LIKE ?
            OR lower(project_names) LIKE ?
            OR lower(comments) LIKE ?
        """,
        (q, q, q, q)
    ).fetchall()

    con.close()

    return {"results": [dict(r) for r in rows]}



@app.get("/ping")
def ping():
    return {"message": "ok"}
