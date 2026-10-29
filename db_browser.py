"""Read-only helpers for the admin database browser."""
import sqlite3
from pathlib import Path

PAGE_SIZE = 50
MAX_SEARCH_LENGTH = 100
MAX_CELL_LENGTH = 1200
REDACTED = "[redacted]"
REDACTED_PARTS = (
    "password", "pw_", "salt", "token", "secret", "signature", "_b64", "b64",
    "photo", "headshot", "image", "poster", "social", "thumb", "snapshot", "payload", "blob",
)
REDACTED_TABLE_COLUMNS = {"meta": {"v"}}


def open_readonly(database_path):
    uri = Path(database_path).resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    return conn


def _quote_identifier(name):
    return '"' + str(name).replace('"', '""') + '"'


def _redacted(name, table=None):
    key = name.lower()
    return (any(part in key for part in REDACTED_PARTS)
            or key in REDACTED_TABLE_COLUMNS.get(table, set()))


def _table_columns(conn, table):
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? AND name NOT LIKE 'sqlite_%'",
        (table,),
    ).fetchone()
    if not exists:
        raise KeyError(table)
    info = conn.execute(f"PRAGMA table_info({_quote_identifier(table)})").fetchall()
    return [{
        "name": row[1],
        "type": row[2] or "",
        "primary_key_order": row[5],
        "redacted": _redacted(row[1], table),
    } for row in info]


def table_summaries(conn):
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    out = []
    for (name,) in tables:
        columns = _table_columns(conn, name)
        count = conn.execute(f"SELECT COUNT(*) FROM {_quote_identifier(name)}").fetchone()[0]
        out.append({
            "name": name,
            "rows": count,
            "columns": [{"name": col["name"], "redacted": col["redacted"]} for col in columns],
        })
    return out


def table_page(conn, table, page=1, search=""):
    columns = _table_columns(conn, table)
    page = max(1, int(page))
    search = str(search or "").strip()[:MAX_SEARCH_LENGTH]
    searchable = [col for col in columns
                  if not col["redacted"] and any(kind in col["type"].upper() for kind in ("TEXT", "CHAR", "CLOB"))]
    where = ""
    params = []
    if search:
        if searchable:
            where = " WHERE (" + " OR ".join(
                f"CAST({_quote_identifier(col['name'])} AS TEXT) LIKE ?" for col in searchable
            ) + ")"
            params = [f"%{search}%"] * len(searchable)
        else:
            where = " WHERE 0"

    table_sql = _quote_identifier(table)
    total = conn.execute(f"SELECT COUNT(*) FROM {table_sql}{where}", params).fetchone()[0]
    pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
    page = min(page, max(pages, 1))

    primary_keys = sorted(
        (col for col in columns if col["primary_key_order"]),
        key=lambda col: col["primary_key_order"],
    )
    order = ", ".join(_quote_identifier(col["name"]) for col in primary_keys) or "rowid"
    visible = [col for col in columns if not col["redacted"]]
    select = ", ".join(_quote_identifier(col["name"]) for col in visible) or "1"
    rows = conn.execute(
        f"SELECT {select} FROM {table_sql}{where} ORDER BY {order} LIMIT ? OFFSET ?",
        params + [PAGE_SIZE, (page - 1) * PAGE_SIZE],
    ).fetchall()

    result_rows = []
    for row in rows:
        values = {}
        for col in columns:
            if col["redacted"]:
                values[col["name"]] = REDACTED
                continue
            value = row[col["name"]] if col in visible else REDACTED
            if isinstance(value, bytes):
                value = f"[binary: {len(value)} bytes]"
            elif isinstance(value, str) and len(value) > MAX_CELL_LENGTH:
                value = value[:MAX_CELL_LENGTH] + " [truncated]"
            values[col["name"]] = value
        result_rows.append(values)

    return {
        "table": table,
        "columns": [{"name": col["name"], "redacted": col["redacted"]} for col in columns],
        "rows": result_rows,
        "page": page,
        "page_size": PAGE_SIZE,
        "total": total,
        "pages": pages,
    }