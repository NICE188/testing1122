# app.py – Admin Royale（深/浅色主题 + 右侧操作列 + 内置模板 · 完整可运行）
from flask import Flask, request, render_template, redirect, url_for, session, flash, abort, send_file, Response
from jinja2 import DictLoader, TemplateNotFound
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, os, io, csv
from datetime import datetime

APP_DB = os.environ.get("APP_DB", "data.db")
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
SECRET_KEY    = os.environ.get("SECRET_KEY", "dev-secret")

app = Flask(__name__)
app.secret_key = SECRET_KEY

@app.get("/health")
def health(): return "ok", 200

# ----------------------- 样式（黑金风，含 Light Mode 覆写） -----------------------
STYLE_CSS = r""":root{
  --bg:#0a0c12; --bg-2:#0d111b; --surface:#0f1522; --line:#212a3d;
  --text:#eaeef7; --muted:#a8b4cc;
  --gold:#f5d479; --gold-2:#ffd166;
  --royal:#8f7aff; --emerald:#25d0a5; --ruby:#ef476f;
  --radius:16px;
}
*{box-sizing:border-box} html,body{height:100%}
body{
  margin:0; color:var(--text);
  font:14px/1.6 Inter,system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;
  background:
    radial-gradient(1400px 700px at 12% -10%, color-mix(in oklab, var(--gold) 14%, transparent), transparent 60%),
    radial-gradient(1400px 700px at 115% 0%, color-mix(in oklab, var(--royal) 14%, transparent), transparent 60%),
    linear-gradient(180deg, var(--bg), var(--bg-2) 1200px);
}

/* 顶部栏 */
.topbar{
  position:sticky; top:0; z-index:30;
  display:flex; align-items:center; justify-content:space-between;
  padding:12px 16px; border-bottom:1px solid var(--line);
  background:rgba(10,14,24,.72); backdrop-filter:blur(10px) saturate(140%);
  box-shadow:0 8px 28px rgba(0,0,0,.35);
}
.brand{display:flex;align-items:center;gap:10px;font-weight:900; letter-spacing:.3px}
.brand::before{content:"♛"; font-size:16px; filter: drop-shadow(0 6px 18px rgba(245,212,121,.35))}
.brand::after{
  content:""; width:7px; height:7px; border-radius:50%;
  background:conic-gradient(from 0deg, var(--gold), var(--royal), var(--gold));
  box-shadow:0 0 10px var(--gold);
}
.nav a,.nav .btn{margin-left:10px;padding:6px 10px;border-radius:12px;border:1px solid rgba(255,255,255,.06);text-decoration:none;color:var(--text);background:transparent}
.nav a:hover,.nav .btn:hover{border-color:var(--line)}

/* 布局与侧栏 */
.layout{display:grid;grid-template-columns:300px 1fr;min-height:calc(100vh - 56px)}
.sidebar{
  position:sticky; top:56px; height:calc(100vh - 56px);
  padding:14px 12px; background:linear-gradient(180deg, rgba(22,26,44,.66), rgba(12,18,34,.86));
  border-right:1px solid var(--line)
}
.main{padding:22px}
.side-menu{display:grid;gap:10px}
.side-menu a{
  display:flex; align-items:center; gap:12px; padding:12px 14px;
  border-radius:var(--radius); border:1px solid rgba(255,255,255,.06);
  text-decoration:none; color:var(--text);
  background:linear-gradient(180deg, rgba(255,255,255,.025), transparent 60%), rgba(16,22,38,.6);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.04);
}
.side-menu a .icon{width:22px;text-align:center}
.side-menu a:hover{
  border-color:#3d4f7c; background:rgba(22,30,50,.75);
  transform: translateY(-1px); transition: transform .12s ease, background .18s ease, border-color .18s ease;
}
.side-menu a.active{
  border-color: color-mix(in oklab, var(--gold) 38%, transparent);
  background:
    linear-gradient(100deg, color-mix(in oklab, var(--gold) 18%, transparent), color-mix(in oklab, var(--royal) 12%, transparent)),
    rgba(22,30,50,.88);
  box-shadow:
    inset 0 0 0 1px color-mix(in oklab, var(--gold) 26%, transparent),
    0 12px 28px rgba(0,0,0,.35);
}

/* 概览卡片与通用面板 */
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px;margin:14px 0}
.card,.panel{
  position:relative;
  background:linear-gradient(180deg, rgba(255,255,255,.04), transparent 60%), var(--surface);
  border:1px solid rgba(255,255,255,.08); border-radius:var(--radius);
  padding:16px; box-shadow:0 28px 70px rgba(0,0,0,.55)
}
.card::before{
  content:""; position:absolute; left:12px; right:12px; top:10px; height:2px; border-radius:2px;
  background:linear-gradient(90deg, color-mix(in oklab, var(--gold) 60%, transparent), transparent);
  opacity:.85; filter: drop-shadow(0 6px 16px rgba(245,212,121,.3));
}
.card-title{font-size:12px;color:var(--muted)} .card-value{font-size:30px;margin-top:8px;letter-spacing:.3px}

/* 表单与按钮（基础） */
.form{display:flex;flex-wrap:wrap;gap:10px}
.form input,.form select,.form textarea,.form button{
  height:40px; padding:8px 12px; border-radius:14px;
  border:1px solid var(--line); background:#0e172b; color:var(--text); outline:0
}
.form textarea{height:auto;min-height:96px;width:100%;resize:vertical}
.form input:focus,.form select:focus,.form textarea:focus{
  border-color:#5c6ea1; box-shadow:0 0 0 3px rgba(92,110,161,.28), inset 0 1px 0 rgba(255,255,255,.06)
}
.btn{
  display:inline-flex; align-items:center; gap:8px; height:38px; padding:0 16px;
  border-radius:14px; border:1px solid rgba(255,255,255,.08);
  background:linear-gradient(180deg, rgba(255,255,255,.03), transparent 60%), rgba(16,22,38,.6);
  color:var(--text); text-decoration:none; cursor:pointer;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.05), 0 10px 24px rgba(0,0,0,.28);
  transition: transform .12s ease, box-shadow .18s ease, border-color .18s ease, background .18s ease;
}
.btn:hover{ transform: translateY(-1px); box-shadow:0 16px 34px rgba(0,0,0,.32) }
.btn:active{ transform: translateY(0); box-shadow:0 8px 18px rgba(0,0,0,.26) }
.btn-edit{
  background: linear-gradient(135deg, color-mix(in oklab, var(--royal) 55%, transparent), color-mix(in oklab, var(--gold) 38%, transparent)), #141f38 !important;
  border-color: color-mix(in oklab, var(--royal) 55%, transparent) !important;
}
.btn-delete{
  background: linear-gradient(135deg, rgba(239,71,111,.62), rgba(244,114,182,.55)), #2a1416 !important;
  border-color: rgba(239,71,111,.62) !important;
}

/* —— 操作列：一排靠右（纯图标 + 紧凑） —— */
.actions-cell{ text-align:right; }
.actions-inline{
  display:flex; justify-content:flex-end; align-items:center;
  gap:8px; flex-wrap:wrap;
}
.actions-inline form{ margin:0; display:inline-flex; }

/* 纯图标按钮（用于启停/编辑/删除） */
.btn-icon{
  width:34px; height:34px; padding:0;
  border-radius:12px;
  display:inline-flex; align-items:center; justify-content:center;
  font-size:16px; line-height:1;
}
.btn-icon:hover{ transform:translateY(-1px) }
.btn-icon:active{ transform:translateY(0) }

/* 表格更紧凑 */
.table-wrap{overflow:auto;border:1px solid rgba(255,255,255,.08);border-radius:var(--radius);box-shadow:0 28px 68px rgba(0,0,0,.52)}
table{border-collapse:separate;border-spacing:0;width:100%}
th{
  position:sticky; top:0; background:rgba(16,24,44,.92);backdrop-filter:blur(4px);
  font-weight:700; font-size:12px; letter-spacing:.3px; color:#d8e3ff;
  border-bottom:1px solid var(--line); text-align:left; padding:10px;
}
td{padding:10px;border-bottom:1px solid var(--line)}
tbody tr:hover{background: linear-gradient(90deg, color-mix(in oklab, var(--gold) 10%, transparent), transparent 60%) !important}
tbody tr:nth-child(even){background:rgba(255,255,255,.02)}

/* 小弹窗 / 大弹窗（保留） */
.modal-backdrop{position:fixed; inset:0; z-index:50; display:none; background:radial-gradient(1200px 600px at 15% -10%, color-mix(in oklab, var(--gold) 16%, transparent), transparent 60%), radial-gradient(1200px 600px at 120% 10%, color-mix(in oklab, var(--royal) 14%, transparent), transparent 60%), rgba(5,8,14,.62); backdrop-filter:blur(10px) saturate(140%)}
.modal-backdrop.open{display:flex; align-items:center; justify-content:center; padding:22px}
.modal{width:min(440px,100%); border-radius:var(--radius); padding:18px; background:linear-gradient(180deg, rgba(255,255,255,.06), transparent 60%), #0e1528; border:1px solid rgba(255,255,255,.14); box-shadow:0 34px 80px rgba(0,0,0,.58); opacity:0; transform:translateY(10px) scale(.985); transition:opacity .18s ease, transform .18s ease; position:relative;}
.modal-backdrop.open .modal{opacity:1; transform:none}

.big-backdrop{position:fixed; inset:0; z-index:55; display:none; background: radial-gradient(1800px 760px at 10% -10%, color-mix(in oklab, var(--gold) 16%, transparent), transparent 60%), radial-gradient(1600px 640px at 120% 0%, color-mix(in oklab, var(--royal) 16%, transparent), transparent 60%), linear-gradient(180deg, rgba(6,10,18,.74), rgba(6,10,18,.64)); backdrop-filter: blur(14px) saturate(140%);}
.big-backdrop.open{display:flex; align-items:center; justify-content:center; padding:30px}
.big-modal{width:min(1080px, 96vw); max-height:90vh; overflow:auto; position:relative; border-radius:20px; background: linear-gradient(180deg, rgba(255,255,255,.08), transparent 58%), radial-gradient(1200px 220px at 50% -8%, rgba(255,255,255,.12), transparent 60%), linear-gradient(180deg, #10182c, #0e1628); border: 1px solid rgba(255,255,255,.16); box-shadow: 0 80px 180px rgba(0,0,0,.76), inset 0 1px 0 rgba(255,255,255,.06);}
.big-header{position:sticky; top:0; display:flex; align-items:center; justify-content:space-between; padding:14px 18px; background: linear-gradient(180deg, rgba(18,26,44,.92), rgba(12,19,33,.86)), linear-gradient(180deg, rgba(255,255,255,.06), transparent); border-bottom: 1px solid rgba(255,255,255,.10);}
.big-title{font-weight:900; letter-spacing:.3px; display:flex; align-items:center; gap:10px; background: linear-gradient(90deg, var(--gold), var(--royal)); -webkit-background-clip:text; background-clip:text; color:transparent;}
.big-close{padding:8px 12px; border-radius:12px; border:1px solid rgba(255,255,255,.16); background:linear-gradient(180deg, rgba(255,255,255,.06), transparent 70%); color:var(--text); cursor:pointer;}
.big-body{padding:20px}

/* —— 手机端优化：操作列自动折两行 —— */
@media (max-width: 640px){
  th, td { padding:8px; }
  .actions-inline{ gap:6px; }
  .actions-inline > form:first-child{ order:0; flex-basis:100%; display:flex; justify-content:flex-end; }
  .actions-inline > *:not(:first-child){ order:1; }
  .btn-icon{ width:32px; height:32px; font-size:15px; border-radius:10px; }
}

/* === Light Mode 变量覆写 === */
:root[data-theme="light"]{
  --bg:#f7f8fb; --bg-2:#eef1f7; --surface:#ffffff; --line:#d8dfec;
  --text:#0b1020; --muted:#5b6780;
  --gold:#c79f2b; --gold-2:#e2b941; --royal:#5e56ff; --emerald:#16a085; --ruby:#d24a64;
}
:root[data-theme="light"] .topbar{
  background:rgba(255,255,255,.84);
  border-bottom:1px solid var(--line);
  box-shadow:0 8px 28px rgba(0,0,0,.08);
}
:root[data-theme="light"] .sidebar{
  background:linear-gradient(180deg, rgba(255,255,255,.85), rgba(255,255,255,.9));
  border-right:1px solid var(--line);
}
:root[data-theme="light"] .card,
:root[data-theme="light"] .panel{
  background:linear-gradient(180deg, rgba(0,0,0,.02), transparent 60%), var(--surface);
  border:1px solid rgba(0,0,0,.06);
  box-shadow:0 10px 30px rgba(0,0,0,.08);
}
:root[data-theme="light"] .btn{
  border-color:rgba(0,0,0,.08);
  background:linear-gradient(180deg, rgba(0,0,0,.02), transparent 60%), rgba(255,255,255,.9);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.6), 0 8px 18px rgba(0,0,0,.08);
  color:var(--text);
}
:root[data-theme="light"] th{
  background:rgba(255,255,255,.92);
  color:#303a58;
  border-bottom:1px solid var(--line);
}
:root[data-theme="light"] tbody tr:nth-child(even){ background:rgba(0,0,0,.02) }
"""

@app.get("/static/style.css")
def static_style(): return Response(STYLE_CSS, mimetype="text/css")

# ----------------------- 内置模板（无需 templates/ 目录） -----------------------
TEMPLATES = {
"base.html": """<!doctype html>
<html lang="zh">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">

  <!-- ① 先设定主题，避免闪烁 -->
  <script>
    (function () {
      try {
        var saved = localStorage.getItem('theme');
        var sysDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
        var theme = saved || (sysDark ? 'dark' : 'light');
        document.documentElement.setAttribute('data-theme', theme);
      } catch (e) {}
    })();
  </script>

  <title>{% block title %}后台 · {{ t.app_name }}{% endblock %}</title>
  <!-- ② 再加载样式（更新版本号确保刷新缓存） -->
  <link rel="stylesheet" href="{{ url_for('static_style') }}?v=160">
</head>
<body class="luxury">
  <header class="topbar">
    <div class="brand">Admin Royale</div>
    <nav class="nav">
      <button id="themeToggle" class="btn" type="button" title="切换主题" aria-label="切换主题">🌙</button>
      {% if session.get('user_id') %}
        <span>👤 {{ session.get('user_id') }}</span>
        <a href="{{ url_for('logout') }}">退出</a>
      {% else %}
        <a href="{{ url_for('login') }}">登录</a>
      {% endif %}
    </nav>
  </header>

  <div class="layout">
    <aside class="sidebar">
      <nav class="side-menu">
        <a href="{{ url_for('dashboard') }}" class="{{ 'active' if request.path == '/' else '' }}"><span class="icon">🏠</span>Dashboard</a>
        <a href="{{ url_for('workers_list') }}" class="{{ 'active' if request.path.startswith('/workers') else '' }}"><span class="icon">👨‍💼</span>工人 / 平台</a>
        <a href="{{ url_for('bank_accounts_list') }}" class="{{ 'active' if request.path.startswith('/bank-accounts') else '' }}"><span class="icon">🏦</span>银行账户</a>
        <a href="{{ url_for('card_rentals_list') }}" class="{{ 'active' if request.path.startswith('/card-rentals') else '' }}"><span class="icon">💳</span>银行卡租金</a>
        <a href="{{ url_for('salaries_list') }}" class="{{ 'active' if request.path.startswith('/salaries') else '' }}"><span class="icon">💵</span>出粮记录</a>
        <a href="{{ url_for('expenses_list') }}" class="{{ 'active' if request.path.startswith('/expenses') else '' }}"><span class="icon">💸</span>开销记录</a>
        <a href="{{ url_for('account_security') }}" class="{{ 'active' if request.path.startswith('/account') or request.path.startswith('/account-security') else '' }}"><span class="icon">🔐</span>安全设置</a>
      </nav>
    </aside>
    <main class="main">
      {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
          <div class="panel" style="margin-bottom:16px">
            {% for category, message in messages %}
              <div>{{ message }}</div>
            {% endfor %}
          </div>
        {% endif %}
      {% endwith %}
      {% block content %}{% endblock %}
    </main>
  </div>

  <!-- 删除确认弹窗 -->
  <div id="confirmBackdrop" class="modal-backdrop" aria-hidden="true">
    <div class="modal">
      <h3>确认操作</h3>
      <p id="confirmText">确定要执行该操作吗？</p>
      <div class="modal-actions" style="display:flex;gap:10px;justify-content:flex-end">
        <button id="confirmCancel" class="btn" type="button">取消</button>
        <button id="confirmOk" class="btn btn-delete" type="button" title="确认删除" aria-label="确认删除">🗑️</button>
      </div>
    </div>
  </div>

  <!-- 大表单弹窗 -->
  <div id="bigBackdrop" class="big-backdrop" aria-hidden="true">
    <div class="big-modal">
      <div class="big-header">
        <div class="big-title" id="bigTitle">📄 表单</div>
        <button id="bigClose" class="big-close" type="button">✖</button>
      </div>
      <div id="bigContent" class="big-body">
        <div class="panel">等待加载…</div>
      </div>
    </div>
  </div>

  <script>
    // 主题按钮逻辑（本地记忆）
    (function () {
      var btn = document.getElementById('themeToggle');
      if (!btn) return;
      function currentTheme() {
        return document.documentElement.getAttribute('data-theme') || 'dark';
      }
      function setIcon() {
        var cur = currentTheme();
        btn.textContent = (cur === 'dark') ? '🌙' : '☀️';
        btn.setAttribute('aria-label', cur === 'dark' ? '切换到亮色' : '切换到暗色');
        btn.title = btn.getAttribute('aria-label');
      }
      setIcon();
      btn.addEventListener('click', function () {
        var cur = currentTheme();
        var next = cur === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', next);
        try { localStorage.setItem('theme', next); } catch (e) {}
        setIcon();
      });
    })();

    // 删除确认
    (function(){
      const backdrop = document.getElementById('confirmBackdrop');
      const txt = document.getElementById('confirmText');
      const btnOK = document.getElementById('confirmOk');
      const btnCancel = document.getElementById('confirmCancel');
      let pendingForm = null;
      function open(msg){ if(msg) txt.textContent = msg; backdrop.classList.add('open'); backdrop.setAttribute('aria-hidden','false'); }
      function close(){ backdrop.classList.remove('open'); backdrop.setAttribute('aria-hidden','true'); pendingForm = null; }
      document.addEventListener('submit', function(e){
        const f = e.target;
        if(f.matches('.confirm')){
          e.preventDefault();
          pendingForm = f;
          open(f.dataset.confirm || '确定要删除这条记录吗？');
        }
      }, true);
      btnCancel.addEventListener('click', close);
      btnOK.addEventListener('click', function(){
        if(pendingForm){ const f = pendingForm; pendingForm=null; close(); f.classList.remove('confirm'); f.submit(); }
      });
      document.addEventListener('keydown', (e)=>{ if(e.key==='Escape') close(); });
      backdrop.addEventListener('click', (e)=>{ if(e.target===backdrop) close(); });
    })();

    // 大弹窗加载器（partial=1）
    (function(){
      const big = document.getElementById('bigBackdrop');
      const content = document.getElementById('bigContent');
      const title = document.getElementById('bigTitle');
      const closeBtn = document.getElementById('bigClose');

      function open(){ big.classList.add('open'); big.setAttribute('aria-hidden','false'); document.body.style.overflow='hidden'; }
      function close(){
        big.classList.add('closing');
        setTimeout(()=>{ big.classList.remove('open','closing'); big.setAttribute('aria-hidden','true'); document.body.style.overflow=''; content.innerHTML=''; title.textContent='📄 表单'; }, 220);
      }

      async function load(url, text){
        title.textContent = text || '📄 表单';
        content.innerHTML = '<div class="panel">正在加载…</div>';
        open();
        try{
          const res = await fetch(url + (url.includes('?') ? '&' : '?') + 'partial=1', {headers:{'X-Requested-With':'fetch'}});
          const html = await res.text();
          content.innerHTML = html;
        }catch(e){
          content.innerHTML = '<div class="panel">加载失败，请重试。</div>';
        }
      }

      document.addEventListener('click', function(ev){
        const el = ev.target.closest('a.js-open-modal, button.js-open-modal');
        if(el){
          ev.preventDefault();
          const href = el.getAttribute('href') || el.dataset.href || '#';
          const tt = el.getAttribute('data-title') || el.title || el.textContent.trim();
          load(href, tt);
        }
      });

      big.addEventListener('submit', async function(ev){
        const f = ev.target;
        if(!big.contains(f)) return;
        ev.preventDefault();
        const data = new FormData(f);
        const btn = f.querySelector('button[type="submit"]'); if(btn){ btn.disabled=true; btn.style.opacity=.75; }
        try{
          await fetch(f.action, {method: f.method || 'POST', body: data, headers:{'X-Requested-With':'fetch'}});
          close(); location.reload();
        }catch(e){ alert('提交失败，请重试'); } finally{ if(btn){ btn.disabled=false; btn.style.opacity=1; } }
      });

      closeBtn.addEventListener('click', close);
      big.addEventListener('click', (e)=>{ if(e.target===big) close(); });
      document.addEventListener('keydown', (e)=>{ if(e.key==='Escape' && big.classList.contains('open')) close(); });
    })();
  </script>
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
<h1>🏠 Dashboard</h1>
<div class="cards">
  <div class="card"><div class="card-title">{{ t.total_workers }}</div><div class="card-value">{{ total_workers }}</div></div>
  <div class="card"><div class="card-title">{{ t.total_rentals }}</div><div class="card-value">{{ '%.2f'|format(total_rentals) }}</div></div>
  <div class="card"><div class="card-title">{{ t.total_salaries }}</div><div class="card-value">{{ '%.2f'|format(total_salaries) }}</div></div>
  <div class="card"><div class="card-title">{{ t.total_expenses }}</div><div class="card-value">{{ '%.2f'|format(total_expenses) }}</div></div>
</div>
{% endblock %}
""",

# ===== 列表页：操作列纯图标，一排靠右 =====
"workers_list.html": """{% extends "base.html" %}
{% block title %}{{ t.workers }} · {{ t.app_name }}{% endblock %}
{% block content %}
<h1>👨‍💼 {{ t.workers }}</h1>
<div class="panel">
  <div class="actions" style="margin-bottom:12px">
    <a class="btn btn-edit js-open-modal" href="{{ url_for('workers_add_form') }}" data-title="➕ 新增工人">➕ {{ t.add }}</a>
    <a class="btn" href="{{ url_for('export_workers') }}">⤓ {{ t.export_workers }}</a>
  </div>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>ID</th><th>{{ t.name }}</th><th>{{ t.company }}</th><th>{{ t.commission }}</th><th>{{ t.expenses }}</th>
          <th>{{ t.created_at }}</th><th>{{ t.actions }}</th>
        </tr>
      </thead>
      <tbody>
        {% for r in rows %}
        <tr>
          <td>{{ r.id }}</td><td>{{ r.name }}</td><td>{{ r.company }}</td><td>{{ r.commission }}</td><td>{{ r.expenses }}</td>
          <td>{{ r.created_at }}</td>
          <td class="actions-cell">
            <div class="actions-inline">
              <form method="post" action="{{ url_for('workers_toggle', wid=r.id) }}">
                <button class="btn btn-icon" type="submit"
                        title="{{ '停用' if r.status==1 else '启用' }}" aria-label="{{ '停用' if r.status==1 else '启用' }}">
                  {{ '✅' if r.status==1 else '🚫' }}
                </button>
              </form>
              <a class="btn btn-edit btn-icon js-open-modal" href="{{ url_for('workers_edit_form', wid=r.id) }}" data-title="✏️ 编辑工人" title="编辑" aria-label="编辑">✏️</a>
              <form method="post" action="{{ url_for('workers_delete', wid=r.id) }}" class="confirm" data-confirm="{{ t.confirm_delete }}">
                <button class="btn btn-delete btn-icon" type="submit" title="删除" aria-label="删除">🗑️</button>
              </form>
            </div>
          </td>
        </tr>
        {% else %}<tr><td colspan="7">{{ t.empty }}</td></tr>{% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}
""",

"bank_accounts_list.html": """{% extends "base.html" %}
{% block title %}{{ t.bank_accounts }} · {{ t.app_name }}{% endblock %}
{% block content %}
<h1>🏦 {{ t.bank_accounts }}</h1>
<div class="panel">
  <div class="actions" style="margin-bottom:12px">
    <a class="btn btn-edit js-open-modal" href="{{ url_for('bank_accounts_add_form') }}" data-title="➕ 新增银行账户">➕ {{ t.add }}</a>
    <a class="btn" href="{{ url_for('export_bank_accounts') }}">⤓ {{ t.export_bank }}</a>
  </div>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>ID</th><th>银行名</th><th>账号</th><th>户名</th><th>卡公司</th><th>{{ t.created_at }}</th><th>{{ t.actions }}</th>
        </tr>
      </thead>
      <tbody>
        {% for r in rows %}
        <tr>
          <td>{{ r.id }}</td><td>{{ r.bank_name }}</td><td>{{ r.account_no }}</td><td>{{ r.holder }}</td><td>{{ r.card_company or '-' }}</td>
          <td>{{ r.created_at }}</td>
          <td class="actions-cell">
            <div class="actions-inline">
              <form method="post" action="{{ url_for('bank_accounts_toggle', bid=r.id) }}">
                <button class="btn btn-icon" type="submit"
                        title="{{ '停用' if r.status==1 else '启用' }}" aria-label="{{ '停用' if r.status==1 else '启用' }}">
                  {{ '✅' if r.status==1 else '🚫' }}
                </button>
              </form>
              <a class="btn btn-edit btn-icon js-open-modal" href="{{ url_for('bank_accounts_edit_form', bid=r.id) }}" data-title="✏️ 编辑银行账户" title="编辑" aria-label="编辑">✏️</a>
              <form method="post" action="{{ url_for('bank_accounts_delete', bid=r.id) }}" class="confirm" data-confirm="{{ t.confirm_delete }}">
                <button class="btn btn-delete btn-icon" type="submit" title="删除" aria-label="删除">🗑️</button>
              </form>
            </div>
          </td>
        </tr>
        {% else %}<tr><td colspan="7">{{ t.empty }}</td></tr>{% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}
""",

"card_rentals_list.html": """{% extends "base.html" %}
{% block title %}{{ t.card_rentals }} · {{ t.app_name }}{% endblock %}
{% block content %}
<h1>💳 {{ t.card_rentals }}</h1>
<div class="panel">
  <div class="actions" style="margin-bottom:12px">
    <a class="btn btn-edit js-open-modal" href="{{ url_for('card_rentals_add_form') }}" data-title="➕ 新增银行卡租金">➕ {{ t.add }}</a>
    <a class="btn" href="{{ url_for('export_card_rentals') }}">⤓ {{ t.export_rentals }}</a>
  </div>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>ID</th><th>银行</th><th>账号</th><th>卡公司</th><th>月租金</th><th>开始</th><th>结束</th><th>备注</th><th>{{ t.created_at }}</th><th>{{ t.actions }}</th>
        </tr>
      </thead>
      <tbody>
        {% for r in rows %}
        <tr>
          <td>{{ r.id }}</td><td>{{ r.bank_name }}</td><td>{{ r.account_no }}</td><td>{{ r.card_company or '-' }}</td>
          <td>{{ r.monthly_rent }}</td><td>{{ r.start_date }}</td><td>{{ r.end_date }}</td><td>{{ r.note }}</td><td>{{ r.created_at }}</td>
          <td class="actions-cell">
            <div class="actions-inline">
              <form method="post" action="{{ url_for('card_rentals_toggle', rid=r.id) }}">
                <button class="btn btn-icon" type="submit"
                        title="{{ '停用' if r.status==1 else '启用' }}" aria-label="{{ '停用' if r.status==1 else '启用' }}">
                  {{ '✅' if r.status==1 else '🚫' }}
                </button>
              </form>
              <a class="btn btn-edit btn-icon js-open-modal" href="{{ url_for('card_rentals_edit_form', rid=r.id) }}" data-title="✏️ 编辑银行卡租金" title="编辑" aria-label="编辑">✏️</a>
              <form method="post" action="{{ url_for('card_rentals_delete', rid=r.id) }}" class="confirm" data-confirm="{{ t.confirm_delete }}">
                <button class="btn btn-delete btn-icon" type="submit" title="删除" aria-label="删除">🗑️</button>
              </form>
            </div>
          </td>
        </tr>
        {% else %}<tr><td colspan="10">{{ t.empty }}</td></tr>{% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}
""",

"salaries_list.html": """{% extends "base.html" %}
{% block title %}{{ t.salaries }} · {{ t.app_name }}{% endblock %}
{% block content %}
<h1>💵 {{ t.salaries }}</h1>
<div class="panel">
  <div class="actions" style="margin-bottom:12px">
    <a class="btn btn-edit js-open-modal" href="{{ url_for('salaries_add_form') }}" data-title="➕ 新增出粮记录">➕ {{ t.add }}</a>
    <a class="btn" href="{{ url_for('export_salaries') }}">⤓ {{ t.export_salaries }}</a>
  </div>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>ID</th><th>{{ t.worker }}</th><th>{{ t.salary_amount }}</th><th>{{ t.pay_date }}</th><th>{{ t.note }}</th><th>{{ t.created_at }}</th><th>{{ t.actions }}</th>
        </tr>
      </thead>
      <tbody>
        {% for r in rows %}
        <tr>
          <td>{{ r.id }}</td><td>{{ r.worker_name }}</td><td>{{ r.amount }}</td><td>{{ r.pay_date }}</td><td>{{ r.note }}</td><td>{{ r.created_at }}</td>
          <td class="actions-cell">
            <div class="actions-inline">
              <form method="post" action="{{ url_for('salaries_toggle', sid=r.id) }}">
                <button class="btn btn-icon" type="submit"
                        title="{{ '停用' if r.status==1 else '启用' }}" aria-label="{{ '停用' if r.status==1 else '启用' }}">
                  {{ '✅' if r.status==1 else '🚫' }}
                </button>
              </form>
              <a class="btn btn-edit btn-icon js-open-modal" href="{{ url_for('salaries_edit_form', sid=r.id) }}" data-title="✏️ 编辑出粮记录" title="编辑" aria-label="编辑">✏️</a>
              <form method="post" action="{{ url_for('salaries_delete', sid=r.id) }}" class="confirm" data-confirm="{{ t.confirm_delete }}">
                <button class="btn btn-delete btn-icon" type="submit" title="删除" aria-label="删除">🗑️</button>
              </form>
            </div>
          </td>
        </tr>
        {% else %}<tr><td colspan="7">{{ t.empty }}</td></tr>{% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}
""",

"expenses_list.html": """{% extends "base.html" %}
{% block title %}{{ t.expenses }} · {{ t.app_name }}{% endblock %}
{% block content %}
<h1>💸 {{ t.expenses }}</h1>
<div class="panel">
  <div class="actions" style="margin-bottom:12px">
    <a class="btn btn-edit js-open-modal" href="{{ url_for('expenses_add_form') }}" data-title="➕ 新增开销记录">➕ {{ t.add }}</a>
    <a class="btn" href="{{ url_for('export_expenses') }}">⤓ {{ t.export_expenses }}</a>
  </div>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>ID</th><th>{{ t.worker }}</th><th>{{ t.expense_amount }}</th><th>{{ t.date }}</th><th>{{ t.expenses_note }}</th><th>{{ t.created_at }}</th><th>{{ t.actions }}</th>
        </tr>
      </thead>
      <tbody>
        {% for r in rows %}
        <tr>
          <td>{{ r.id }}</td><td>{{ r.worker_name }}</td><td>{{ r.amount }}</td><td>{{ r.date }}</td><td>{{ r.note }}</td><td>{{ r.created_at }}</td>
          <td class="actions-cell">
            <div class="actions-inline">
              <form method="post" action="{{ url_for('expenses_toggle', eid=r.id) }}">
                <button class="btn btn-icon" type="submit"
                        title="{{ '停用' if r.status==1 else '启用' }}" aria-label="{{ '停用' if r.status==1 else '启用' }}">
                  {{ '✅' if r.status==1 else '🚫' }}
                </button>
              </form>
              <a class="btn btn-edit btn-icon js-open-modal" href="{{ url_for('expenses_edit_form', eid=r.id) }}" data-title="✏️ 编辑开销记录" title="编辑" aria-label="编辑">✏️</a>
              <form method="post" action="{{ url_for('expenses_delete', eid=r.id) }}" class="confirm" data-confirm="{{ t.confirm_delete }}">
                <button class="btn btn-delete btn-icon" type="submit" title="删除" aria-label="删除">🗑️</button>
              </form>
            </div>
          </td>
        </tr>
        {% else %}<tr><td colspan="7">{{ t.empty }}</td></tr>{% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}
""",

# ———— 账号安全页 ————
"account_security.html": """{% extends "base.html" %}
{% block title %}账号安全 · {{ t.app_name }}{% endblock %}
{% block content %}
<div class="panel">
  <h2>🔐 账号安全</h2>
  <div class="actions">
    <a class="btn js-open-modal" href="{{ url_for('account_credentials') }}" data-title="🧑‍💻 修改登录账号/密码">🧑‍💻 修改登录账号/密码</a>
    <a class="btn js-open-modal" href="{{ url_for('account_change_password') }}" data-title="🔑 修改密码">🔑 修改密码</a>
    <a class="btn js-open-modal" href="{{ url_for('account_change_username') }}" data-title="🆔 修改用户名">🆔 修改用户名</a>
    <a class="btn btn-delete js-open-modal" href="{{ url_for('account_reset') }}" data-title="🛠 管理员重置密码">🛠 管理员重置密码</a>
  </div>
</div>
{% endblock %}
""",

# ———— partials（弹窗表单） ————
"partials/account_credentials_form.html": """
<div class="panel">
  <h2>🧑‍💻 修改登录账号/密码</h2>
  <form class="form" method="post" action="{{ url_for('account_credentials_post') }}">
    <input name="username" placeholder="{{ t.username }}" required>
    <input name="password" type="password" placeholder="{{ t.password }}" required>
    <button class="btn btn-edit" type="submit">💾 {{ t.save }}</button>
  </form>
</div>
""",
"partials/account_change_password_form.html": """
<div class="panel">
  <h2>🔑 修改密码</h2>
  <form class="form" method="post" action="{{ url_for('account_change_password_post') }}">
    <input name="old_password" type="password" placeholder="旧密码" required>
    <input name="new_password" type="password" placeholder="新密码" required>
    <button class="btn btn-edit" type="submit">💾 {{ t.save }}</button>
  </form>
</div>
""",
"partials/account_change_username_form.html": """
<div class="panel">
  <h2>🆔 修改用户名</h2>
  <form class="form" method="post" action="{{ url_for('account_change_username_post') }}">
    <input name="new_username" placeholder="新用户名" required>
    <button class="btn btn-edit" type="submit">💾 {{ t.save }}</button>
  </form>
</div>
""",
"partials/account_reset_form.html": """
<div class="panel">
  <h2>🛠 管理员重置密码</h2>
  <form class="form" method="post" action="{{ url_for('account_reset_post') }}">
    <input name="target_username" placeholder="目标用户名" required>
    <input name="new_password" type="password" placeholder="新密码" required>
    <button class="btn btn-delete" type="submit">💾 {{ t.save }}</button>
  </form>
</div>
""",
"partials/workers_form.html": """
<div class="panel">
  <h2 style="margin-top:0">{{ '✏️ 编辑工人' if r else '➕ 新增工人' }}</h2>
  <form class="form" method="post" action="{{ url_for('workers_edit', wid=r.id) if r else url_for('workers_add') }}">
    <input name="name" value="{{ r.name if r else '' }}" placeholder="{{ t.name }}" required>
    <input name="company" value="{{ r.company if r else '' }}" placeholder="{{ t.company }}">
    <input name="commission" type="number" step="0.01" value="{{ r.commission if r else '' }}" placeholder="{{ t.commission }}">
    <input name="expenses" type="number" step="0.01" value="{{ r.expenses if r else '' }}" placeholder="{{ t.expenses }}">
    <button class="btn btn-edit" type="submit">💾 {{ t.save if r else t.add }}</button>
  </form>
</div>
""",
"partials/bank_accounts_form.html": """
<div class="panel">
  <h2 style="margin-top:0">{{ '✏️ 编辑银行账户' if r else '➕ 新增银行账户' }}</h2>
  <form class="form" method="post" action="{{ url_for('bank_accounts_edit', bid=r.id) if r else url_for('bank_accounts_add') }}">
    <input name="bank_name" value="{{ r.bank_name if r else '' }}" placeholder="银行名" required>
    <input name="account_no" value="{{ r.account_no if r else '' }}" placeholder="账号" required>
    <input name="holder" value="{{ r.holder if r else '' }}" placeholder="户名" required>
    <input name="card_company" value="{{ r.card_company if r else '' }}" placeholder="银行卡公司（如 Visa / Master / 银联）">
    <select name="status">
      <option value="1" {% if r and r.status==1 %}selected{% endif %}>{{ t.active }}</option>
      <option value="0" {% if r and r.status==0 %}selected{% endif %}>{{ t.inactive }}</option>
    </select>
    <button class="btn btn-edit" type="submit">💾 {{ t.save if r else t.add }}</button>
  </form>
</div>
""",
"partials/card_rentals_form.html": """
<div class="panel">
  <h2 style="margin-top:0">{{ '✏️ 编辑银行卡租金' if r else '➕ 新增银行卡租金' }}</h2>
  <form class="form" method="post" action="{{ url_for('card_rentals_edit', rid=r.id) if r else url_for('card_rentals_add') }}">
    <input name="bank_name"    value="{{ r.bank_name if r else '' }}" placeholder="银行名称" required>
    <input name="account_no"   value="{{ r.account_no if r else '' }}" placeholder="银行账号" required>
    <input name="card_company" value="{{ r.card_company if r else '' }}" placeholder="银行卡公司（如 Visa / Master / 银联）">
    <input name="monthly_rent" type="number" step="0.01" value="{{ r.monthly_rent if r else '' }}" placeholder="月租金" required>
    <input name="start_date"   type="date" value="{{ r.start_date if r else '' }}" placeholder="开始日期">
    <input name="end_date"     type="date" value="{{ r.end_date if r else '' }}" placeholder="结束日期">
    <textarea name="note" placeholder="备注">{{ r.note if r else '' }}</textarea>
    <button class="btn btn-edit" type="submit">💾 {{ t.save if r else t.add }}</button>
  </form>
</div>
""",
"partials/salaries_form.html": """
<div class="panel">
  <h2 style="margin-top:0">{{ '✏️ 编辑出粮记录' if r else '➕ 新增出粮记录' }}</h2>
  <form class="form" method="post" action="{{ url_for('salaries_edit', sid=r.id) if r else url_for('salaries_add') }}">
    <select name="worker_id">
      {% for w in workers %}
        <option value="{{ w.id }}" {% if r and r.worker_id==w.id %}selected{% endif %}>{{ w.name }}</option>
      {% endfor %}
    </select>
    <input name="amount" type="number" step="0.01" value="{{ r.amount if r else '' }}" placeholder="{{ t.salary_amount }}" required>
    <input name="pay_date" type="date" value="{{ r.pay_date if r else '' }}" placeholder="{{ t.pay_date }}" required>
    <textarea name="note" placeholder="{{ t.note }}">{{ r.note if r else '' }}</textarea>
    <button class="btn btn-edit" type="submit">💾 {{ t.save if r else t.add }}</button>
  </form>
</div>
""",
"partials/expenses_form.html": """
<div class="panel">
  <h2 style="margin-top:0">{{ '✏️ 编辑开销记录' if r else '➕ 新增开销记录' }}</h2>
  <form class="form" method="post" action="{{ url_for('expenses_edit', eid=r.id) if r else url_for('expenses_add') }}">
    <select name="worker_id">
      <option value="">不关联工人</option>
      {% for w in workers %}
        <option value="{{ w.id }}" {% if r and r.worker_id==w.id %}selected{% endif %}>{{ w.name }}</option>
      {% endfor %}
    </select>
    <input name="amount" type="number" step="0.01" value="{{ r.amount if r else '' }}" placeholder="{{ t.expense_amount }}" required>
    <input name="date" type="date" value="{{ r.date if r else '' }}" placeholder="{{ t.date }}" required>
    <textarea name="note" placeholder="{{ t.expenses_note }}">{{ r.note if r else '' }}</textarea>
    <button class="btn btn-edit" type="submit">💾 {{ t.save if r else t.add }}</button>
  </form>
</div>
""",
}

app.jinja_loader = DictLoader(TEMPLATES)

@app.errorhandler(TemplateNotFound)
def _tnf(e): return (f"Oops, template not found: <b>{e.name}</b>", 500)

@app.errorhandler(Exception)
def _any(e):
    import traceback; traceback.print_exc()
    return (f"Error: <b>{e.__class__.__name__}</b><br>Message: {str(e)}", 500)

# ----------------------- 文案 / 多语言 -----------------------
I18N = {
    "zh": {
        "app_name": "NepWin Ops",
        "login_tip": "请输入管理员账号和密码。",
        "username": "用户名","password": "密码","login": "登录",
        "workers": "工人 / 平台","bank_accounts": "银行账户","card_rentals": "银行卡租金",
        "salaries": "出粮记录","expenses": "开销记录","actions": "操作",
        "add": "新增","edit": "编辑","delete": "删除","save": "保存","back": "返回",
        "confirm_delete": "确定要删除这条记录吗？","empty": "暂无数据","created_at": "创建时间",
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

# ----------------------- DB 工具与初始化 -----------------------
def conn():
    c = sqlite3.connect(APP_DB)
    c.row_factory = sqlite3.Row
    return c

def ensure_column(c, table, col, decl, default_value=None):
    cur = c.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    cols = [r["name"] for r in cur.fetchall()]
    if col not in cols:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
        if default_value is not None:
            cur.execute(f"UPDATE {table} SET {col}=?", (default_value,))

def init_db():
    with conn() as c:
        cur = c.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password_hash TEXT, is_admin INTEGER DEFAULT 1
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS workers(
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, company TEXT, commission REAL DEFAULT 0.0, expenses REAL DEFAULT 0.0, status INTEGER DEFAULT 1, created_at TEXT
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS bank_accounts(
            id INTEGER PRIMARY KEY AUTOINCREMENT, bank_name TEXT, account_no TEXT, holder TEXT, status INTEGER DEFAULT 1, created_at TEXT
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS card_rentals(
            id INTEGER PRIMARY KEY AUTOINCREMENT, bank_account_id INTEGER, monthly_rent REAL, start_date TEXT, end_date TEXT, note TEXT, status INTEGER DEFAULT 1, created_at TEXT
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS salaries(
            id INTEGER PRIMARY KEY AUTOINCREMENT, worker_id INTEGER, amount REAL, pay_date TEXT, note TEXT, status INTEGER DEFAULT 1, created_at TEXT
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS expenses(
            id INTEGER PRIMARY KEY AUTOINCREMENT, worker_id INTEGER, amount REAL, date TEXT, note TEXT, status INTEGER DEFAULT 1, created_at TEXT
        )""")
        # 兜底列 + 卡公司
        ensure_column(c, "workers", "status", "INTEGER DEFAULT 1", 1)
        ensure_column(c, "bank_accounts", "status", "INTEGER DEFAULT 1", 1)
        ensure_column(c, "bank_accounts", "card_company", "TEXT", "")
        ensure_column(c, "card_rentals", "status", "INTEGER DEFAULT 1", 1)
        ensure_column(c, "salaries", "status", "INTEGER DEFAULT 1", 1)
        ensure_column(c, "expenses", "status", "INTEGER DEFAULT 1", 1)

        # 默认管理员
        cur.execute("SELECT COUNT(*) n FROM users")
        if cur.fetchone()["n"] == 0:
            cur.execute("INSERT INTO users(username, password_hash, is_admin) VALUES(?,?,1)",
                        (ADMIN_USERNAME, generate_password_hash(ADMIN_PASSWORD)))
        c.commit()

@app.before_request
def _ctx():
    setattr(request, "lang", get_lang())

@app.context_processor
def _inject():
    return {"t": T(), "lang": get_lang()}

# ----------------------- 鉴权 -----------------------
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
        u = c.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if not u or not check_password_hash(u["password_hash"], password):
            flash("用户名或密码不正确", "error"); return redirect(url_for("login"))
        session["user_id"] = u["username"]
    return redirect(url_for("dashboard"))

@app.get("/logout")
def logout(): session.clear(); return redirect(url_for("login"))

# ----------------------- Dashboard -----------------------
@app.get("/")
def dashboard():
    if require_login(): return require_login()
    with conn() as c:
        total_workers = c.execute("SELECT COUNT(*) n FROM workers").fetchone()["n"]
        total_rentals = c.execute("SELECT IFNULL(SUM(monthly_rent),0) s FROM card_rentals").fetchone()["s"]
        total_salaries = c.execute("SELECT IFNULL(SUM(amount),0) s FROM salaries").fetchone()["s"]
        total_expenses = c.execute("SELECT IFNULL(SUM(amount),0) s FROM expenses").fetchone()["s"]
    return render_template("dashboard.html", total_workers=total_workers,total_rentals=total_rentals,total_salaries=total_salaries,total_expenses=total_expenses)

# ----------------------- 账号安全 -----------------------
@app.get("/account-security")
def account_security():
    if require_login(): return require_login()
    return render_template("account_security.html")

@app.get("/account/credentials")
def account_credentials():
    if require_login(): return require_login()
    if request.args.get("partial") == "1":
        return render_template("partials/account_credentials_form.html")
    return render_template("account_security.html")

@app.post("/account/credentials")
def account_credentials_post():
    if require_login(): return require_login()
    new_username = request.form.get("username","").strip()
    new_password = request.form.get("password","").strip()
    if not new_username or not new_password:
        flash("用户名与密码不能为空", "error"); return redirect(url_for("account_security"))
    with conn() as c:
        u = c.execute("SELECT * FROM users WHERE username=?", (session["user_id"],)).fetchone()
        if not u: abort(403)
        c.execute("UPDATE users SET username=?, password_hash=? WHERE id=?", (new_username, generate_password_hash(new_password), u["id"]))
        c.commit()
        session["user_id"] = new_username
    flash("登录账号与密码已更新", "success"); return redirect(url_for("account_security"))

@app.get("/account/change-password")
def account_change_password():
    if require_login(): return require_login()
    if request.args.get("partial") == "1":
        return render_template("partials/account_change_password_form.html")
    return render_template("account_security.html")

@app.post("/account/change-password")
def account_change_password_post():
    if require_login(): return require_login()
    old_pw = request.form.get("old_password",""); new_pw = request.form.get("new_password","")
    with conn() as c:
        u = c.execute("SELECT * FROM users WHERE username=?", (session["user_id"],)).fetchone()
        if not u or not check_password_hash(u["password_hash"], old_pw):
            flash("旧密码不正确", "error"); return redirect(url_for("account_security"))
        c.execute("UPDATE users SET password_hash=? WHERE id=?", (generate_password_hash(new_pw), u["id"]))
        c.commit()
    flash("密码已更新", "success"); return redirect(url_for("account_security"))

@app.get("/account/change-username")
def account_change_username():
    if require_login(): return require_login()
    if request.args.get("partial") == "1":
        return render_template("partials/account_change_username_form.html")
    return render_template("account_security.html")

@app.post("/account/change-username")
def account_change_username_post():
    if require_login(): return require_login()
    new_username = request.form.get("new_username","").strip()
    if not new_username:
        flash("新用户名不能为空", "error"); return redirect(url_for("account_security"))
    with conn() as c:
        u = c.execute("SELECT * FROM users WHERE username=?", (session["user_id"],)).fetchone()
        if not u: abort(403)
        c.execute("UPDATE users SET username=? WHERE id=?", (new_username, u["id"]))
        c.commit()
        session["user_id"] = new_username
    flash("用户名已更新", "success"); return redirect(url_for("account_security"))

@app.get("/account/reset")
def account_reset():
    if require_login(): return require_login()
    if request.args.get("partial") == "1":
        return render_template("partials/account_reset_form.html")
    return render_template("account_security.html")

@app.post("/account/reset")
def account_reset_post():
    if require_login(): return require_login()
    target_username = request.form.get("target_username","").strip()
    new_password = request.form.get("new_password","").strip()
    with conn() as c:
        u = c.execute("SELECT * FROM users WHERE username=?", (target_username,)).fetchone()
        if not u:
            flash("目标用户不存在", "error"); return redirect(url_for("account_security"))
        c.execute("UPDATE users SET password_hash=? WHERE id=?", (generate_password_hash(new_password), u["id"]))
        c.commit()
    flash("目标用户密码已重置", "success"); return redirect(url_for("account_security"))

# ----------------------- 工人 / 平台 -----------------------
@app.get("/workers")
def workers_list():
    if require_login(): return require_login()
    with conn() as c:
        rows = c.execute("SELECT * FROM workers ORDER BY id DESC").fetchall()
    return render_template("workers_list.html", rows=rows)

@app.get("/workers/add")
def workers_add_form():
    if require_login(): return require_login()
    return render_template("partials/workers_form.html")

@app.post("/workers/add")
def workers_add():
    if require_login(): return require_login()
    name = request.form.get("name","").strip()
    company = request.form.get("company","").strip()
    commission = float(request.form.get("commission") or 0)
    expenses = float(request.form.get("expenses") or 0)
    with conn() as c:
        c.execute("""INSERT INTO workers(name,company,commission,expenses,status,created_at) VALUES(?,?,?,?,1,?)""",
                  (name, company, commission, expenses, datetime.utcnow().isoformat()))
        c.commit()
    return redirect(url_for("workers_list"))

@app.get("/workers/<int:wid>/edit")
def workers_edit_form(wid):
    if require_login(): return require_login()
    with conn() as c:
        r = c.execute("SELECT * FROM workers WHERE id=?", (wid,)).fetchone()
    if not r: abort(404)
    if request.args.get("partial") == "1":
        return render_template("partials/workers_form.html", r=r)
    return redirect(url_for("workers_list"))

@app.post("/workers/<int:wid>/edit")
def workers_edit(wid):
    if require_login(): return require_login()
    name = request.form.get("name","").strip()
    company = request.form.get("company","").strip()
    commission = float(request.form.get("commission") or 0)
    expenses = float(request.form.get("expenses") or 0)
    with conn() as c:
        c.execute("""UPDATE workers SET name=?, company=?, commission=?, expenses=? WHERE id=?""",
                  (name, company, commission, expenses, wid))
        c.commit()
    return redirect(url_for("workers_list"))

@app.post("/workers/<int:wid>/toggle")
def workers_toggle(wid):
    if require_login(): return require_login()
    with conn() as c:
        cur = c.cursor(); cur.execute("SELECT status FROM workers WHERE id=?", (wid,)); row = cur.fetchone()
        if not row: abort(404)
        cur.execute("UPDATE workers SET status=? WHERE id=?", (0 if row['status']==1 else 1, wid)); c.commit()
    return redirect(url_for("workers_list"))

@app.post("/workers/<int:wid>/delete")
def workers_delete(wid):
    if require_login(): return require_login()
    with conn() as c: c.execute("DELETE FROM workers WHERE id=?", (wid,)); c.commit()
    return redirect(url_for("workers_list"))

@app.get("/export/workers.csv")
def export_workers():
    if require_login(): return require_login()
    out = io.StringIO(); w = csv.writer(out)
    w.writerow(["id","name","company","commission","expenses","status","created_at"])
    with conn() as c:
        for r in c.execute("SELECT * FROM workers ORDER BY id DESC"):
            w.writerow([r['id'],r['name'],r['company'],r['commission'],r['expenses'],r['status'],r['created_at']])
    mem = io.BytesIO(out.getvalue().encode("utf-8"))
    return send_file(mem, mimetype="text/csv", as_attachment=True, download_name="workers.csv")

# ----------------------- 银行账户 -----------------------
@app.get("/bank-accounts")
def bank_accounts_list():
    if require_login(): return require_login()
    with conn() as c:
        rows = c.execute("SELECT * FROM bank_accounts ORDER BY id DESC").fetchall()
    return render_template("bank_accounts_list.html", rows=rows)

@app.get("/bank-accounts/add")
def bank_accounts_add_form():
    if require_login(): return require_login()
    return render_template("partials/bank_accounts_form.html")

@app.post("/bank-accounts/add")
def bank_accounts_add():
    if require_login(): return require_login()
    bank_name = request.form.get("bank_name","").strip()
    account_no = request.form.get("account_no","").strip()
    holder = request.form.get("holder","").strip()
    card_company = request.form.get("card_company","").strip()
    status = 1 if request.form.get("status") == "1" else 0
    with conn() as c:
        c.execute("""INSERT INTO bank_accounts(bank_name,account_no,holder,status,created_at,card_company) VALUES(?,?,?,?,?,?)""",
                  (bank_name, account_no, holder, status, datetime.utcnow().isoformat(), card_company))
        c.commit()
    return redirect(url_for("bank_accounts_list"))

@app.get("/bank-accounts/<int:bid>/edit")
def bank_accounts_edit_form(bid):
    if require_login(): return require_login()
    with conn() as c:
        r = c.execute("SELECT * FROM bank_accounts WHERE id=?", (bid,)).fetchone()
    if not r: abort(404)
    if request.args.get("partial") == "1":
        return render_template("partials/bank_accounts_form.html", r=r)
    return redirect(url_for("bank_accounts_list"))

@app.post("/bank-accounts/<int:bid>/edit")
def bank_accounts_edit(bid):
    if require_login(): return require_login()
    bank_name = request.form.get("bank_name","").strip()
    account_no = request.form.get("account_no","").strip()
    holder = request.form.get("holder","").strip()
    card_company = request.form.get("card_company","").strip()
    status = 1 if request.form.get("status") == "1" else 0
    with conn() as c:
        c.execute("""UPDATE bank_accounts SET bank_name=?, account_no=?, holder=?, status=?, card_company=? WHERE id=?""",
                  (bank_name, account_no, holder, status, card_company, bid)); c.commit()
    return redirect(url_for("bank_accounts_list"))

@app.post("/bank-accounts/<int:bid>/toggle")
def bank_accounts_toggle(bid):
    if require_login(): return require_login()
    with conn() as c:
        cur = c.cursor(); cur.execute("SELECT status FROM bank_accounts WHERE id=?", (bid,)); row = cur.fetchone()
        if not row: abort(404)
        cur.execute("UPDATE bank_accounts SET status=? WHERE id=?", (0 if row['status']==1 else 1, bid)); c.commit()
    return redirect(url_for("bank_accounts_list"))

@app.post("/bank-accounts/<int:bid>/delete")
def bank_accounts_delete(bid):
    if require_login(): return require_login()
    with conn() as c: c.execute("DELETE FROM bank_accounts WHERE id=?", (bid,)); c.commit()
    return redirect(url_for("bank_accounts_list"))

@app.get("/export/bank_accounts.csv")
def export_bank_accounts():
    if require_login(): return require_login()
    out = io.StringIO(); w = csv.writer(out)
    w.writerow(["id","bank_name","account_no","holder","card_company","status","created_at"])
    with conn() as c:
        for r in c.execute("SELECT * FROM bank_accounts ORDER BY id DESC"):
            w.writerow([r['id'],r['bank_name'],r['account_no'],r['holder'],r['card_company'],r['status'],r['created_at']])
    mem = io.BytesIO(out.getvalue().encode("utf-8"))
    return send_file(mem, mimetype="text/csv", as_attachment=True, download_name="bank_accounts.csv")

# ----------------------- 银行卡租金 -----------------------
def get_or_create_bank_account(bank_name:str, account_no:str, card_company:str):
    bank_name = (bank_name or "").strip()
    account_no = (account_no or "").strip()
    card_company = (card_company or "").strip()
    if not bank_name or not account_no:
        raise ValueError("bank_name / account_no 必填")
    with conn() as c:
        ex = c.execute("SELECT id, card_company FROM bank_accounts WHERE bank_name=? AND account_no=?", (bank_name, account_no)).fetchone()
        if ex:
            if (not ex["card_company"]) and card_company:
                c.execute("UPDATE bank_accounts SET card_company=? WHERE id=?", (card_company, ex["id"]))
                c.commit()
            return ex["id"]
        c.execute("""INSERT INTO bank_accounts(bank_name, account_no, holder, status, created_at, card_company)
                     VALUES(?,?,?,?,?,?)""", (bank_name, account_no, "", 1, datetime.utcnow().isoformat(), card_company))
        c.commit()
        nid = c.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
        return nid

@app.get("/card-rentals")
def card_rentals_list():
    if require_login(): return require_login()
    with conn() as c:
        rows = c.execute("""
            SELECT cr.*, ba.bank_name, ba.account_no, ba.card_company
            FROM card_rentals cr LEFT JOIN bank_accounts ba ON ba.id = cr.bank_account_id
            ORDER BY cr.id DESC
        """).fetchall()
    return render_template("card_rentals_list.html", rows=rows)

@app.get("/card-rentals/add")
def card_rentals_add_form():
    if require_login(): return require_login()
    return render_template("partials/card_rentals_form.html")

@app.post("/card-rentals/add")
def card_rentals_add():
    if require_login(): return require_login()
    bank_name    = request.form.get("bank_name","").strip()
    account_no   = request.form.get("account_no","").strip()
    card_company = request.form.get("card_company","").strip()
    monthly_rent = float(request.form.get("monthly_rent") or 0)
    start_date   = request.form.get("start_date","")
    end_date     = request.form.get("end_date","")
    note         = request.form.get("note","")
    bank_account_id = get_or_create_bank_account(bank_name, account_no, card_company)
    with conn() as c:
        c.execute("""INSERT INTO card_rentals(bank_account_id, monthly_rent, start_date, end_date, note, status, created_at)
                     VALUES(?,?,?,?,?,1,?)""",
                  (bank_account_id, monthly_rent, start_date, end_date, note, datetime.utcnow().isoformat()))
        c.commit()
    return redirect(url_for("card_rentals_list"))

@app.get("/card-rentals/<int:rid>/edit")
def card_rentals_edit_form(rid):
    if require_login(): return require_login()
    with conn() as c:
        r = c.execute("""
            SELECT cr.*, ba.bank_name, ba.account_no, ba.card_company
            FROM card_rentals cr LEFT JOIN bank_accounts ba ON ba.id = cr.bank_account_id
            WHERE cr.id=?
        """, (rid,)).fetchone()
    if not r: abort(404)
    if request.args.get("partial") == "1":
        return render_template("partials/card_rentals_form.html", r=r)
    return redirect(url_for("card_rentals_list"))

@app.post("/card-rentals/<int:rid>/edit")
def card_rentals_edit(rid):
    if require_login(): return require_login()
    bank_name    = request.form.get("bank_name","").strip()
    account_no   = request.form.get("account_no","").strip()
    card_company = request.form.get("card_company","").strip()
    monthly_rent = float(request.form.get("monthly_rent") or 0)
    start_date   = request.form.get("start_date","")
    end_date     = request.form.get("end_date","")
    note         = request.form.get("note","")
    bank_account_id = get_or_create_bank_account(bank_name, account_no, card_company)
    with conn() as c:
        c.execute("""UPDATE card_rentals
                     SET bank_account_id=?, monthly_rent=?, start_date=?, end_date=?, note=?
                     WHERE id=?""",
                  (bank_account_id, monthly_rent, start_date, end_date, note, rid))
        c.commit()
    return redirect(url_for("card_rentals_list"))

@app.post("/card-rentals/<int:rid>/toggle")
def card_rentals_toggle(rid):
    if require_login(): return require_login()
    with conn() as c:
        cur = c.cursor(); cur.execute("SELECT status FROM card_rentals WHERE id=?", (rid,)); row = cur.fetchone()
        if not row: abort(404)
        cur.execute("UPDATE card_rentals SET status=? WHERE id=?", (0 if row['status']==1 else 1, rid)); c.commit()
    return redirect(url_for("card_rentals_list"))

@app.post("/card-rentals/<int:rid>/delete")
def card_rentals_delete(rid):
    if require_login(): return require_login()
    with conn() as c: c.execute("DELETE FROM card_rentals WHERE id=?", (rid,)); c.commit()
    return redirect(url_for("card_rentals_list"))

@app.get("/export/card_rentals.csv")
def export_card_rentals():
    if require_login(): return require_login()
    out = io.StringIO(); w = csv.writer(out)
    w.writerow(["id","bank_account_id","monthly_rent","start_date","end_date","note","status","created_at"])
    with conn() as c:
        for r in c.execute("SELECT * FROM card_rentals ORDER BY id DESC"):
            w.writerow([r['id'],r['bank_account_id'],r['monthly_rent'],r['start_date'],r['end_date'],r['note'],r['status'],r['created_at']])
    mem = io.BytesIO(out.getvalue().encode("utf-8"))
    return send_file(mem, mimetype="text/csv", as_attachment=True, download_name="card_rentals.csv")

# ----------------------- 出粮记录 -----------------------
@app.get("/salaries")
def salaries_list():
    if require_login(): return require_login()
    with conn() as c:
        rows = c.execute("""
            SELECT s.*, w.name AS worker_name FROM salaries s
            LEFT JOIN workers w ON w.id = s.worker_id ORDER BY s.id DESC
        """).fetchall()
    return render_template("salaries_list.html", rows=rows)

@app.get("/salaries/add")
def salaries_add_form():
    if require_login(): return require_login()
    with conn() as c:
        workers = c.execute("SELECT id, name FROM workers ORDER BY id DESC").fetchall()
    return render_template("partials/salaries_form.html", workers=workers)

@app.post("/salaries/add")
def salaries_add():
    if require_login(): return require_login()
    worker_id = int(request.form.get("worker_id") or 0)
    amount = float(request.form.get("amount") or 0)
    pay_date = request.form.get("pay_date","")
    note = request.form.get("note","")
    with conn() as c:
        c.execute("""INSERT INTO salaries(worker_id, amount, pay_date, note, status, created_at) VALUES(?,?,?,?,1,?)""",
                  (worker_id, amount, pay_date, note, datetime.utcnow().isoformat()))
        c.commit()
    return redirect(url_for("salaries_list"))

@app.get("/salaries/<int:sid>/edit")
def salaries_edit_form(sid):
    if require_login(): return require_login()
    with conn() as c:
        r = c.execute("SELECT * FROM salaries WHERE id=?", (sid,)).fetchone()
        workers = c.execute("SELECT id, name FROM workers ORDER BY id DESC").fetchall()
    if not r: abort(404)
    if request.args.get("partial") == "1":
        return render_template("partials/salaries_form.html", r=r, workers=workers)
    return redirect(url_for("salaries_list"))

@app.post("/salaries/<int:sid>/edit")
def salaries_edit(sid):
    if require_login(): return require_login()
    worker_id = int(request.form.get("worker_id") or 0)
    amount = float(request.form.get("amount") or 0)
    pay_date = request.form.get("pay_date","")
    note = request.form.get("note","")
    with conn() as c:
        c.execute("""UPDATE salaries SET worker_id=?, amount=?, pay_date=?, note=? WHERE id=?""",
                  (worker_id, amount, pay_date, note, sid)); c.commit()
    return redirect(url_for("salaries_list"))

@app.post("/salaries/<int:sid>/toggle")
def salaries_toggle(sid):
    if require_login(): return require_login()
    with conn() as c:
        cur = c.cursor(); cur.execute("SELECT status FROM salaries WHERE id=?", (sid,)); row = cur.fetchone()
        if not row: abort(404)
        cur.execute("UPDATE salaries SET status=? WHERE id=?", (0 if row['status']==1 else 1, sid)); c.commit()
    return redirect(url_for("salaries_list"))

@app.post("/salaries/<int:sid>/delete")
def salaries_delete(sid):
    if require_login(): return require_login()
    with conn() as c: c.execute("DELETE FROM salaries WHERE id=?", (sid,)); c.commit()
    return redirect(url_for("salaries_list"))

@app.get("/export/salaries.csv")
def export_salaries():
    if require_login(): return require_login()
    out = io.StringIO(); w = csv.writer(out)
    w.writerow(["id","worker_id","amount","pay_date","note","status","created_at"])
    with conn() as c:
        for r in c.execute("SELECT * FROM salaries ORDER BY id DESC"):
            w.writerow([r['id'],r['worker_id'],r['amount'],r['pay_date'],r['note'],r['status'],r['created_at']])
    mem = io.BytesIO(out.getvalue().encode("utf-8"))
    return send_file(mem, mimetype="text/csv", as_attachment=True, download_name="salaries.csv")

# ----------------------- 开销记录 -----------------------
@app.get("/expenses")
def expenses_list():
    if require_login(): return require_login()
    with conn() as c:
        rows = c.execute("""
            SELECT e.*, w.name AS worker_name FROM expenses e
            LEFT JOIN workers w ON w.id = e.worker_id ORDER BY e.id DESC
        """).fetchall()
    return render_template("expenses_list.html", rows=rows)

@app.get("/expenses/add")
def expenses_add_form():
    if require_login(): return require_login()
    with conn() as c:
        workers = c.execute("SELECT id, name FROM workers ORDER BY id DESC").fetchall()
    return render_template("partials/expenses_form.html", workers=workers)

@app.post("/expenses/add")
def expenses_add():
    if require_login(): return require_login()
    worker_id = int(request.form.get("worker_id") or 0)
    amount = float(request.form.get("amount") or 0)
    date = request.form.get("date","")
    note = request.form.get("note","")
    with conn() as c:
        c.execute("""INSERT INTO expenses(worker_id, amount, date, note, status, created_at)
                     VALUES(?,?,?,?,1,?)""", (worker_id, amount, date, note, datetime.utcnow().isoformat()))
        c.commit()
    return redirect(url_for("expenses_list"))

@app.get("/expenses/<int:eid>/edit")
def expenses_edit_form(eid):
    if require_login(): return require_login()
    with conn() as c:
        r = c.execute("SELECT * FROM expenses WHERE id=?", (eid,)).fetchone()
        workers = c.execute("SELECT id, name FROM workers ORDER BY id DESC").fetchall()
    if not r: abort(404)
    if request.args.get("partial") == "1":
        return render_template("partials/expenses_form.html", r=r, workers=workers)
    return redirect(url_for("expenses_list"))

@app.post("/expenses/<int:eid>/edit")
def expenses_edit(eid):
    if require_login(): return require_login()
    worker_id = int(request.form.get("worker_id") or 0)
    amount = float(request.form.get("amount") or 0)
    date = request.form.get("date","")
    note = request.form.get("note","")
    with conn() as c:
        c.execute("""UPDATE expenses SET worker_id=?, amount=?, date=?, note=? WHERE id=?""",
                  (worker_id, amount, date, note, eid)); c.commit()
    return redirect(url_for("expenses_list"))

@app.post("/expenses/<int:eid>/toggle")
def expenses_toggle(eid):
    if require_login(): return require_login()
    with conn() as c:
        cur = c.cursor(); cur.execute("SELECT status FROM expenses WHERE id=?", (eid,)); row = cur.fetchone()
        if not row: abort(404)
        cur.execute("UPDATE expenses SET status=? WHERE id=?", (0 if row['status']==1 else 1, eid)); c.commit()
    return redirect(url_for("expenses_list"))

@app.post("/expenses/<int:eid>/delete")
def expenses_delete(eid):
    if require_login(): return require_login()
    with conn() as c: c.execute("DELETE FROM expenses WHERE id=?", (eid,)); c.commit()
    return redirect(url_for("expenses_list"))

@app.get("/export/expenses.csv")
def export_expenses():
    if require_login(): return require_login()
    out = io.StringIO(); w = csv.writer(out)
    w.writerow(["id","worker_id","amount","date","note","status","created_at"])
    with conn() as c:
        for r in c.execute("SELECT * FROM expenses ORDER BY id DESC"):
            w.writerow([r['id'],r['worker_id'],r['amount'],r['date'],r['note'],r['status'],r['created_at']])
    mem = io.BytesIO(out.getvalue().encode("utf-8"))
    return send_file(mem, mimetype="text/csv", as_attachment=True, download_name="expenses.csv")

# ----------------------- 启动 -----------------------
def _bootstrap():
    try:
        init_db()
    except Exception as e:
        print("DB init error:", e)

_bootstrap()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
