from flask import Flask, request, jsonify, render_template, redirect, url_for, send_file, session, g
import sqlite3, csv, io, os
from datetime import datetime

APP_DB = "data.db"
app = Flask(__name__)

# ---------- i18n: 多语言（中文/英文） ----------
app.secret_key = os.environ.get("SECRET_KEY", "dev-key")
LANGS = ("en", "zh")
T = {
    "en": {
        "AppTitle": "Ops Dashboard",
        "Overview": "Overview",
        "Workers/Platforms": "Workers / Platforms",
        "Bank Accounts": "Bank Accounts",
        "Card Rentals": "Card Rentals",
        "Salary Records": "Salary Records",
        "Export": "Export",
        "Export Workers": "Export Workers",
        "Export Bank Accounts": "Export Bank Accounts",
        "Export Card Rentals": "Export Card Rentals",
        "Export Salaries": "Export Salaries",
        "Total Workers": "Total Workers",
        "Total Card Rentals": "Total Card Rentals",
        "Total Salaries": "Total Salaries",
        "Dashboard Tip": "Welcome! Use the left sidebar to navigate, and export CSV on the top-right.",
        "Add New": "Add New",
        "Name": "Name",
        "Company": "Company",
        "Commission": "Commission",
        "Expenses": "Expenses",
        "Created At": "Created At",
        "Worker": "Worker",
        "Bank Name": "Bank Name",
        "Account Number": "Account Number",
        "Amount": "Amount",
        "Date": "Date",
        "Note": "Note",
        "Pay Date": "Pay Date",
        "Actions": "Actions",
        "No Data": "No data yet",
        "Language": "Language",
        "English": "English",
        "Chinese": "Chinese",
        "Add": "Add",
        "Rental Amount": "Rental Amount",
        "Salary Amount": "Salary Amount",
        "Filters": "Filters",
        "Save": "Save",
        "Cancel": "Cancel",
        "Required": "required",
        "ID": "ID"
    },
    "zh": {
        "AppTitle": "运营看板",
        "Overview": "概览",
        "Workers/Platforms": "工人 / 平台",
        "Bank Accounts": "银行账户",
        "Card Rentals": "银行卡租金",
        "Salary Records": "出粮记录",
        "Export": "导出",
        "Export Workers": "导出工人",
        "Export Bank Accounts": "导出银行账户",
        "Export Card Rentals": "导出租金",
        "Export Salaries": "导出出粮",
        "Total Workers": "总工人/平台数",
        "Total Card Rentals": "银行卡租金累计",
        "Total Salaries": "出粮累计",
        "Dashboard Tip": "欢迎使用：左侧切换模块进行录入与查询，右上角可一键导出 CSV。",
        "Add New": "新增",
        "Name": "名字",
        "Company": "公司",
        "Commission": "佣金",
        "Expenses": "开销",
        "Created At": "创建时间",
        "Worker": "工人",
        "Bank Name": "银行名称",
        "Account Number": "账户号码",
        "Amount": "金额",
        "Date": "日期",
        "Note": "备注",
        "Pay Date": "出粮日期",
        "Actions": "操作",
        "No Data": "暂无数据",
        "Language": "语言",
        "English": "英文",
        "Chinese": "华语",
        "Add": "新增",
        "Rental Amount": "租金金额",
        "Salary Amount": "出粮金额",
        "Filters": "筛选",
        "Save": "保存",
        "Cancel": "取消",
        "Required": "必填",
        "ID": "ID"
    }
}

def get_lang():
    lang = session.get("lang")
    if lang in LANGS:
        return lang
    best = request.accept_languages.best_match(LANGS)
    return best or "zh"

@app.before_request
def _set_lang():
    g.lang = get_lang()

@app.context_processor
def inject_i18n():
    def _(key):
        lang = getattr(g, "lang", "zh")
        return T.get(lang, {}).get(key, key)
    return {"_": _, "current_lang": get_lang(), "LANGS": LANGS}

@app.route("/lang/<code>")
def set_lang(code):
    if code not in LANGS:
        code = "zh"
    session["lang"] = code
    ref = request.headers.get("Referer") or url_for("home")
    return redirect(ref)

# ---------- DB helpers ----------
def get_db():
    con = sqlite3.connect(APP_DB)
    con.row_factory = sqlite3.Row
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
    """)
    con.commit()
    con.close()

if not os.path.exists(APP_DB):
    init_db()

# ---------- Web UI ----------
@app.route("/")
def home():
    con = get_db()
    total_workers = con.execute("SELECT COUNT(*) c FROM workers").fetchone()["c"]
    total_rentals = con.execute("SELECT IFNULL(SUM(rental_amount),0) s FROM card_rentals").fetchone()["s"]
    total_salaries = con.execute("SELECT IFNULL(SUM(salary_amount),0) s FROM salary_payments").fetchone()["s"]
    total_expenses = con.execute("SELECT IFNULL(SUM(amount),0) s FROM expenses").fetchone()["s"]   # 👈 新增
    con.close()
    return render_template("index.html",
                           total_workers=total_workers,
                           total_rentals=total_rentals,
                           total_salaries=total_salaries)

# ---- workers ----
@app.route("/workers")
def workers_list():
    con = get_db()
    rows = con.execute("SELECT * FROM workers ORDER BY id DESC").fetchall()
    con.close()
    return render_template("workers.html", rows=rows)

@app.route("/workers/add", methods=["POST"])
def workers_add():
    data = request.form or request.json
    name = (data.get("name") or "").strip()
    if not name:
        return "Name is required", 400
    company = data.get("company") or ""
    commission = float(data.get("commission") or 0)
    expenses = float(data.get("expenses") or 0)
    con = get_db()
    con.execute(
        "INSERT INTO workers (name, company, commission, expenses) VALUES (?, ?, ?, ?)",
        (name, company, commission, expenses)
    )
    con.commit()
    con.close()
    if request.is_json:
        return jsonify({"ok": True})
    return redirect(url_for("workers_list"))

# ---- bank accounts ----
@app.route("/bank-accounts")
def bank_accounts_list():
    con = get_db()
    rows = con.execute("""
        SELECT b.*, w.name AS worker_name
        FROM bank_accounts b
        JOIN workers w ON w.id = b.worker_id
        ORDER BY b.id DESC
    """).fetchall()
    workers = con.execute("SELECT id, name FROM workers ORDER BY name").fetchall()
    con.close()
    return render_template("bank_accounts.html", rows=rows, workers=workers)

@app.route("/bank-accounts/add", methods=["POST"])
def bank_accounts_add():
    data = request.form or request.json
    worker_id = int(data.get("worker_id")) if data.get("worker_id") else 0
    account_number = (data.get("account_number") or "").strip()
    bank_name = (data.get("bank_name") or "").strip()
    if not (worker_id and account_number and bank_name):
        return "worker_id, account_number, bank_name required", 400
    con = get_db()
    con.execute(
        "INSERT INTO bank_accounts (worker_id, account_number, bank_name) VALUES (?, ?, ?)",
        (worker_id, account_number, bank_name)
    )
    con.commit()
    con.close()
    if request.is_json:
        return jsonify({"ok": True})
    return redirect(url_for("bank_accounts_list"))

# ---- card rentals ----
@app.route("/card-rentals")
def card_rentals_list():
    con = get_db()
    rows = con.execute("""
        SELECT c.*, w.name AS worker_name
        FROM card_rentals c
        JOIN workers w ON w.id = c.worker_id
        ORDER BY c.date DESC, c.id DESC
    """).fetchall()
    workers = con.execute("SELECT id, name FROM workers ORDER BY name").fetchall()
    con.close()
    return render_template("card_rentals.html", rows=rows, workers=workers)

@app.route("/card-rentals/add", methods=["POST"])
def card_rentals_add():
    data = request.form or request.json
    worker_id = int(data.get("worker_id")) if data.get("worker_id") else 0
    rental_amount = float(data.get("rental_amount") or 0)
    date = (data.get("date") or "").strip()
    note = data.get("note") or ""
    if not (worker_id and rental_amount and date):
        return "worker_id, rental_amount, date required", 400
    try:
        datetime.fromisoformat(date)
    except ValueError:
        return "date must be ISO format YYYY-MM-DD", 400
    con = get_db()
    con.execute(
        "INSERT INTO card_rentals (worker_id, rental_amount, date, note) VALUES (?, ?, ?, ?)",
        (worker_id, rental_amount, date, note)
    )
    con.commit()
    con.close()
    if request.is_json:
        return jsonify({"ok": True})
    return redirect(url_for("card_rentals_list"))

# ---- salaries ----
@app.route("/salaries")
def salaries_list():
    con = get_db()
    rows = con.execute("""
        SELECT s.*, w.name AS worker_name
        FROM salary_payments s
        JOIN workers w ON w.id = s.worker_id
        ORDER BY s.pay_date DESC, s.id DESC
    """).fetchall()
    workers = con.execute("SELECT id, name FROM workers ORDER BY name").fetchall()
    con.close()
    return render_template("salaries.html", rows=rows, workers=workers)

@app.route("/salaries/add", methods=["POST"])
def salaries_add():
    data = request.form or request.json
    worker_id = int(data.get("worker_id")) if data.get("worker_id") else 0
    salary_amount = float(data.get("salary_amount") or 0)
    pay_date = (data.get("pay_date") or "").strip()
    note = data.get("note") or ""
    if not (worker_id and salary_amount and pay_date):
        return "worker_id, salary_amount, pay_date required", 400
    try:
        datetime.fromisoformat(pay_date)
    except ValueError:
        return "pay_date must be ISO format YYYY-MM-DD", 400
    con = get_db()
    con.execute(
        "INSERT INTO salary_payments (worker_id, salary_amount, pay_date, note) VALUES (?, ?, ?, ?)",
        (worker_id, salary_amount, pay_date, note)
    )
    con.commit()
    con.close()
    if request.is_json:
        return jsonify({"ok": True})
    return redirect(url_for("salaries_list"))

# ---------- 导出 CSV ----------
def export_csv(query, headers, filename):
    con = get_db()
    rows = con.execute(query).fetchall()
    con.close()
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(headers)
    for r in rows:
        cw.writerow([r[h] for h in headers])
    mem = io.BytesIO()
    mem.write(si.getvalue().encode("utf-8-sig"))
    mem.seek(0)
    return send_file(mem, mimetype="text/csv", as_attachment=True, download_name=filename)

@app.route("/export/workers.csv")
def export_workers():
    return export_csv(
        "SELECT id,name,company,commission,expenses,created_at FROM workers ORDER BY id",
        ["id","name","company","commission","expenses","created_at"],
        "workers.csv"
    )

@app.route("/export/bank_accounts.csv")
def export_bank():
    return export_csv(
        """SELECT b.id, w.name as worker_name, b.account_number, b.bank_name, b.created_at
           FROM bank_accounts b JOIN workers w ON w.id=b.worker_id ORDER BY b.id""",
        ["id","worker_name","account_number","bank_name","created_at"],
        "bank_accounts.csv"
    )

@app.route("/export/card_rentals.csv")
def export_rentals():
    return export_csv(
        """SELECT c.id, w.name as worker_name, c.rental_amount, c.date, c.note, c.created_at
           FROM card_rentals c JOIN workers w ON w.id=c.worker_id ORDER BY c.date DESC, c.id""",
        ["id","worker_name","rental_amount","date","note","created_at"],
        "card_rentals.csv"
    )

@app.route("/export/salaries.csv")
def export_salaries():
    return export_csv(
        """SELECT s.id, w.name as worker_name, s.salary_amount, s.pay_date, s.note, s.created_at
           FROM salary_payments s JOIN workers w ON w.id=s.worker_id ORDER BY s.pay_date DESC, s.id""",
        ["id","worker_name","salary_amount","pay_date","note","created_at"],
        "salaries.csv"
    )

# ---------- 简单 REST API ----------
@app.route("/api/workers", methods=["GET"])
def api_workers():
    con = get_db()
    rows = con.execute("SELECT * FROM workers ORDER BY id DESC").fetchall()
    con.close()
    return jsonify([dict(r) for r in rows])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
