# app.py
from flask import (
    Flask, request, jsonify, render_template, redirect,
    url_for, send_file, session, g
)
import sqlite3, csv, io, os
from datetime import datetime

APP_DB = "data.db"
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-key-change-me")  # 用于会话（语言切换）

# ---------- 简单 i18n ----------
LANGUAGES = {
    "en": "English",
    "zh": "中文",
}
# 仅示例关键词；模版里用 {{ t('Workers') }} 这类键
T = {
    "en": {
        "Dashboard": "Dashboard",
        "Workers": "Workers",
        "Bank Accounts": "Bank Accounts",
        "Card Rentals": "Card Rentals",
        "Salaries": "Salaries",
        "Expenses": "Expenses",
        "Totals": "Totals",
        "Total Workers": "Total Workers",
        "Total Rentals": "Total Rentals",
        "Total Salaries": "Total Salaries",
        "Total Expenses": "Total Expenses",
        "Add": "Add",
        "Save": "Save",
        "Name": "Name",
        "Company": "Company",
        "Commission": "Commission",
        "Expenses (field)": "Expenses",
        "Created At": "Created At",
        "Worker": "Worker",
        "Account Number": "Account Number",
        "Bank Name": "Bank Name",
        "Amount": "Amount",
        "Date": "Date",
        "Category": "Category",
        "Note": "Note",
        "Salary Amount": "Salary Amount",
        "Pay Date": "Pay Date",
    },
    "zh": {
        "Dashboard": "概览",
        "Workers": "工人/平台",
        "Bank Accounts": "银行账户",
        "Card Rentals": "银行卡租金",
        "Salaries": "出粮记录",
        "Expenses": "开销",
        "Totals": "汇总",
        "Total Workers": "工人总数",
        "Total Rentals": "租金合计",
        "Total Salaries": "工资合计",
        "Total Expenses": "开销合计",
        "Add": "新增",
        "Save": "保存",
        "Name": "名字",
        "Company": "公司",
        "Commission": "佣金",
        "Expenses (field)": "开销",
        "Created At": "创建时间",
        "Worker": "工人",
        "Account Number": "账户号码",
        "Bank Name": "银行名称",
        "Amount": "金额",
        "Date": "日期",
        "Category": "类别",
        "Note": "备注",
        "Salary Amount": "工资金额",
        "Pay Date": "出粮日期",
    }
}

@app.before_request
def _load_locale():
    g.locale = session.get("locale", "zh") if session.get("locale") in LANGUAGES else "zh"

@app.context_processor
def inject_i18n():
    def t(key):
        return T.get(g.locale, T["zh"]).get(key, key)
    return {"t": t, "current_locale": g.locale, "LANGUAGES": LANGUAGES}

@app.route("/set-locale/<lang>")
def set_locale(lang):
    if lang in LANGUAGES:
        session["locale"] = lang
    return redirect(request.referrer or url_for("home"))

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

    -- 新增：开销表（可与 worker 关联，也可为 None 表示公共开销）
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        worker_id INTEGER,
        amount REAL NOT NULL,
        date TEXT NOT NULL,
        category TEXT,
        note TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(worker_id) REFERENCES workers(id)
    );
    """)
    con.commit()
    con.close()

# 确保每次启动都校验表结构（IF NOT EXISTS 不会重复建表）
init_db()

# ---------- 工具 ----------
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

# ---------- 首页 ----------
@app.route("/")
def home():
    con = get_db()
    total_workers = con.execute("SELECT COUNT(*) c FROM workers").fetchone()["c"]
    total_rentals = con.execute("SELECT IFNULL(SUM(rental_amount),0) s FROM card_rentals").fetchone()["s"]
    total_salaries = con.execute("SELECT IFNULL(SUM(salary_amount),0) s FROM salary_payments").fetchone()["s"]
    total_expenses = con.execute("SELECT IFNULL(SUM(amount),0) s FROM expenses").fetchone()["s"]
    con.close()
    return render_template(
        "index.html",
        total_workers=total_workers,
        total_rentals=total_rentals,
        total_salaries=total_salaries,
        total_expenses=total_expenses,
    )

# 提供给前端条形图的数据（你可以在 index.html 里用 Chart.js/ApexCharts 调这个接口）
@app.route("/chart/summary.json")
def chart_summary():
    con = get_db()
    total_rentals = con.execute("SELECT IFNULL(SUM(rental_amount),0) s FROM card_rentals").fetchone()["s"]
    total_salaries = con.execute("SELECT IFNULL(SUM(salary_amount),0) s FROM salary_payments").fetchone()["s"]
    total_expenses = con.execute("SELECT IFNULL(SUM(amount),0) s FROM expenses").fetchone()["s"]
    con.close()
    return jsonify({
        "labels": ["Rentals", "Salaries", "Expenses"],
        "data": [total_rentals, total_salaries, total_expenses]
    })

# ---------- Workers ----------
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
    expenses_field = float(data.get("expenses") or 0)
    con = get_db()
    con.execute(
        "INSERT INTO workers (name, company, commission, expenses) VALUES (?, ?, ?, ?)",
        (name, company, commission, expenses_field)
    )
    con.commit()
    con.close()
    if request.is_json:
        return jsonify({"ok": True})
    return redirect(url_for("workers_list"))

# ---------- Bank Accounts ----------
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
    worker_id = int(data.get("worker_id", 0))
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

# ---------- Card Rentals ----------
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
    worker_id = int(data.get("worker_id", 0))
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

# ---------- Salaries ----------
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
    worker_id = int(data.get("worker_id", 0))
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

# ---------- Expenses ----------
@app.route("/expenses")
def expenses_list():
    con = get_db()
    rows = con.execute("""
        SELECT e.*, w.name AS worker_name
        FROM expenses e
        LEFT JOIN workers w ON w.id = e.worker_id
        ORDER BY e.date DESC, e.id DESC
    """).fetchall()
    workers = con.execute("SELECT id, name FROM workers ORDER BY name").fetchall()
    con.close()
    # 你的 expenses.html 表头可包含：ID | 工人 | 金额 | 日期 | 类别 | 备注 | 创建时间
    return render_template("expenses.html", rows=rows, workers=workers)

@app.route("/expenses/add", methods=["POST"])
def expenses_add():
    data = request.form or request.json
    worker_id_raw = data.get("worker_id")
    worker_id = int(worker_id_raw) if worker_id_raw not in (None, "", "null") else None
    amount = float(data.get("amount") or 0)
    date = (data.get("date") or "").strip()
    category = (data.get("category") or "").strip()
    note = data.get("note") or ""
    if not (amount and date):
        return "amount and date required", 400
    try:
        datetime.fromisoformat(date)
    except ValueError:
        return "date must be ISO format YYYY-MM-DD", 400
    con = get_db()
    con.execute(
        "INSERT INTO expenses (worker_id, amount, date, category, note) VALUES (?, ?, ?, ?, ?)",
        (worker_id, amount, date, category, note)
    )
    con.commit()
    con.close()
    if request.is_json:
        return jsonify({"ok": True})
    return redirect(url_for("expenses_list"))

# ---------- CSV 导出 ----------
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

@app.route("/export/expenses.csv")
def export_expenses():
    return export_csv(
        """SELECT e.id, w.name AS worker_name, e.amount, e.date, e.category, e.note, e.created_at
           FROM expenses e LEFT JOIN workers w ON w.id=e.worker_id
           ORDER BY e.date DESC, e.id""",
        ["id","worker_name","amount","date","category","note","created_at"],
        "expenses.csv"
    )

# ---------- 简单 REST API（示例） ----------
@app.route("/api/workers", methods=["GET"])
def api_workers():
    con = get_db()
    rows = con.execute("SELECT * FROM workers ORDER BY id DESC").fetchall()
    con.close()
    return jsonify([dict(r) for r in rows])

# ---------- 错误处理 ----------
@app.errorhandler(500)
def internal_error(e):
    # 开发可打开详细错误（app.run(debug=True)），这里给个简单提示
    return "Server Error (500) - check console/logs for details.", 500

# ---------- Run ----------
if __name__ == "__main__":
    # 部署时可改为：host="0.0.0.0", port=int(os.environ.get("PORT", 5000))
    app.run(debug=True)
