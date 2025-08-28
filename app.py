from flask import Flask, request, jsonify, render_template, redirect, url_for, send_file
import sqlite3, csv, io, os
from datetime import datetime

APP_DB = "data.db"
app = Flask(__name__)

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
        date TEXT NOT NULL, -- ISO日期
        note TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(worker_id) REFERENCES workers(id)
    );

    CREATE TABLE IF NOT EXISTS salary_payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        worker_id INTEGER NOT NULL,
        salary_amount REAL NOT NULL,
        pay_date TEXT NOT NULL, -- 发薪日期
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
    date = (data.get("date") or "").strip()
    note = data.get("note") or ""
    if not (worker_id and rental_amount and date):
        return "worker_id, rental_amount, date required", 400
    # 简单校验日期
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

# ---------- 简单 REST API 示例（可选） ----------
@app.route("/api/workers", methods=["GET"])
def api_workers():
    con = get_db()
    rows = con.execute("SELECT * FROM workers ORDER BY id DESC").fetchall()
    con.close()
    return jsonify([dict(r) for r in rows])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
