from flask import (
    Flask, request, jsonify, render_template, render_template_string,
    redirect, url_for, send_file, session, abort, flash
)
import sqlite3, csv, io, os, logging
from datetime import datetime
from jinja2 import TemplateNotFound
from werkzeug.security import generate_password_hash, check_password_hash

# -----------------------------------------------------------------------------
# 基本配置
# -----------------------------------------------------------------------------
APP_DB = os.environ.get("APP_DB", "data.db")

# 首次初始化的默认账号（之后以数据库为准）
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")

# -----------------------------------------------------------------------------
# 日志 & 错误处理
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)

@app.errorhandler(TemplateNotFound)
def handle_tpl_not_found(e):
    return (
        f"Oops, template not found: <b>templates/{e.name}</b><br>"
        "请把对应页面文件放到 <code>templates/</code> 目录，并确认文件名大小写一致。",
        500,
    )

@app.errorhandler(Exception)
def handle_any_error(e):
    app.logger.exception("Unhandled error")
    return (
        f"Error: <b>{e.__class__.__name__}</b><br>"
        f"Message: {str(e)}<br>"
        "请到部署平台（如 Railway）的日志面板查看完整堆栈。",
        500,
    )

@app.get("/__diag__")
def __diag():
    return render_template_string("OK — lang={{lang}}, app={{t.app_name}}")

@app.get("/favicon.ico")
def favicon():
    return ("", 204)

# -----------------------------------------------------------------------------
# I18N
# -----------------------------------------------------------------------------
I18N = {
    "zh": {
        "app_name": "NepWin Ops",
        "welcome_tip": "欢迎进入后台管理系统！",
        "login_tip": "请输入管理员账号和密码。",
        "username": "用户名",
        "password": "密码",
        "login": "登录",
        "logout": "退出",
        "workers": "工人 / 平台",
        "bank_accounts": "银行账户",
        "card_rentals": "银行卡租金",
        "salaries": "出粮记录",
        "expenses": "开销记录",
        "actions": "操作",
        "add": "新增",
        "edit": "编辑",
        "delete": "删除",
        "save": "保存",
        "back": "返回",
        "confirm_delete": "确定要删除吗？",
        "empty": "暂无数据",
        "created_at": "创建时间",
        "status": "状态",
        "active": "启用",
        "inactive": "停用",
        "name": "姓名",
        "company": "公司",
        "commission": "佣金",
        "salary_amount": "工资金额",
        "pay_date": "发放日期",
        "note": "备注",
        "date": "日期",
        "worker": "工人",
        "expense_amount": "开销金额",
        "expenses_note": "开销备注",
        "export_workers": "导出工人",
        "export_bank": "导出银行账户",
        "export_rentals": "导出租金",
        "export_salaries": "导出工资",
        "export_expenses": "导出开销",
        "total_workers": "工人总数",
        "total_rentals": "总租金",
        "total_salaries": "总工资",
        "total_expenses": "总开销",
    },
    "en": {
        "app_name": "NepWin Ops",
        "welcome_tip": "Welcome to the dashboard!",
        "login_tip": "Please enter your admin credentials.",
        "username": "Username",
        "password": "Password",
        "login": "Login",
        "logout": "Logout",
        "workers": "Workers / Platforms",
        "bank_accounts": "Bank Accounts",
        "card_rentals": "Card Rentals",
        "salaries": "Salaries",
        "expenses": "Expenses",
        "actions": "Actions",
        "add": "Add",
        "edit": "Edit",
        "delete": "Delete",
        "save": "Save",
        "back": "Back",
        "confirm_delete": "Are you sure you want to delete?",
        "empty": "No data",
        "created_at": "Created At",
        "status": "Status",
        "active": "Active",
        "inactive": "Inactive",
        "name": "Name",
        "company": "Company",
        "commission": "Commission",
        "salary_amount": "Salary Amount",
        "pay_date": "Pay Date",
        "note": "Note",
        "date": "Date",
        "worker": "Worker",
        "expense_amount": "Expense Amount",
        "expenses_note": "Expense Note",
        "export_workers": "Export Workers",
        "export_bank": "Export Bank Accounts",
        "export_rentals": "Export Rentals",
        "export_salaries": "Export Salaries",
        "export_expenses": "Export Expenses",
        "total_workers": "Total Workers",
        "total_rentals": "Total Rentals",
        "total_salaries": "Total Salaries",
        "total_expenses": "Total Expenses",
    },
}

# -----------------------------------------------------------------------------
# 工具函数
# -----------------------------------------------------------------------------
def get_lang():
    return request.args.get("lang") or request.cookies.get("lang") or "zh"

def T():
    lang = get_lang()
    return I18N.get(lang, I18N["zh"])

def conn():
    c = sqlite3.connect(APP_DB)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    with conn() as c:
        cur = c.cursor()
        # users
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password_hash TEXT,
                is_admin INTEGER DEFAULT 1
            )
        """)
        # workers
        cur.execute("""
            CREATE TABLE IF NOT EXISTS workers(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                company TEXT,
                commission REAL DEFAULT 0.0,
                expenses REAL DEFAULT 0.0,
                created_at TEXT
            )
        """)
        # bank_accounts
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bank_accounts(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bank_name TEXT,
                account_no TEXT,
                holder TEXT,
                status INTEGER DEFAULT 1,
                created_at TEXT
            )
        """)
        # card_rentals
        cur.execute("""
            CREATE TABLE IF NOT EXISTS card_rentals(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bank_account_id INTEGER,
                monthly_rent REAL,
                start_date TEXT,
                end_date TEXT,
                note TEXT,
                created_at TEXT
            )
        """)
        # salaries
        cur.execute("""
            CREATE TABLE IF NOT EXISTS salaries(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                worker_id INTEGER,
                amount REAL,
                pay_date TEXT,
                note TEXT,
                created_at TEXT
            )
        """)
        # expenses
        cur.execute("""
            CREATE TABLE IF NOT EXISTS expenses(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                worker_id INTEGER,
                amount REAL,
                date TEXT,
                note TEXT,
                created_at TEXT
            )
        """)
        # default admin
        cur.execute("SELECT COUNT(*) n FROM users")
        n = cur.fetchone()["n"]
        if n == 0:
            cur.execute(
                "INSERT INTO users(username, password_hash, is_admin) VALUES(?,?,1)",
                (ADMIN_USERNAME, generate_password_hash(ADMIN_PASSWORD))
            )
        c.commit()

# -----------------------------------------------------------------------------
# 请求级上下文
# -----------------------------------------------------------------------------
@app.before_request
def inject_globals():
    # 简单的全局模板变量
    lang = get_lang()
    setattr(request, "lang", lang)

@app.context_processor
def inject_t():
    return {"t": T(), "lang": get_lang()}

# -----------------------------------------------------------------------------
# Auth
# -----------------------------------------------------------------------------
def require_login():
    if not session.get("user_id"):
        return redirect(url_for("login", next=request.path))

@app.get("/login")
def login():
    return render_template("login.html")

@app.post("/login")
def login_post():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()
    with conn() as c:
        cur = c.cursor()
        cur.execute("SELECT * FROM users WHERE username=?", (username,))
        u = cur.fetchone()
        if not u or not check_password_hash(u["password_hash"], password):
            flash("用户名或密码不正确", "error")
            return redirect(url_for("login"))
        session["user_id"] = u["username"]
    return redirect(url_for("dashboard"))

@app.get("/logout")
def logout():
    session.clear
    return redirect(url_for("login"))

# -----------------------------------------------------------------------------
# Dashboard
# -----------------------------------------------------------------------------
@app.get("/")
def dashboard():
    if require_login(): return require_login()
    with conn() as c:
        cur = c.cursor()
        cur.execute("SELECT COUNT(*) n FROM workers"); total_workers = cur.fetchone()["n"]
        cur.execute("SELECT IFNULL(SUM(monthly_rent),0) s FROM card_rentals"); total_rentals = cur.fetchone()["s"]
        cur.execute("SELECT IFNULL(SUM(amount),0) s FROM salaries"); total_salaries = cur.fetchone()["s"]
        cur.execute("SELECT IFNULL(SUM(amount),0) s FROM expenses"); total_expenses = cur.fetchone()["s"]
    return render_template("dashboard.html",
                           total_workers=total_workers,
                           total_rentals=total_rentals,
                           total_salaries=total_salaries,
                           total_expenses=total_expenses)

# -----------------------------------------------------------------------------
# 安全中心：账号/密码修改、重置
# -----------------------------------------------------------------------------
@app.get("/account-security")
def account_security():
    if require_login(): return require_login()
    return render_template("account_security.html")

@app.get("/account/credentials")
def account_credentials():
    if require_login(): return require_login()
    return render_template("account_credentials.html")

@app.post("/account/credentials")
def account_credentials_post():
    if require_login(): return require_login()
    new_username = request.form.get("username","").strip()
    new_password = request.form.get("password","").strip()
    if not new_username or not new_password:
        flash("用户名与密码不能为空", "error")
        return redirect(url_for("account_credentials"))
    with conn() as c:
        cur = c.cursor()
        cur.execute("SELECT * FROM users WHERE username=?", (session["user_id"],))
        u = cur.fetchone()
        if not u:
            abort(403)
        cur.execute("UPDATE users SET username=?, password_hash=? WHERE id=?",
                    (new_username, generate_password_hash(new_password), u["id"]))
        c.commit()
        session["user_id"] = new_username
    flash("登录账号与密码已更新", "success")
    return redirect(url_for("dashboard"))

@app.get("/account/change-password")
def account_change_password():
    if require_login(): return require_login()
    return render_template("account_change_password.html")

@app.post("/account/change-password")
def account_change_password_post():
    if require_login(): return require_login()
    old_pw = request.form.get("old_password","")
    new_pw = request.form.get("new_password","")
    if not old_pw or not new_pw:
        flash("请输入旧密码与新密码", "error")
        return redirect(url_for("account_change_password"))
    with conn() as c:
        cur = c.cursor()
        cur.execute("SELECT * FROM users WHERE username=?", (session["user_id"],))
        u = cur.fetchone()
        if not u or not check_password_hash(u["password_hash"], old_pw):
            flash("旧密码不正确", "error")
            return redirect(url_for("account_change_password"))
        cur.execute("UPDATE users SET password_hash=? WHERE id=?",
                    (generate_password_hash(new_pw), u["id"]))
        c.commit()
    flash("密码已更新", "success")
    return redirect(url_for("dashboard"))

@app.get("/account/change-username")
def account_change_username():
    if require_login(): return require_login()
    return render_template("account_change_username.html")

@app.post("/account/change-username")
def account_change_username_post():
    if require_login(): return require_login()
    new_username = request.form.get("new_username","").strip()
    if not new_username:
        flash("新用户名不能为空", "error")
        return redirect(url_for("account_change_username"))
    with conn() as c:
        cur = c.cursor()
        cur.execute("SELECT * FROM users WHERE username=?", (session["user_id"],))
        u = cur.fetchone()
        if not u:
            abort(403)
        cur.execute("UPDATE users SET username=? WHERE id=?", (new_username, u["id"]))
        c.commit()
        session["user_id"] = new_username
    flash("用户名已更新", "success")
    return redirect(url_for("dashboard"))

@app.get("/account/reset")
def account_reset():
    if require_login(): return require_login()
    return render_template("account_reset.html")

@app.post("/account/reset")
def account_reset_post():
    if require_login(): return require_login()
    target_username = request.form.get("target_username","").strip()
    new_password = request.form.get("new_password","").strip()
    if not target_username or not new_password:
        flash("目标用户名与新密码不能为空", "error")
        return redirect(url_for("account_reset"))
    with conn() as c:
        cur = c.cursor()
        cur.execute("SELECT * FROM users WHERE username=?", (target_username,))
        u = cur.fetchone()
        if not u:
            flash("目标用户不存在", "error")
            return redirect(url_for("account_reset"))
        cur.execute("UPDATE users SET password_hash=? WHERE id=?",
                    (generate_password_hash(new_password), u["id"]))
        c.commit()
    flash("目标用户密码已重置", "success")
    return redirect(url_for("dashboard"))

# -----------------------------------------------------------------------------
# 工人 / 平台 CRUD
# -----------------------------------------------------------------------------
@app.get("/workers")
def workers_list():
    if require_login(): return require_login()
    with conn() as c:
        cur = c.cursor()
        cur.execute("SELECT * FROM workers ORDER BY id DESC")
        rows = cur.fetchall()
    return render_template("workers_list.html", rows=rows)

@app.post("/workers/add")
def workers_add():
    if require_login(): return require_login()
    name = request.form.get("name","").strip()
    company = request.form.get("company","").strip()
    commission = float(request.form.get("commission") or 0)
    expenses = float(request.form.get("expenses") or 0)
    with conn() as c:
        cur = c.cursor()
        cur.execute("""
            INSERT INTO workers(name,company,commission,expenses,created_at)
            VALUES(?,?,?,?,?)
        """, (name, company, commission, expenses, datetime.utcnow().isoformat()))
        c.commit()
    return redirect(url_for("workers_list"))

@app.get("/workers/<int:wid>/edit")
def workers_edit_form(wid):
    if require_login(): return require_login()
    with conn() as c:
        cur = c.cursor()
        cur.execute("SELECT * FROM workers WHERE id=?", (wid,))
        r = cur.fetchone()
        if not r: abort(404)
    return render_template("workers_edit.html", r=r)

@app.post("/workers/<int:wid>/edit")
def workers_edit(wid):
    if require_login(): return require_login()
    name = request.form.get("name","").strip()
    company = request.form.get("company","").strip()
    commission = float(request.form.get("commission") or 0)
    expenses = float(request.form.get("expenses") or 0)
    with conn() as c:
        cur = c.cursor()
        cur.execute("""
            UPDATE workers SET name=?, company=?, commission=?, expenses=? WHERE id=?
        """, (name, company, commission, expenses, wid))
        c.commit()
    return redirect(url_for("workers_list"))

@app.post("/workers/<int:wid>/delete")
def workers_delete(wid):
    if require_login(): return require_login()
    with conn() as c:
        c.execute("DELETE FROM workers WHERE id=?", (wid,))
        c.commit()
    return redirect(url_for("workers_list"))

@app.get("/export/workers.csv")
def export_workers():
    if require_login(): return require_login()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id","name","company","commission","expenses","created_at"])
    with conn() as c:
        cur = c.cursor()
        for r in c.execute("SELECT * FROM workers ORDER BY id DESC"):
            writer.writerow([r["id"],r["name"],r["company"],r["commission"],r["expenses"],r["created_at"]])
    mem = io.BytesIO(output.getvalue().encode("utf-8"))
    return send_file(mem, mimetype="text/csv", as_attachment=True, download_name="workers.csv")

# -----------------------------------------------------------------------------
# 银行账户 CRUD
# -----------------------------------------------------------------------------
@app.get("/bank-accounts")
def bank_accounts_list():
    if require_login(): return require_login()
    with conn() as c:
        cur = c.cursor()
        cur.execute("SELECT * FROM bank_accounts ORDER BY id DESC")
        rows = cur.fetchall()
    return render_template("bank_accounts_list.html", rows=rows)

@app.post("/bank-accounts/add")
def bank_accounts_add():
    if require_login(): return require_login()
    bank_name = request.form.get("bank_name","").strip()
    account_no = request.form.get("account_no","").strip()
    holder = request.form.get("holder","").strip()
    status = 1 if request.form.get("status") == "1" else 0
    with conn() as c:
        cur = c.cursor()
        cur.execute("""
            INSERT INTO bank_accounts(bank_name,account_no,holder,status,created_at)
            VALUES(?,?,?,?,?)
        """, (bank_name, account_no, holder, status, datetime.utcnow().isoformat()))
        c.commit()
    return redirect(url_for("bank_accounts_list"))

@app.get("/bank-accounts/<int:bid>/edit")
def bank_accounts_edit_form(bid):
    if require_login(): return require_login()
    with conn() as c:
        cur = c.cursor()
        cur.execute("SELECT * FROM bank_accounts WHERE id=?", (bid,))
        r = cur.fetchone()
        if not r: abort(404)
    return render_template("bank_accounts_edit.html", r=r)

@app.post("/bank-accounts/<int:bid>/edit")
def bank_accounts_edit(bid):
    if require_login(): return require_login()
    bank_name = request.form.get("bank_name","").strip()
    account_no = request.form.get("account_no","").strip()
    holder = request.form.get("holder","").strip()
    status = 1 if request.form.get("status") == "1" else 0
    with conn() as c:
        cur = c.cursor()
        cur.execute("""
            UPDATE bank_accounts SET bank_name=?, account_no=?, holder=?, status=? WHERE id=?
        """, (bank_name, account_no, holder, status, bid))
        c.commit()
    return redirect(url_for("bank_accounts_list"))

@app.post("/bank-accounts/<int:bid>/delete")
def bank_accounts_delete(bid):
    if require_login(): return require_login()
    with conn() as c:
        c.execute("DELETE FROM bank_accounts WHERE id=?", (bid,))
        c.commit()
    return redirect(url_for("bank_accounts_list"))

@app.get("/export/bank_accounts.csv")
def export_bank_accounts():
    if require_login(): return require_login()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id","bank_name","account_no","holder","status","created_at"])
    with conn() as c:
        cur = c.cursor()
        for r in c.execute("SELECT * FROM bank_accounts ORDER BY id DESC"):
            writer.writerow([r["id"],r["bank_name"],r["account_no"],r["holder"],r["status"],r["created_at"]])
    mem = io.BytesIO(output.getvalue().encode("utf-8"))
    return send_file(mem, mimetype="text/csv", as_attachment=True, download_name="bank_accounts.csv")

# -----------------------------------------------------------------------------
# 银行卡租金 CRUD
# -----------------------------------------------------------------------------
@app.get("/card-rentals")
def card_rentals_list():
    if require_login(): return require_login()
    with conn() as c:
        cur = c.cursor()
        cur.execute("""
            SELECT cr.*, ba.bank_name, ba.account_no
            FROM card_rentals cr
            LEFT JOIN bank_accounts ba ON ba.id = cr.bank_account_id
            ORDER BY cr.id DESC
        """)
        rows = cur.fetchall()
        cur.execute("SELECT id, bank_name, account_no FROM bank_accounts ORDER BY id DESC")
        banks = cur.fetchall()
    return render_template("card_rentals_list.html", rows=rows, banks=banks)

@app.post("/card-rentals/add")
def card_rentals_add():
    if require_login(): return require_login()
    bank_account_id = int(request.form.get("bank_account_id") or 0)
    monthly_rent = float(request.form.get("monthly_rent") or 0)
    start_date = request.form.get("start_date","")
    end_date = request.form.get("end_date","")
    note = request.form.get("note","")
    with conn() as c:
        cur = c.cursor()
        cur.execute("""
            INSERT INTO card_rentals(bank_account_id, monthly_rent, start_date, end_date, note, created_at)
            VALUES(?,?,?,?,?,?)
        """, (bank_account_id, monthly_rent, start_date, end_date, note, datetime.utcnow().isoformat()))
        c.commit()
    return redirect(url_for("card_rentals_list"))

@app.get("/card-rentals/<int:rid>/edit")
def card_rentals_edit_form(rid):
    if require_login(): return require_login()
    with conn() as c:
        cur = c.cursor()
        cur.execute("SELECT * FROM card_rentals WHERE id=?", (rid,))
        r = cur.fetchone()
        if not r: abort(404)
        cur.execute("SELECT id, bank_name, account_no FROM bank_accounts ORDER BY id DESC")
        banks = cur.fetchall()
    return render_template("card_rentals_edit.html", r=r, banks=banks)

@app.post("/card-rentals/<int:rid>/edit")
def card_rentals_edit(rid):
    if require_login(): return require_login()
    bank_account_id = int(request.form.get("bank_account_id") or 0)
    monthly_rent = float(request.form.get("monthly_rent") or 0)
    start_date = request.form.get("start_date","")
    end_date = request.form.get("end_date","")
    note = request.form.get("note","")
    with conn() as c:
        cur = c.cursor()
        cur.execute("""
            UPDATE card_rentals SET bank_account_id=?, monthly_rent=?, start_date=?, end_date=?, note=? WHERE id=?
        """, (bank_account_id, monthly_rent, start_date, end_date, note, rid))
        c.commit()
    return redirect(url_for("card_rentals_list"))

@app.post("/card-rentals/<int:rid>/delete")
def card_rentals_delete(rid):
    if require_login(): return require_login()
    with conn() as c:
        c.execute("DELETE FROM card_rentals WHERE id=?", (rid,))
        c.commit()
    return redirect(url_for("card_rentals_list"))

@app.get("/export/card_rentals.csv")
def export_card_rentals():
    if require_login(): return require_login()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id","bank_account_id","monthly_rent","start_date","end_date","note","created_at"])
    with conn() as c:
        cur = c.cursor()
        for r in c.execute("SELECT * FROM card_rentals ORDER BY id DESC"):
            writer.writerow([r["id"],r["bank_account_id"],r["monthly_rent"],r["start_date"],r["end_date"],r["note"],r["created_at"]])
    mem = io.BytesIO(output.getvalue().encode("utf-8"))
    return send_file(mem, mimetype="text/csv", as_attachment=True, download_name="card_rentals.csv")

# -----------------------------------------------------------------------------
# 出粮记录（工资） CRUD
# -----------------------------------------------------------------------------
@app.get("/salaries")
def salaries_list():
    if require_login(): return require_login()
    with conn() as c:
        cur = c.cursor()
        cur.execute("""
            SELECT s.*, w.name AS worker_name
            FROM salaries s LEFT JOIN workers w ON w.id = s.worker_id
            ORDER BY s.id DESC
        """)
        rows = cur.fetchall()
        cur.execute("SELECT id, name FROM workers ORDER BY id DESC")
        workers = cur.fetchall()
    return render_template("salaries_list.html", rows=rows, workers=workers)

@app.post("/salaries/add")
def salaries_add():
    if require_login(): return require_login()
    worker_id = int(request.form.get("worker_id") or 0)
    amount = float(request.form.get("amount") or 0)
    pay_date = request.form.get("pay_date","")
    note = request.form.get("note","")
    with conn() as c:
        cur = c.cursor()
        cur.execute("""
            INSERT INTO salaries(worker_id, amount, pay_date, note, created_at)
            VALUES(?,?,?,?,?)
        """, (worker_id, amount, pay_date, note, datetime.utcnow().isoformat()))
        c.commit()
    return redirect(url_for("salaries_list"))

@app.get("/salaries/<int:sid>/edit")
def salaries_edit_form(sid):
    if require_login(): return require_login()
    with conn() as c:
        cur = c.cursor()
        cur.execute("SELECT * FROM salaries WHERE id=?", (sid,))
        r = cur.fetchone()
        if not r: abort(404)
        cur.execute("SELECT id, name FROM workers ORDER BY id DESC")
        workers = cur.fetchall()
    return render_template("salaries_edit.html", r=r, workers=workers)

@app.post("/salaries/<int:sid>/edit")
def salaries_edit(sid):
    if require_login(): return require_login()
    worker_id = int(request.form.get("worker_id") or 0)
    amount = float(request.form.get("amount") or 0)
    pay_date = request.form.get("pay_date","")
    note = request.form.get("note","")
    with conn() as c:
        cur = c.cursor()
        cur.execute("""
            UPDATE salaries SET worker_id=?, amount=?, pay_date=?, note=? WHERE id=?
        """, (worker_id, amount, pay_date, note, sid))
        c.commit()
    return redirect(url_for("salaries_list"))

@app.post("/salaries/<int:sid>/delete")
def salaries_delete(sid):
    if require_login(): return require_login()
    with conn() as c:
        c.execute("DELETE FROM salaries WHERE id=?", (sid,))
        c.commit()
    return redirect(url_for("salaries_list"))

@app.get("/export/salaries.csv")
def export_salaries():
    if require_login(): return require_login()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id","worker_id","amount","pay_date","note","created_at"])
    with conn() as c:
        cur = c.cursor()
        for r in c.execute("SELECT * FROM salaries ORDER BY id DESC"):
            writer.writerow([r["id"],r["worker_id"],r["amount"],r["pay_date"],r["note"],r["created_at"]])
    mem = io.BytesIO(output.getvalue().encode("utf-8"))
    return send_file(mem, mimetype="text/csv", as_attachment=True, download_name="salaries.csv")

# -----------------------------------------------------------------------------
# 开销 CRUD
# -----------------------------------------------------------------------------
@app.get("/expenses")
def expenses_list():
    if require_login(): return require_login()
    with conn() as c:
        cur = c.cursor()
        cur.execute("""
            SELECT e.*, w.name AS worker_name
            FROM expenses e LEFT JOIN workers w ON w.id = e.worker_id
            ORDER BY e.id DESC
        """)
        rows = cur.fetchall()
        cur.execute("SELECT id, name FROM workers ORDER BY id DESC")
        workers = cur.fetchall()
    return render_template("expenses_list.html", rows=rows, workers=workers)

@app.post("/expenses/add")
def expenses_add():
    if require_login(): return require_login()
    worker_id = int(request.form.get("worker_id") or 0)
    amount = float(request.form.get("amount") or 0)
    date = request.form.get("date","")
    note = request.form.get("note","")
    with conn() as c:
        cur = c.cursor()
        cur.execute("""
            INSERT INTO expenses(worker_id, amount, date, note, created_at)
            VALUES(?,?,?,?,?)
        """, (worker_id, amount, date, note, datetime.utcnow().isoformat()))
        c.commit()
    return redirect(url_for("expenses_list"))

@app.get("/expenses/<int:eid>/edit")
def expenses_edit_form(eid):
    if require_login(): return require_login()
    with conn() as c:
        cur = c.cursor()
        cur.execute("SELECT * FROM expenses WHERE id=?", (eid,))
        r = cur.fetchone()
        if not r: abort(404)
        cur.execute("SELECT id, name FROM workers ORDER BY id DESC")
        workers = cur.fetchall()
    return render_template("expenses_edit.html", r=r, workers=workers)

@app.post("/expenses/<int:eid>/edit")
def expenses_edit(eid):
    if require_login(): return require_login()
    worker_id = int(request.form.get("worker_id") or 0)
    amount = float(request.form.get("amount") or 0)
    date = request.form.get("date","")
    note = request.form.get("note","")
    with conn() as c:
        cur = c.cursor()
        cur.execute("""
            UPDATE expenses SET worker_id=?, amount=?, date=?, note=? WHERE id=?
        """, (worker_id, amount, date, note, eid))
        c.commit()
    return redirect(url_for("expenses_list"))

@app.post("/expenses/<int:eid>/delete")
def expenses_delete(eid):
    if require_login(): return require_login()
    with conn() as c:
        c.execute("DELETE FROM expenses WHERE id=?", (eid,))
        c.commit()
    return redirect(url_for("expenses_list"))

@app.get("/export/expenses.csv")
def export_expenses():
    if require_login(): return require_login()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id","worker_id","amount","date","note","created_at"])
    with conn() as c:
        cur = c.cursor()
        for r in c.execute("SELECT * FROM expenses ORDER BY id DESC"):
            writer.writerow([r["id"],r["worker_id"],r["amount"],r["date"],r["note"],r["created_at"]])
    mem = io.BytesIO(output.getvalue().encode("utf-8"))
    return send_file(mem, mimetype="text/csv", as_attachment=True, download_name="expenses.csv")

# ✅ 关键：在 gunicorn 导入时也初始化数据库（首次部署避免 "no such table"）
init_db()

# -----------------------------------------------------------------------------
# 本地启动（Railway 用 Procfile 启动，无需走这里）
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
