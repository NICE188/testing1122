# app.py —— 单文件可运行：侧边栏 + 列表页 + 表单弹窗（美化版）+ 启用/停用 + 删除确认 + 导出CSV + 登录鉴权
from flask import (
    Flask, request, render_template, render_template_string,
    redirect, url_for, send_file, session, abort, flash, Response
)
import sqlite3, csv, io, os, logging
from datetime import datetime
from jinja2 import TemplateNotFound, DictLoader
from werkzeug.security import generate_password_hash, check_password_hash

# ============ 环境变量 ============
APP_DB = os.environ.get("APP_DB", "data.db")
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
SECRET_KEY    = os.environ.get("SECRET_KEY", "dev-secret")

app = Flask(__name__)
app.secret_key = SECRET_KEY

# ============ 高质感 CSS（含弹窗美化/动画/骨架屏/滚动锁定） ============
STYLE_CSS = r""":root{
  --bg:#090d14; --bg-2:#0e1524; --surface:#0f1726; --line:#26314a;
  --text:#e9eef7; --muted:#9db0c8;
  --accent:#f2c94c; --accent-2:#ff9f43;
  --ok:#22c55e; --warn:#ef4444;
  --shadow:0 10px 40px rgba(0,0,0,.45);
}
*{box-sizing:border-box}
html,body{height:100%}
body{
  margin:0; color:var(--text);
  font:14px/1.6 Inter,system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;
  background:
    radial-gradient(1200px 700px at 10% -10%, rgba(242,201,76,.10), transparent 60%),
    radial-gradient(1200px 700px at 120% 10%, rgba(255,159,67,.10), transparent 60%),
    linear-gradient(to bottom, var(--bg), var(--bg-2) 1200px);
}
body::before{
  content:""; position:fixed; inset:0; pointer-events:none; z-index:0;
  background-image:
    repeating-linear-gradient(0deg, rgba(255,255,255,.05) 0, rgba(255,255,255,.05) 1px, transparent 1px, transparent 24px),
    repeating-linear-gradient(90deg, rgba(255,255,255,.05) 0, rgba(255,255,255,.05) 1px, transparent 1px, transparent 24px);
  opacity:.14;
  mask-image:
    radial-gradient(1200px 800px at 20% 0%, #000 40%, transparent 100%),
    radial-gradient(1200px 800px at 110% 10%, #000 40%, transparent 100%);
}

/* 顶部栏 */
.topbar{
  position:sticky; top:0; z-index:30;
  display:flex; align-items:center; justify-content:space-between;
  padding:12px 16px; border-bottom:1px solid var(--line);
  background:rgba(11,17,30,.75); backdrop-filter:blur(10px) saturate(140%);
}
.brand{display:flex;align-items:center;gap:10px;font-weight:700;letter-spacing:.3px}
.brand::after{
  content:""; width:7px; height:7px; border-radius:50%;
  background:conic-gradient(from 0deg, var(--accent), var(--accent-2), var(--accent));
  box-shadow:0 0 10px rgba(242,201,76,.9), 0 0 18px rgba(255,159,67,.5);
}
.nav a{margin-left:12px;padding:6px 10px;border:1px solid transparent;border-radius:10px}
.nav a:hover{border-color:var(--line)} .user{opacity:.85;margin-right:8px}

/* 布局：侧栏 + 主区 */
.layout{display:grid;grid-template-columns:260px 1fr;min-height:calc(100vh - 56px);position:relative;z-index:1}
.sidebar{
  position:sticky; top:56px; height:calc(100vh - 56px); padding:14px 10px 16px;
  background:linear-gradient(180deg, rgba(24,28,43,.65), rgba(15,22,38,.8));
  border-right:1px solid var(--line); box-shadow:inset 0 1px 0 rgba(255,255,255,.04);
}
.sidebar::before{
  content:""; position:absolute; inset:0; pointer-events:none; opacity:.22;
  background-image:
    repeating-linear-gradient(0deg, rgba(255,255,255,.06) 0, rgba(255,255,255,.06) 1px, transparent 1px, transparent 22px),
    repeating-linear-gradient(90deg, rgba(255,255,255,.06) 0, rgba(255,255,255,.06) 1px, transparent 1px, transparent 22px);
}
.main{padding:20px}

/* 侧栏折叠 */
body.side-collapsed .layout{grid-template-columns:80px 1fr}
body.side-collapsed .sidebar{padding-left:8px;padding-right:8px}
body.side-collapsed .side-title{display:none}
body.side-collapsed .side-menu a{justify-content:center}
body.side-collapsed .side-menu a .label{display:none}

/* 侧栏菜单 */
.side-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px}
.side-title{font-size:12px;color:var(--muted);letter-spacing:.4px}
.side-toggle{display:inline-flex;align-items:center;gap:6px;border:1px solid var(--line);border-radius:10px;padding:6px 10px;background:#0f1522;cursor:pointer}
.side-menu{display:grid;gap:8px}
.side-menu a{
  position:relative; display:flex; align-items:center; gap:12px;
  padding:12px 12px; border-radius:14px; border:1px solid rgba(255,255,255,.04);
  color:var(--text); text-decoration:none; transition:all .18s ease;
  background:linear-gradient(180deg, rgba(255,255,255,.02), transparent 70%), rgba(14,20,34,.35);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.03);
}
.side-menu a .icon{width:22px;text-align:center;filter:saturate(112%)}
.side-menu a:hover{transform:translateX(2px);border-color:#364466;background:rgba(20,28,46,.55)}
.side-menu a.active{
  border-color:#3e4c72;
  background:linear-gradient(90deg, rgba(242,201,76,.16), rgba(242,201,76,.04) 60%, transparent),
             linear-gradient(180deg, rgba(255,255,255,.03), transparent 70%), rgba(18,26,44,.65);
  box-shadow:inset 0 0 0 1px rgba(242,201,76,.22), 0 8px 18px rgba(0,0,0,.28);
}
.side-menu a.active::before{
  content:""; position:absolute; left:-1px; top:10px; bottom:10px; width:3px; border-radius:3px;
  background:linear-gradient(180deg,var(--accent),var(--accent-2));
  box-shadow:0 0 10px rgba(242,201,76,.65);
}

/* 标题/卡片/面板 */
.page-title{margin:6px 0 16px;font-size:20px;display:flex;align-items:center;gap:8px;text-shadow:0 0 1px rgba(0,0,0,.2)}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px;margin:14px 0}
.card{
  background:linear-gradient(180deg, rgba(255,255,255,.04), transparent 60%), var(--surface);
  border:1px solid rgba(255,255,255,.06); border-radius:18px; padding:16px;
  box-shadow:var(--shadow); backdrop-filter:blur(6px);
}
.card-title{font-size:12px;color:var(--muted)} .card-value{font-size:28px;margin-top:6px}
.panel{
  background:linear-gradient(180deg, rgba(255,255,255,.04), transparent 60%), var(--surface);
  border:1px solid rgba(255,255,255,.06); border-radius:18px; padding:16px; margin-bottom:16px;
  box-shadow:var(--shadow); backdrop-filter:blur(6px);
}

/* 表单与按钮 */
.form{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:12px}
.form input,.form select,.form button, .form textarea{
  height:38px;padding:6px 12px;border-radius:12px;border:1px solid var(--line);
  background:#0f1522;color:var(--text);outline:0;transition:border-color .15s, box-shadow .15s
}
.form textarea{height:auto;min-height:84px;width:100%;resize:vertical}
.form input:focus,.form select:focus,.form textarea:focus{border-color:#4a5a86; box-shadow:0 0 0 3px rgba(74,90,134,.28)}
.form button{background:linear-gradient(180deg,#141b2b,#101626);border-color:#3f4b6b;cursor:pointer}
.form button:hover{box-shadow:0 8px 20px rgba(0,0,0,.35)}
.form .danger{border-color:#7a2a2a;background:linear-gradient(180deg,#2a1416,#1b0f11)}
.btn{
  --bcol: rgba(255,255,255,.06);
  display:inline-flex; align-items:center; gap:8px;
  height:36px; padding:0 14px; border-radius:12px;
  border:1px solid var(--bcol);
  background:linear-gradient(180deg, rgba(255,255,255,.03), transparent 60%), rgba(16,22,38,.5);
  color:var(--text); text-decoration:none; cursor:pointer; user-select:none;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.05), 0 8px 18px rgba(0,0,0,.25);
  transition:transform .15s ease, box-shadow .2s ease, border-color .2s ease, background .2s ease;
}
.btn:hover{transform:translateY(-1px); box-shadow:inset 0 1px 0 rgba(255,255,255,.06), 0 12px 24px rgba(0,0,0,.32)}
.btn .ico{font-size:16px;line-height:1}
.btn-edit{--bcol:#5176ff66; background:radial-gradient(90% 120% at -10% -20%, rgba(81,118,255,.35), transparent 60%), linear-gradient(180deg, rgba(255,255,255,.04), transparent 60%), #13203a; border-color:#4b69ff80}
.btn-delete{--bcol:#d14a4a66; background:radial-gradient(90% 120% at -10% -20%, rgba(209,74,74,.32), transparent 60%), linear-gradient(180deg, rgba(255,255,255,.03), transparent 60%), #2a1416; border-color:#d14a4a99}
.actions{display:flex;gap:10px}

/* 状态开关 */
.toggle{
  display:inline-flex; align-items:center; gap:8px;
  height:30px; padding:0 10px; border-radius:999px; border:1px solid rgba(255,255,255,.08);
  font-weight:600; letter-spacing:.2px; cursor:pointer; user-select:none;
  background:linear-gradient(180deg, rgba(255,255,255,.04), transparent 60%), rgba(18,26,44,.6);
  color:#dbeafe; box-shadow:inset 0 1px 0 rgba(255,255,255,.05), 0 8px 18px rgba(0,0,0,.2);
}
.toggle .dot{width:10px;height:10px;border-radius:50%}
.toggle.on{border-color:#1d4630;background:#0f1f18;color:#bbf7d0}
.toggle.on .dot{background:var(--ok)}
.toggle.off{border-color:#4a1d1d;background:#241112;color:#fecaca}
.toggle.off .dot{background:var(--warn)}

/* 表格 */
.table-wrap{overflow:auto;border:1px solid rgba(255,255,255,.06);border-radius:18px;box-shadow:var(--shadow);backdrop-filter:blur(6px)}
table{border-collapse:separate;border-spacing:0;width:100%}
th{position:sticky; top:0; z-index:1; background:rgba(15,22,38,.9); backdrop-filter:blur(4px); font-weight:600; font-size:12px; color:#bcd0e6; letter-spacing:.2px; border-bottom:1px solid var(--line); text-align:left; padding:12px}
td{padding:12px;border-bottom:1px solid var(--line)}
tbody tr:hover{background:rgba(255,255,255,.03)}
tbody tr:nth-child(even){background:rgba(255,255,255,.015)}

/* ===== 删除确认弹窗（小） —— 美化版 ===== */
.modal-backdrop{
  position:fixed; inset:0; z-index:50; display:none;
  background:radial-gradient(1200px 600px at 15% -10%, rgba(242,201,76,.12), transparent 60%),
             radial-gradient(1200px 600px at 120% 10%, rgba(255,159,67,.12), transparent 60%),
             rgba(5,8,14,.58);
  backdrop-filter:blur(10px) saturate(140%);
}
.modal-backdrop.open{display:flex; align-items:center; justify-content:center; padding:20px}
.modal{
  width:min(420px,100%);
  position:relative; overflow:hidden;
  border-radius:16px; padding:18px;
  background:linear-gradient(180deg, rgba(255,255,255,.06), transparent 60%), var(--surface);
  border:1px solid rgba(255,255,255,.10);
  box-shadow:0 28px 60px rgba(0,0,0,.55);
  opacity:0; transform:translateY(10px) scale(.985);
  transition:opacity .22s ease, transform .22s ease;
}
.modal-backdrop.open .modal{opacity:1; transform:none}
.modal h3{margin:0 0 10px; letter-spacing:.2px}
.modal p{margin:0 0 14px; color:#9db0c8}
.modal-actions{display:flex; gap:10px; justify-content:flex-end}
.btn-ghost{--bcol:rgba(255,255,255,.10); background:rgba(15,22,38,.6)}
.modal::before{
  content:""; position:absolute; inset:0; pointer-events:none;
  border-radius:inherit;
  background:linear-gradient(180deg, rgba(242,201,76,.18), rgba(255,159,67,.10), transparent 60%);
  mask:linear-gradient(#000,#000) content-box, linear-gradient(#000,#000);
  -webkit-mask:linear-gradient(#000,#000) content-box, linear-gradient(#000,#000);
  padding:1px; border-radius:inherit;
  opacity:.18;
}

/* ===== 大弹窗（表单）—— 高级质感 + 动画 + 骨架 ===== */
.big-backdrop{
  position:fixed; inset:0; z-index:55; display:none;
  background:radial-gradient(1600px 700px at 10% -10%, rgba(242,201,76,.10), transparent 60%),
             radial-gradient(1600px 700px at 120% 10%, rgba(80,160,255,.10), transparent 60%),
             rgba(6,10,18,.62);
  backdrop-filter:blur(14px) saturate(145%);
}
.big-backdrop.open{display:flex; align-items:center; justify-content:center; padding:24px}
.big-backdrop.closing{pointer-events:none}

/* 容器卡片 */
.big-modal{
  width:min(920px, 96vw); max-height:90vh; overflow:auto;
  position:relative; border-radius:20px;
  background:linear-gradient(180deg, rgba(255,255,255,.06), transparent 60%), var(--surface);
  border:1px solid rgba(255,255,255,.12);
  box-shadow:
    0 40px 100px rgba(0,0,0,.65),
    0 0 0 1px rgba(255,255,255,.06) inset;
  opacity:0; transform:translateY(14px) scale(.985);
  transition:opacity .24s ease, transform .24s ease;
}
.big-backdrop.open .big-modal{opacity:1; transform:none}
.big-backdrop.closing .big-modal{opacity:0; transform:translateY(6px) scale(.985)}

.big-modal::before{
  content:""; position:absolute; inset:-1px; border-radius:inherit; pointer-events:none;
  background:
    linear-gradient(180deg, rgba(242,201,76,.35), rgba(255,159,67,.18) 40%, rgba(81,118,255,.18) 80%, transparent);
  opacity:.20; filter:blur(0.4px);
}

/* 头部 */
.big-header{
  position:sticky; top:0; z-index:1;
  display:flex; align-items:center; justify-content:space-between;
  padding:14px 16px;
  background:linear-gradient(180deg, rgba(17,24,40,.92), rgba(15,22,38,.82));
  border-bottom:1px solid rgba(255,255,255,.08);
  backdrop-filter:blur(6px);
}
.big-title{font-weight:700; letter-spacing:.2px; display:flex; align-items:center; gap:8px}
.big-title::before{content:"✨"; opacity:.9}
.big-body{padding:16px 16px 18px}

/* 关闭按钮 */
.big-close{
  --bcol:rgba(255,255,255,.12);
  padding:8px 12px; border-radius:12px; border:1px solid var(--bcol);
  background:rgba(15,22,38,.55); color:var(--text); cursor:pointer;
  transition:transform .16s ease, box-shadow .2s ease, border-color .2s ease;
}
.big-close:hover{transform:translateY(-1px); box-shadow:0 10px 22px rgba(0,0,0,.35); border-color:#3f4b6b}

/* 弹窗内表单的间距优化 */
.big-body .form{gap:12px}
.big-body .form input,.big-body .form select,.big-body .form textarea{border-radius:14px}

/* 加载骨架与轻量 spinner（打开弹窗时先展示） */
.skel{display:grid; gap:10px}
.skel .line{
  height:14px; border-radius:10px; overflow:hidden;
  background:linear-gradient(90deg, rgba(255,255,255,.06) 0%, rgba(255,255,255,.12) 50%, rgba(255,255,255,.06) 100%);
  background-size:240px 100%; animation:shimmer 1.25s infinite linear;
}
.skel .line.lg{height:22px; border-radius:12px}
@keyframes shimmer{from{background-position:-240px 0} to{background-position:240px 0}}
.spinner{
  width:18px; height:18px; border-radius:50%;
  border:2px solid rgba(255,255,255,.25); border-top-color:rgba(255,255,255,.8);
  animation:spin .8s linear infinite; display:inline-block; vertical-align:middle;
}
@keyframes spin{to{transform:rotate(360deg)}}

/* 打开弹窗时锁定页面滚动 */
body.modal-open{overflow:hidden}

/* 滚动条 */
*::-webkit-scrollbar{height:10px;width:10px}
*::-webkit-scrollbar-thumb{background:#2a3754;border-radius:10px;border:2px solid #0f1522}
*::-webkit-scrollbar-thumb:hover{background:#35476b}

/* 移动端 */
@media (max-width: 960px){
  .layout{grid-template-columns:1fr}
  .sidebar{position:relative;top:auto;height:auto;border-right:none;border-bottom:1px solid var(--line)}
}
"""

@app.get("/static/style.css")
def static_style():
    return Response(STYLE_CSS, mimetype="text/css")

# ============ 模板（DictLoader，免 templates 目录） ============
TEMPLATES = {
"base.html": """<!doctype html>
<html lang="zh">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{% block title %}后台 · {{ t.app_name }}{% endblock %}</title>
  <link rel="stylesheet" href="{{ url_for('static_style') }}?v=50">
</head>
<body>
  <header class="topbar">
    <div class="brand">
      ⚜️ Admin Panel
      <button id="collapseBtn" class="side-toggle" type="button" title="折叠/展开侧边栏">菜单</button>
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

  <div class="layout">
    <aside class="sidebar">
      <div class="side-head"><div class="side-title">导航</div></div>
      <nav class="side-menu">
        <a href="{{ url_for('dashboard') }}" class="{{ 'active' if request.path == '/' else '' }}"><span class="icon">🏠</span><span class="label">Dashboard</span></a>
        <a href="{{ url_for('workers_list') }}" class="{{ 'active' if request.path.startswith('/workers') else '' }}"><span class="icon">👨‍💼</span><span class="label">工人 / 平台</span></a>
        <a href="{{ url_for('bank_accounts_list') }}" class="{{ 'active' if request.path.startswith('/bank-accounts') else '' }}"><span class="icon">🏦</span><span class="label">银行账户</span></a>
        <a href="{{ url_for('card_rentals_list') }}" class="{{ 'active' if request.path.startswith('/card-rentals') else '' }}"><span class="icon">💳</span><span class="label">银行卡租金</span></a>
        <a href="{{ url_for('salaries_list') }}" class="{{ 'active' if request.path.startswith('/salaries') else '' }}"><span class="icon">💵</span><span class="label">出粮记录</span></a>
        <a href="{{ url_for('expenses_list') }}" class="{{ 'active' if request.path.startswith('/expenses') else '' }}"><span class="icon">💸</span><span class="label">开销记录</span></a>
        <a href="{{ url_for('account_security') }}" class="{{ 'active' if request.path.startswith('/account') or request.path.startswith('/account-security') else '' }}"><span class="icon">🔐</span><span class="label">安全设置</span></a>
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

  <!-- 删除确认弹窗（小） -->
  <div id="confirmBackdrop" class="modal-backdrop" role="dialog" aria-modal="true" aria-hidden="true">
    <div class="modal">
      <h3>确认操作</h3>
      <p id="confirmText">确定要执行该操作吗？</p>
      <div class="modal-actions">
        <button id="confirmCancel" class="btn btn-ghost" type="button">取消</button>
        <button id="confirmOk" class="btn btn-delete" type="button"><span class="ico">🗑️</span> 确认删除</button>
      </div>
    </div>
  </div>

  <!-- 表单弹窗（大） -->
  <div id="bigBackdrop" class="big-backdrop" aria-hidden="true">
    <div class="big-modal">
      <div class="big-header">
        <div class="big-title" id="bigTitle">📄 表单</div>
        <button id="bigClose" class="big-close" type="button">✖</button>
      </div>
      <div id="bigContent"></div>
    </div>
  </div>

  <script>
    // 侧栏折叠状态记忆
    (function(){
      const key='__side_collapsed__';
      try{
        if(localStorage.getItem(key)==='1'){ document.body.classList.add('side-collapsed'); }
        document.getElementById('collapseBtn')?.addEventListener('click',()=>{
          document.body.classList.toggle('side-collapsed');
          localStorage.setItem(key, document.body.classList.contains('side-collapsed')?'1':'0');
        });
      }catch(e){}
    })();

    // 删除确认（拦截 .confirm 表单）
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

    // ===== 表单弹窗（美化 + 交互增强）=====
    (function(){
      const big = document.getElementById('bigBackdrop');
      const content = document.getElementById('bigContent');
      const title = document.getElementById('bigTitle');
      const closeBtn = document.getElementById('bigClose');

      let focusTrapHandlers = [];
      function lockScroll(){ document.body.classList.add('modal-open'); }
      function unlockScroll(){ document.body.classList.remove('modal-open'); }

      function open(){
        big.classList.add('open');
        big.setAttribute('aria-hidden','false');
        lockScroll();
        setTimeout(() => {
          const focusables = big.querySelectorAll('a,button,input,select,textarea,[tabindex]:not([tabindex="-1"])');
          if (focusables.length) focusables[0].focus();
        }, 10);
        const onKey = (e)=>{
          if(e.key==='Tab'){
            const f = big.querySelectorAll('a,button,input,select,textarea,[tabindex]:not([tabindex="-1"])');
            if(!f.length) return;
            const first = f[0], last = f[f.length-1];
            if(e.shiftKey && document.activeElement===first){ last.focus(); e.preventDefault(); }
            else if(!e.shiftKey && document.activeElement===last){ first.focus(); e.preventDefault(); }
          }else if(e.key==='Escape'){ close(); }
        };
        document.addEventListener('keydown', onKey);
        focusTrapHandlers.push(onKey);
      }

      function close(){
        big.classList.add('closing');
        setTimeout(()=>{
          big.classList.remove('open','closing');
          big.setAttribute('aria-hidden','true');
          content.innerHTML = '';
          title.textContent = '📄 表单';
          unlockScroll();
        }, 220);
        focusTrapHandlers.forEach(fn=>document.removeEventListener('keydown', fn));
        focusTrapHandlers = [];
      }

      async function load(url, text){
        title.textContent = text || '📄 表单';
        content.innerHTML = `
          <div class="big-body">
            <div class="skel" aria-busy="true">
              <span class="line lg"></span>
              <span class="line"></span>
              <span class="line"></span>
              <span class="line"></span>
              <span class="line lg"></span>
              <div style="margin-top:6px"><span class="spinner"></span> 正在加载…</div>
            </div>
          </div>`;
        open();
        try{
          const res = await fetch(url + (url.includes('?') ? '&' : '?') + 'partial=1', {headers:{'X-Requested-With':'fetch'}});
          const html = await res.text();
          content.innerHTML = `<div class="big-body">${html}</div>`;
        }catch(e){
          content.innerHTML = '<div class="big-body"><div class="panel"><h3>加载失败</h3><p style="color:#9db0c8">请检查网络或稍后再试。</p></div></div>';
        }
      }

      // 打开弹窗
      document.addEventListener('click', function(ev){
        const el = ev.target.closest('a.js-open-modal, button.js-open-modal');
        if(el){
          ev.preventDefault();
          const href = el.getAttribute('href') || el.dataset.href || '#';
          const tt = el.getAttribute('data-title') || el.title || el.textContent.trim();
          load(href, tt);
        }
      });

      // 弹窗内提交（AJAX 提交后刷新列表）
      big.addEventListener('submit', async function(ev){
        const f = ev.target;
        if(!big.contains(f)) return;
        ev.preventDefault();
        const data = new FormData(f);
        const btn = f.querySelector('button[type="submit"]');
        if(btn){ btn.disabled = True = true; btn.style.opacity = .75; }
        try{
          await fetch(f.action, {method: f.method || 'POST', body: data, headers:{'X-Requested-With':'fetch'}});
          close();
          location.reload();
        }catch(e){
          alert('提交失败，请重试');
        }finally{
          if(btn){ btn.disabled = false; btn.style.opacity = 1; }
        }
      });

      // 关闭
      closeBtn.addEventListener('click', close);
      big.addEventListener('click', (e)=>{ if(e.target===big) close(); });
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
<h1 class="page-title">🏠 Dashboard</h1>
<div class="cards">
  <div class="card"><div class="card-title">{{ t.total_workers }}</div><div class="card-value">{{ total_workers }}</div></div>
  <div class="card"><div class="card-title">{{ t.total_rentals }}</div><div class="card-value">{{ '%.2f'|format(total_rentals) }}</div></div>
  <div class="card"><div class="card-title">{{ t.total_salaries }}</div><div class="card-value">{{ '%.2f'|format(total_salaries) }}</div></div>
  <div class="card"><div class="card-title">{{ t.total_expenses }}</div><div class="card-value">{{ '%.2f'|format(total_expenses) }}</div></div>
</div>
{% endblock %}
""",

# ===== 列表页（新增/编辑按钮 => 弹窗） =====
"workers_list.html": """{% extends "base.html" %}
{% block title %}{{ t.workers }} · {{ t.app_name }}{% endblock %}
{% block content %}
<h1 class="page-title">👨‍💼 {{ t.workers }}</h1>
<div class="panel">
  <div class="actions" style="margin-bottom:12px">
    <a class="btn btn-edit js-open-modal" href="{{ url_for('workers_add_form') }}" data-title="➕ 新增工人"><span class="ico">➕</span> {{ t.add }}</a>
    <a class="btn" href="{{ url_for('export_workers') }}">⤓ {{ t.export_workers }}</a>
  </div>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>ID</th><th>{{ t.name }}</th><th>{{ t.company }}</th><th>{{ t.commission }}</th><th>{{ t.expenses }}</th>
          <th>{{ t.status }}</th><th>{{ t.created_at }}</th><th>{{ t.actions }}</th>
        </tr>
      </thead>
      <tbody>
        {% for r in rows %}
        <tr>
          <td>{{ r.id }}</td>
          <td>{{ r.name }}</td>
          <td>{{ r.company }}</td>
          <td>{{ r.commission }}</td>
          <td>{{ r.expenses }}</td>
          <td class="toggle-wrap">
            <form method="post" action="{{ url_for('workers_toggle', wid=r.id) }}">
              <button class="toggle {{ 'on' if r.status==1 else 'off' }}" type="submit" title="切换状态">
                <span class="dot"></span>{{ t.active if r.status==1 else t.inactive }}
              </button>
            </form>
          </td>
          <td>{{ r.created_at }}</td>
          <td class="actions">
            <a class="btn btn-edit js-open-modal" href="{{ url_for('workers_edit_form', wid=r.id) }}" data-title="✏️ 编辑工人"><span class="ico">✏️</span> {{ t.edit }}</a>
            <form method="post" action="{{ url_for('workers_delete', wid=r.id) }}" class="confirm" data-confirm="{{ t.confirm_delete }}">
              <button class="btn btn-delete" type="submit"><span class="ico">🗑️</span> {{ t.delete }}</button>
            </form>
          </td>
        </tr>
        {% else %}
        <tr><td colspan="8">{{ t.empty }}</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}
""",

"bank_accounts_list.html": """{% extends "base.html" %}
{% block title %}{{ t.bank_accounts }} · {{ t.app_name }}{% endblock %}
{% block content %}
<h1 class="page-title">🏦 {{ t.bank_accounts }}</h1>
<div class="panel">
  <div class="actions" style="margin-bottom:12px">
    <a class="btn btn-edit js-open-modal" href="{{ url_for('bank_accounts_add_form') }}" data-title="➕ 新增银行账户"><span class="ico">➕</span> {{ t.add }}</a>
    <a class="btn" href="{{ url_for('export_bank_accounts') }}">⤓ {{ t.export_bank }}</a>
  </div>
  <div class="table-wrap">
    <table>
      <thead><tr><th>ID</th><th>银行名</th><th>账号</th><th>户名</th><th>{{ t.status }}</th><th>{{ t.created_at }}</th><th>{{ t.actions }}</th></tr></thead>
      <tbody>
        {% for r in rows %}
        <tr>
          <td>{{ r.id }}</td><td>{{ r.bank_name }}</td><td>{{ r.account_no }}</td><td>{{ r.holder }}</td>
          <td class="toggle-wrap">
            <form method="post" action="{{ url_for('bank_accounts_toggle', bid=r.id) }}">
              <button class="toggle {{ 'on' if r.status==1 else 'off' }}" type="submit">
                <span class="dot"></span>{{ t.active if r.status==1 else t.inactive }}
              </button>
            </form>
          </td>
          <td>{{ r.created_at }}</td>
          <td class="actions">
            <a class="btn btn-edit js-open-modal" href="{{ url_for('bank_accounts_edit_form', bid=r.id) }}" data-title="✏️ 编辑银行账户"><span class="ico">✏️</span> {{ t.edit }}</a>
            <form method="post" action="{{ url_for('bank_accounts_delete', bid=r.id) }}" class="confirm" data-confirm="{{ t.confirm_delete }}">
              <button class="btn btn-delete" type="submit"><span class="ico">🗑️</span> {{ t.delete }}</button>
            </form>
          </td>
        </tr>
        {% else %}<tr><td colspan="7">{{ t.empty }}</td></tr>{% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}
""},

"card_rentals_list.html": """{% extends "base.html" %}
{% block title %}{{ t.card_rentals }} · {{ t.app_name }}{% endblock %}
{% block content %}
<h1 class="page-title">💳 {{ t.card_rentals }}</h1>
<div class="panel">
  <div class="actions" style="margin-bottom:12px">
    <a class="btn btn-edit js-open-modal" href="{{ url_for('card_rentals_add_form') }}" data-title="➕ 新增银行卡租金"><span class="ico">➕</span> {{ t.add }}</a>
    <a class="btn" href="{{ url_for('export_card_rentals') }}">⤓ {{ t.export_rentals }}</a>
  </div>
  <div class="table-wrap">
    <table>
      <thead><tr><th>ID</th><th>银行</th><th>账号</th><th>月租金</th><th>开始</th><th>结束</th><th>{{ t.status }}</th><th>备注</th><th>{{ t.created_at }}</th><th>{{ t.actions }}</th></tr></thead>
      <tbody>
        {% for r in rows %}
        <tr>
          <td>{{ r.id }}</td><td>{{ r.bank_name }}</td><td>{{ r.account_no }}</td><td>{{ r.monthly_rent }}</td><td>{{ r.start_date }}</td><td>{{ r.end_date }}</td>
          <td class="toggle-wrap">
            <form method="post" action="{{ url_for('card_rentals_toggle', rid=r.id) }}">
              <button class="toggle {{ 'on' if r.status==1 else 'off' }}" type="submit">
                <span class="dot"></span>{{ t.active if r.status==1 else t.inactive }}
              </button>
            </form>
          </td>
          <td>{{ r.note }}</td><td>{{ r.created_at }}</td>
          <td class="actions">
            <a class="btn btn-edit js-open-modal" href="{{ url_for('card_rentals_edit_form', rid=r.id) }}" data-title="✏️ 编辑银行卡租金"><span class="ico">✏️</span> {{ t.edit }}</a>
            <form method="post" action="{{ url_for('card_rentals_delete', rid=r.id) }}" class="confirm" data-confirm="{{ t.confirm_delete }}">
              <button class="btn btn-delete" type="submit"><span class="ico">🗑️</span> {{ t.delete }}</button>
            </form>
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
<h1 class="page-title">💵 {{ t.salaries }}</h1>
<div class="panel">
  <div class="actions" style="margin-bottom:12px">
    <a class="btn btn-edit js-open-modal" href="{{ url_for('salaries_add_form') }}" data-title="➕ 新增出粮记录"><span class="ico">➕</span> {{ t.add }}</a>
    <a class="btn" href="{{ url_for('export_salaries') }}">⤓ {{ t.export_salaries }}</a>
  </div>
  <div class="table-wrap">
    <table>
      <thead><tr><th>ID</th><th>{{ t.worker }}</th><th>{{ t.salary_amount }}</th><th>{{ t.pay_date }}</th><th>{{ t.status }}</th><th>{{ t.note }}</th><th>{{ t.created_at }}</th><th>{{ t.actions }}</th></tr></thead>
      <tbody>
        {% for r in rows %}
        <tr>
          <td>{{ r.id }}</td><td>{{ r.worker_name }}</td><td>{{ r.amount }}</td><td>{{ r.pay_date }}</td>
          <td class="toggle-wrap">
            <form method="post" action="{{ url_for('salaries_toggle', sid=r.id) }}">
              <button class="toggle {{ 'on' if r.status==1 else 'off' }}" type="submit"><span class="dot"></span>{{ t.active if r.status==1 else t.inactive }}</button>
            </form>
          </td>
          <td>{{ r.note }}</td><td>{{ r.created_at }}</td>
          <td class="actions">
            <a class="btn btn-edit js-open-modal" href="{{ url_for('salaries_edit_form', sid=r.id) }}" data-title="✏️ 编辑出粮记录"><span class="ico">✏️</span> {{ t.edit }}</a>
            <form method="post" action="{{ url_for('salaries_delete', sid=r.id) }}" class="confirm" data-confirm="{{ t.confirm_delete }}">
              <button class="btn btn-delete" type="submit"><span class="ico">🗑️</span> {{ t.delete }}</button>
            </form>
          </td>
        </tr>
        {% else %}<tr><td colspan="8">{{ t.empty }}</td></tr>{% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}
""",

"expenses_list.html": """{% extends "base.html" %}
{% block title %}{{ t.expenses }} · {{ t.app_name }}{% endblock %}
{% block content %}
<h1 class="page-title">💸 {{ t.expenses }}</h1>
<div class="panel">
  <div class="actions" style="margin-bottom:12px">
    <a class="btn btn-edit js-open-modal" href="{{ url_for('expenses_add_form') }}" data-title="➕ 新增开销记录"><span class="ico">➕</span> {{ t.add }}</a>
    <a class="btn" href="{{ url_for('export_expenses') }}">⤓ {{ t.export_expenses }}</a>
  </div>
  <div class="table-wrap">
    <table>
      <thead><tr><th>ID</th><th>{{ t.worker }}</th><th>{{ t.expense_amount }}</th><th>{{ t.date }}</th><th>{{ t.status }}</th><th>{{ t.expenses_note }}</th><th>{{ t.created_at }}</th><th>{{ t.actions }}</th></tr></thead>
      <tbody>
        {% for r in rows %}
        <tr>
          <td>{{ r.id }}</td><td>{{ r.worker_name }}</td><td>{{ r.amount }}</td><td>{{ r.date }}</td>
          <td class="toggle-wrap">
            <form method="post" action="{{ url_for('expenses_toggle', eid=r.id) }}">
              <button class="toggle {{ 'on' if r.status==1 else 'off' }}" type="submit"><span class="dot"></span>{{ t.active if r.status==1 else t.inactive }}</button>
            </form>
          </td>
          <td>{{ r.note }}</td><td>{{ r.created_at }}</td>
          <td class="actions">
            <a class="btn btn-edit js-open-modal" href="{{ url_for('expenses_edit_form', eid=r.id) }}" data-title="✏️ 编辑开销记录"><span class="ico">✏️</span> {{ t.edit }}</a>
            <form method="post" action="{{ url_for('expenses_delete', eid=r.id) }}" class="confirm" data-confirm="{{ t.confirm_delete }}">
              <button class="btn btn-delete" type="submit"><span class="ico">🗑️</span> {{ t.delete }}</button>
            </form>
          </td>
        </tr>
        {% else %}<tr><td colspan="8">{{ t.empty }}</td></tr>{% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}
""",

# ===== 弹窗表单 partials（所有新增/编辑） =====
"partials/workers_form.html": """
<div class="panel">
  <h2 style="margin-top:0">{{ '✏️ 编辑工人' if r else '➕ 新增工人' }}</h2>
  <form class="form" method="post" action="{{ url_for('workers_edit', wid=r.id) if r else url_for('workers_add') }}">
    <input name="name" value="{{ r.name if r else '' }}" placeholder="{{ t.name }}" required>
    <input name="company" value="{{ r.company if r else '' }}" placeholder="{{ t.company }}">
    <input name="commission" type="number" step="0.01" value="{{ r.commission if r else '' }}" placeholder="{{ t.commission }}">
    <input name="expenses" type="number" step="0.01" value="{{ r.expenses if r else '' }}" placeholder="{{ t.expenses }}">
    <button class="btn btn-edit" type="submit"><span class="ico">💾</span> {{ t.save if r else t.add }}</button>
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
    <select name="status">
      <option value="1" {% if r and r.status==1 %}selected{% endif %}>{{ t.active }}</option>
      <option value="0" {% if r and r.status==0 %}selected{% endif %}>{{ t.inactive }}</option>
    </select>
    <button class="btn btn-edit" type="submit"><span class="ico">💾</span> {{ t.save if r else t.add }}</button>
  </form>
</div>
""",

"partials/card_rentals_form.html": """
<div class="panel">
  <h2 style="margin-top:0">{{ '✏️ 编辑银行卡租金' if r else '➕ 新增银行卡租金' }}</h2>
  <form class="form" method="post" action="{{ url_for('card_rentals_edit', rid=r.id) if r else url_for('card_rentals_add') }}">
    <select name="bank_account_id" required>
      {% for b in banks %}
        <option value="{{ b.id }}" {% if r and r.bank_account_id==b.id %}selected{% endif %}>{{ b.bank_name }} - {{ b.account_no }}</option>
      {% endfor %}
    </select>
    <input name="monthly_rent" type="number" step="0.01" value="{{ r.monthly_rent if r else '' }}" placeholder="月租金" required>
    <input name="start_date" type="date" value="{{ r.start_date if r else '' }}" placeholder="开始日期">
    <input name="end_date" type="date" value="{{ r.end_date if r else '' }}" placeholder="结束日期">
    <textarea name="note" placeholder="备注">{{ r.note if r else '' }}</textarea>
    <button class="btn btn-edit" type="submit"><span class="ico">💾</span> {{ t.save if r else t.add }}</button>
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
    <button class="btn btn-edit" type="submit"><span class="ico">💾</span> {{ t.save if r else t.add }}</button>
  </form>
</div>
""",

"partials/expenses_form.html": """
<div class="panel">
  <h2 style="margin-top:0">{{ '✏️ 编辑开销记录' if r else '➕ 新增开销记录' }}</h2>
  <form class="form" method="post" action="{{ url_for('expenses_edit', eid=r.id) if r else url_for('expenses_add') }}">
    <select name="worker_id">
      <option value="">{{ '不关联工人' if lang=='zh' else 'No worker' }}</option>
      {% for w in workers %}
        <option value="{{ w.id }}" {% if r and r.worker_id==w.id %}selected{% endif %}>{{ w.name }}</option>
      {% endfor %}
    </select>
    <input name="amount" type="number" step="0.01" value="{{ r.amount if r else '' }}" placeholder="{{ t.expense_amount }}" required>
    <input name="date" type="date" value="{{ r.date if r else '' }}" placeholder="{{ t.date }}" required>
    <textarea name="note" placeholder="{{ t.expenses_note }}">{{ r.note if r else '' }}</textarea>
    <button class="btn btn-edit" type="submit"><span class="ico">💾</span> {{ t.save if r else t.add }}</button>
  </form>
</div>
""",

# ===== 安全设置：弹窗 partials =====
"partials/account_credentials_form.html": """
<div class="panel">
  <h2 style="margin-top:0">🧑‍💻 修改登录账号/密码</h2>
  <form class="form" method="post" action="{{ url_for('account_credentials_post') }}">
    <input name="username" placeholder="{{ t.username }}" required>
    <input name="password" type="password" placeholder="{{ t.password }}" required>
    <button class="btn btn-edit" type="submit"><span class="ico">💾</span> {{ t.save }}</button>
  </form>
</div>
""",
"partials/account_change_password_form.html": """
<div class="panel">
  <h2 style="margin-top:0">🔑 修改密码</h2>
  <form class="form" method="post" action="{{ url_for('account_change_password_post') }}">
    <input name="old_password" type="password" placeholder="旧密码" required>
    <input name="new_password" type="password" placeholder="新密码" required>
    <button class="btn btn-edit" type="submit"><span class="ico">💾</span> {{ t.save }}</button>
  </form>
</div>
""",
"partials/account_change_username_form.html": """
<div class="panel">
  <h2 style="margin-top:0">🆔 修改用户名</h2>
  <form class="form" method="post" action="{{ url_for('account_change_username_post') }}">
    <input name="new_username" placeholder="新用户名" required>
    <button class="btn btn-edit" type="submit"><span class="ico">💾</span> {{ t.save }}</button>
  </form>
</div>
""",
"partials/account_reset_form.html": """
<div class="panel">
  <h2 style="margin-top:0">🛠 管理员重置密码</h2>
  <form class="form" method="post" action="{{ url_for('account_reset_post') }}">
    <input name="target_username" placeholder="目标用户名" required>
    <input name="new_password" type="password" placeholder="新密码" required>
    <button class="btn btn-delete" type="submit"><span class="ico">💾</span> {{ t.save }}</button>
  </form>
</div>
""",

# ===== 安全中心主页（按钮也走弹窗） =====
"account_security.html": """{% extends "base.html" %}
{% block title %}账号安全 · {{ t.app_name }}{% endblock %}
{% block content %}
<div class="panel">
  <h2>🔐 账号安全</h2>
  <div class="actions">
    <a class="btn js-open-modal" href="{{ url_for('account_credentials') }}" data-title="🧑‍💻 修改登录账号/密码">🧑‍💻 修改登录账号/密码</a>
    <a class="btn js-open-modal" href="{{ url_for('account_change_password') }}" data-title="🔑 修改密码">🔑 修改密码</a>
    <a class="btn js-open-modal" href="{{ url_for('account_change_username') }}" data-title="🆔 修改用户名">🆔 修改用户名</a>
    <a class="btn btn-delete js-open-modal" href="{{ url_for('account_reset') }}" data-title="🛠 管理员重置密码"><span class="ico">🛠</span> 管理员重置密码</a>
  </div>
</div>
{% endblock %}
""",
}
app.jinja_loader = DictLoader(TEMPLATES)

# ============ 日志 & 错误 ============
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

# ============ I18N ============
I18N = {
    "zh": {
        "app_name": "NepWin Ops",
        "login_tip": "请输入管理员账号和密码。",
        "username": "用户名","password": "密码","login": "登录","logout": "退出",
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

# ============ DB 助手 & 初始化 ============
def conn():
    c = sqlite3.connect(APP_DB); c.row_factory = sqlite3.Row; return c

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
        # 迁移旧库：补 status 列
        ensure_column(c, "workers", "status", "INTEGER DEFAULT 1", 1)
        ensure_column(c, "bank_accounts", "status", "INTEGER DEFAULT 1", 1)
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
def inject_globals():
    setattr(request, "lang", get_lang())

@app.context_processor
def inject_t():
    return {"t": T(), "lang": get_lang()}

# ============ Auth ============
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

# ============ Dashboard ============
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

# ============ 安全中心（GET 返回弹窗 partial） ============
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
        cur = c.cursor(); cur.execute("SELECT * FROM users WHERE username=?", (session["user_id"],))
        u = cur.fetchone()
        if not u: abort(403)
        cur.execute("UPDATE users SET username=?, password_hash=? WHERE id=?",
                    (new_username, generate_password_hash(new_password), u["id"]))
        c.commit(); session["user_id"] = new_username
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
    if not old_pw or not new_pw:
        flash("请输入旧密码与新密码", "error"); return redirect(url_for("account_security"))
    with conn() as c:
        cur = c.cursor(); cur.execute("SELECT * FROM users WHERE username=?", (session["user_id"],))
        u = cur.fetchone()
        if not u or not check_password_hash(u["password_hash"], old_pw):
            flash("旧密码不正确", "error"); return redirect(url_for("account_security"))
        cur.execute("UPDATE users SET password_hash=? WHERE id=?", (generate_password_hash(new_pw), u["id"]))
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
        cur = c.cursor(); cur.execute("SELECT * FROM users WHERE username=?", (session["user_id"],))
        u = cur.fetchone()
        if not u: abort(403)
        cur.execute("UPDATE users SET username=? WHERE id=?", (new_username, u["id"]))
        c.commit(); session["user_id"] = new_username
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
    if not target_username or not new_password:
        flash("目标用户名与新密码不能为空", "error"); return redirect(url_for("account_security"))
    with conn() as c:
        cur = c.cursor(); cur.execute("SELECT * FROM users WHERE username=?", (target_username,))
        u = cur.fetchone()
        if not u:
            flash("目标用户不存在", "error"); return redirect(url_for("account_security"))
        cur.execute("UPDATE users SET password_hash=? WHERE id=?", (generate_password_hash(new_password), u["id"]))
        c.commit()
    flash("目标用户密码已重置", "success"); return redirect(url_for("account_security"))

# ============ 工人 / 平台 ============
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
        c.execute("""INSERT INTO workers(name,company,commission,expenses,status,created_at)
                     VALUES(?,?,?,?,1,?)""", (name, company, commission, expenses, datetime.utcnow().isoformat()))
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
        cur = c.cursor()
        cur.execute("SELECT status FROM workers WHERE id=?", (wid,))
        row = cur.fetchone()
        if not row: abort(404)
        newv = 0 if (row["status"]==1) else 1
        cur.execute("UPDATE workers SET status=? WHERE id=?", (newv, wid))
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
    writer.writerow(["id","name","company","commission","expenses","status","created_at"])
    with conn() as c:
        for r in c.execute("SELECT * FROM workers ORDER BY id DESC"):
            writer.writerow([r["id"],r["name"],r["company"],r["commission"],r["expenses"],r["status"],r["created_at"]])
    mem = io.BytesIO(output.getvalue().encode("utf-8"))
    return send_file(mem, mimetype="text/csv", as_attachment=True, download_name="workers.csv")

# ============ 银行账户 ============
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
    status = 1 if request.form.get("status") == "1" else 0
    with conn() as c:
        c.execute("""INSERT INTO bank_accounts(bank_name,account_no,holder,status,created_at)
                     VALUES(?,?,?,?,?)""", (bank_name, account_no, holder, status, datetime.utcnow().isoformat()))
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
    status = 1 if request.form.get("status") == "1" else 0
    with conn() as c:
        c.execute("""UPDATE bank_accounts SET bank_name=?, account_no=?, holder=?, status=? WHERE id=?""",
                  (bank_name, account_no, holder, status, bid))
        c.commit()
    return redirect(url_for("bank_accounts_list"))

@app.post("/bank-accounts/<int:bid>/toggle")
def bank_accounts_toggle(bid):
    if require_login(): return require_login()
    with conn() as c:
        cur = c.cursor()
        cur.execute("SELECT status FROM bank_accounts WHERE id=?", (bid,))
        row = cur.fetchone()
        if not row: abort(404)
        newv = 0 if (row["status"]==1) else 1
        cur.execute("UPDATE bank_accounts SET status=? WHERE id=?", (newv, bid))
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

# ============ 银行卡租金 ============
@app.get("/card-rentals")
def card_rentals_list():
    if require_login(): return require_login()
    with conn() as c:
        cur = c.cursor()
        rows = cur.execute("""SELECT cr.*, ba.bank_name, ba.account_no
                              FROM card_rentals cr LEFT JOIN bank_accounts ba ON ba.id = cr.bank_account_id
                              ORDER BY cr.id DESC""").fetchall()
    return render_template("card_rentals_list.html", rows=rows)

@app.get("/card-rentals/add")
def card_rentals_add_form():
    if require_login(): return require_login()
    with conn() as c:
        banks = c.execute("SELECT id, bank_name, account_no FROM bank_accounts ORDER BY id DESC").fetchall()
    return render_template("partials/card_rentals_form.html", banks=banks)

@app.post("/card-rentals/add")
def card_rentals_add():
    if require_login(): return require_login()
    bank_account_id = int(request.form.get("bank_account_id") or 0)
    monthly_rent = float(request.form.get("monthly_rent") or 0)
    start_date = request.form.get("start_date","")
    end_date = request.form.get("end_date","")
    note = request.form.get("note","")
    with conn() as c:
        c.execute("""INSERT INTO card_rentals(bank_account_id, monthly_rent, start_date, end_date, note, status, created_at)
                     VALUES(?,?,?,?,?,1,?)""", (bank_account_id, monthly_rent, start_date, end_date, note, datetime.utcnow().isoformat()))
        c.commit()
    return redirect(url_for("card_rentals_list"))

@app.get("/card-rentals/<int:rid>/edit")
def card_rentals_edit_form(rid):
    if require_login(): return require_login()
    with conn() as c:
        r = c.execute("SELECT * FROM card_rentals WHERE id=?", (rid,)).fetchone()
        if not r: abort(404)
        banks = c.execute("SELECT id, bank_name, account_no FROM bank_accounts ORDER BY id DESC").fetchall()
    if request.args.get("partial") == "1":
        return render_template("partials/card_rentals_form.html", r=r, banks=banks)
    return redirect(url_for("card_rentals_list"))

@app.post("/card-rentals/<int:rid>/edit")
def card_rentals_edit(rid):
    if require_login(): return require_login()
    bank_account_id = int(request.form.get("bank_account_id") or 0)
    monthly_rent = float(request.form.get("monthly_rent") or 0)
    start_date = request.form.get("start_date","")
    end_date = request.form.get("end_date","")
    note = request.form.get("note","")
    with conn() as c:
        c.execute("""UPDATE card_rentals SET bank_account_id=?, monthly_rent=?, start_date=?, end_date=?, note=? WHERE id=?""",
                  (bank_account_id, monthly_rent, start_date, end_date, note, rid))
        c.commit()
    return redirect(url_for("card_rentals_list"))

@app.post("/card-rentals/<int:rid>/toggle")
def card_rentals_toggle(rid):
    if require_login(): return require_login()
    with conn() as c:
        cur = c.cursor()
        cur.execute("SELECT status FROM card_rentals WHERE id=?", (rid,))
        row = cur.fetchone()
        if not row: abort(404)
        newv = 0 if (row["status"]==1) else 1
        cur.execute("UPDATE card_rentals SET status=? WHERE id=?", (newv, rid))
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
    writer.writerow(["id","bank_account_id","monthly_rent","start_date","end_date","note","status","created_at"])
    with conn() as c:
        for r in c.execute("SELECT * FROM card_rentals ORDER BY id DESC"):
            writer.writerow([r["id"],r["bank_account_id"],r["monthly_rent"],r["start_date"],r["end_date"],r["note"],r["status"],r["created_at"]])
    mem = io.BytesIO(output.getvalue().encode("utf-8"))
    return send_file(mem, mimetype="text/csv", as_attachment=True, download_name="card_rentals.csv")

# ============ 出粮记录 ============
@app.get("/salaries")
def salaries_list():
    if require_login(): return require_login()
    with conn() as c:
        cur = c.cursor()
        rows = cur.execute("""SELECT s.*, w.name AS worker_name
                              FROM salaries s LEFT JOIN workers w ON w.id = s.worker_id
                              ORDER BY s.id DESC""").fetchall()
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
        c.execute("""INSERT INTO salaries(worker_id, amount, pay_date, note, status, created_at)
                     VALUES(?,?,?,?,1,?)""", (worker_id, amount, pay_date, note, datetime.utcnow().isoformat()))
        c.commit()
    return redirect(url_for("salaries_list"))

@app.get("/salaries/<int:sid>/edit")
def salaries_edit_form(sid):
    if require_login(): return require_login()
    with conn() as c:
        r = c.execute("SELECT * FROM salaries WHERE id=?", (sid,)).fetchone()
        if not r: abort(404)
        workers = c.execute("SELECT id, name FROM workers ORDER BY id DESC").fetchall()
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
                  (worker_id, amount, pay_date, note, sid))
        c.commit()
    return redirect(url_for("salaries_list"))

@app.post("/salaries/<int:sid>/toggle")
def salaries_toggle(sid):
    if require_login(): return require_login()
    with conn() as c:
        cur = c.cursor()
        cur.execute("SELECT status FROM salaries WHERE id=?", (sid,))
        row = cur.fetchone()
        if not row: abort(404)
        newv = 0 if (row["status"]==1) else 1
        cur.execute("UPDATE salaries SET status=? WHERE id=?", (newv, sid))
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
    writer.writerow(["id","worker_id","amount","pay_date","note","status","created_at"])
    with conn() as c:
        for r in c.execute("SELECT * FROM salaries ORDER BY id DESC"):
            writer.writerow([r["id"],r["worker_id"],r["amount"],r["pay_date"],r["note"],r["status"],r["created_at"]])
    mem = io.BytesIO(output.getvalue().encode("utf-8"))
    return send_file(mem, mimetype="text/csv", as_attachment=True, download_name="salaries.csv")

# ============ 开销 ============
@app.get("/expenses")
def expenses_list():
    if require_login(): return require_login()
    with conn() as c:
        cur = c.cursor()
        rows = cur.execute("""SELECT e.*, w.name AS worker_name
                              FROM expenses e LEFT JOIN workers w ON w.id = e.worker_id
                              ORDER BY e.id DESC""").fetchall()
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
        if not r: abort(404)
        workers = c.execute("SELECT id, name FROM workers ORDER BY id DESC").fetchall()
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
                  (worker_id, amount, date, note, eid))
        c.commit()
    return redirect(url_for("expenses_list"))

@app.post("/expenses/<int:eid>/toggle")
def expenses_toggle(eid):
    if require_login(): return require_login()
    with conn() as c:
        cur = c.cursor()
        cur.execute("SELECT status FROM expenses WHERE id=?", (eid,))
        row = cur.fetchone()
        if not row: abort(404)
        newv = 0 if (row["status"]==1) else 1
        cur.execute("UPDATE expenses SET status=? WHERE id=?", (newv, eid))
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
    writer.writerow(["id","worker_id","amount","date","note","status","created_at"])
    with conn() as c:
        for r in c.execute("SELECT * FROM expenses ORDER BY id DESC"):
            writer.writerow([r["id"],r["worker_id"],r["amount"],r["date"],r["note"],r["status"],r["created_at"]])
    mem = io.BytesIO(output.getvalue().encode("utf-8"))
    return send_file(mem, mimetype="text/csv", as_attachment=True, download_name="expenses.csv")

# 初始化数据库
init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
