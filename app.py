import sqlite3
from datetime import date, datetime
from pathlib import Path
import calendar
import html as htmlmod

import streamlit as st

# ============================================================
# Pallab's Hostel Ledger — Streamlit + SQLite
# Shared database version of the HTML tracker.
# ============================================================

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "hostel_ledger.db"

st.set_page_config(
    page_title="Pallab's Hostel Ledger",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# -----------------------------
# Database
# -----------------------------
def db():
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    con = db()
    con.executescript("""
    CREATE TABLE IF NOT EXISTS month_settings (
        month TEXT PRIMARY KEY,
        mess_opening REAL NOT NULL DEFAULT 0,
        canteen_opening REAL NOT NULL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS meals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL UNIQUE,
        mess_morning INTEGER NOT NULL DEFAULT 0,
        mess_night INTEGER NOT NULL DEFAULT 0,
        canteen_morning INTEGER NOT NULL DEFAULT 0,
        canteen_evening INTEGER NOT NULL DEFAULT 0,
        note TEXT NOT NULL DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS deposits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        account TEXT NOT NULL CHECK(account IN ('mess','canteen')),
        amount REAL NOT NULL,
        note TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """)
    con.commit()
    con.close()

def ensure_month(month_key: str):
    con = db()
    con.execute(
        "INSERT OR IGNORE INTO month_settings(month) VALUES (?)",
        (month_key,),
    )
    con.commit()
    con.close()

def get_month(month_key):
    ensure_month(month_key)
    con = db()
    row = con.execute(
        "SELECT * FROM month_settings WHERE month=?", (month_key,)
    ).fetchone()
    con.close()
    return row

def set_opening(month_key, mess, canteen):
    con = db()
    con.execute("""
        INSERT INTO month_settings(month, mess_opening, canteen_opening)
        VALUES (?, ?, ?)
        ON CONFLICT(month) DO UPDATE SET
          mess_opening=excluded.mess_opening,
          canteen_opening=excluded.canteen_opening
    """, (month_key, float(mess), float(canteen)))
    con.commit()
    con.close()

def get_meals(month_key):
    con = db()
    rows = con.execute(
        "SELECT * FROM meals WHERE substr(date,1,7)=? ORDER BY date", (month_key,)
    ).fetchall()
    con.close()
    return rows

def get_meal(ds):
    con = db()
    row = con.execute("SELECT * FROM meals WHERE date=?", (ds,)).fetchone()
    con.close()
    return row

def save_meal(ds, mm, mn, cm, ce, note):
    con = db()
    con.execute("""
        INSERT INTO meals(date,mess_morning,mess_night,canteen_morning,canteen_evening,note)
        VALUES(?,?,?,?,?,?)
        ON CONFLICT(date) DO UPDATE SET
          mess_morning=excluded.mess_morning,
          mess_night=excluded.mess_night,
          canteen_morning=excluded.canteen_morning,
          canteen_evening=excluded.canteen_evening,
          note=excluded.note
    """, (ds, int(mm), int(mn), int(cm), int(ce), note.strip()))
    con.commit()
    con.close()

def get_deposits(month_key):
    con = db()
    rows = con.execute("""
        SELECT * FROM deposits
        WHERE substr(date,1,7)=?
        ORDER BY date DESC, id DESC
    """, (month_key,)).fetchall()
    con.close()
    return rows

def add_deposit(ds, account, amount, note):
    con = db()
    con.execute(
        "INSERT INTO deposits(date,account,amount,note) VALUES(?,?,?,?)",
        (ds, account, float(amount), note.strip() or "Deposit"),
    )
    con.commit()
    con.close()

def delete_deposit(deposit_id):
    con = db()
    con.execute("DELETE FROM deposits WHERE id=?", (int(deposit_id),))
    con.commit()
    con.close()

def seed_imported():
    # Seed only once. Existing user edits are never overwritten.
    con = db()
    count = con.execute("SELECT COUNT(*) AS n FROM meals").fetchone()["n"]
    if count == 0:
        imported = IMPORTED_MEALS
        for x in imported:
            con.execute("""
                INSERT OR IGNORE INTO meals
                (date,mess_morning,mess_night,canteen_morning,canteen_evening,note)
                VALUES(?,?,?,?,?,?)
            """, (
                x["date"], int(x["mm"]), int(x["mn"]),
                int(x["cm"]), int(x["ce"]), x.get("note","")
            ))
        con.commit()
    con.close()

# -----------------------------
# Seed data from v20
# -----------------------------
IMPORTED_MEALS = [{'date': '2026-07-01', 'cm': False, 'mm': True, 'ce': False, 'mn': True, 'note': ''}, {'date': '2026-07-02', 'cm': False, 'mm': True, 'ce': False, 'mn': False, 'note': ''}, {'date': '2026-07-03', 'cm': False, 'mm': True, 'ce': False, 'mn': True, 'note': ''}, {'date': '2026-07-04', 'cm': False, 'mm': True, 'ce': False, 'mn': True, 'note': ''}, {'date': '2026-07-05', 'cm': False, 'mm': True, 'ce': False, 'mn': True, 'note': ''}, {'date': '2026-07-06', 'cm': False, 'mm': True, 'ce': False, 'mn': False, 'note': ''}, {'date': '2026-07-07', 'cm': False, 'mm': True, 'ce': False, 'mn': True, 'note': ''}, {'date': '2026-07-08', 'cm': False, 'mm': True, 'ce': False, 'mn': True, 'note': ''}, {'date': '2026-07-09', 'cm': False, 'mm': True, 'ce': False, 'mn': False, 'note': ''}, {'date': '2026-07-10', 'cm': False, 'mm': True, 'ce': False, 'mn': True, 'note': ''}, {'date': '2026-07-11', 'cm': False, 'mm': False, 'ce': False, 'mn': True, 'note': ''}, {'date': '2026-07-12', 'cm': False, 'mm': True, 'ce': False, 'mn': False, 'note': ''}, {'date': '2026-07-13', 'cm': False, 'mm': True, 'ce': False, 'mn': True, 'note': ''}, {'date': '2026-07-14', 'cm': False, 'mm': True, 'ce': False, 'mn': True, 'note': ''}, {'date': '2026-07-15', 'cm': False, 'mm': True, 'ce': False, 'mn': True, 'note': ''}, {'date': '2026-07-16', 'cm': False, 'mm': False, 'ce': False, 'mn': False, 'note': ''}, {'date': '2026-07-17', 'cm': False, 'mm': False, 'ce': False, 'mn': False, 'note': ''}, {'date': '2026-07-18', 'cm': False, 'mm': False, 'ce': False, 'mn': False, 'note': ''}, {'date': '2026-07-19', 'cm': False, 'mm': False, 'ce': False, 'mn': False, 'note': ''}, {'date': '2026-07-20', 'cm': False, 'mm': False, 'ce': False, 'mn': True, 'note': ''}, {'date': '2026-07-21', 'cm': False, 'mm': True, 'ce': False, 'mn': False, 'note': ''}, {'date': '2026-07-22', 'cm': False, 'mm': True, 'ce': False, 'mn': True, 'note': ''}, {'date': '2026-07-23', 'cm': False, 'mm': True, 'ce': False, 'mn': True, 'note': ''}, {'date': '2026-07-24', 'cm': False, 'mm': True, 'ce': False, 'mn': True, 'note': ''}, {'date': '2026-07-25', 'cm': False, 'mm': False, 'ce': False, 'mn': True, 'note': ''}, {'date': '2026-07-26', 'cm': False, 'mm': True, 'ce': False, 'mn': True, 'note': ''}, {'date': '2026-07-27', 'cm': False, 'mm': True, 'ce': False, 'mn': False, 'note': ''}, {'date': '2026-07-28', 'cm': False, 'mm': False, 'ce': False, 'mn': False, 'note': ''}, {'date': '2026-07-29', 'cm': False, 'mm': True, 'ce': False, 'mn': True, 'note': ''}, {'date': '2026-07-30', 'cm': False, 'mm': True, 'ce': False, 'mn': False, 'note': ''}, {'date': '2026-07-31', 'cm': False, 'mm': False, 'ce': False, 'mn': False, 'note': ''}]
init_db()
seed_imported()

# -----------------------------
# Styling
# -----------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

html, body, [class*="css"] {
    font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
.stApp {
    background:
      radial-gradient(circle at 8% 2%, rgba(124,92,255,.14), transparent 27%),
      radial-gradient(circle at 93% 9%, rgba(33,173,156,.10), transparent 25%),
      linear-gradient(145deg,#090d14 0%,#111722 55%,#0c1018 100%);
    color:#edf1fa;
}
.block-container { max-width: 1180px; padding-top: 1.2rem; padding-bottom: 2rem; }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"] { visibility:hidden; height:0; }
section[data-testid="stSidebar"] { background:#0f141e; }

.hero {
    background:linear-gradient(135deg,#111827,#1c2234);
    border:1px solid #2b3445;
    border-radius:25px;
    padding:22px 24px;
    box-shadow:0 20px 55px rgba(0,0,0,.34);
    position:relative;
    overflow:hidden;
}
.hero:after {
    content:""; position:absolute; width:230px; height:230px; border-radius:50%;
    right:-80px; top:-130px; background:rgba(255,255,255,.055);
}
.hero-title { font-size:29px; font-weight:900; letter-spacing:-.8px; margin:0; }
.hero-sub { color:#9da7ba; font-size:12px; margin-top:6px; }
.live {
    display:inline-block; margin-left:7px; padding:3px 8px; border-radius:99px;
    background:rgba(45,205,184,.13); color:#6fe0d0; font-weight:800;
}
.card {
    background:rgba(21,27,39,.94);
    border:1px solid #293243;
    border-radius:20px;
    padding:17px;
    box-shadow:0 14px 38px rgba(0,0,0,.20);
}
.card h3 { margin:0 0 6px; font-size:16px; }
.muted { color:#8f99ad; font-size:12px; line-height:1.55; }
.balance { font-size:32px; font-weight:950; letter-spacing:-1px; margin-top:6px; }
.purple { color:#9d7cff; } .teal { color:#21c1ad; } .orange { color:#f2a34b; }
.metric {
    background:#151b27; border:1px solid #2a3343; border-radius:17px;
    padding:14px; min-height:95px; box-shadow:0 10px 25px rgba(0,0,0,.16);
}
.metric-label { color:#929caf; font-size:11px; }
.metric-value { font-size:25px; font-weight:950; margin-top:6px; }
.account-mess { background:linear-gradient(135deg,#151b2b,#1a1930); }
.account-cant { background:linear-gradient(135deg,#142321,#132a28); }
.chip {
    display:inline-block; background:#202638; border:1px solid #39445a;
    padding:8px 11px; border-radius:10px; color:#e8ebf4; font-size:12px; margin-right:5px;
}
.calendar {
    display:grid; grid-template-columns:repeat(7,1fr); gap:7px;
}
.dow { text-align:center; color:#858fa4; font-size:10px; font-weight:800; text-transform:uppercase; padding:5px; }
.day {
    min-height:88px; background:linear-gradient(145deg,#171e2a,#121822);
    border:1px solid #2a3343; border-radius:13px; padding:7px;
}
.day.today { outline:2px solid #6657b7; outline-offset:1px; }
.daynum { font-weight:900; font-size:12px; }
.mark { display:inline-block; margin:6px 3px 0 0; padding:4px 5px; border-radius:6px;
        background:#282145; color:#c9bdff; font-size:9px; font-weight:900; }
.mark.c { background:#342719; color:#ffc985; }
.summary-row {
    display:flex; justify-content:space-between; gap:12px; padding:9px 0;
    border-bottom:1px solid #2a3243; font-size:12px;
}
.summary-row:last-child { border-bottom:0; }
.section-title { font-size:18px; font-weight:900; margin:0; }
.smallcaps { color:#737d91; font-size:10px; font-weight:800; letter-spacing:.7px; text-transform:uppercase; }
div[data-testid="stButton"] > button {
    border-radius:11px; border:1px solid #30394a; background:#1d2432; color:#edf1fa;
    font-weight:800;
}
div[data-testid="stButton"] > button:hover { border-color:#7866dc; color:#fff; }
button[kind="primary"], div[data-testid="stButton"] button[kind="primary"] {
    background:linear-gradient(135deg,#7659f2,#9d72ff)!important; border:0!important; color:#fff!important;
}
input, textarea, [data-baseweb="select"] > div {
    background:#111722!important; color:#edf1fa!important; border-color:#30394a!important;
}
div[data-testid="stExpander"] {
    background:#151b27; border:1px solid #2a3343; border-radius:15px;
}
hr { border-color:#293243; }
@media(max-width:700px){
 .calendar{gap:4px}.day{min-height:74px;padding:5px}.block-container{padding-left:.7rem;padding-right:.7rem}
}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Helpers
# -----------------------------
def month_key(y, m):
    return f"{y:04d}-{m:02d}"

def month_label(y, m):
    return date(y,m,1).strftime("%B %Y")

def money(x):
    return f"₹{float(x or 0):,.0f}"

def counts(rows):
    out = {"mm":0,"mn":0,"cm":0,"ce":0}
    for r in rows:
        out["mm"] += int(r["mess_morning"])
        out["mn"] += int(r["mess_night"])
        out["cm"] += int(r["canteen_morning"])
        out["ce"] += int(r["canteen_evening"])
    return out

def month_start_dates(y,m):
    first = date(y,m,1)
    return first.weekday()  # Mon=0

# -----------------------------
# Session state
# -----------------------------
today_date = date.today()
if "view_year" not in st.session_state:
    st.session_state.view_year = today_date.year
    st.session_state.view_month = today_date.month

y = st.session_state.view_year
mo = st.session_state.view_month
mk = month_key(y,mo)
ensure_month(mk)

# -----------------------------
# Header
# -----------------------------
st.markdown(f"""
<div class="hero">
  <div class="hero-title">🍽️ Pallab's Hostel Ledger</div>
  <div class="hero-sub">
    Shared hostel account · monthly records · live database tracking
    <span class="live">● LIVE</span>
  </div>
</div>
""", unsafe_allow_html=True)

# Action row
a1,a2,a3,a4,a5 = st.columns([1,1,1,1,1.15])
with a1:
    if st.button("＋ Meal", use_container_width=True, type="primary"):
        st.session_state["meal_open"] = True
        st.session_state["meal_date"] = today_date.isoformat()
with a2:
    if st.button("🍛 Mess Money", use_container_width=True):
        st.session_state["money_open"] = True
        st.session_state["money_account"] = "mess"
        st.session_state["money_date"] = today_date.isoformat()
with a3:
    if st.button("☕ Canteen Money", use_container_width=True):
        st.session_state["money_open"] = True
        st.session_state["money_account"] = "canteen"
        st.session_state["money_date"] = today_date.isoformat()
with a4:
    if st.button("📌 Opening", use_container_width=True):
        st.session_state["opening_open"] = True
with a5:
    # icon only as requested in the HTML version
    if st.button("🌙", help="Dark theme is the default", use_container_width=True):
        st.toast("Dark theme is active.")

# -----------------------------
# Month navigation
# -----------------------------
c1,c2,c3,c4 = st.columns([1,1.6,1,1])
with c1:
    if st.button("‹ Previous", use_container_width=True):
        if mo == 1: y,mo = y-1,12
        else: mo -= 1
        st.session_state.view_year, st.session_state.view_month = y,mo
        st.rerun()
with c2:
    st.markdown(f"<div style='text-align:center;font-size:21px;font-weight:900;padding:8px'>{month_label(y,mo)}</div>", unsafe_allow_html=True)
with c3:
    if st.button("Next ›", use_container_width=True):
        if mo == 12: y,mo = y+1,1
        else: mo += 1
        st.session_state.view_year, st.session_state.view_month = y,mo
        st.rerun()
with c4:
    if st.button("Today", use_container_width=True):
        st.session_state.view_year, st.session_state.view_month = today_date.year,today_date.month
        st.rerun()

month = get_month(mk)
meals = get_meals(mk)
deposits = get_deposits(mk)
cnt = counts(meals)
mess_dep = sum(float(r["amount"]) for r in deposits if r["account"]=="mess")
cant_dep = sum(float(r["amount"]) for r in deposits if r["account"]=="canteen")
mess_bal = float(month["mess_opening"]) + mess_dep
cant_bal = float(month["canteen_opening"]) + cant_dep

# -----------------------------
# Opening balance
# -----------------------------
st.markdown(f"""
<div class="card" style="margin-top:14px;background:linear-gradient(135deg,#171b29,#1b2030)">
  <div style="display:flex;justify-content:space-between;gap:15px;align-items:center;flex-wrap:wrap">
    <div>
      <div class="section-title">💰 Opening Balance — {month_label(y,mo)}</div>
      <div class="muted">Manual opening balance for this month · included in the available balance.</div>
    </div>
    <div>
      <span class="chip">🍛 Mess <b class="purple">{money(month["mess_opening"])}</b></span>
      <span class="chip">☕ Canteen <b class="teal">{money(month["canteen_opening"])}</b></span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# -----------------------------
# Top metrics
# -----------------------------
cols = st.columns(4)
metrics = [
    ("🍛 Mess Available", money(mess_bal), "purple"),
    ("☕ Canteen Available", money(cant_bal), "teal"),
    ("🍛 Mess Meals", cnt["mm"]+cnt["mn"], "purple"),
    ("☕ Canteen Counts", cnt["cm"]+cnt["ce"], "orange"),
]
for col,(lab,val,cl) in zip(cols,metrics):
    with col:
        st.markdown(f"""
        <div class="metric">
          <div class="metric-label">{lab}</div>
          <div class="metric-value {cl}">{val}</div>
        </div>
        """, unsafe_allow_html=True)

# Account cards
a,b = st.columns(2)
with a:
    st.markdown(f"""
    <div class="card account-mess">
      <h3>🍛 Mess — selected month</h3>
      <div class="balance purple">{money(mess_bal)}</div>
      <div class="muted">Opening <b>{money(month["mess_opening"])}</b> + Deposits <b>{money(mess_dep)}</b> · Meals {cnt["mm"]+cnt["mn"]}</div>
    </div>
    """, unsafe_allow_html=True)
with b:
    st.markdown(f"""
    <div class="card account-cant">
      <h3>☕ Canteen — selected month</h3>
      <div class="balance teal">{money(cant_bal)}</div>
      <div class="muted">Opening <b>{money(month["canteen_opening"])}</b> + Deposits <b>{money(cant_dep)}</b> · Counts {cnt["cm"]+cnt["ce"]}</div>
    </div>
    """, unsafe_allow_html=True)

# -----------------------------
# Calendar
# -----------------------------
st.markdown("<div class='card' style='margin-top:14px'>", unsafe_allow_html=True)
h1,h2 = st.columns([4,1])
with h1:
    st.markdown(f"<div class='section-title'>📅 Daily Meals</div><div class='muted'>Click a date to edit meal counts for {month_label(y,mo)}. No meal price is used.</div>", unsafe_allow_html=True)
with h2:
    if st.button("＋ Add Meal", use_container_width=True, type="primary"):
        st.session_state["meal_open"] = True
        st.session_state["meal_date"] = today_date.isoformat()

week = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
grid = st.columns(7)
for col,name in zip(grid,week):
    with col: st.markdown(f"<div class='dow'>{name}</div>", unsafe_allow_html=True)

offset = month_start_dates(y,mo)
days = calendar.monthrange(y,mo)[1]
cells = [None]*offset + list(range(1,days+1))
while len(cells)%7: cells.append(None)

for start in range(0,len(cells),7):
    cols = st.columns(7)
    for col,day_num in zip(cols,cells[start:start+7]):
        with col:
            if day_num is None:
                st.markdown("<div style='height:90px'></div>", unsafe_allow_html=True)
                continue
            ds = f"{mk}-{day_num:02d}"
            row = get_meal(ds)
            marks=[]
            if row:
                if row["mess_morning"]: marks.append('<span class="mark">MM</span>')
                if row["mess_night"]: marks.append('<span class="mark">MN</span>')
                if row["canteen_morning"]: marks.append('<span class="mark c">CM</span>')
                if row["canteen_evening"]: marks.append('<span class="mark c">CE</span>')
            if not marks: marks=['<span class="muted" style="font-size:9px">Tap to add</span>']
            is_today = ds == today_date.isoformat()
            st.markdown(
                f"<div class='day{' today' if is_today else ''}'><div class='daynum'>{day_num}</div>{''.join(marks)}</div>",
                unsafe_allow_html=True
            )
            if st.button("Edit", key=f"edit_{ds}", use_container_width=True):
                st.session_state["meal_open"] = True
                st.session_state["meal_date"] = ds
                st.rerun()
st.markdown("</div>", unsafe_allow_html=True)

# -----------------------------
# Monthly counts + deposits
# -----------------------------
m1,m2 = st.columns(2)
with m1:
    st.markdown(f"""
    <div class="card">
      <div class="section-title">🍛 Mess — this month</div>
      <div class="summary-row"><span>Morning</span><b>{cnt["mm"]}</b></div>
      <div class="summary-row"><span>Night</span><b>{cnt["mn"]}</b></div>
      <div class="summary-row"><span>Total meals</span><b>{cnt["mm"]+cnt["mn"]}</b></div>
    </div>
    """, unsafe_allow_html=True)
with m2:
    st.markdown(f"""
    <div class="card">
      <div class="section-title">☕ Canteen — this month</div>
      <div class="summary-row"><span>Morning</span><b>{cnt["cm"]}</b></div>
      <div class="summary-row"><span>Evening</span><b>{cnt["ce"]}</b></div>
      <div class="summary-row"><span>Total counts</span><b>{cnt["cm"]+cnt["ce"]}</b></div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
d1,d2 = st.columns([1.2,.8])
with d1:
    st.markdown(f"<div class='card'><div class='section-title'>💳 Deposits — {month_label(y,mo)}</div><div class='muted'>Only deposits for the selected month are shown.</div></div>", unsafe_allow_html=True)
    if deposits:
        for r in deposits:
            cc = st.columns([1.15,1,1.4,.8,.35])
            cc[0].write(date.fromisoformat(r["date"]).strftime("%d %b %Y"))
            cc[1].write("🍛 Mess" if r["account"]=="mess" else "☕ Canteen")
            cc[2].write(r["note"] or "Deposit")
            cc[3].write(f"**{money(r['amount'])}**")
            if cc[4].button("×", key=f"del_{r['id']}"):
                delete_deposit(r["id"])
                st.rerun()
    else:
        st.info(f"No deposits in {month_label(y,mo)}.")

with d2:
    rows = [
        ("🍛 Mess meals", cnt["mm"]+cnt["mn"]),
        ("☕ Canteen counts", cnt["cm"]+cnt["ce"]),
        ("🍛 Mess morning", cnt["mm"]),
        ("🍛 Mess night", cnt["mn"]),
        ("☕ Canteen morning", cnt["cm"]),
        ("☕ Canteen evening", cnt["ce"]),
        ("🍛 Mess opening", money(month["mess_opening"])),
        ("☕ Canteen opening", money(month["canteen_opening"])),
        ("🍛 Mess deposits", money(mess_dep)),
        ("☕ Canteen deposits", money(cant_dep)),
        ("🍛 Mess balance", money(mess_bal)),
        ("☕ Canteen balance", money(cant_bal)),
    ]
    st.markdown("<div class='card'><div class='section-title'>⚡ Monthly Summary</div>", unsafe_allow_html=True)
    for label,val in rows:
        st.markdown(f"<div class='summary-row'><span>{label}</span><b>{val}</b></div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# -----------------------------
# Dialog-like forms
# -----------------------------
if st.session_state.get("opening_open"):
    with st.form("opening_form"):
        st.markdown(f"### 💰 Opening Balance — {month_label(y,mo)}")
        st.caption("Enter the opening balance manually. There is no automatic previous-month option.")
        o1,o2=st.columns(2)
        with o1:
            om=st.number_input("🍛 Mess Opening Balance (₹)", min_value=0.0, value=float(month["mess_opening"]), step=1.0)
        with o2:
            oc=st.number_input("☕ Canteen Opening Balance (₹)", min_value=0.0, value=float(month["canteen_opening"]), step=1.0)
        s1,s2=st.columns(2)
        with s1:
            if st.form_submit_button("Save Opening Balance", type="primary"):
                set_opening(mk,om,oc)
                st.session_state["opening_open"]=False
                st.rerun()
        with s2:
            if st.form_submit_button("Cancel"):
                st.session_state["opening_open"]=False
                st.rerun()

if st.session_state.get("meal_open"):
    ds = st.session_state.get("meal_date", today_date.isoformat())
    existing = get_meal(ds)
    # New meal => all unchecked. Editing an existing calendar date => load saved state.
    default_mm = bool(existing["mess_morning"]) if existing else False
    default_mn = bool(existing["mess_night"]) if existing else False
    default_cm = bool(existing["canteen_morning"]) if existing else False
    default_ce = bool(existing["canteen_evening"]) if existing else False
    with st.form("meal_form"):
        st.markdown(f"### 🍽️ Meals — {month_label(y,mo)}")
        f1,f2=st.columns(2)
        with f1:
            selected_date=st.date_input("Date", value=date.fromisoformat(ds))
        with f2:
            note=st.text_input("Note", value=(existing["note"] if existing else ""), placeholder="Optional")
        st.caption("For a new meal entry, all choices start unchecked.")
        q1,q2=st.columns(2)
        with q1:
            cm=st.checkbox("☕ Canteen Morning", value=default_cm)
            ce=st.checkbox("☕ Canteen Evening", value=default_ce)
        with q2:
            mm=st.checkbox("🍛 Mess Morning", value=default_mm)
            mn=st.checkbox("🌙 Mess Night", value=default_mn)
        b1,b2=st.columns(2)
        with b1:
            if st.form_submit_button("Save Meal", type="primary"):
                if selected_date.strftime("%Y-%m") != mk:
                    st.error(f"Meal date must be inside {month_label(y,mo)}.")
                else:
                    save_meal(selected_date.isoformat(),mm,mn,cm,ce,note)
                    st.session_state["meal_open"]=False
                    st.rerun()
        with b2:
            if st.form_submit_button("Cancel"):
                st.session_state["meal_open"]=False
                st.rerun()

if st.session_state.get("money_open"):
    acc=st.session_state.get("money_account","mess")
    ds=st.session_state.get("money_date",today_date.isoformat())
    with st.form("money_form"):
        st.markdown("### 💳 Monthly Money")
        st.caption("New deposit entries start with today's live date and belong only to the selected month.")
        f1,f2=st.columns(2)
        with f1:
            account=st.selectbox("Account",["mess","canteen"],index=0 if acc=="mess" else 1)
        with f2:
            selected_date=st.date_input("Date",value=date.fromisoformat(ds))
        f3,f4=st.columns(2)
        with f3:
            amount=st.number_input("Amount (₹)",min_value=0.0,step=10.0,value=0.0)
        with f4:
            note=st.text_input("Note",placeholder="e.g. August payment")
        st.markdown(f"<div class='card'>This month: <b>{money((mess_dep if account=='mess' else cant_dep))}</b></div>",unsafe_allow_html=True)
        b1,b2=st.columns(2)
        with b1:
            if st.form_submit_button("Add Money",type="primary"):
                if amount<=0:
                    st.error("Enter a valid amount.")
                elif selected_date.strftime("%Y-%m")!=mk:
                    st.error(f"Deposit date must be inside {month_label(y,mo)}.")
                else:
                    add_deposit(selected_date.isoformat(),account,amount,note)
                    st.session_state["money_open"]=False
                    st.rerun()
        with b2:
            if st.form_submit_button("Cancel"):
                st.session_state["money_open"]=False
                st.rerun()

st.markdown("<div style='text-align:center;color:#687287;font-size:10px;padding:22px 0 4px'>Pallab's Hostel Ledger · Shared SQLite database · meal counts only</div>", unsafe_allow_html=True)
