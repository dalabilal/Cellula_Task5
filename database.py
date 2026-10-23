import io
import os
import re
import sqlite3
from pathlib import Path

import pandas as pd

DB_PATH = "data.db"

FORBIDDEN = {
    "insert", "update", "delete", "drop", "alter", "create", "attach",
    "detach", "pragma", "vacuum", "truncate",
}


def load_dataset(file_bytes, filename):
    ext = filename.split(".")[-1].lower()
    if ext == "csv":
        df = pd.read_csv(io.BytesIO(file_bytes))
    elif ext in ("xlsx", "xls"):
        df = pd.read_excel(io.BytesIO(file_bytes))
    else:
        raise ValueError("Only .csv and .xlsx files are supported")

    # clean names so the LLM never needs quotes (Arabic letters are kept)
    df.columns = [re.sub(r"\W+", "_", str(c)).strip("_") or f"col{i}" for i, c in enumerate(df.columns)]
    table = re.sub(r"[^0-9a-zA-Z_]+", "_", filename.rsplit(".", 1)[0]).strip("_").lower() or "data"
    if table[0].isdigit():
        table = "t_" + table

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)  # one dataset at a time
    conn = sqlite3.connect(DB_PATH)
    try:
        df.to_sql(table, conn, index=False)
    finally:
        conn.close()
    return {"table": table, "columns": list(df.columns), "rows": len(df)}


def get_schema():
    if not os.path.exists(DB_PATH):
        raise ValueError("No dataset yet. Upload one with POST /dataset first")
    conn = sqlite3.connect(DB_PATH)
    try:
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        parts = []
        for t in tables:
            cols = conn.execute(f'PRAGMA table_info("{t}")').fetchall()
            col_text = ", ".join(f"{c[1]} ({c[2]})" for c in cols)
            sample = conn.execute(f'SELECT * FROM "{t}" LIMIT 3').fetchall()
            parts.append(f"Table: {t}\nColumns: {col_text}\nSample rows: {sample}")
        return "\n\n".join(parts)
    finally:
        conn.close()


def validate_sql(sql):
    s = sql.strip().rstrip(";").strip()
    if not s:
        raise ValueError("Empty SQL")
    if ";" in s:
        raise ValueError("Only one SQL statement is allowed")
    if not s.lower().startswith(("select", "with")):
        raise ValueError("Only SELECT queries are allowed")
    bad = set(re.findall(r"[a-z_]+", s.lower())) & FORBIDDEN
    if bad:
        raise ValueError(f"Forbidden SQL keyword: {', '.join(sorted(bad))}")
    return s


def run_sql(sql, limit=100):
    sql = validate_sql(sql)
    if not os.path.exists(DB_PATH):
        raise ValueError("No dataset yet. Upload one with POST /dataset first")

    conn = sqlite3.connect(Path(DB_PATH).resolve().as_uri() + "?mode=ro", uri=True)
    try:
        conn.execute("EXPLAIN " + sql)  
        cur = conn.execute(sql)
        columns = [d[0] for d in cur.description]
        rows = [list(r) for r in cur.fetchmany(limit)]
        return columns, rows
    finally:
        conn.close()
