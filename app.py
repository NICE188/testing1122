# app.py
from flask import Flask, request, jsonify, render_template, redirect, url_for, send_file, session
import sqlite3, csv, io, os
from datetime import datetime
from collections import defaultdict

# -----------------------------
# 基础设置 & DB 位置（可写路径）
# -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
APP_DB = os.path.join(DATA_DIR, "data.db")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-me-please")

# -----------------------------
# 简易多语言（中文 / 英文）
# -----------------------------
I18N = {
    "zh": {
        "brand": "Nepwin88",
        "dashboard": "概览",
        "workers": "工人 / 平台",
        "bank_accounts": "银行账户",
        "card_rentals": "银行卡租金",
        "salaries": "出粮记录",
        "expenses": "开销",
        "export_workers": "导出工人",
        "export_bank": "导出银行账户",
        "export_rentals": "导出银行卡租金",
        "export_salaries": "导出出粮记录",
        "export_expenses": "导出开销",
        "total_workers": "总工人数",
        "total_rentals": "租金合计",
        "total_salaries": "工资合计",
        "total_expenses": "开销合计",
        "welcome": "欢迎！使用左侧侧边栏进行导航，右上角可导出 CSV。",
    },
    "en": {
        "brand": "Nepwin88",
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
        "welcome": "Welcome! Use the left sidebar to navigate, and export CSV on the top-right.",
    }
}

def t():
    """根据 session 中的语言返回翻译字典"""
    lang = session.get("lang", "zh")
    return I18N.get(lang, I18N["zh"])

@app.route("/set-lang/<lang>")
def set_lang(lang):
    if lang not in I18N:
        lang = "zh"
    session["lang"] = lang
    return redirect(request.referrer or url_for("home"))

# -----------------------------
# DB helpers
# -----------------------------
def get_db():
    con = sqlite3.connect(APP_DB, check_same_thread=False)
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
        date TEXT NOT NULL, -- YYYY-MM-DD
        note TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(worker_id) REFERENCES workers(id)
    );

    CREATE TABLE IF NOT EXISTS salary_payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        worker_id INTEGER NOT NULL,
        salary_amount REAL NOT NULL,
        pay_date TEXT NOT NULL, -- YYYY-MM-DD
        note TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(worker_id) REFERENCES workers(id)
    );

    -- 新增 Expenses 表
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        worker_id INTEGER,           -- 可选：与工人关联
        amount REAL NOT NULL,
        date TEXT NOT NULL,          -- YYYY-MM-DD
        category TEXT,               -- 类别(可选)
        note TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(worker_id) REFERENCES workers(id)
    );
    """)
    con.commit()
    con.close()

if not os.path.exists(APP_DB):
    init_db()

# -----------------------------
# 健康检查
# -----------------------------
@app.route("/healthz")
def healthz():
    return "ok", 200

# -----------------------------
# 页面：Dashboard
# -----------------------------
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
        t=t(),
        total_workers=total_workers,
        total_rentals=total_rentals,
        total_salaries=total_salaries,
        total_expenses=total_expenses
    )

# -----------------------------
# Workers CRUD
# -----------------------------
@app.route("/workers")
def workers_list():
    con = get_db()
    rows = con.execute("SELECT * FROM workers ORDER BY id DESC").fetchall()
    con.close()
    return render_template("workers.html", t=t(), rows=rows)

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

# -----------------------------
# Bank Accounts
# -----------------------------
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
    return render_template("bank_accounts.html", t=t(), rows=rows, workers=workers)

@app.route("/bank-accounts/add", methods=["POST"])
def bank_accounts_add():
    data = request.form or request.json
    worker_id = int(data.get("worker_id"))
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

# -----------------------------
# Card Rentals
# -----------------------------
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
    return render_template("card_rentals.html", t=t(), rows=rows, workers=workers)

@app.route("/card-rentals/add", methods=["POST"])
def card_rentals_add():
    data = request.form or request.json
    worker_id = int(data.get("worker_id"))
    rental_amount = float(data.get("rental_amount"))
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

# -----------------------------
# Salaries
# -----------------------------
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
    return render_template("salaries.html", t=t(), rows=rows, workers=workers)

@app.route("/salaries/add", methods=["POST"])
def salaries_add():
    data = request.form or request.json
    worker_id = int(data.get("worker_id"))
    salary_amount = float(data.get("salary_amount"))
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

# -----------------------------
# Expenses（新模块）
# -----------------------------
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
    return render_template("expenses.html", t=t(), rows=rows, workers=workers)

@app.route("/expenses/add", methods=["POST"])
def expenses_add():
    data = request.form or request.json
    worker_id_raw = data.get("worker_id")
    worker_id = int(worker_id_raw) if worker_id_raw not in (None, "", "null") else None
    amount = float(data.get("amount"))
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

# -----------------------------
# Chart 数据（Dashboard 柱状图汇总）
# 返回：每月 sums
# -----------------------------
@app.route("/api/chart-summary")
def chart_summary():
    """
    返回类似：
    {
      "labels": ["2025-01","2025-02",...],
      "card_rentals": [1200, 760, ...],
      "salaries": [5000, 4800, ...],
      "expenses": [300, 900, ...]
    }
    """
    con = get_db()
    # 读取三张表，按 YYYY-MM 汇总
    def rows_to_month_sum(rows, col_amount, col_date):
        m = defaultdict(float)
        for r in rows:
            try:
                d = datetime.fromisoformat(r[col_date]).strftime("%Y-%m")
            except Exception:
                continue
            m[d] += float(r[col_amount] or 0)
        return m

    rentals = con.execute("SELECT rental_amount, date FROM card_rentals").fetchall()
    salaries = con.execute("SELECT salary_amount, pay_date FROM salary_payments").fetchall()
    expenses = con.execute("SELECT amount, date FROM expenses").fetchall()
    con.close()

    m_rentals = rows_to_month_sum(rentals, "rental_amount", "date")
    m_salaries = rows_to_month_sum(salaries, "salary_amount", "pay_date")
    m_expenses = rows_to_month_sum(expenses, "amount", "date")

    # 统一所有月份
    months = sorted(set(m_rentals.keys()) | set(m_salaries.keys()) | set(m_expenses.keys()))
    data = {
        "labels": months,
        "card_rentals": [round(m_rentals.get(m, 0), 2) for m in months],
        "salaries": [round(m_salaries.get(m, 0), 2) for m in months],
        "expenses": [round(m_expenses.get(m, 0), 2) for m in months],
    }
    return jsonify(data)

# -----------------------------
# CSV 导出
# -----------------------------
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

@app.route("/export/expenses.csv")
def export_expenses():
    return export_csv(
        """SELECT e.id, w.name as worker_name, e.amount, e.date, e.category, e.note, e.created_at
           FROM expenses e LEFT JOIN workers w ON w.id=e.worker_id
           ORDER BY e.date DESC, e.id""",
        ["id","worker_name","amount","date","category","note","created_at"],
        "expenses.csv"
    )

# -----------------------------
# 启动
# -----------------------------
if __name__ == "__main__":
    # 本地调试；Railway 会注入 $PORT
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
