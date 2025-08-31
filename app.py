from flask import (
    Flask, request, render_template, render_template_string,
    redirect, url_for, send_file, session, abort, flash, Response
)
import sqlite3, csv, io, os, logging
from datetime import datetime
from jinja2 import TemplateNotFound, DictLoader
from werkzeug.security import generate_password_hash, check_password_hash

# =========================
# 可配置环境变量（Railway上设置）
# =========================
APP_DB = os.environ.get("APP_DB", "data.db")
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
SECRET_KEY    = os.environ.get("SECRET_KEY", "dev-secret")

app = Flask(__name__)
app.secret_key = SECRET_KEY

# =========================
# 侧边栏样式（通过 /static/style.css 输出）
# =========================
STYLE_CSS = """:root{
  --bg:#0b0f17; --card:#121826; --line:#2a3346; --text:#e6edf6; --muted:#9fb0c3; --accent:#d4af37;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif}

/* 顶部栏 */
.topbar{display:flex;align-items:center;justify-content:space-between;padding:12px 16px;border-bottom:1px solid var(--line);position:sticky;top:0;background:rgba(11,15,23,.9);backdrop-filter:saturate(140%) blur(8px);z-index:20}
.brand{font-weight:700;letter-spacing:.5px;display:flex;align-items:center;gap:10px}
.nav a{margin-left:12px;padding:6px 10px;border:1px solid transparent;border-radius:10px}
.nav a:hover{border-color:var(--line)}
.user{opacity:.8;margin-right:8px}

/* 布局：侧栏 + 主内容 */
.layout{display:grid;grid-template-columns:240px 1fr;min-height:calc(100vh - 56px)}
.sidebar{border-right:1px solid var(--line);background:#0f1522;position:sticky;top:56px;height:calc(100vh - 56px);padding:12px}
.main{padding:16px}

/* 侧栏菜单 */
.side-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px}
.side-title{font-size:12px;color:var(--muted);letter-spacing:.4px}
.side-toggle{display:none}
.side-menu{display:grid;gap:6px}
.side-menu a{display:flex;align-items:center;gap:10px;padding:10px 12px;border:1px solid transparent;border-radius:12px;text-decoration:none;color:var(--text)}
.side-menu a:hover{background:#0c121f;border-color:var(--line)}
.side-menu a.active{background:#141b2b;border-color:#39425a}

/* 原有组件 */
.page-title{margin:10px 0 16px;font-size:20px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:12px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px}
.card-title{font-size:12px;color:var(--muted)}
.card-value{font-size:24px;margin-top:6px}
.panel{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;margin-bottom:16px}
.form{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:12px}
.form input,.form select,.form button{height:36px;padding:6px 10px;border-radius:10px;border:1px solid var(--line);background:#0f1522;color:var(--text)}
.form button{background:#141b2b;border-color:#39425a;cursor:pointer}
.form .danger{border-color:#6b2a2a;background:#241216}
.table-wrap{overflow:auto;border:1px solid var(--line);border-radius:14px}
table{border-collapse:collapse;width:100%}
th,td{padding:10px;border-bottom:1px solid var(--line);text-align:left}
.actions{display:flex;gap:6px}
.flash-wrap{display:grid;gap:8px;margin-bottom:12px}
.flash{padding:10px;border-radius:12px;background:#141b2b;border:1px solid var(--line)}
.flash.success{border-color:#2f6b2a;background:#162414}
.flash.error{border-color:#6b2a2a;background:#241216}
.footer{opacity:.6;text-align:center;padding:20px}

/* 移动端 */
@media (max-width: 960px){
  .layout{grid-template-columns:1fr}
  .sidebar{position:relative;top:auto;height:auto;border-right:none;border-bottom:1px solid var(--line)}
  .side-toggle{display:inline-flex;align-items:center;gap:6px;border:1px solid var(--line);border-radius:10px;padding:6px 10px;background:#0f1522;cursor:pointer}
  .side-menu{margin-top:10px}
}
"""

@app.get("/static/style.css")
def static_style():
    return Response(STYLE_CSS, mimetype="text/css")

# =========================
# 内嵌模板（含侧边栏）
# =========================
TEMPLATES = {
"base.html": """<!doctype html>
<html lang="zh">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{% block title %}后台 · {{ t.app_name }}{% endblock %}</title>
  <link rel="stylesheet" href="{{ url_for('static_style') }}">
</head>
<body>
  <!-- 顶部栏 -->
  <header class="topbar">
    <div class="brand">
      ⚜️ Admin Panel
      <button class="side-toggle" onclick="document.body.classList.toggle('side-open')">菜单</button>
    </div>
    <nav class="nav">
      {% if session.get('user_id') %}
        <span class="user">👤 {{ session.get('user_id') }}</span>
        <a href="{{ url_for('logout') }}">退出</a>
      {% else %}
        <a href="{{ url_for('login') }}">登录</a>
      {% endif %}
    </nav>
  </header>

  <!-- 主布局：侧栏 + 主内容 -->
  <div class="layout">
    <aside class="sidebar">
      <div class="side-head">
        <div class="side-title">导航</div>
      </div>
      <nav class="side-menu">
        <a href="{{ url_for('dashboard') }}" class="{{ 'active' if request.path == '/' else '' }}">🏠 Dashboard</a>
        <a href="{{ url_for('workers_list') }}" class="{{ 'active' if request.path.startswith('/workers') else '' }}">👨‍💼 工人 / 平台</a>
        <a href="{{ url_for('bank_accounts_list') }}" class="{{ 'active' if request.path.startswith('/bank-accounts') else '' }}">🏦 银行账户</a>
        <a href="{{ url_for('card_rentals_list') }}" class="{{ 'active' if request.path.startswith('/card-rentals') else '' }}">💳 银行卡租金</a>
        <a href="{{ url_for('salaries_list') }}" class="{{ 'active' if request.path.startswith('/salaries') else '' }}">💵 出粮记录</a>
        <a href="{{ url_for('expenses_list') }}" class="{{ 'active' if request.path.startswith('/expenses') else '' }}">💸 开销记录</a>
        <a href="{{ url_for('account_security') }}" class="{{ 'active' if request.path.startswith('/account') or request.path.startswith('/account-security') else '' }}">🔐 安全设置</a>
      </nav>
    </aside>

    <main class="main">
      {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
          <div class="flash-wrap">
          {% for category, message in messages %}
            <div class="flash {{ category }}">{{ message }}</div>
          {% endfor %}
          </div>
        {% endif %}
      {% endwith %}
      {% block content %}{% endblock %}
      <footer class="footer">© {{ 2025 }} Admin</footer>
    </main>
  </div>
</body>
</html>
""",

"login.html": """{% extends "base.html" %}
{% block title %}登录 · {{ t.app_name }}{% endblock %}
{% block content %}
<div class="panel">
  <h2>登录</h2>
  <p>{{ t.login_tip }}</p>
  <form class="form" method="post" action="{{ url_for('login_post') }}">
    <input name="username" placeholder="{{ t.username }}" required>
    <input name="password" type="password" placeholder="{{ t.password }}" required>
    <button class="btn" type="submit">{{ t.login }}</button>
  </form>
</div>
{% endblock %}
""",

"dashboard.html": """{% extends "base.html" %}
{% block title %}Dashboard · {{ t.app_name }}{% endblock %}
{% block content %}
<h1 class="page-title">🏠 Dashboard</h1>
<div class="cards">
  <div class="card"><div class="card-title">{{ t.total_workers }}</div><div class="card-value">{{ total_workers }}</div></div>
  <div class="card"><div class="card-title">{{ t.total_rentals }}</div><div class="card-value">{{ '%.2f'|format(total_rentals) }}</div></div>
  <div class="card"><div class="card-title">{{ t.total_salaries }}</div><div class="card-value">{{ '%.2f'|format(total_salaries) }}</div></div>
  <div class="card"><div class="card-title">{{ t.total_expenses }}</div><div class="card-value">{{ '%.2f'|format(total_expenses) }}</div></div>
</div>
{# 侧边栏已提供导航，这里不再显示快捷按钮 #}
{% endblock %}
""",

"account_security.html": """{% extends "base.html" %}
{% block title %}账号安全 · {{ t.app_name if t else "App" }}{% endblock %}
{% block content %}
<div class="panel">
  <h2>🔐 账号安全</h2>
  <p>这里可以管理登录账号、修改密码、修改用户名以及管理员重置密码。</p>
  <div class="actions">
    <a class="btn" href="{{ url_for('account_credentials') }}">🧑‍💻 修改登录账号/密码</a>
    <a class="btn" href="{{ url_for('account_change_password') }}">🔑 修改密码</a>
    <a class="btn" href="{{ url_for('account_change_username') }}">🆔 修改用户名</a>
    <a class="btn" href="{{ url_for('account_reset') }}">🛠 管理员重置密码</a>
  </div>
</div>
<style>.actions{display:flex;flex-wrap:wrap;gap:12px;margin-top:12px}
.btn{display:inline-block;padding:10px 14px;border:1px solid var(--line);border-radius:10px;text-decoration:none}</style>
{% endblock %}
""",

"account_credentials.html": """{% extends "base.html" %}
{% block title %}安全中心（登录账号/密码） · {{ t.app_name }}{% endblock %}
{% block content %}
<h1 class="page-title">🧑‍💻 修改登录账号/密码</h1>
<form class="form" method="post" action="{{ url_for('account_credentials_post') }}">
  <input name="username" placeholder="{{ t.username }}" required>
  <input name="password" type="password" placeholder="{{ t.password }}" required>
  <button class="btn" type="submit">{{ t.save }}</button>
  <a class="btn" href="{{ url_for('dashboard') }}">{{ t.back }}</a>
</form>
{% endblock %}
""",

"account_change_password.html": """{% extends "base.html" %}
{% block title %}修改密码 · {{ t.app_name }}{% endblock %}
{% block content %}
<h1 class="page-title">🔑 修改密码</h1>
<form class="form" method="post" action="{{ url_for('account_change_password_post') }}">
  <input name="old_password" type="password" placeholder="旧密码" required>
  <input name="new_password" type="password" placeholder="新密码" required>
  <button class="btn" type="submit">{{ t.save }}</button>
  <a class="btn" href="{{ url_for('dashboard') }}">{{ t.back }}</a>
</form>
{% endblock %}
""",

"account_change_username.html": """{% extends "base.html" %}
{% block title %}修改用户名 · {{ t.app_name }}{% endblock %}
{% block content %}
<h1 class="page-title">🆔 修改用户名</h1>
<form class="form" method="post" action="{{ url_for('account_change_username_post') }}">
  <input name="new_username" placeholder="新用户名" required>
  <button class="btn" type="submit">{{ t.save }}</button>
  <a class="btn" href="{{ url_for('dashboard') }}">{{ t.back }}</a>
</form>
{% endblock %}
""",

"account_reset.html": """{% extends "base.html" %}
{% block title %}重置密码（管理员） · {{ t.app_name }}{% endblock %}
{% block content %}
<h1 class="page-title">🛠 管理员重置密码</h1>
<form class="form" method="post" action="{{ url_for('account_reset_post') }}">
  <input name="target_username" placeholder="目标用户名" required>
  <input name="new_password" type="password" placeholder="新密码" required>
  <button class="btn" type="submit">{{ t.save }}</button>
  <a class="btn" href="{{ url_for('dashboard') }}">{{ t.back }}</a>
</form>
{% endblock %}
""",

"workers_list.html": """{% extends "base.html" %}
{% block title %}{{ t.workers }} · {{ t.app_name }}{% endblock %}
{% block content %}
<h1 class="page-title">👨‍💼 {{ t.workers }}</h1>
<div class="panel">
  <form class="form" action="{{ url_for('workers_add') }}" method="post">
    <input name="name" placeholder="{{ t.name }}" required>
    <input name="company" placeholder="{{ t.company }}">
    <input name="commission" type="number" step="0.01" placeholder="{{ t.commission }}">
    <input name="expenses" type="number" step="0.01" placeholder="{{ t.expenses }}">
    <button class="btn" type="submit">{{ t.add }}</button>
    <a class="btn" href="{{ url_for('export_workers') }}">⤓ {{ t.export_workers }}</a>
  </form>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>ID</th><th>{{ t.name }}</th><th>{{ t.company }}</th><th>{{ t.commission }}</th><th>{{ t.expenses }}</th><th>{{ t.created_at }}</th><th>{{ t.actions }}</th>
        </tr>
      </thead>
      <tbody>
        {% for r in rows %}
        <tr>
          <td>{{ r.id }}</td><td>{{ r.name }}</td><td>{{ r.company }}</td><td>{{ r.commission }}</td><td>{{ r.expenses }}</td><td>{{ r.created_at }}</td>
          <td class="actions">
            <a class="btn" href="{{ url_for('workers_edit_form', wid=r.id) }}">{{ t.edit }}</a>
            <form method="post" action="{{ url_for('workers_delete', wid=r.id) }}" onsubmit="return confirm('{{ t.confirm_delete }}')">
              <button class="btn danger" type="submit">{{ t.delete }}</button>
            </form>
          </td>
        </tr>
        {% else %}
        <tr><td colspan="7">{{ t.empty }}</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}
""",

"workers_edit.html": """{% extends "base.html" %}
{% block title %}{{ t.edit }} — {{ t.workers }}{% endblock %}
{% block content %}
<h1 class="page-title">{{ t.edit }} — {{ t.workers }}</h1>
<form class="form" method="post" action="{{ url_for('workers_edit', wid=r.id) }}">
  <input name="name" value="{{ r.name }}" placeholder="{{ t.name }}" required>
  <input name="company" value="{{ r.company }}" placeholder="{{ t.company }}">
  <input name="commission" type="number" step="0.01" value="{{ r.commission }}" placeholder="{{ t.commission }}">
  <input name="expenses" type="number" step="0.01" value="{{ r.expenses }}" placeholder="{{ t.expenses }}">
  <button class="btn" type="submit">{{ t.save }}</button>
  <a class="btn" href="{{ url_for('workers_list') }}">{{ t.back }}</a>
</form>
{% endblock %}
""",

"bank_accounts_list.html": """{% extends "base.html" %}
{% block title %}{{ t.bank_accounts }} · {{ t.app_name }}{% endblock %}
{% block content %}
<h1 class="page-title">🏦 {{ t.bank_accounts }}</h1>
<div class="panel">
  <form class="form" action="{{ url_for('bank_accounts_add') }}" method="post">
    <input name="bank_name" placeholder="银行名" required>
    <input name="account_no" placeholder="账号" required>
    <input name="holder" placeholder="户名" required>
    <select name="status"><option value="1">{{ t.active }}</option><option value="0">{{ t.inactive }}</option></select>
    <button class="btn" type="submit">{{ t.add }}</button>
    <a class="btn" href="{{ url_for('export_bank_accounts') }}">⤓ {{ t.export_bank }}</a>
  </form>
  <div class="table-wrap">
    <table>
      <thead><tr><th>ID</th><th>银行名</th><th>账号</th><th>户名</th><th>{{ t.status }}</th><th>{{ t.created_at }}</th><th>{{ t.actions }}</th></tr></thead>
      <tbody>
        {% for r in rows %}
        <tr>
          <td>{{ r.id }}</td><td>{{ r.bank_name }}</td><td>{{ r.account_no }}</td><td>{{ r.holder }}</td>
          <td>{{ t.active if r.status==1 else t.inactive }}</td><td>{{ r.created_at }}</td>
          <td class="actions">
            <a class="btn" href="{{ url_for('bank_accounts_edit_form', bid=r.id) }}">{{ t.edit }}</a>
            <form method="post" action="{{ url_for('bank_accounts_delete', bid=r.id) }}" onsubmit="return confirm('{{ t.confirm_delete }}')">
              <button class="btn danger" type="submit">{{ t.delete }}</button>
            </form>
          </td>
        </tr>
        {% else %}<tr><td colspan="7">{{ t.empty }}</td></tr>{% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}
""",

"bank_accounts_edit.html": """{% extends "base.html" %}
{% block title %}{{ t.edit }} — {{ t.bank_accounts }}{% endblock %}
{% block content %}
<h1 class="page-title">{{ t.edit }} — {{ t.bank_accounts }}</h1>
<form class="form" method="post" action="{{ url_for('bank_accounts_edit', bid=r.id) }}">
  <input name="bank_name" value="{{ r.bank_name }}" placeholder="银行名" required>
  <input name="account_no" value="{{ r.account_no }}" placeholder="账号" required>
  <input name="holder" value="{{ r.holder }}" placeholder="户名" required>
  <select name="status">
    <option value="1" {% if r.status==1 %}selected{% endif %}>{{ t.active }}</option>
    <option value="0" {% if r.status==0 %}selected{% endif %}>{{ t.inactive }}</option>
  </select>
  <button class="btn" type="submit">{{ t.save }}</button>
  <a class="btn" href="{{ url_for('bank_accounts_list') }}">{{ t.back }}</a>
</form>
{% endblock %}
""",

"card_rentals_list.html": """{% extends "base.html" %}
{% block title %}{{ t.card_rentals }} · {{ t.app_name }}{% endblock %}
{% block content %}
<h1 class="page-title">💳 {{ t.card_rentals }}</h1>
<div class="panel">
  <form class="form" action="{{ url_for('card_rentals_add') }}" method="post">
    <select name="bank_account_id" required>
      {% for b in banks %}<option value="{{ b.id }}">{{ b.bank_name }} - {{ b.account_no }}</option>{% endfor %}
    </select>
    <input name="monthly_rent" type="number" step="0.01" placeholder="月租金" required>
    <input name="start_date" type="date" placeholder="开始日期">
    <input name="end_date" type="date" placeholder="结束日期">
    <input name="note" placeholder="备注">
    <button class="btn" type="submit">{{ t.add }}</button>
    <a class="btn" href="{{ url_for('export_card_rentals') }}">⤓ {{ t.export_rentals }}</a>
  </form>
  <div class="table-wrap">
    <table>
      <thead><tr><th>ID</th><th>银行</th><th>账号</th><th>月租金</th><th>开始</th><th>结束</th><th>备注</th><th>{{ t.created_at }}</th><th>{{ t.actions }}</th></tr></thead>
      <tbody>
        {% for r in rows %}
        <tr>
          <td>{{ r.id }}</td><td>{{ r.bank_name }}</td><td>{{ r.account_no }}</td><td>{{ r.monthly_rent }}</td><td>{{ r.start_date }}</td><td>{{ r.end_date }}</td><td>{{ r.note }}</td><td>{{ r.created_at }}</td>
          <td class="actions">
            <a class="btn" href="{{ url_for('card_rentals_edit_form', rid=r.id) }}">{{ t.edit }}</a>
            <form method="post" action="{{ url_for('card_rentals_delete', rid=r.id) }}" onsubmit="return confirm('{{ t.confirm_delete }}')">
              <button class="btn danger" type="submit">{{ t.delete }}</button>
            </form>
          </td>
        </tr>
        {% else %}<tr><td colspan="9">{{ t.empty }}</td></tr>{% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}
""",

"card_rentals_edit.html": """{% extends "base.html" %}
{% block title %}{{ t.edit }} — {{ t.card_rentals }}{% endblock %}
{% block content %}
<h1 class="page-title">{{ t.edit }} — {{ t.card_rentals }}</h1>
<form class="form" method="post" action="{{ url_for('card_rentals_edit', rid=r.id) }}">
  <select name="bank_account_id">
    {% for b in banks %}
    <option value="{{ b.id }}" {% if r.bank_account_id==b.id %}selected{% endif %}>{{ b.bank_name }} - {{ b.account_no }}</option>
    {% endfor %}
  </select>
  <input name="monthly_rent" type="number" step="0.01" value="{{ r.monthly_rent }}" placeholder="月租金">
  <input name="start_date" type="date" value="{{ r.start_date }}">
  <input name="end_date" type="date" value="{{ r.end_date }}">
  <input name="note" value="{{ r.note }}" placeholder="备注">
  <button class="btn" type="submit">{{ t.save }}</button>
  <a class="btn" href="{{ url_for('card_rentals_list') }}">{{ t.back }}</a>
</form>
{% endblock %}
""",

"salaries_list.html": """{% extends "base.html" %}
{% block title %}{{ t.salaries }} · {{ t.app_name }}{% endblock %}
{% block content %}
<h1 class="page-title">💵 {{ t.salaries }}</h1>
<div class="panel">
  <form class="form" action="{{ url_for('salaries_add') }}" method="post">
    <select name="worker_id">{% for w in workers %}<option value="{{ w.id }}">{{ w.name }}</option>{% endfor %}</select>
    <input name="amount" type="number" step="0.01" placeholder="{{ t.salary_amount }}" required>
    <input name="pay_date" type="date" placeholder="{{ t.pay_date }}" required>
    <input name="note" placeholder="{{ t.note }}">
    <button class="btn" type="submit">{{ t.add }}</button>
    <a class="btn" href="{{ url_for('export_salaries') }}">⤓ {{ t.export_salaries }}</a>
  </form>
  <div class="table-wrap">
    <table>
      <thead><tr><th>ID</th><th>{{ t.worker }}</th><th>{{ t.salary_amount }}</th><th>{{ t.pay_date }}</th><th>{{ t.note }}</th><th>{{ t.created_at }}</th><th>{{ t.actions }}</th></tr></thead>
      <tbody>
        {% for r in rows %}
        <tr>
          <td>{{ r.id }}</td><td>{{ r.worker_name }}</td><td>{{ r.amount }}</td><td>{{ r.pay_date }}</td><td>{{ r.note }}</td><td>{{ r.created_at }}</td>
          <td class="actions">
            <a class="btn" href="{{ url_for('salaries_edit_form', sid=r.id) }}">{{ t.edit }}</a>
            <form method="post" action="{{ url_for('salaries_delete', sid=r.id) }}" onsubmit="return confirm('{{ t.confirm_delete }}')">
              <button class="btn danger" type="submit">{{ t.delete }}</button>
            </form>
          </td>
        </tr>
        {% else %}<tr><td colspan="7">{{ t.empty }}</td></tr>{% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}
""",

"salaries_edit.html": """{% extends "base.html" %}
{% block title %}{{ t.edit }} — {{ t.salaries }}{% endblock %}
{% block content %}
<h1 class="page-title">{{ t.edit }} — {{ t.salaries }}</h1>
<form class="form" method="post" action="{{ url_for('salaries_edit', sid=r.id) }}">
  <select name="worker_id">{% for w in workers %}<option value="{{ w.id }}" {% if r.worker_id==w.id %}selected{% endif %}>{{ w.name }}</option>{% endfor %}</select>
  <input name="amount" type="number" step="0.01" value="{{ r.amount }}" placeholder="{{ t.salary_amount }}">
  <input name="pay_date" type="date" value="{{ r.pay_date }}">
  <input name="note" value="{{ r.note }}" placeholder="{{ t.note }}">
  <button class="btn" type="submit">{{ t.save }}</button>
  <a class="btn" href="{{ url_for('salaries_list') }}">{{ t.back }}</a>
</form>
{% endblock %}
""",

"expenses_list.html": """{% extends "base.html" %}
{% block title %}{{ t.expenses }} · {{ t.app_name }}{% endblock %}
{% block content %}
<h1 class="page-title">💸 {{ t.expenses }}</h1>
<div class="panel">
  <form class="form" action="{{ url_for('expenses_add') }}" method="post">
    <select name="worker_id">
      <option value="">{{ '不关联工人' if lang=='zh' else 'No worker' }}</option>
      {% for w in workers %}<option value="{{ w.id }}">{{ w.name }}</option>{% endfor %}
    </select>
    <input name="amount" type="number" step="0.01" placeholder="{{ t.expense_amount }}" required>
    <input name="date" type="date" placeholder="{{ t.date }}" required>
    <input name="note" placeholder="{{ t.expenses_note }}">
    <button class="btn" type="submit">{{ t.add }}</button>
    <a class="btn" href="{{ url_for('export_expenses') }}">⤓ {{ t.export_expenses }}</a>
  </form>
  <div class="table-wrap">
    <table>
      <thead><tr><th>ID</th><th>{{ t.worker }}</th><th>{{ t.expense_amount }}</th><th>{{ t.date }}</th><th>{{ t.expenses_note }}</th><th>{{ t.created_at }}</th><th>{{ t.actions }}</th></tr></thead>
      <tbody>
        {% for r in rows %}
        <tr>
          <td>{{ r.id }}</td><td>{{ r.worker_name }}</td><td>{{ r.amount }}</td><td>{{ r.date }}</td><td>{{ r.note }}</td><td>{{ r.created_at }}</td>
          <td class="actions">
            <a class="btn" href="{{ url_for('expenses_edit_form', eid=r.id) }}">{{ t.edit }}</a>
            <form method="post" action="{{ url_for('expenses_delete', eid=r.id) }}" onsubmit="return confirm('{{ t.confirm_delete }}')">
              <button class="btn danger" type="submit">{{ t.delete }}</button>
            </form>
          </td>
        </tr>
        {% else %}<tr><td colspan="7">{{ t.empty }}</td></tr>{% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}
""",

"expenses_edit.html": """{% extends "base.html" %}
{% block title %}{{ t.edit }} — {{ t.expenses }}{% endblock %}
{% block content %}
<h1 class="page-title">{{ t.edit }} — {{ t.expenses }}</h1>
<form class="form" method="post" action="{{ url_for('expenses_edit', eid=r.id) }}">
  <select name="worker_id">
    <option value="">{{ '不关联工人' if lang=='zh' else 'No worker' }}</option>
    {% for w in workers %}<option value="{{ w.id }}" {% if r.worker_id==w.id %}selected{% endif %}>{{ w.name }}</option>{% endfor %}
  </select>
  <input name="amount" type="number" step="0.01" value="{{ r.amount }}" placeholder="{{ t.expense_amount }}">
  <input name="date" type="date" value="{{ r.date }}">
  <input name="note" value="{{ r.note }}" placeholder="{{ t.expenses_note }}">
  <button class="btn" type="submit">{{ t.save }}</button>
  <a class="btn" href="{{ url_for('expenses_list') }}">{{ t.back }}</a>
</form>
{% endblock %}
""",
}
app.jinja_loader = DictLoader(TEMPLATES)

# =========================
# 日志 & 错误
# =========================
logging.basicConfig(level=logging.INFO)

@app.errorhandler(TemplateNotFound)
def handle_tpl_not_found(e):
    return (f"Oops, template not found: <b>{e.name}</b>", 500)

@app.errorhandler(Exception)
def handle_any_error(e):
    app.logger.exception("Unhandled error")
    return (f"Error: <b>{e.__class__.__name__}</b><br>Message: {str(e)}", 500)

@app.get("/__diag__")
def __diag():
    return render_template_string("OK — lang={{lang}}, app={{t.app_name}}")

# =========================
# I18N
# =========================
I18N = {
    "zh": {
        "app_name": "NepWin Ops",
        "login_tip": "请输入管理员账号和密码。",
        "username": "用户名","password": "密码","login": "登录","logout": "退出",
        "workers": "工人 / 平台","bank_accounts": "银行账户","card_rentals": "银行卡租金",
        "salaries": "出粮记录","expenses": "开销记录","actions": "操作",
        "add": "新增","edit": "编辑","delete": "删除","save": "保存","back": "返回",
        "confirm_delete": "确定要删除吗？","empty": "暂无数据","created_at": "创建时间",
        "status": "状态","active": "启用","inactive": "停用","name": "姓名","company": "公司",
        "commission": "佣金","salary_amount": "工资金额","pay_date": "发放日期","note": "备注",
        "date": "日期","worker": "工人","expense_amount": "开销金额","expenses_note": "开销备注",
        "export_workers": "导出工人","export_bank": "导出银行账户","export_rentals": "导出租金",
        "export_salaries": "导出工资","export_expenses": "导出开销",
        "total_workers": "工人总数","total_rentals": "总租金","total_salaries": "总工资","total_expenses": "总开销",
    }
}
def get_lang(): return request.args.get("lang") or request.cookies.get("lang") or "zh"
def T(): return I18N.get(get_lang(), I18N["zh"])

# =========================
# DB helpers & 初始化
# =========================
def conn():
    c = sqlite3.connect(APP_DB); c.row_factory = sqlite3.Row; return c

def init_db():
    with conn() as c:
        cur = c.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password_hash TEXT, is_admin INTEGER DEFAULT 1
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS workers(
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, company TEXT, commission REAL DEFAULT 0.0, expenses REAL DEFAULT 0.0, created_at TEXT
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS bank_accounts(
            id INTEGER PRIMARY KEY AUTOINCREMENT, bank_name TEXT, account_no TEXT, holder TEXT, status INTEGER DEFAULT 1, created_at TEXT
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS card_rentals(
            id INTEGER PRIMARY KEY AUTOINCREMENT, bank_account_id INTEGER, monthly_rent REAL, start_date TEXT, end_date TEXT, note TEXT, created_at TEXT
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS salaries(
            id INTEGER PRIMARY KEY AUTOINCREMENT, worker_id INTEGER, amount REAL, pay_date TEXT, note TEXT, created_at TEXT
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS expenses(
            id INTEGER PRIMARY KEY AUTOINCREMENT, worker_id INTEGER, amount REAL, date TEXT, note TEXT, created_at TEXT
        )""")
        # 默认管理员
        cur.execute("SELECT COUNT(*) n FROM users"); 
        if cur.fetchone()["n"] == 0:
            cur.execute("INSERT INTO users(username, password_hash, is_admin) VALUES(?,?,1)",
                        (ADMIN_USERNAME, generate_password_hash(ADMIN_PASSWORD)))
        c.commit()

@app.before_request
def inject_globals():
    setattr(request, "lang", get_lang())

@app.context_processor
def inject_t():
    return {"t": T(), "lang": get_lang()}

# =========================
# Auth
# =========================
def require_login():
    if not session.get("user_id"):
        return redirect(url_for("login", next=request.path))

@app.get("/login")
def login(): return render_template("login.html")

@app.post("/login")
def login_post():
    username = request.form.get("username","").strip()
    password = request.form.get("password","").strip()
    with conn() as c:
        cur = c.cursor(); cur.execute("SELECT * FROM users WHERE username=?", (username,))
        u = cur.fetchone()
        if not u or not check_password_hash(u["password_hash"], password):
            flash("用户名或密码不正确", "error"); return redirect(url_for("login"))
        session["user_id"] = u["username"]
    return redirect(url_for("dashboard"))

@app.get("/logout")
def logout():
    session.clear(); return redirect(url_for("login"))

# =========================
# Dashboard
# =========================
@app.get("/")
def dashboard():
    if require_login(): return require_login()
    with conn() as c:
        cur = c.cursor()
        cur.execute("SELECT COUNT(*) n FROM workers"); total_workers = cur.fetchone()["n"]
        cur.execute("SELECT IFNULL(SUM(monthly_rent),0) s FROM card_rentals"); total_rentals = cur.fetchone()["s"]
        cur.execute("SELECT IFNULL(SUM(amount),0) s FROM salaries"); total_salaries = cur.fetchone()["s"]
        cur.execute("SELECT IFNULL(SUM(amount),0) s FROM expenses"); total_expenses = cur.fetchone()["s"]
    return render_template("dashboard.html", total_workers=total_workers,
                           total_rentals=total_rentals,total_salaries=total_salaries,total_expenses=total_expenses)

# =========================
# 安全中心
# =========================
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
        flash("用户名与密码不能为空", "error"); return redirect(url_for("account_credentials"))
    with conn() as c:
        cur = c.cursor(); cur.execute("SELECT * FROM users WHERE username=?", (session["user_id"],))
        u = cur.fetchone(); 
        if not u: abort(403)
        cur.execute("UPDATE users SET username=?, password_hash=? WHERE id=?",
                    (new_username, generate_password_hash(new_password), u["id"]))
        c.commit(); session["user_id"] = new_username
    flash("登录账号与密码已更新", "success"); return redirect(url_for("dashboard"))

@app.get("/account/change-password")
def account_change_password():
    if require_login(): return require_login()
    return render_template("account_change_password.html")

@app.post("/account/change-password")
def account_change_password_post():
    if require_login(): return require_login()
    old_pw = request.form.get("old_password",""); new_pw = request.form.get("new_password","")
    if not old_pw or not new_pw:
        flash("请输入旧密码与新密码", "error"); return redirect(url_for("account_change_password"))
    with conn() as c:
        cur = c.cursor(); cur.execute("SELECT * FROM users WHERE username=?", (session["user_id"],))
        u = cur.fetchone()
        if not u or not check_password_hash(u["password_hash"], old_pw):
            flash("旧密码不正确", "error"); return redirect(url_for("account_change_password"))
        cur.execute("UPDATE users SET password_hash=? WHERE id=?", (generate_password_hash(new_pw), u["id"]))
        c.commit()
    flash("密码已更新", "success"); return redirect(url_for("dashboard"))

@app.get("/account/change-username")
def account_change_username():
    if require_login(): return require_login()
    return render_template("account_change_username.html")

@app.post("/account/change-username")
def account_change_username_post():
    if require_login(): return require_login()
    new_username = request.form.get("new_username","").strip()
    if not new_username:
        flash("新用户名不能为空", "error"); return redirect(url_for("account_change_username"))
    with conn() as c:
        cur = c.cursor(); cur.execute("SELECT * FROM users WHERE username=?", (session["user_id"],))
        u = cur.fetchone(); 
        if not u: abort(403)
        cur.execute("UPDATE users SET username=? WHERE id=?", (new_username, u["id"]))
        c.commit(); session["user_id"] = new_username
    flash("用户名已更新", "success"); return redirect(url_for("dashboard"))

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
        flash("目标用户名与新密码不能为空", "error"); return redirect(url_for("account_reset"))
    with conn() as c:
        cur = c.cursor(); cur.execute("SELECT * FROM users WHERE username=?", (target_username,))
        u = cur.fetchone()
        if not u:
            flash("目标用户不存在", "error"); return redirect(url_for("account_reset"))
        cur.execute("UPDATE users SET password_hash=? WHERE id=?", (generate_password_hash(new_password), u["id"]))
        c.commit()
    flash("目标用户密码已重置", "success"); return redirect(url_for("dashboard"))

# =========================
# 工人 / 平台
# =========================
@app.get("/workers")
def workers_list():
    if require_login(): return require_login()
    with conn() as c:
        cur = c.cursor(); cur.execute("SELECT * FROM workers ORDER BY id DESC"); rows = cur.fetchall()
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
        cur.execute("""INSERT INTO workers(name,company,commission,expenses,created_at)
                       VALUES(?,?,?,?,?)""", (name, company, commission, expenses, datetime.utcnow().isoformat()))
        c.commit()
    return redirect(url_for("workers_list"))

@app.get("/workers/<int:wid>/edit")
def workers_edit_form(wid):
    if require_login(): return require_login()
    with conn() as c:
        cur = c.cursor(); cur.execute("SELECT * FROM workers WHERE id=?", (wid,)); r = cur.fetchone()
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
        cur.execute("""UPDATE workers SET name=?, company=?, commission=?, expenses=? WHERE id=?""",
                    (name, company, commission, expenses, wid))
        c.commit()
    return redirect(url_for("workers_list"))

@app.post("/workers/<int:wid>/delete")
def workers_delete(wid):
    if require_login(): return require_login()
    with conn() as c:
        c.execute("DELETE FROM workers WHERE id=?", (wid,)); c.commit()
    return redirect(url_for("workers_list"))

@app.get("/export/workers.csv")
def export_workers():
    if require_login(): return require_login()
    output = io.StringIO(); writer = csv.writer(output)
    writer.writerow(["id","name","company","commission","expenses","created_at"])
    with conn() as c:
        for r in c.execute("SELECT * FROM workers ORDER BY id DESC"):
            writer.writerow([r["id"],r["name"],r["company"],r["commission"],r["expenses"],r["created_at"]])
    mem = io.BytesIO(output.getvalue().encode("utf-8"))
    return send_file(mem, mimetype="text/csv", as_attachment=True, download_name="workers.csv")

# =========================
# 银行账户
# =========================
@app.get("/bank-accounts")
def bank_accounts_list():
    if require_login(): return require_login()
    with conn() as c:
        cur = c.cursor(); cur.execute("SELECT * FROM bank_accounts ORDER BY id DESC"); rows = cur.fetchall()
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
        cur.execute("""INSERT INTO bank_accounts(bank_name,account_no,holder,status,created_at)
                       VALUES(?,?,?,?,?)""", (bank_name, account_no, holder, status, datetime.utcnow().isoformat()))
        c.commit()
    return redirect(url_for("bank_accounts_list"))

@app.get("/bank-accounts/<int:bid>/edit")
def bank_accounts_edit_form(bid):
    if require_login(): return require_login()
    with conn() as c:
        cur = c.cursor(); cur.execute("SELECT * FROM bank_accounts WHERE id=?", (bid,)); r = cur.fetchone()
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
        cur.execute("""UPDATE bank_accounts SET bank_name=?, account_no=?, holder=?, status=? WHERE id=?""",
                    (bank_name, account_no, holder, status, bid))
        c.commit()
    return redirect(url_for("bank_accounts_list"))

@app.post("/bank-accounts/<int:bid>/delete")
def bank_accounts_delete(bid):
    if require_login(): return require_login()
    with conn() as c:
        c.execute("DELETE FROM bank_accounts WHERE id=?", (bid,)); c.commit()
    return redirect(url_for("bank_accounts_list"))

@app.get("/export/bank_accounts.csv")
def export_bank_accounts():
    if require_login(): return require_login()
    output = io.StringIO(); writer = csv.writer(output)
    writer.writerow(["id","bank_name","account_no","holder","status","created_at"])
    with conn() as c:
        for r in c.execute("SELECT * FROM bank_accounts ORDER BY id DESC"):
            writer.writerow([r["id"],r["bank_name"],r["account_no"],r["holder"],r["status"],r["created_at"]])
    mem = io.BytesIO(output.getvalue().encode("utf-8"))
    return send_file(mem, mimetype="text/csv", as_attachment=True, download_name="bank_accounts.csv")

# =========================
# 银行卡租金
# =========================
@app.get("/card-rentals")
def card_rentals_list():
    if require_login(): return require_login()
    with conn() as c:
        cur = c.cursor()
        cur.execute("""SELECT cr.*, ba.bank_name, ba.account_no
                       FROM card_rentals cr LEFT JOIN bank_accounts ba ON ba.id = cr.bank_account_id
                       ORDER BY cr.id DESC""")
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
        cur.execute("""INSERT INTO card_rentals(bank_account_id, monthly_rent, start_date, end_date, note, created_at)
                       VALUES(?,?,?,?,?,?)""", (bank_account_id, monthly_rent, start_date, end_date, note, datetime.utcnow().isoformat()))
        c.commit()
    return redirect(url_for("card_rentals_list"))

@app.get("/card-rentals/<int:rid>/edit")
def card_rentals_edit_form(rid):
    if require_login(): return require_login()
    with conn() as c:
        cur = c.cursor(); cur.execute("SELECT * FROM card_rentals WHERE id=?", (rid,)); r = cur.fetchone()
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
        cur.execute("""UPDATE card_rentals SET bank_account_id=?, monthly_rent=?, start_date=?, end_date=?, note=? WHERE id=?""",
                    (bank_account_id, monthly_rent, start_date, end_date, note, rid))
        c.commit()
    return redirect(url_for("card_rentals_list"))

@app.post("/card-rentals/<int:rid>/delete")
def card_rentals_delete(rid):
    if require_login(): return require_login()
    with conn() as c:
        c.execute("DELETE FROM card_rentals WHERE id=?", (rid,)); c.commit()
    return redirect(url_for("card_rentals_list"))

@app.get("/export/card_rentals.csv")
def export_card_rentals():
    if require_login(): return require_login()
    output = io.StringIO(); writer = csv.writer(output)
    writer.writerow(["id","bank_account_id","monthly_rent","start_date","end_date","note","created_at"])
    with conn() as c:
        for r in c.execute("SELECT * FROM card_rentals ORDER BY id DESC"):
            writer.writerow([r["id"],r["bank_account_id"],r["monthly_rent"],r["start_date"],r["end_date"],r["note"],r["created_at"]])
    mem = io.BytesIO(output.getvalue().encode("utf-8"))
    return send_file(mem, mimetype="text/csv", as_attachment=True, download_name="card_rentals.csv")

# =========================
# 出粮记录
# =========================
@app.get("/salaries")
def salaries_list():
    if require_login(): return require_login()
    with conn() as c:
        cur = c.cursor()
        cur.execute("""SELECT s.*, w.name AS worker_name
                       FROM salaries s LEFT JOIN workers w ON w.id = s.worker_id
                       ORDER BY s.id DESC""")
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
        cur.execute("""INSERT INTO salaries(worker_id, amount, pay_date, note, created_at)
                       VALUES(?,?,?,?,?)""", (worker_id, amount, pay_date, note, datetime.utcnow().isoformat()))
        c.commit()
    return redirect(url_for("salaries_list"))

@app.get("/salaries/<int:sid>/edit")
def salaries_edit_form(sid):
    if require_login(): return require_login()
    with conn() as c:
        cur = c.cursor(); cur.execute("SELECT * FROM salaries WHERE id=?", (sid,)); r = cur.fetchone()
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
        cur.execute("""UPDATE salaries SET worker_id=?, amount=?, pay_date=?, note=? WHERE id=?""",
                    (worker_id, amount, pay_date, note, sid))
        c.commit()
    return redirect(url_for("salaries_list"))

@app.post("/salaries/<int:sid>/delete")
def salaries_delete(sid):
    if require_login(): return require_login()
    with conn() as c:
        c.execute("DELETE FROM salaries WHERE id=?", (sid,)); c.commit()
    return redirect(url_for("salaries_list"))

@app.get("/export/salaries.csv")
def export_salaries():
    if require_login(): return require_login()
    output = io.StringIO(); writer = csv.writer(output)
    writer.writerow(["id","worker_id","amount","pay_date","note","created_at"])
    with conn() as c:
        for r in c.execute("SELECT * FROM salaries ORDER BY id DESC"):
            writer.writerow([r["id"],r["worker_id"],r["amount"],r["pay_date"],r["note"],r["created_at"]])
    mem = io.BytesIO(output.getvalue().encode("utf-8"))
    return send_file(mem, mimetype="text/csv", as_attachment=True, download_name="salaries.csv")

# =========================
# 开销
# =========================
@app.get("/expenses")
def expenses_list():
    if require_login(): return require_login()
    with conn() as c:
        cur = c.cursor()
        cur.execute("""SELECT e.*, w.name AS worker_name
                       FROM expenses e LEFT JOIN workers w ON w.id = e.worker_id
                       ORDER BY e.id DESC""")
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
        cur.execute("""INSERT INTO expenses(worker_id, amount, date, note, created_at)
                       VALUES(?,?,?,?,?)""", (worker_id, amount, date, note, datetime.utcnow().isoformat()))
        c.commit()
    return redirect(url_for("expenses_list"))

@app.get("/expenses/<int:eid>/edit")
def expenses_edit_form(eid):
    if require_login(): return require_login()
    with conn() as c:
        cur = c.cursor(); cur.execute("SELECT * FROM expenses WHERE id=?", (eid,)); r = cur.fetchone()
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
        cur.execute("""UPDATE expenses SET worker_id=?, amount=?, date=?, note=? WHERE id=?""",
                    (worker_id, amount, date, note, eid))
        c.commit()
    return redirect(url_for("expenses_list"))

@app.post("/expenses/<int:eid>/delete")
def expenses_delete(eid):
    if require_login(): return require_login()
    with conn() as c:
        c.execute("DELETE FROM expenses WHERE id=?", (eid,)); c.commit()
    return redirect(url_for("expenses_list"))

@app.get("/export/expenses.csv")
def export_expenses():
    if require_login(): return require_login()
    output = io.StringIO(); writer = csv.writer(output)
    writer.writerow(["id","worker_id","amount","date","note","created_at"])
    with conn() as c:
        for r in c.execute("SELECT * FROM expenses ORDER BY id DESC"):
            writer.writerow([r["id"],r["worker_id"],r["amount"],r["date"],r["note"],r["created_at"]])
    mem = io.BytesIO(output.getvalue().encode("utf-8"))
    return send_file(mem, mimetype="text/csv", as_attachment=True, download_name="expenses.csv")

# 初始化数据库
init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
