from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Literal
import json
import logging
import sqlite3
from pathlib import Path

from .config import SQLITE_DB_PATH
from . import db_init

logging.basicConfig(level=logging.DEBUG)

app = FastAPI(title="Starry Sample Viewer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://starrydata-project-no-2-frontend.onrender.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# グローバル接続（startup で初期化）
con = None

@app.on_event("startup")
def startup_event():
    global con

    # DB がなければ初期化
    if not SQLITE_DB_PATH.exists():
        print("[startup] DB が存在しないため初期化します")
        db_init.ensure_parquet()

    print("[startup] SQLite DB を開きます")
    con = sqlite3.connect(SQLITE_DB_PATH, check_same_thread=False)
    print("[startup] SQLite DB 接続 OK")


# ====== 以下、あなたの既存ロジックをそのまま使用 ======

class SearchRequest(BaseModel):
    components: List[str] = []
    query: Optional[str] = None
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


import re

def build_components_filter_sql(components, query, mode):
    if (not components) and query:
        components = re.split(r"\s+", query.strip())

    if mode == "exact":
        if not query:
            return "1=1"
        q = query.strip().replace("'", "''")
        return f"lower(composition) = lower('{q}')"

    if not components:
        return "1=1"

    clauses = []
    for c in components:
        c = c.strip()
        if c:
            c2 = c.replace("'", "''")
            clauses.append(f"lower(composition) LIKE '%' || lower('{c2}') || '%'")

    return " AND ".join(clauses) if clauses else "1=1"


@app.post("/api/search", response_model=SearchResponse)
def search_axis(request: SearchRequest):
    global con

    condition = build_components_filter_sql(request.components, request.query, request.mode)

    sql = f"""
        SELECT
            prop_x,
            prop_y,
            GROUP_CONCAT(DISTINCT unit_x),
            GROUP_CONCAT(DISTINCT unit_y)
        FROM sample
        WHERE {condition}
        GROUP BY prop_x, prop_y
        ORDER BY prop_x, prop_y
    """

    try:
        rows = con.execute(sql).fetchall()
    except Exception as e:
        raise HTTPException(500, f"search_axis error: {e}")

    axis_options = []
    form_categories = set()

    for r in rows:
        axis_options.append(
            AxisOption(
                prop_x=r[0],
                prop_y=r[1],
                unit_x_list=[u for u in (r[2] or "").split(",") if u],
                unit_y_list=[u for u in (r[3] or "").split(",") if u],
            )
        )

    form_sql = f"SELECT DISTINCT sample_info FROM sample WHERE {condition}"
    try:
        form_rows = con.execute(form_sql).fetchall()
    except Exception as e:
        raise HTTPException(500, f"form_category error: {e}")

    for fr in form_rows:
        raw = fr[0]
        if not raw:
            continue
        try:
            info = json.loads(raw)
        except:
            continue

        form = info.get("Form")
        if isinstance(form, dict):
            cat = form.get("category")
        else:
            cat = form

        if cat:
            form_categories.add(str(cat).strip())

    return SearchResponse(
        axis_options=axis_options,
        form_category_options=sorted(form_categories)
    )


def _to_float_or_none(v):
    if v is None:
        return None
    try:
        return float(str(v).strip())
    except:
        return None


@app.post("/api/filter", response_model=FilterResponse)
def filter_points(payload: dict = Body(...)):
    global con

    components = payload.get("components") or []
    query = payload.get("query")
    mode = payload.get("mode") or "all_terms"

    prop_x = str(payload.get("prop_x") or "")
    prop_y = str(payload.get("prop_y") or "")
    unit_x = str(payload.get("unit_x") or "")
    unit_y = str(payload.get("unit_y") or "")
    form_category_filter = str(payload.get("form_category") or "")

    if not prop_x or not prop_y:
        raise HTTPException(400, "prop_x / prop_y が指定されていません。")

    condition = build_components_filter_sql(components, query, mode)

    axis_cond = f"prop_x='{prop_x}' AND prop_y='{prop_y}'"
    if unit_x:
        axis_cond += f" AND unit_x='{unit_x}'"
    if unit_y:
        axis_cond += f" AND unit_y='{unit_y}'"

    range_cond = []
    x_min = _to_float_or_none(payload.get("x_min"))
    x_max = _to_float_or_none(payload.get("x_max"))
    y_min = _to_float_or_none(payload.get("y_min"))
    y_max = _to_float_or_none(payload.get("y_max"))

    if x_min is not None:
        range_cond.append(f"x >= {x_min}")
    if x_max is not None:
        range_cond.append(f"x <= {x_max}")
    if y_min is not None:
        range_cond.append(f"y >= {y_min}")
    if y_max is not None:
        range_cond.append(f"y <= {y_max}")

    where_sql = " AND ".join([condition, axis_cond] + range_cond)

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
            except:
                info = {}

        form = info.get("Form", {})
        purity = info.get("Purity", {})

        if not isinstance(form, dict):
            form = {"category": str(form), "comment": ""}
        if not isinstance(purity, dict):
            purity = {"category": str(purity), "comment": ""}

        if form_category_filter and form.get("category") != form_category_filter:
            continue

        points.append(
            Point(
                SID=r[0],
                x=r[1],
                y=r[2],
                composition=r[3],
                form_category=form.get("category"),
                form_comment=form.get("comment"),
                purity_category=purity.get("category"),
                purity_comment=purity.get("comment"),
            )
        )

    return FilterResponse(axis_x=prop_x, axis_y=prop_y, points=points)


@app.get("/api/paper/{sid}", response_model=Paper)
def get_paper(sid: str):
    global con

    sid2 = sid.replace("'", "''")
    sql = f"SELECT * FROM papers WHERE SID='{sid2}' LIMIT 1"

    row = con.execute(sql).fetchone()
    if not row:
        raise HTTPException(404, "Paper not found")

    col_names = [d[0] for d in con.description]
    data = dict(zip(col_names, row))

    return Paper(**data)


@app.get("/ping")
def ping():
    return {"message": "ok"}
