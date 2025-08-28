from flask import Flask, request, jsonify, render_template, redirect, url_for, send_file, g, make_response
import sqlite3, csv, io, os
from datetime import datetime, date
from collections import defaultdict

APP_DB = "data.db"
app = Flask(__name__)

# ---------------- i18n（极简双语） ----------------
STRINGS = {
    "en": {
        "AppTitle": "Nepwin88",
        "Dashboard": "Dashboard",
        "WorkersPlatforms": "Workers / Platforms",
        "BankAccounts": "Bank Accounts",
        "CardRentals": "Card Rentals",
        "SalaryRecords": "Salary Records",
        "Language": "Language",
        "Overview": "Overview",
        "ExportWorkers": "Export Workers",
        "ExportBank": "Export Bank Accounts",
        "ExportRentals": "Export Card Rentals",
        "ExportSalaries": "Export Salaries",
        "TotalWorkers": "Total Workers",
        "TotalCardRentals": "Total Card Rentals",
        "TotalSalaries": "Total Salaries",
        "DashboardTip": "Welcome! Use the left sidebar to navigate, and export CSV in the top-right.",
        "MonthlyTitle": "Monthly Rentals vs Salaries",
        "Last6": "Last 6 months",
        "Last12": "Last 12 months",
        "Add": "Add",
        "Actions": "Actions",
        "Name": "Name",
        "Company": "Company",
        "Commission": "Commission",
        "Expenses": "Expenses",
        "CreatedAt": "Created At",
        "Worker": "Worker",
        "AccountNumber": "Account Number",
        "BankName": "Bank Name",
        "RentalAmount": "Rental Amount",
        "Date": "Date",
        "Note": "Note",
        "SalaryAmount": "Salary Amount",
        "PayDate": "Pay Date",
        "Submit": "Submit",
        "NoData": "No data",
        "TipsISODate": "Use ISO date (YYYY-MM-DD)."
    },
    "zh": {
        "AppTitle": "Nepwin88",
        "Dashboard": "概览",
        "WorkersPlatforms": "工人 / 平台",
        "BankAccounts": "银行账户",
        "CardRentals": "银行卡租金",
        "SalaryRecords": "出粮记录",
        "Language": "语言",
        "Overview": "概览",
        "ExportWorkers": "导出工人",
        "ExportBank": "导出银行账户",
        "ExportRentals": "导出银行卡租金",
        "ExportSalaries": "导出出粮记录",
        "TotalWorkers": "工人总数",
        "TotalCardRentals": "租金合计",
        "TotalSalaries": "出粮合计",
        "DashboardTip": "欢迎！使用左侧侧边栏导航，右上角可导出 CSV。",
        "MonthlyTitle": "月度租金 vs 出粮",
        "Last6": "最近6个月",
        "Last12": "最近12个月",
        "Add": "新增",
        "Actions": "操作",
        "Name": "名字",
        "Company": "公司",
        "Commission": "佣金",
        "Expenses": "开销",
        "CreatedAt": "创建时间",
        "Worker": "工人",
        "AccountNumber": "户口号码",
        "BankName": "银行名称",
        "RentalAmount": "租金金额",
        "Date": "日期",
        "Note": "备注",
        "SalaryAmount": "出粮金额",
        "PayDate": "出粮日期",
        "Submit": "提交",
        "NoData": "暂无数据",
        "TipsISODate": "请输入 ISO 日期（YYYY-MM-DD）。"
    }
}
DEFAULT_LANG = "zh"

@app.before_request
def set_lang():
    lang = request.args.get("lang") or request.cookies.get("lang") or DEFAULT_LANG
    if lang not in STRINGS:
        lang = DEFAULT_LANG
    g.lang = lang

@app.after_request
def persist_lang(resp):
    # 如果本次请求显式传了 lang，用 cookie 记住
    lang = request.args.get("lang")
    if lang and lang in STRINGS:
        resp.set_cookie("lang", lang, max_age=60*60*24*365)
    return resp

@app.context_processor
def inject_i18n():
    def _(key):
        return STRINGS.get(getattr(g, "lang", DEFAULT_LANG), {}).get(key, key)
    def url_with_lang(endpoint, **kwargs):
        # 所有导航链接都带上当前语言
        kwargs["lang"] = getattr(g, "lang", DEFAULT_LANG)
        return url_for(endpoint, **kwargs)
    return {"_": _, "urlL": url_with_lang, "curLang": lambda: getattr(g, "lang", DEFAULT_LANG)}

# ---------------- DB helpers ----------------
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

# ---------------- Web UI ----------------
@app.route("/")
def home():
    con = get_db()
    total_workers = con.execute("SELECT COUNT(*) c FROM workers").fetchone()["c"]
    total_rentals = con.execute("SELECT IFNULL(SUM(rental_amount),0) s FROM card_rentals").fetchone()["s"]
    total_salaries = con.execute("SELECT IFNULL(SUM(salary_amount),0) s FROM salary_payments").fetchone()["s"]
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
    return redirect(url_for("workers_list", lang=g.lang))

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
    return redirect(url_for("bank_accounts_list", lang=g.lang))

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
    worker_id = int(data.get("worker_id"))
    rental_amount = float(data.get("rental_amount"))
    date_str = (data.get("date") or "").strip()
    note = data.get("note") or ""
    if not (worker_id and rental_amount and date_str):
        return "worker_id, rental_amount, date required", 400
    try:
        datetime.fromisoformat(date_str)
    except ValueError:
        return "date must be ISO format YYYY-MM-DD", 400
    con = get_db()
    con.execute(
        "INSERT INTO card_rentals (worker_id, rental_amount, date, note) VALUES (?, ?, ?, ?)",
        (worker_id, rental_amount, date_str, note)
    )
    con.commit()
    con.close()
    if request.is_json:
        return jsonify({"ok": True})
    return redirect(url_for("card_rentals_list", lang=g.lang))

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
    return redirect(url_for("salaries_list", lang=g.lang))

# ---------- 导出为 CSV ----------
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

# ---------- Dashboard 柱状图数据 ----------
@app.route("/api/overview/monthly")
def api_overview_monthly():
    n = int(request.args.get("months", 6))
    today = date.today()
    labels = []
    y, m = today.year, today.month
    for _ in range(n):
        labels.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    labels.reverse()

    con = get_db()
    rentals = defaultdict(float)
    for row in con.execute("""
        SELECT substr(date,1,7) ym, IFNULL(SUM(rental_amount),0) total
        FROM card_rentals GROUP BY ym
    """):
        rentals[row["ym"]] = float(row["total"] or 0)

    salaries = defaultdict(float)
    for row in con.execute("""
        SELECT substr(pay_date,1,7) ym, IFNULL(SUM(salary_amount),0) total
        FROM salary_payments GROUP BY ym
    """):
        salaries[row["ym"]] = float(row["total"] or 0)
    con.close()

    data_rentals = [round(rentals.get(ym, 0), 2) for ym in labels]
    data_salaries = [round(salaries.get(ym, 0), 2) for ym in labels]
    return jsonify({"labels": labels, "rentals": data_rentals, "salaries": data_salaries})

# ---------- API 示例 ----------
@app.route("/api/workers", methods=["GET"])
def api_workers():
    con = get_db()
    rows = con.execute("SELECT * FROM workers ORDER BY id DESC").fetchall()
    con.close()
    return jsonify([dict(r) for r in rows])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
