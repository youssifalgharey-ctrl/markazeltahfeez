import html
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query, Body, Header, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import text, inspect
from app.database import get_db, engine
from app.config import settings, DATA_DIR
from app.models.user import User
from app.security.deps import get_current_user, require_admin
from app.security.jwt_handler import decode_access_token

router = APIRouter(tags=["db-console"])

def verify_token_admin(token: Optional[str], db: Session) -> Optional[User]:
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload:
        return None
    username = payload.get("sub")
    token_version = payload.get("version", 1)
    if not username:
        return None
    user = (
        db.query(User).filter(User.email == username).first()
        or db.query(User).filter(User.phone == username).first()
        or db.query(User).filter(User.userCode == username).first()
    )
    if not user or user.role != "ADMIN":
        return None
    curr_v = user.token_version if user.token_version is not None else 1
    if token_version != curr_v:
        return None
    return user

@router.get("/h2-console", response_class=HTMLResponse)
def h2_console(
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    admin_user = verify_token_admin(token, db)
    if not admin_user:
        return HTMLResponse(
            status_code=403,
            content="""<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="UTF-8"><title>غير مصرح</title>
<style>body{font-family:Tahoma,sans-serif;background:#0f172a;color:#f8fafc;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;}
.box{background:#1e293b;padding:32px;border-radius:16px;border:1px solid #334155;text-align:center;max-width:480px;}
h2{color:#ef4444;margin-bottom:12px;}p{color:#94a3b8;font-size:14px;line-height:1.6;}
a{display:inline-block;background:#059669;color:#fff;text-decoration:none;padding:10px 22px;border-radius:8px;font-weight:bold;margin-top:18px;}
</style></head><body><div class="box"><h2>⛔ غير مصرح بالدخول</h2>
<p>هذه الصفحة مخصصة لمدير المنصة فقط وتتطلب تسجيل الدخول بحساب مسؤول.</p>
<a href="/admin.html">الانتقال للوحة التحكم وسجل الدخول كمسؤول</a></div></body></html>"""
        )

    # Collect tables info
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    tables_data = []
    with engine.connect() as conn:
        for t in table_names:
            try:
                cnt = conn.execute(text(f'SELECT count(*) FROM "{t}"')).scalar()
            except Exception:
                cnt = 0
            cols = [c["name"] for c in inspector.get_columns(t)]
            tables_data.append({"name": t, "count": cnt, "columns": cols})

    tables_html = ""
    for td in tables_data:
        cols_str = ", ".join(td["columns"][:6]) + ("..." if len(td["columns"]) > 6 else "")
        tables_html += f"""
        <div class="table-card" onclick="loadTableData('{td['name']}')">
            <div class="table-head">
                <span class="table-name"><i class="fa-solid fa-table"></i> {td['name']}</span>
                <span class="table-badge">{td['count']} سجل</span>
            </div>
            <div class="table-cols">{cols_str}</div>
        </div>
        """

    db_path = (DATA_DIR / "authdb.sqlite3").resolve().as_posix()

    html_content = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>مستكشف قاعدة البيانات والباك إند - Quran Platform</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {{
            --bg: #0b0f19;
            --card: #131b2e;
            --border: #1e293b;
            --gold: #f59e0b;
            --emerald: #10b981;
            --text: #f1f5f9;
            --muted: #94a3b8;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: 'Cairo', Tahoma, sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; padding: 20px; }}
        .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); padding-bottom: 16px; margin-bottom: 20px; flex-wrap: wrap; gap: 12px; }}
        .header h1 {{ font-size: 20px; color: var(--emerald); display: flex; align-items: center; gap: 10px; }}
        .nav-links {{ display: flex; gap: 10px; }}
        .btn {{ display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px; border-radius: 8px; text-decoration: none; font-size: 13px; font-weight: bold; border: 1px solid var(--border); background: var(--card); color: var(--text); transition: 0.2s; cursor: pointer; }}
        .btn:hover {{ border-color: var(--emerald); color: var(--emerald); }}
        .btn-primary {{ background: #059669; border-color: #059669; color: #fff; }}
        .btn-primary:hover {{ background: #047857; color: #fff; }}
        .info-bar {{ background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 12px 18px; font-size: 13px; margin-bottom: 20px; display: flex; justify-content: space-between; flex-wrap: wrap; gap: 10px; }}
        .grid {{ display: grid; grid-template-columns: 320px 1fr; gap: 20px; }}
        @media(max-width: 900px){{ .grid {{ grid-template-columns: 1fr; }} }}
        .sidebar {{ display: flex; flex-direction: column; gap: 12px; }}
        .table-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 12px; cursor: pointer; transition: 0.2s; }}
        .table-card:hover {{ border-color: var(--emerald); transform: translateX(-3px); }}
        .table-head {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }}
        .table-name {{ font-weight: bold; font-size: 14px; color: var(--emerald); }}
        .table-badge {{ background: rgba(16,185,129,0.15); color: #34d399; font-size: 11px; padding: 2px 8px; border-radius: 12px; }}
        .table-cols {{ font-size: 11.5px; color: var(--muted); font-family: monospace; direction: ltr; text-align: right; }}
        .main-panel {{ display: flex; flex-direction: column; gap: 16px; }}
        .sql-box {{ background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 16px; }}
        .sql-box h3 {{ font-size: 15px; margin-bottom: 10px; color: var(--gold); }}
        textarea {{ width: 100%; height: 80px; background: #070b13; border: 1px solid var(--border); border-radius: 6px; padding: 10px; color: #38bdf8; font-family: monospace; font-size: 13px; resize: vertical; }}
        .results-box {{ background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 16px; min-height: 250px; overflow-x: auto; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 12.5px; }}
        th {{ background: #070b13; border-bottom: 2px solid var(--border); padding: 10px; text-align: right; color: var(--muted); }}
        td {{ padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.05); font-family: monospace; }}
        tr:hover td {{ background: rgba(255,255,255,0.02); }}
    </style>
</head>
<body>
    <div class="header">
        <h1><i class="fa-solid fa-database"></i> مستكشف قاعدة البيانات والباك إند (Database & Backend Console)</h1>
        <div class="nav-links">
            <a href="/docs" target="_blank" class="btn btn-primary"><i class="fa-solid fa-bolt"></i> مستندات الـ API التفاعلية (Swagger UI)</a>
            <a href="/admin.html" class="btn"><i class="fa-solid fa-gauge"></i> لوحة تحكم الإدارة</a>
            <a href="/home.html" class="btn"><i class="fa-solid fa-house"></i> الواجهة الرئيسية</a>
        </div>
    </div>

    <div class="info-bar">
        <div><strong>محرك قاعدة البيانات:</strong> SQLite 3 (FastAPI Backend)</div>
        <div><strong>المسار:</strong> <code style="direction:ltr; color:#38bdf8;">{db_path}</code></div>
        <div><strong>المسؤول:</strong> {admin_user.fullName} ({admin_user.userCode})</div>
    </div>

    <div class="grid">
        <div class="sidebar">
            <h3 style="font-size:14px; color:var(--gold); margin-bottom:4px;"><i class="fa-solid fa-layer-group"></i> جداول قاعدة البيانات ({len(table_names)})</h3>
            {tables_html}
        </div>

        <div class="main-panel">
            <div class="sql-box">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                    <h3><i class="fa-solid fa-terminal"></i> تنفيذ استعلام SQL</h3>
                    <button class="btn btn-primary" onclick="runQuery()"><i class="fa-solid fa-play"></i> تشغيل الاستعلام</button>
                </div>
                <textarea id="sqlInput">SELECT * FROM "APP_USER" LIMIT 20;</textarea>
            </div>

            <div class="results-box">
                <div id="statusMsg" style="margin-bottom:10px; font-size:13px; color:var(--muted);">اضغط على أي جدول في القائمة لعرض بياناته، أو اكتب استعلام SQL واضغط تشغيل.</div>
                <div id="tableOutput"></div>
            </div>
        </div>
    </div>

    <script>
        var token = "{token or ''}";

        function loadTableData(tableName) {{
            document.getElementById('sqlInput').value = 'SELECT * FROM "' + tableName + '" LIMIT 50;';
            runQuery();
        }}

        async function runQuery() {{
            var sql = document.getElementById('sqlInput').value.trim();
            if (!sql) return;

            var statusEl = document.getElementById('statusMsg');
            var outEl = document.getElementById('tableOutput');
            statusEl.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> جاري تنفيذ الاستعلام...';

            try {{
                var resp = await fetch('/api/admin/sql', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                        'Authorization': 'Bearer ' + token
                    }},
                    body: JSON.stringify({{ query: sql }})
                }});
                var data = await resp.json();
                if (!resp.ok) {{
                    statusEl.innerHTML = '<span style="color:#ef4444;"><i class="fa-solid fa-triangle-exclamation"></i> ' + (data.detail || 'حدث خطأ أثناء التنفيذ') + '</span>';
                    outEl.innerHTML = '';
                    return;
                }}

                statusEl.innerHTML = '<span style="color:#10b981;"><i class="fa-solid fa-circle-check"></i> تم جلب ' + data.rows.length + ' سجل بنجاح</span>';

                if (data.rows.length === 0) {{
                    outEl.innerHTML = '<p style="color:#64748b; padding:20px; text-align:center;">الجدول فارغ لا يحتوي على سجلات مطابقة.</p>';
                    return;
                }}

                var html = '<table><thead><tr>';
                data.columns.forEach(function(col) {{
                    html += '<th>' + col + '</th>';
                }});
                html += '</tr></thead><tbody>';

                data.rows.forEach(function(row) {{
                    html += '<tr>';
                    data.columns.forEach(function(col) {{
                        var val = row[col];
                        if (val === null || val === undefined) val = '<span style="color:#475569;">NULL</span>';
                        else if (typeof val === 'string' && val.length > 50) val = val.substring(0, 50) + '...';
                        html += '<td>' + String(val) + '</td>';
                    }});
                    html += '</tr>';
                }});
                html += '</tbody></table>';
                outEl.innerHTML = html;

            }} catch (err) {{
                statusEl.innerHTML = '<span style="color:#ef4444;">فشل الاتصال: ' + err.message + '</span>';
            }}
        }}

        // Run initial query
        document.addEventListener('DOMContentLoaded', function() {{
            runQuery();
        }});
    </script>
</body>
</html>"""
    return HTMLResponse(content=html_content)

@router.post("/api/admin/sql")
def execute_sql(
    body: Dict[str, str] = Body(...),
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    query = body.get("query", "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="الاستعلام فارغ")

    # Safety: allow only read-only SELECT queries or explain
    first_word = query.split()[0].upper() if query.split() else ""
    if first_word not in ("SELECT", "PRAGMA", "EXPLAIN"):
        raise HTTPException(status_code=400, detail="يُسمح فقط باستعلامات القراءة (SELECT) لأمان قاعدة البيانات")

    try:
        with engine.connect() as conn:
            result = conn.execute(text(query))
            columns = list(result.keys()) if result.returns_rows else []
            rows = [dict(row._mapping) for row in result.fetchmany(100)]
            return {"columns": columns, "rows": rows}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
