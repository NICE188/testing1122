from flask import (
    Flask, request, jsonify, render_template, render_template_string,
    redirect, url_for, send_file, session, abort
)
import sqlite3, csv, io, os, traceback, secrets, string
from datetime import datetime
from jinja2 import TemplateNotFound
from werkzeug.security import generate_password_hash, check_password_hash

APP_DB = os.environ.get("APP_DB", "data.db")

# ====== 简单账号（初始化时写入 users 表；后续改动都在 DB）======
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")  # session 用

# ---------------- I18N（含账号安全相关文案） ----------------
I18N = {
    "zh": {
        "app_name": "Nepwin88",
        "dashboard": "Dashboard",
        "workers": "工人 / 平台",
        "bank_accounts": "银行账户",
        "card_rentals": "银行卡租金",
        "salaries": "出粮记录",
        "expenses": "开销记录",
        "export_workers": "导出工人",
        "export_bank": "导出银行账户",
        "export_rentals": "导出银行卡租金",
        "export_salaries": "导出出粮",
        "export_expenses": "导出开销",
        "total_workers": "Total Workers",
        "total_rentals": "Total Card Rentals",
        "total_salaries": "Total Salaries",
        "total_expenses": "Total Expenses",
        "welcome_tip": "使用左侧侧边栏导航，右上角可导出 CSV。",
        "add": "新增",
        "name": "名字",
        "company": "公司",
        "commission": "佣金",
        "expense_amount": "金额",
        "expenses_note": "备注",
        "created_at": "创建时间",
        "actions": "操作",
        "account_number": "账户号码",
        "bank_name": "银行名字",
        "worker": "工人",
        "rental_amount": "租金金额",
        "date": "日期",
        "salary_amount": "工资金额",
        "pay_date": "发薪日期",
        "note": "备注",
        "submit": "提交",
        "language": "语言",
        "empty": "暂无数据",
        "status": "状态",
        "active": "启用",
        "inactive": "停用",
        "activate": "启用",
        "deactivate": "停用",
        "edit": "编辑",
        "delete": "删除",
        "save": "保存",
        "back": "返回",
        "confirm_delete": "确认删除？",
        "cannot_delete_worker_with_refs": "该工人存在关联记录，不能删除。",
        "login": "登录",
        "logout": "退出",
        "username": "用户名",
        "password": "密码",
        "login_failed": "用户名或密码错误",

        # account / security
        "account_security": "账号安全",
        "reset_pw": "重置密码",
        "change_pw": "修改密码",
        "change_user_id": "修改用户名",
        "current_password": "当前密码",
        "new_password": "新密码",
        "confirm_password": "确认新密码",
        "new_username": "新用户名",
        "submit_change": "提交修改",
        "reset_done": "已重置密码",
        "new_pw_is": "新的密码是",
        "wrong_password": "当前密码不正确",
        "pw_not_match": "两次输入的新密码不一致",
        "username_taken": "该用户名已被占用",
        "update_ok": "更新成功",
    },
    "en": {
        "app_name": "Nepwin88",
        "dashboard": "Dashboard",
        "workers": "Workers / Platforms",
        "bank_accounts": "Bank Accounts",
        "card_rentals": "Card Rentals",
        "salaries": "Salary Records",
        "expenses": "Expenses",
        "export_workers": "Export Workers",
        "export_bank": "Export Bank Accounts",
        "export_rentals": "Export Card Rentals",
        "export_salaries": "Export Salaries",
        "export_expenses": "Export Expenses",
        "total_workers": "Total Workers",
        "total_rentals": "Total Card Rentals",
        "total_salaries": "Total Salaries",
        "total_expenses": "Total Expenses",
        "welcome_tip": "Use the left sidebar to navigate. Export CSV at top-right.",
        "add": "Add",
        "name": "Name",
        "company": "Company",
        "commission": "Commission",
        "expense_amount": "Amount",
        "expenses_note": "Note",
        "created_at": "Created At",
        "actions": "Actions",
        "account_number": "Account Number",
        "bank_name": "Bank Name",
        "worker": "Worker",
        "rental_amount": "Rental Amount",
        "date": "Date",
        "salary_amount": "Salary Amount",
        "pay_date": "Pay Date",
        "note": "Note",
        "submit": "Submit",
        "language": "Language",
        "empty": "No data yet",
        "status": "Status",
        "active": "Active",
        "inactive": "Inactive",
        "activate": "Activate",
        "deactivate": "Deactivate",
        "edit": "Edit",
        "delete": "Delete",
        "save": "Save",
        "back": "Back",
        "confirm_delete": "Confirm delete?",
        "cannot_delete_worker_with_refs": "Cannot delete worker because related records exist.",
        "login": "Login",
        "logout": "Logout",
        "username": "Username",
        "password": "Password",
        "login_failed": "Wrong username or password",

        # account / security
        "account_security": "Account Security",
        "reset_pw": "Reset Password",
        "change_pw": "Change Password",
        "change_user_id": "Change Username",
        "current_password": "Current Password",
        "new_password": "New Password",
        "confirm_password": "Confirm New Password",
        "new_username": "New Username",
        "submit_change": "Submit",
        "reset_done": "Password has been reset",
        "new_pw_is": "New password is",
        "wrong_password": "Current password is incorrect",
        "pw_not_match": "New passwords do not match",
        "username_taken": "Username already taken",
        "update_ok": "Updated successfully",
    }
}

def get_lang():
    lang = request.args.get("lang")
    if lang in I18N:
        session["lang"] = lang
    return session.get("lang", "zh")

@app.context_processor
def inject_i18n():
    lang = get_lang()
    t = I18N[lang]
    return dict(t=t, lang=lang)

# ----------------- 简易登录保护 -----------------
def is_logged_in():
    return bool(session.get("user_id"))

@app.before_request
def require_login():
    open_endpoints = {
        "login", "login_post", "logout", "health", "static",
        "_debug_template_paths"
    }
    if request.endpoint in open_endpoints:
        return
    if not is_logged_in():
        next_url = request.path
        return redirect(url_for("login", next=next_url))

# ---------------- DB helpers ----------------
def get_db():
    con = sqlite3.connect(APP_DB)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con

def init_db():
    con = get_db()
    cur = con.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS workers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        company TEXT,
        commission REAL DEFAULT 0,
        expenses REAL DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS bank_accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        worker_id INTEGER NOT NULL,
        account_number TEXT NOT NULL,
        bank_name TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(worker_id) REFERENCES workers(id)
    );

    CREATE TABLE IF NOT EXISTS card_rentals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        worker_id INTEGER NOT NULL,
        rental_amount REAL NOT NULL,
        date TEXT NOT NULL,
        note TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(worker_id) REFERENCES workers(id)
    );

    CREATE TABLE IF NOT EXISTS salary_payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        worker_id INTEGER NOT NULL,
        salary_amount REAL NOT NULL,
        pay_date TEXT NOT NULL,
        note TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(worker_id) REFERENCES workers(id)
    );

    CREATE TABLE IF NOT EXISTS expense_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        worker_id INTEGER,
        amount REAL NOT NULL,
        date TEXT NOT NULL,
        note TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(worker_id) REFERENCES workers(id)
    );

    -- 新增 users 表（仅 1 条管理员记录）
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)
    con.commit()
    # 初始化管理员
    row = con.execute("SELECT COUNT(*) c FROM users").fetchone()
    if row["c"] == 0:
        con.execute(
            "INSERT INTO users (username, password_hash) VALUES (?,?)",
            (ADMIN_USERNAME, generate_password_hash(ADMIN_PASSWORD))
        )
        con.commit()
    con.close()

def ensure_is_active_columns():
    tables = ["workers", "bank_accounts", "card_rentals", "salary_payments", "expense_records"]
    con = get_db()
    for tname in tables:
        cols = con.execute(f"PRAGMA table_info({tname})").fetchall()
        if not any(c["name"] == "is_active" for c in cols):
            con.execute(f"ALTER TABLE {tname} ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1")
    con.commit(); con.close()

if not os.path.exists(APP_DB):
    init_db()
else:
    init_db()  # 安全起见，确保 users 表存在
ensure_is_active_columns()

# ---------------- Health ----------------
@app.get("/health")
def health():
    return "ok", 200

# ---------------- 调试端点：查看模板检索目录 ----------------
@app.get("/__debug/template_paths")
def _debug_template_paths():
    paths = getattr(app.jinja_loader, "searchpath", [])
    return {"template_searchpath": paths}, 200

# ---------------- 全局错误处理 ----------------
@app.errorhandler(Exception)
def _handle_any_error(e):
    app.logger.exception("Unhandled exception")
    if os.environ.get("SHOW_ERRORS", "0") == "1":
        return "<pre style='white-space:pre-wrap;line-height:1.4;font-family:ui-monospace,Menlo,Consolas,monospace'>" + \
               traceback.format_exc() + "</pre>", 500
    try:
        return render_template("500.html", error=str(e)), 500
    except Exception:
        return render_template_string("""
        <!doctype html><meta charset="utf-8">
        <title>Internal Server Error</title>
        <style>body{background:#0b1220;color:#e7ebf3;font:16px/1.6 system-ui;padding:40px}</style>
        <h1>Server Error (500)</h1>
        <p>{{ error }}</p>
        """, error=str(e)), 500

# =============== 账号安全（登录 / 退出 / 安全中心）================
def _inline_login_template():
    return """
<!doctype html>
<html lang="{{ 'zh' if lang=='zh' else 'en' }}">
<head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{{ '登录' if lang=='zh' else 'Login' }} · Nepwin88</title>
  <style>
    :root{--card:rgba(16,22,39,.78);--line:rgba(148,163,184,.25);--txt:#e7ebf3}
    *{box-sizing:border-box} html,body{height:100%}
    body{margin:0;color:var(--txt);font:16px/1.6 system-ui,-apple-system,Segoe UI,Roboto,Inter,Helvetica,Arial;
      background:#0b1220;}
    .wrap{min-height:100%;display:grid;place-items:center;padding:32px}
    .card{width:min(480px,92vw);background:var(--card);border:1px solid var(--line);border-radius:20px;
      box-shadow:0 20px 40px rgba(0,0,0,.35);backdrop-filter: blur(10px);padding:26px}
    h1{margin:0 0 10px;font-size:22px}
    .muted{color:#9fb0ca;margin:0 0 18px}
    .field{display:grid;gap:6px;margin:12px 0}
    input{width:100%;padding:12px 14px;border-radius:12px;background:#0e1626;border:1px solid rgba(148,163,184,.32);color:#e7ebf3;outline:none}
    input:focus{border-color:#3659d6;box-shadow:0 0 0 3px rgba(54,89,214,.20)}
    .actions{display:flex;justify-content:space-between;align-items:center;margin-top:12px}
    button{padding:10px 14px;border-radius:12px;background:linear-gradient(180deg,#1e2638,#1a2233);
      border:1px solid rgba(148,163,184,.32);color:#e7ebf3;cursor:pointer}
    .lang a{color:#60a5fa;text-decoration:none;margin-left:8px}
    .err{background:#3b1a1a;border:1px solid rgba(239,68,68,.45);padding:10px 12px;border-radius:12px;margin-bottom:10px}
  </style>
</head>
<body>
<div class="wrap">
  <div class="card">
    <h1>{{ '登录' if lang=='zh' else 'Login' }}</h1>
    <p class="muted">{{ '请输入管理员账号登录系统' if lang=='zh' else 'Enter admin credentials' }}</p>
    {% if error %}<div class="err">{{ error }}</div>{% endif %}
    <form method="post" action="{{ url_for('login_post') }}">
      <input type="hidden" name="next" value="{{ next_url }}">
      <div class="field">
        <label>{{ t.username if lang=='zh' else 'Username' }}</label>
        <input name="username" autocomplete="username" required>
      </div>
      <div class="field">
        <label>{{ t.password if lang=='zh' else 'Password' }}</label>
        <input type="password" name="password" autocomplete="current-password" required>
      </div>
      <div class="actions">
        <div class="lang">
          {{ t.language }}:
          <a href="?lang=zh">中文</a>|
          <a href="?lang=en">English</a>
        </div>
        <button type="submit">{{ t.login if lang=='zh' else 'Login' }}</button>
      </div>
    </form>
  </div>
</div>
</body>
</html>
"""

def _inline_account_security_template():
    return """
<!doctype html>
<html lang="{{ 'zh' if lang=='zh' else 'en' }}">
<head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{{ t.account_security }}</title>
  <style>
    body{background:#0b1220;color:#e7ebf3;font:15px/1.6 system-ui;margin:0}
    .wrap{max-width:900px;margin:40px auto;padding:0 16px}
    .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px}
    .card{background:rgba(16,22,39,.78);border:1px solid rgba(148,163,184,.25);border-radius:16px;padding:16px}
    h1{font-size:22px;margin:0 0 16px}
    h2{font-size:16px;margin:0 0 10px}
    input{width:100%;padding:10px;border-radius:10px;background:#0e1626;border:1px solid rgba(148,163,184,.32);color:#e7ebf3;margin:6px 0}
    button{padding:10px 12px;border-radius:10px;background:#1c2436;border:1px solid rgba(148,163,184,.32);color:#e7ebf3;cursor:pointer}
    .msg{margin:12px 0;padding:10px;border-radius:10px;background:#0d1b2a;border:1px solid rgba(148,163,184,.25)}
    .ok{border-color:rgba(34,197,94,.4);background:#0f2a1a}
    .warn{border-color:rgba(250,204,21,.4);background:#2a230f}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>{{ t.account_security }}</h1>
    {% if msg %}<div class="msg ok">{{ msg|safe }}</div>{% endif %}
    <div class="grid">
      <div class="card">
        <h2>🔁 {{ t.reset_pw }}</h2>
        <form method="post" action="{{ url_for('account_reset_password') }}">
          <button type="submit">RESET</button>
        </form>
      </div>

      <div class="card">
        <h2>🔒 {{ t.change_pw }}</h2>
        <form method="post" action="{{ url_for('account_change_password') }}">
          <label>{{ t.current_password }}</label>
          <input type="password" name="old_pw" required>
          <label>{{ t.new_password }}</label>
          <input type="password" name="new_pw" required>
          <label>{{ t.confirm_password }}</label>
          <input type="password" name="new_pw2" required>
          <button type="submit">{{ t.submit_change }}</button>
        </form>
      </div>

      <div class="card">
        <h2>🆔 {{ t.change_user_id }}</h2>
        <form method="post" action="{{ url_for('account_change_username') }}">
          <label>{{ t.new_username }}</label>
          <input name="new_username" required>
          <label>{{ t.current_password }}</label>
          <input type="password" name="pw" required>
          <button type="submit">{{ t.submit_change }}</button>
        </form>
      </div>
    </div>
  </div>
</body>
</html>
"""

def _current_user():
    con = get_db()
    u = None
    if session.get("user_id"):
        u = con.execute("SELECT * FROM users WHERE username=?", (session["user_id"],)).fetchone()
    if not u:
        u = con.execute("SELECT * FROM users ORDER BY id LIMIT 1").fetchone()
    con.close()
    return u

@app.get("/login")
def login():
    if is_logged_in():
        return redirect(url_for("home"))
    next_url = request.args.get("next", url_for("home"))
    try:
        return render_template("login.html", next_url=next_url, error=None)
    except TemplateNotFound:
        return render_template_string(_inline_login_template(), next_url=next_url, error=None)

@app.post("/login")
def login_post():
    username = (request.form.get("username") or "").strip()
    password = (request.form.get("password") or "").strip()
    next_url = request.form.get("next") or url_for("home")

    con = get_db()
    u = con.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    con.close()
    ok = bool(u and check_password_hash(u["password_hash"], password))
    if ok:
        session["user_id"] = username
        return redirect(next_url)
    # 登录失败
    try:
        return render_template("login.html", next_url=next_url,
                               error=I18N[get_lang()]["login_failed"]), 401
    except TemplateNotFound:
        return render_template_string(_inline_login_template(), next_url=next_url,
                                      error=I18N[get_lang()]["login_failed"]), 401

@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.get("/account")
def account_security():
    msg = request.args.get("msg")
    try:
        return render_template("account_security.html", msg=msg)
    except TemplateNotFound:
        return render_template_string(_inline_account_security_template(), msg=msg)

@app.post("/account/reset-password")
def account_reset_password():
    # 生成随机 12 位密码
    alphabet = string.ascii_letters + string.digits
    new_pw = "".join(secrets.choice(alphabet) for _ in range(12))
    con = get_db()
    con.execute("UPDATE users SET password_hash=? WHERE id=(SELECT id FROM users ORDER BY id LIMIT 1)",
                (generate_password_hash(new_pw),))
    con.commit(); con.close()
    # 同步 session（仍然有效，不强制登出）
    msg = f"{I18N[get_lang()]['reset_done']} · {I18N[get_lang()]['new_pw_is']}: <b>{new_pw}</b>"
    return redirect(url_for("account_security", msg=msg))

@app.post("/account/change-password")
def account_change_password():
    old_pw = request.form.get("old_pw") or ""
    new_pw = request.form.get("new_pw") or ""
    new_pw2 = request.form.get("new_pw2") or ""
    if new_pw != new_pw2:
        return redirect(url_for("account_security", msg=I18N[get_lang()]["pw_not_match"]))
    u = _current_user()
    if not u or not check_password_hash(u["password_hash"], old_pw):
        return redirect(url_for("account_security", msg=I18N[get_lang()]["wrong_password"]))
    con = get_db()
    con.execute("UPDATE users SET password_hash=? WHERE id=?", (generate_password_hash(new_pw), u["id"]))
    con.commit(); con.close()
    return redirect(url_for("account_security", msg=I18N[get_lang()]["update_ok"]))

@app.post("/account/change-username")
def account_change_username():
    new_username = (request.form.get("new_username") or "").strip()
    pw = request.form.get("pw") or ""
    if not new_username:
        return redirect(url_for("account_security", msg="Username required"))
    u = _current_user()
    if not u or not check_password_hash(u["password_hash"], pw):
        return redirect(url_for("account_security", msg=I18N[get_lang()]["wrong_password"]))
    con = get_db()
    exists = con.execute("SELECT 1 FROM users WHERE username=? AND id<>?", (new_username, u["id"])).fetchone()
    if exists:
        con.close()
        return redirect(url_for("account_security", msg=I18N[get_lang()]["username_taken"]))
    con.execute("UPDATE users SET username=? WHERE id=?", (new_username, u["id"]))
    con.commit(); con.close()
    session["user_id"] = new_username
    return redirect(url_for("account_security", msg=I18N[get_lang()]["update_ok"]))

# ================= Home / Dashboard & 业务原有路由（保持不变）=================
@app.route("/")
def home():
    con = get_db()
    total_workers = con.execute("SELECT COUNT(*) c FROM workers").fetchone()["c"]
    total_rentals = con.execute("SELECT IFNULL(SUM(rental_amount),0) s FROM card_rentals").fetchone()["s"]
    total_salaries = con.execute("SELECT IFNULL(SUM(salary_amount),0) s FROM salary_payments").fetchone()["s"]
    total_expenses = con.execute("SELECT IFNULL(SUM(amount),0) s FROM expense_records").fetchone()["s"]
    con.close()
    try:
        return render_template("index.html",
                               total_workers=total_workers,
                               total_rentals=total_rentals,
                               total_salaries=total_salaries,
                               total_expenses=total_expenses)
    except TemplateNotFound:
        return render_template_string("""
        <!doctype html><meta charset="utf-8">
        <title>Dashboard</title>
        <style>body{background:#0b1220;color:#e7ebf3;font:16px/1.6 system-ui;padding:24px}</style>
        <h1>Dashboard</h1>
        <ul>
          <li>Total Workers: {{ total_workers }}</li>
          <li>Total Card Rentals: {{ total_rentals }}</li>
          <li>Total Salaries: {{ total_salaries }}</li>
          <li>Total Expenses: {{ total_expenses }}</li>
        </ul>
        """, total_workers=total_workers, total_rentals=total_rentals,
           total_salaries=total_salaries, total_expenses=total_expenses)

@app.get("/api/summary")
def api_summary():
    con = get_db()
    def q(sql): return con.execute(sql).fetchall()
    months_sql = """
        WITH m(n) AS (
          SELECT strftime('%Y-%m', date('now','start of month','-5 months'))
          UNION ALL
          SELECT strftime('%Y-%m', date(substr(n||'-01',1,10),'start of month','+1 month'))
          FROM m WHERE n < strftime('%Y-%m', 'now', 'start of month')
        )
        SELECT n AS ym FROM m;
    """
    months = [r["ym"] for r in q(months_sql)]
    def series(table, field, date_field):
        rows = q(f"""
            SELECT strftime('%Y-%m', {date_field}) ym, IFNULL(SUM({field}),0) total
            FROM {table}
            WHERE {date_field} >= date('now','start of month','-5 months')
            GROUP BY ym
        """)
        d = {r["ym"]: r["total"] for r in rows}
        return [float(d.get(m, 0)) for m in months]
    rentals = series("card_rentals", "rental_amount", "date")
    salaries = series("salary_payments", "salary_amount", "pay_date")
    expenses = series("expense_records", "amount", "date")
    con.close()
    return jsonify({"months": months, "rentals": rentals, "salaries": salaries, "expenses": expenses})

def _toggle_active(table, rid):
    con = get_db()
    row = con.execute(f"SELECT is_active FROM {table} WHERE id=?", (rid,)).fetchone()
    if not row:
        con.close()
        return False
    con.execute(f"UPDATE {table} SET is_active = CASE is_active WHEN 1 THEN 0 ELSE 1 END WHERE id=?", (rid,))
    con.commit(); con.close()
    return True

# ---- Workers
@app.route("/workers")
def workers_list():
    con = get_db()
    dt_from = request.args.get("from"); dt_to = request.args.get("to")
    sql = "SELECT * FROM workers WHERE 1=1"; args = []
    if dt_from: sql += " AND datetime(created_at) >= datetime(?)"; args.append(dt_from)
    if dt_to:   sql += " AND datetime(created_at) <= datetime(?)"; args.append(dt_to)
    sql += " ORDER BY id DESC"
    rows = con.execute(sql, args).fetchall()
    con.close()
    try:
        return render_template("workers.html", rows=rows)
    except TemplateNotFound:
        return render_template_string("<pre>{{ rows|length }} workers</pre>", rows=rows)

@app.post("/workers/add")
def workers_add():
    d = request.form or request.json
    name = (d.get("name") or "").strip()
    if not name: return "Name is required", 400
    company = d.get("company") or ""
    commission = float(d.get("commission") or 0)
    expenses = float(d.get("expenses") or 0)
    con = get_db()
    con.execute("INSERT INTO workers (name, company, commission, expenses) VALUES (?,?,?,?)",
                (name, company, commission, expenses))
    con.commit(); con.close()
    return redirect(url_for("workers_list"))

@app.post("/workers/<int:wid>/toggle")
def workers_toggle(wid):
    _toggle_active("workers", wid)
    return redirect(url_for("workers_list"))

@app.get("/workers/<int:wid>/edit")
def workers_edit_form(wid):
    con = get_db()
    r = con.execute("SELECT * FROM workers WHERE id=?", (wid,)).fetchone()
    con.close()
    if not r: abort(404)
    try:
        return render_template("workers_edit.html", r=r)
    except TemplateNotFound:
        return render_template_string("<pre>edit worker {{ r['id'] }}</pre>", r=r)

@app.post("/workers/<int:wid>/edit")
def workers_edit(wid):
    d = request.form or request.json
    name = (d.get("name") or "").strip()
    company = d.get("company") or ""
    commission = float(d.get("commission") or 0)
    expenses = float(d.get("expenses") or 0)
    con = get_db()
    con.execute("UPDATE workers SET name=?, company=?, commission=?, expenses=? WHERE id=?",
                (name, company, commission, expenses, wid))
    con.commit(); con.close()
    return redirect(url_for("workers_list"))

@app.post("/workers/<int:wid>/delete")
def workers_delete(wid):
    con = get_db()
    total = 0
    for table, col in [("bank_accounts","worker_id"),("card_rentals","worker_id"),
                       ("salary_payments","worker_id"),("expense_records","worker_id")]:
        total += con.execute(f"SELECT COUNT(*) c FROM {table} WHERE {col}=?", (wid,)).fetchone()["c"]
    if total>0:
        con.close()
        return I18N[get_lang()]["cannot_delete_worker_with_refs"], 400
    con.execute("DELETE FROM workers WHERE id=?", (wid,))
    con.commit(); con.close()
    return redirect(url_for("workers_list"))

# ---- Bank Accounts
@app.route("/bank-accounts")
def bank_accounts_list():
    con = get_db()
    rows = con.execute("""
      SELECT b.*, w.name AS worker_name
      FROM bank_accounts b JOIN workers w ON w.id=b.worker_id
      ORDER BY b.id DESC
    """).fetchall()
    workers = con.execute("SELECT id,name FROM workers ORDER BY name").fetchall()
    con.close()
    try:
        return render_template("bank_accounts.html", rows=rows, workers=workers)
    except TemplateNotFound:
        return render_template_string("<pre>{{ rows|length }} bank accounts</pre>", rows=rows)

@app.post("/bank-accounts/add")
def bank_accounts_add():
    d = request.form or request.json
    worker_id = int(d.get("worker_id"))
    account_number = (d.get("account_number") or "").strip()
    bank_name = (d.get("bank_name") or "").strip()
    if not (worker_id and account_number and bank_name):
        return "worker_id, account_number, bank_name required", 400
    con = get_db()
    con.execute("INSERT INTO bank_accounts (worker_id, account_number, bank_name) VALUES (?,?,?)",
                (worker_id, account_number, bank_name))
    con.commit(); con.close()
    return redirect(url_for("bank_accounts_list"))

@app.post("/bank-accounts/<int:bid>/toggle")
def bank_accounts_toggle(bid):
    _toggle_active("bank_accounts", bid)
    return redirect(url_for("bank_accounts_list"))

@app.get("/bank-accounts/<int:bid>/edit")
def bank_accounts_edit_form(bid):
    con = get_db()
    r = con.execute("SELECT * FROM bank_accounts WHERE id=?", (bid,)).fetchone()
    workers = con.execute("SELECT id,name FROM workers ORDER BY name").fetchall()
    con.close()
    if not r: abort(404)
    try:
        return render_template("bank_accounts_edit.html", r=r, workers=workers)
    except TemplateNotFound:
        return render_template_string("<pre>edit bank account {{ r['id'] }}</pre>", r=r)

@app.post("/bank-accounts/<int:bid>/edit")
def bank_accounts_edit(bid):
    d = request.form or request.json
    worker_id = int(d.get("worker_id"))
    account_number = (d.get("account_number") or "").strip()
    bank_name = (d.get("bank_name") or "").strip()
    con = get_db()
    con.execute("UPDATE bank_accounts SET worker_id=?, account_number=?, bank_name=? WHERE id=?",
                (worker_id, account_number, bank_name, bid))
    con.commit(); con.close()
    return redirect(url_for("bank_accounts_list"))

@app.post("/bank-accounts/<int:bid>/delete")
def bank_accounts_delete(bid):
    con = get_db()
    con.execute("DELETE FROM bank_accounts WHERE id=?", (bid,))
    con.commit(); con.close()
    return redirect(url_for("bank_accounts_list"))

# ---- Card Rentals
@app.route("/card-rentals")
def card_rentals_list():
    con = get_db()
    rows = con.execute("""
      SELECT c.*, w.name AS worker_name
      FROM card_rentals c JOIN workers w ON w.id=c.worker_id
      ORDER BY c.date DESC, c.id DESC
    """).fetchall()
    workers = con.execute("SELECT id,name FROM workers ORDER BY name").fetchall()
    con.close()
    try:
        return render_template("card_rentals.html", rows=rows, workers=workers)
    except TemplateNotFound:
        return render_template_string("<pre>{{ rows|length }} card rentals</pre>", rows=rows)

@app.post("/card-rentals/add")
def card_rentals_add():
    d = request.form or request.json
    worker_id = int(d.get("worker_id"))
    rental_amount = float(d.get("rental_amount"))
    date = (d.get("date") or "").strip()
    note = d.get("note") or ""
    try:
        datetime.fromisoformat(date)
    except Exception:
        return "date must be YYYY-MM-DD", 400
    con = get_db()
    con.execute("INSERT INTO card_rentals (worker_id, rental_amount, date, note) VALUES (?,?,?,?)",
                (worker_id, rental_amount, date, note))
    con.commit(); con.close()
    return redirect(url_for("card_rentals_list"))

@app.post("/card-rentals/<int:cid>/toggle")
def card_rentals_toggle(cid):
    _toggle_active("card_rentals", cid)
    return redirect(url_for("card_rentals_list"))

@app.get("/card-rentals/<int:cid>/edit")
def card_rentals_edit_form(cid):
    con = get_db()
    r = con.execute("SELECT * FROM card_rentals WHERE id=?", (cid,)).fetchone()
    workers = con.execute("SELECT id,name FROM workers ORDER BY name").fetchall()
    con.close()
    if not r: abort(404)
    try:
        return render_template("card_rentals_edit.html", r=r, workers=workers)
    except TemplateNotFound:
        return render_template_string("<pre>edit card rental {{ r['id'] }}</pre>", r=r)

@app.post("/card-rentals/<int:cid>/edit")
def card_rentals_edit(cid):
    d = request.form or request.json
    worker_id = int(d.get("worker_id"))
    rental_amount = float(d.get("rental_amount"))
    date = (d.get("date") or "").strip()
    note = d.get("note") or ""
    try:
        datetime.fromisoformat(date)
    except Exception:
        return "date must be YYYY-MM-DD", 400
    con = get_db()
    con.execute("UPDATE card_rentals SET worker_id=?, rental_amount=?, date=?, note=? WHERE id=?",
                (worker_id, rental_amount, date, note, cid))
    con.commit(); con.close()
    return redirect(url_for("card_rentals_list"))

@app.post("/card-rentals/<int:cid>/delete")
def card_rentals_delete(cid):
    con = get_db()
    con.execute("DELETE FROM card_rentals WHERE id=?", (cid,))
    con.commit(); con.close()
    return redirect(url_for("card_rentals_list"))

# ---- Salaries
@app.route("/salaries")
def salaries_list():
    con = get_db()
    rows = con.execute("""
      SELECT s.*, w.name AS worker_name
      FROM salary_payments s JOIN workers w ON w.id=s.worker_id
      ORDER BY s.pay_date DESC, s.id DESC
    """).fetchall()
    workers = con.execute("SELECT id,name FROM workers ORDER BY name").fetchall()
    con.close()
    try:
        return render_template("salaries.html", rows=rows, workers=workers)
    except TemplateNotFound:
        return render_template_string("<pre>{{ rows|length }} salaries</pre>", rows=rows)

@app.post("/salaries/add")
def salaries_add():
    d = request.form or request.json
    worker_id = int(d.get("worker_id"))
    salary_amount = float(d.get("salary_amount"))
    pay_date = (d.get("pay_date") or "").strip()
    note = d.get("note") or ""
    try:
        datetime.fromisoformat(pay_date)
    except Exception:
        return "pay_date must be YYYY-MM-DD", 400
    con = get_db()
    con.execute("INSERT INTO salary_payments (worker_id, salary_amount, pay_date, note) VALUES (?,?,?,?)",
                (worker_id, salary_amount, pay_date, note))
    con.commit(); con.close()
    return redirect(url_for("salaries_list"))

@app.post("/salaries/<int:sid>/toggle")
def salaries_toggle(sid):
    _toggle_active("salary_payments", sid)
    return redirect(url_for("salaries_list"))

@app.get("/salaries/<int:sid>/edit")
def salaries_edit_form(sid):
    con = get_db()
    r = con.execute("SELECT * FROM salary_payments WHERE id=?", (sid,)).fetchone()
    workers = con.execute("SELECT id,name FROM workers ORDER BY name").fetchall()
    con.close()
    if not r: abort(404)
    try:
        return render_template("salaries_edit.html", r=r, workers=workers)
    except TemplateNotFound:
        return render_template_string("<pre>edit salary {{ r['id'] }}</pre>", r=r)

@app.post("/salaries/<int:sid>/edit")
def salaries_edit(sid):
    d = request.form or request.json
    worker_id = int(d.get("worker_id"))
    salary_amount = float(d.get("salary_amount"))
    pay_date = (d.get("pay_date") or "").strip()
    note = d.get("note") or ""
    try:
        datetime.fromisoformat(pay_date)
    except Exception:
        return "pay_date must be YYYY-MM-DD", 400
    con = get_db()
    con.execute("UPDATE salary_payments SET worker_id=?, salary_amount=?, pay_date=?, note=? WHERE id=?",
                (worker_id, salary_amount, pay_date, note, sid))
    con.commit(); con.close()
    return redirect(url_for("salaries_list"))

@app.post("/salaries/<int:sid>/delete")
def salaries_delete(sid):
    con = get_db()
    con.execute("DELETE FROM salary_payments WHERE id=?", (sid,))
    con.commit(); con.close()
    return redirect(url_for("salaries_list"))

# ---- Expenses
@app.route("/expenses")
def expenses_list():
    con = get_db()
    rows = con.execute("""
      SELECT e.*, w.name AS worker_name
      FROM expense_records e
      LEFT JOIN workers w ON w.id=e.worker_id
      ORDER BY e.date DESC, e.id DESC
    """).fetchall()
    workers = con.execute("SELECT id,name FROM workers ORDER BY name").fetchall()
    con.close()
    try:
        return render_template("expenses.html", rows=rows, workers=workers)
    except TemplateNotFound:
        return render_template_string("<pre>{{ rows|length }} expenses</pre>", rows=rows)

@app.post("/expenses/add")
def expenses_add():
    d = request.form or request.json
    worker_id = d.get("worker_id")
    worker_id = int(worker_id) if worker_id else None
    amount = float(d.get("amount"))
    date = (d.get("date") or "").strip()
    note = d.get("note") or ""
    try:
        datetime.fromisoformat(date)
    except Exception:
        return "date must be YYYY-MM-DD", 400
    con = get_db()
    con.execute("INSERT INTO expense_records (worker_id, amount, date, note) VALUES (?,?,?,?)",
                (worker_id, amount, date, note))
    con.commit(); con.close()
    return redirect(url_for("expenses_list"))

@app.post("/expenses/<int:eid>/toggle")
def expenses_toggle(eid):
    _toggle_active("expense_records", eid)
    return redirect(url_for("expenses_list"))

@app.get("/expenses/<int:eid>/edit")
def expenses_edit_form(eid):
    con = get_db()
    r = con.execute("SELECT * FROM expense_records WHERE id=?", (eid,)).fetchone()
    workers = con.execute("SELECT id,name FROM workers ORDER BY name").fetchall()
    con.close()
    if not r: abort(404)
    try:
        return render_template("expenses_edit.html", r=r, workers=workers)
    except TemplateNotFound:
        return render_template_string("<pre>edit expense {{ r['id'] }}</pre>", r=r)

@app.post("/expenses/<int:eid>/edit")
def expenses_edit(eid):
    d = request.form or request.json
    worker_id = d.get("worker_id"); worker_id = int(worker_id) if worker_id else None
    amount = float(d.get("amount"))
    date = (d.get("date") or "").strip()
    note = d.get("note") or ""
    try:
        datetime.fromisoformat(date)
    except Exception:
        return "date must be YYYY-MM-DD", 400
    con = get_db()
    con.execute("UPDATE expense_records SET worker_id=?, amount=?, date=?, note=? WHERE id=?",
                (worker_id, amount, date, note, eid))
    con.commit(); con.close()
    return redirect(url_for("expenses_list"))

@app.post("/expenses/<int:eid>/delete")
def expenses_delete(eid):
    con = get_db()
    con.execute("DELETE FROM expense_records WHERE id=?", (eid,))
    con.commit(); con.close()
    return redirect(url_for("expenses_list"))

# ---- Export
def export_csv(query, headers, filename):
    con = get_db()
    rows = con.execute(query).fetchall()
    con.close()
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(headers)
    for r in rows: cw.writerow([r[h] for h in headers])
    mem = io.BytesIO(si.getvalue().encode("utf-8-sig"))
    mem.seek(0)
    return send_file(mem, mimetype="text/csv", as_attachment=True, download_name=filename)

@app.get("/export/workers.csv")
def export_workers():
    return export_csv(
        "SELECT id,name,company,commission,expenses,created_at FROM workers ORDER BY id",
        ["id","name","company","commission","expenses","created_at"],
        "workers.csv"
    )

@app.get("/export/bank_accounts.csv")
def export_bank():
    return export_csv(
        """SELECT b.id, w.name as worker_name, b.account_number, b.bank_name, b.created_at
           FROM bank_accounts b JOIN workers w ON w.id=b.worker_id ORDER BY b.id""",
        ["id","worker_name","account_number","bank_name","created_at"],
        "bank_accounts.csv"
    )

@app.get("/export/card_rentals.csv")
def export_rentals():
    return export_csv(
        """SELECT c.id, w.name as worker_name, c.rental_amount, c.date, c.note, c.created_at
           FROM card_rentals c JOIN workers w ON w.id=c.worker_id ORDER BY c.date DESC, c.id""",
        ["id","worker_name","rental_amount","date","note","created_at"],
        "card_rentals.csv"
    )

@app.get("/export/salaries.csv")
def export_salaries():
    return export_csv(
        """SELECT s.id, w.name as worker_name, s.salary_amount, s.pay_date, s.note, s.created_at
           FROM salary_payments s JOIN workers w ON w.id=s.worker_id ORDER BY s.pay_date DESC, s.id""",
        ["id","worker_name","salary_amount","pay_date","note","created_at"],
        "salaries.csv"
    )

@app.get("/export/expenses.csv")
def export_expenses():
    return export_csv(
        """SELECT e.id, w.name as worker_name, e.amount, e.date, e.note, e.created_at
           FROM expense_records e LEFT JOIN workers w ON w.id=e.worker_id ORDER BY e.date DESC, e.id""",
        ["id","worker_name","amount","date","note","created_at"],
        "expenses.csv"
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
