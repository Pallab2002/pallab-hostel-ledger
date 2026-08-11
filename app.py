
from datetime import date
import calendar
import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor

# ============================================================
# Pallab's Hostel Ledger — Ultra Fast + Supabase PostgreSQL
# ============================================================

st.set_page_config(
    page_title="Pallab's Hostel Ledger 1",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# -----------------------------
# Supabase connection
# -----------------------------
@st.cache_resource(show_spinner=False)
def get_connection():
    url = st.secrets.get("SUPABASE_DB_URL")
    if not url:
        raise RuntimeError("SUPABASE_DB_URL is missing from Streamlit Secrets.")
    return psycopg2.connect(
        url,
        cursor_factory=RealDictCursor,
        connect_timeout=8,
        sslmode="require",
        keepalives=1,
        keepalives_idle=30,
        keepalives_interval=10,
        keepalives_count=3,
    )

def db():
    try:
        con = get_connection()
        # Fast health check. Reconnect once if the cached connection went stale.
        if con.closed:
            get_connection.clear()
            con = get_connection()
        return con
    except Exception as e:
        get_connection.clear()
        try:
            return get_connection()
        except Exception as e2:
            st.error(f"Supabase connection failed: {type(e2).__name__}: {e2}")
            st.stop()

@st.cache_resource(show_spinner=False)
def init_db_once():
    con = db()
    with con.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS month_settings (
                month TEXT PRIMARY KEY,
                mess_opening NUMERIC NOT NULL DEFAULT 0,
                canteen_opening NUMERIC NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS meals (
                id BIGSERIAL PRIMARY KEY,
                date DATE NOT NULL UNIQUE,
                mess_morning BOOLEAN NOT NULL DEFAULT FALSE,
                mess_night BOOLEAN NOT NULL DEFAULT FALSE,
                canteen_morning BOOLEAN NOT NULL DEFAULT FALSE,
                canteen_evening BOOLEAN NOT NULL DEFAULT FALSE,
                note TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS deposits (
                id BIGSERIAL PRIMARY KEY,
                date DATE NOT NULL,
                account TEXT NOT NULL CHECK(account IN ('mess','canteen')),
                amount NUMERIC NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_meals_date ON meals(date);
            CREATE INDEX IF NOT EXISTS idx_deposits_date ON deposits(date);
            CREATE INDEX IF NOT EXISTS idx_deposits_account_date ON deposits(account,date);
        """)
    con.commit()
    return True

init_db_once()

# -----------------------------
# Cached reads
# -----------------------------
@st.cache_data(ttl=60, show_spinner=False)
def load_month(month_key):
    con = db()
    with con.cursor() as cur:
        cur.execute("""
            SELECT month, mess_opening, canteen_opening
            FROM month_settings
            WHERE month=%s
        """, (month_key,))
        month = cur.fetchone()
        if not month:
            cur.execute("""
                INSERT INTO month_settings(month)
                VALUES(%s)
                ON CONFLICT(month) DO NOTHING
            """, (month_key,))
            con.commit()
            cur.execute("""
                SELECT month, mess_opening, canteen_opening
                FROM month_settings WHERE month=%s
            """, (month_key,))
            month = cur.fetchone()

        cur.execute("""
            SELECT id, date, mess_morning, mess_night,
                   canteen_morning, canteen_evening, note
            FROM meals
            WHERE date >= %s::date
              AND date < (%s::date + INTERVAL '1 month')
            ORDER BY date
        """, (month_key + "-01", month_key + "-01"))

        meals = cur.fetchall()

        cur.execute("""
            SELECT id, date, account, amount, note
            FROM deposits
            WHERE date >= %s::date
              AND date < (%s::date + INTERVAL '1 month')
            ORDER BY date DESC, id DESC
        """, (month_key + "-01", month_key + "-01"))

        deposits = cur.fetchall()

    return month, meals, deposits

def invalidate():
    load_month.clear()

def notify(message, icon="✅"):
    # Show the notification on the next Streamlit run, including after st.rerun().
    st.session_state["_toast"] = (message, icon)

if "_toast" in st.session_state:
    _msg, _icon = st.session_state.pop("_toast")
    st.toast(_msg, icon=_icon)

# -----------------------------
# Writes
# -----------------------------
def set_opening(month_key, mess, canteen):
    con = db()
    with con.cursor() as cur:
        cur.execute("""
            INSERT INTO month_settings(month, mess_opening, canteen_opening)
            VALUES(%s,%s,%s)
            ON CONFLICT(month) DO UPDATE SET
                mess_opening=EXCLUDED.mess_opening,
                canteen_opening=EXCLUDED.canteen_opening
        """, (month_key, float(mess), float(canteen)))
    con.commit()
    invalidate()
    notify("Opening balance saved successfully.", "💰")

def save_meal(ds, mm, mn, cm, ce, note):
    con = db()
    with con.cursor() as cur:
        cur.execute("""
            INSERT INTO meals(
                date,mess_morning,mess_night,
                canteen_morning,canteen_evening,note
            )
            VALUES(%s,%s,%s,%s,%s,%s)
            ON CONFLICT(date) DO UPDATE SET
                mess_morning=EXCLUDED.mess_morning,
                mess_night=EXCLUDED.mess_night,
                canteen_morning=EXCLUDED.canteen_morning,
                canteen_evening=EXCLUDED.canteen_evening,
                note=EXCLUDED.note
        """, (ds, bool(mm), bool(mn), bool(cm), bool(ce), note.strip()))
    con.commit()
    invalidate()
    notify("Meal saved successfully.", "🍽️")

def add_deposit(ds, account, amount, note):
    con = db()
    with con.cursor() as cur:
        cur.execute("""
            INSERT INTO deposits(date,account,amount,note)
            VALUES(%s,%s,%s,%s)
        """, (ds, account, float(amount), note.strip() or "Deposit"))
    con.commit()
    invalidate()
    notify("Money added successfully.", "💳")

def delete_deposit(deposit_id):
    con = db()
    with con.cursor() as cur:
        cur.execute("DELETE FROM deposits WHERE id=%s", (int(deposit_id),))
    con.commit()
    invalidate()
    notify("Deposit deleted successfully.", "🗑️")

# -----------------------------
# Helpers
# -----------------------------
def month_key(y, m):
    return f"{y:04d}-{m:02d}"

def month_label(y, m):
    return date(y, m, 1).strftime("%B %Y")

def money(x):
    return f"₹{float(x or 0):,.0f}"

def count_meals(rows):
    out = {"mm": 0, "mn": 0, "cm": 0, "ce": 0}
    for r in rows:
        out["mm"] += int(bool(r["mess_morning"]))
        out["mn"] += int(bool(r["mess_night"]))
        out["cm"] += int(bool(r["canteen_morning"]))
        out["ce"] += int(bool(r["canteen_evening"]))
    return out

# -----------------------------
# CSS — no nested/indented HTML blocks
# -----------------------------
st.markdown("""
<style>
:root{
  --bg:#080c14; --panel:#121927; --panel2:#171f2e; --line:#293449;
  --text:#edf2ff; --muted:#8f9bb0; --purple:#9b78ff; --teal:#20c4ae; --orange:#f5a343;
}
html,body,[class*="css"]{
  font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
}
.stApp{
  background:
    radial-gradient(circle at 7% 0%,rgba(124,92,255,.16),transparent 25%),
    radial-gradient(circle at 96% 10%,rgba(32,196,174,.10),transparent 23%),
    linear-gradient(145deg,#080c14,#0e1521 55%,#080c13);
  color:var(--text);
}
.block-container{
  width:100%;max-width:1240px;padding:1rem 1rem 2rem;
  margin:0 auto;box-sizing:border-box
}
[data-testid="stHeader"]{background:transparent}
[data-testid="stToolbar"]{display:none}
.hero{
  background:linear-gradient(135deg,#111827,#1b2233);
  border:1px solid #2a3448;border-radius:24px;padding:22px 25px;
  box-shadow:0 18px 50px rgba(0,0,0,.28);position:relative;overflow:hidden
}
.hero:after{
  content:"";position:absolute;width:240px;height:240px;border-radius:50%;
  right:-90px;top:-145px;background:rgba(255,255,255,.055)
}
.hero-title{font-size:30px;font-weight:900;letter-spacing:-.8px}
.hero-sub{font-size:12px;color:#9ba7bb;margin-top:5px}
.live{display:inline-block;margin-left:6px;padding:3px 8px;border-radius:99px;
background:rgba(32,196,174,.14);color:#6de2d1;font-weight:800}
.card{
  background:rgba(18,25,39,.95);border:1px solid var(--line);border-radius:19px;
  padding:17px;box-shadow:0 12px 34px rgba(0,0,0,.18)
}
.section-title{font-size:18px;font-weight:900}
.muted{color:var(--muted);font-size:12px;line-height:1.5}
.chip{
  display:inline-block;background:#202a3d;border:1px solid #39465e;
  padding:8px 11px;border-radius:10px;color:#e9edfa;font-size:12px;margin:3px
}
.purple{color:var(--purple)} .teal{color:var(--teal)} .orange{color:var(--orange)}
.metric{
  background:#121927;border:1px solid #2a3549;border-radius:16px;padding:14px;
  min-height:92px;box-shadow:0 9px 24px rgba(0,0,0,.15)
}
.metric-label{color:#929db1;font-size:11px}
.metric-value{font-size:25px;font-weight:950;margin-top:6px}
.account-mess{background:linear-gradient(135deg,#151b2b,#1a1931)}
.account-cant{background:linear-gradient(135deg,#132522,#132b29)}
.balance{font-size:32px;font-weight:950;margin-top:6px}
.summary-row{
  display:flex;justify-content:space-between;gap:12px;padding:9px 0;
  border-bottom:1px solid #293345;font-size:12px
}
.summary-row:last-child{border-bottom:0}
.dow{text-align:center;color:#7f8ba0;font-size:10px;font-weight:800;padding:4px;text-transform:uppercase}
.day{
  min-height:88px;background:linear-gradient(145deg,#171f2c,#111824);
  border:1px solid #293447;border-radius:12px;padding:7px
}
.day.today{outline:2px solid #705ce0;outline-offset:1px}
.daynum{font-weight:900;font-size:12px}
.mark{display:inline-block;margin:5px 3px 0 0;padding:4px 5px;border-radius:6px;
background:#282044;color:#cbbfff;font-size:9px;font-weight:900}
.mark.c{background:#35281a;color:#ffc982}
div[data-testid="stButton"]>button{
  border-radius:11px;border:1px solid #303b50;background:#1b2433;color:#edf2ff;
  font-weight:800;min-height:42px
}
div[data-testid="stButton"]>button:hover{border-color:#7866dc;color:#fff}
button[kind="primary"],div[data-testid="stButton"] button[kind="primary"]{
  background:linear-gradient(135deg,#7659f2,#9d72ff)!important;border:0!important;color:#fff!important
}
input,textarea,[data-baseweb="select"]>div{
  background:#101722!important;color:#edf2ff!important;border-color:#303b50!important
}
[data-testid="stForm"]{
  background:#121927;border:1px solid #2b364a;border-radius:18px;padding:15px
}
@media(max-width:700px){
  .block-container{padding:.6rem .45rem 1.3rem!important}
  .hero{border-radius:18px;padding:15px}
  .hero-title{font-size:21px}
  .hero-sub{font-size:10px}
  .metric{min-height:76px;padding:10px;border-radius:13px}
  .metric-label{font-size:9px}.metric-value{font-size:20px}
  .card{padding:12px;border-radius:15px}
  .section-title{font-size:16px}.balance{font-size:27px}
  .day{min-height:60px;padding:4px 3px;border-radius:9px}
  .daynum{font-size:10px}.mark{font-size:7px;padding:2px 3px;margin:3px 1px 0 0}
  div[data-testid="stButton"]>button{min-height:42px;font-size:11px;padding:5px}
}

.dialog-note{color:#8f9bb0;font-size:12px}

/* ---------- Clean compact UI ---------- */
.hero-sub:empty { display:none; }
.muted:empty { display:none; }

[data-testid="stDialog"] [data-testid="stVerticalBlock"] {
    gap: .55rem;
}
[data-testid="stDialog"] .stCaption {
    display:none;
}
[data-testid="stDialog"] label {
    font-size: 12px !important;
    font-weight: 700 !important;
}
[data-testid="stDialog"] input {
    min-height: 42px !important;
}
[data-testid="stDialog"] button {
    min-height: 42px !important;
}

/* Make text/amount fields visually clean and fast to use. */
.clean-input input {
    font-variant-numeric: tabular-nums;
}

/* Hide native number spinners if any remain. */
input[type="number"]::-webkit-inner-spin-button,
input[type="number"]::-webkit-outer-spin-button {
    -webkit-appearance: none;
    margin: 0;
}
input[type="number"] {
    -moz-appearance: textfield;
}

/* ---------- Streamlit layout safety + generous spacing ---------- */
[data-testid="stHorizontalBlock"]{
  width:100%!important;
  max-width:100%!important;
  box-sizing:border-box!important;
  display:flex!important;
  gap:18px!important;
  align-items:stretch!important;
  margin-bottom:18px!important;
}
[data-testid="stHorizontalBlock"] > [data-testid="column"]{
  min-width:0!important;
  max-width:100%!important;
  box-sizing:border-box!important;
  flex:1 1 0!important;
  width:0!important;
}
[data-testid="stHorizontalBlock"] > [data-testid="column"] > div{
  width:100%!important;
  max-width:100%!important;
  min-width:0!important;
  box-sizing:border-box!important;
}
[data-testid="stHorizontalBlock"] button,
[data-testid="stHorizontalBlock"] .card,
[data-testid="stHorizontalBlock"] .metric{
  width:100%!important;
  max-width:100%!important;
  box-sizing:border-box!important;
}
[data-testid="stHorizontalBlock"] + [data-testid="stHorizontalBlock"]{
  margin-top:6px!important;
}

/* Extra separation between major cards and sections. */
.card{margin-bottom:18px!important;}
.metric{margin-bottom:4px!important;}

/* Keep calendar columns compact while still separated. */
.day{width:100%!important;box-sizing:border-box!important;}

/* Mobile: enough gap without making the page horizontally scroll. */
@media(max-width:700px){
  [data-testid="stHorizontalBlock"]{
    gap:8px!important;
    margin-bottom:12px!important;
  }
  .card{margin-bottom:12px!important;}
}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Session / current month
# -----------------------------
today = date.today()

if "view_year" not in st.session_state:
    st.session_state.view_year = today.year
    st.session_state.view_month = today.month

y = st.session_state.view_year
mo = st.session_state.view_month
mk = month_key(y, mo)

# -----------------------------
# Header + actions
# -----------------------------
st.markdown(
    '<div class="hero"><div class="hero-title">🍽️ Pallab\'s Hostel Ledger</div>'
    '<div class="hero-sub"><span class="live">● LIVE</span></div></div>',
    unsafe_allow_html=True
)

a1,a2,a3,a4,a5 = st.columns([1.05,1.05,1.05,1.05,.45], gap="large")
with a1:
    if st.button("＋ Meal", use_container_width=True, type="primary"):
        st.session_state.meal_open = True
        st.session_state.meal_date = today.isoformat()
        st.rerun()
with a2:
    if st.button("🍛 Mess Money", use_container_width=True):
        st.session_state.money_open = True
        st.session_state.money_account = "mess"
        st.session_state.money_date = today.isoformat()
        st.rerun()
with a3:
    if st.button("☕ Canteen Money", use_container_width=True):
        st.session_state.money_open = True
        st.session_state.money_account = "canteen"
        st.session_state.money_date = today.isoformat()
        st.rerun()
with a4:
    if st.button("📌 Opening", use_container_width=True):
        st.session_state.opening_open = True
        st.rerun()
with a5:
    st.button("🌙", use_container_width=True, help="Dark theme")

c1,c2,c3,c4 = st.columns([1,1.25,1,1], gap="medium")
with c1:
    if st.button("‹ Previous", use_container_width=True):
        if mo == 1: y,mo = y-1,12
        else: mo -= 1
        st.session_state.view_year,st.session_state.view_month = y,mo
        st.rerun()
with c2:
    st.markdown(
        f'<div style="text-align:center;font-size:21px;font-weight:900;padding:8px">'
        f'{month_label(y,mo)}</div>', unsafe_allow_html=True
    )
with c3:
    if st.button("Next ›", use_container_width=True):
        if mo == 12: y,mo = y+1,1
        else: mo += 1
        st.session_state.view_year,st.session_state.view_month = y,mo
        st.rerun()
with c4:
    if st.button("Today", use_container_width=True):
        st.session_state.view_year,st.session_state.view_month=today.year,today.month
        st.rerun()

# -----------------------------
# ONE cached read for the entire selected month
# -----------------------------
month, meals, deposits = load_month(mk)

cnt = count_meals(meals)
mess_dep = sum(float(r["amount"]) for r in deposits if r["account"] == "mess")
cant_dep = sum(float(r["amount"]) for r in deposits if r["account"] == "canteen")
mess_bal = float(month["mess_opening"]) + mess_dep
cant_bal = float(month["canteen_opening"]) + cant_dep

# Fast lookup for calendar: no DB calls in the loop
meal_by_date = {str(r["date"]): r for r in meals}

# -----------------------------
# Opening balance
# -----------------------------
opening_html = (
    f'<div class="card" style="margin-top:14px">'
    f'<div style="display:flex;justify-content:space-between;gap:14px;align-items:center;flex-wrap:wrap">'
    f'<div><div class="section-title">💰 Opening Balance — {month_label(y,mo)}</div></div>'
    f'<div><span class="chip">🍛 Mess <b class="purple">{money(month["mess_opening"])}</b></span>'
    f'<span class="chip">☕ Canteen <b class="teal">{money(month["canteen_opening"])}</b></span></div>'
    f'</div></div>'
)
st.markdown(opening_html, unsafe_allow_html=True)

# -----------------------------
# Metrics
# -----------------------------
metrics = [
    ("🍛 Mess Available", money(mess_bal), "purple"),
    ("☕ Canteen Available", money(cant_bal), "teal"),
    ("🍛 Mess Meals", cnt["mm"] + cnt["mn"], "purple"),
    ("☕ Canteen Counts", cnt["cm"] + cnt["ce"], "orange"),
]
cols = st.columns(4, gap="medium")
for col,(label,value,colour) in zip(cols,metrics):
    with col:
        st.markdown(
            f'<div class="metric"><div class="metric-label">{label}</div>'
            f'<div class="metric-value {colour}">{value}</div></div>',
            unsafe_allow_html=True
        )

# -----------------------------
# Account cards
# -----------------------------
a,b = st.columns(2, gap="large")
with a:
    st.markdown(
        f'<div class="card account-mess"><div class="section-title">🍛 Mess — selected month</div>'
        f'<div class="balance purple">{money(mess_bal)}</div>'
        f'<div class="muted">Opening <b>{money(month["mess_opening"])}</b> + '
        f'Deposits <b>{money(mess_dep)}</b> · Meals {cnt["mm"]+cnt["mn"]}</div></div>',
        unsafe_allow_html=True
    )
with b:
    st.markdown(
        f'<div class="card account-cant"><div class="section-title">☕ Canteen — selected month</div>'
        f'<div class="balance teal">{money(cant_bal)}</div>'
        f'<div class="muted">Opening <b>{money(month["canteen_opening"])}</b> + '
        f'Deposits <b>{money(cant_dep)}</b> · Counts {cnt["cm"]+cnt["ce"]}</div></div>',
        unsafe_allow_html=True
    )

# -----------------------------
# Calendar
# -----------------------------
st.markdown(
    f'<div class="card" style="margin-top:14px">'
    f'<div class="section-title">📅 Daily Meals</div>',
    unsafe_allow_html=True
)

week = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
head = st.columns(7, gap="small")
for col,name in zip(head,week):
    with col:
        st.markdown(f'<div class="dow">{name}</div>', unsafe_allow_html=True)

offset = date(y,mo,1).weekday()
days = calendar.monthrange(y,mo)[1]
cells = [None]*offset + list(range(1,days+1))
while len(cells) % 7:
    cells.append(None)

for start in range(0,len(cells),7):
    cols = st.columns(7, gap="small")
    for col,day_num in zip(cols,cells[start:start+7]):
        with col:
            if day_num is None:
                st.markdown('<div style="height:82px"></div>', unsafe_allow_html=True)
                continue
            ds = f"{mk}-{day_num:02d}"
            row = meal_by_date.get(ds)
            marks = []
            if row:
                if row["mess_morning"]: marks.append('<span class="mark">MM</span>')
                if row["mess_night"]: marks.append('<span class="mark">MN</span>')
                if row["canteen_morning"]: marks.append('<span class="mark c">CM</span>')
                if row["canteen_evening"]: marks.append('<span class="mark c">CE</span>')
            if not marks:
                marks = ['<span class="muted" style="font-size:9px">No entry</span>']
            today_class = " today" if ds == today.isoformat() else ""
            st.markdown(
                f'<div class="day{today_class}"><div class="daynum">{day_num}</div>'
                f'{"".join(marks)}</div>',
                unsafe_allow_html=True
            )
            if st.button("Edit", key=f"edit_{ds}", use_container_width=True):
                st.session_state.meal_open = True
                st.session_state.meal_date = ds
                st.rerun()

st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------
# Monthly counts
# -----------------------------
m1,m2 = st.columns(2, gap="large")
with m1:
    st.markdown(
        f'<div class="card"><div class="section-title">🍛 Mess — this month</div>'
        f'<div class="summary-row"><span>Morning</span><b>{cnt["mm"]}</b></div>'
        f'<div class="summary-row"><span>Night</span><b>{cnt["mn"]}</b></div>'
        f'<div class="summary-row"><span>Total meals</span><b>{cnt["mm"]+cnt["mn"]}</b></div></div>',
        unsafe_allow_html=True
    )
with m2:
    st.markdown(
        f'<div class="card"><div class="section-title">☕ Canteen — this month</div>'
        f'<div class="summary-row"><span>Morning</span><b>{cnt["cm"]}</b></div>'
        f'<div class="summary-row"><span>Evening</span><b>{cnt["ce"]}</b></div>'
        f'<div class="summary-row"><span>Total counts</span><b>{cnt["cm"]+cnt["ce"]}</b></div></div>',
        unsafe_allow_html=True
    )

# -----------------------------
# Deposits + summary
# -----------------------------
d1,d2 = st.columns([1.2,.8], gap="large")
with d1:
    st.markdown(
        f'<div class="card"><div class="section-title">💳 Deposits — {month_label(y,mo)}</div>'
        f'</div>',
        unsafe_allow_html=True
    )
    if deposits:
        for r in deposits:
            cc = st.columns([1.15,1,.95,.75,.25])
            with cc[0]:
                st.write(r["date"].strftime("%d %b %Y") if hasattr(r["date"],"strftime") else str(r["date"]))
            with cc[1]:
                st.write("🍛 Mess" if r["account"]=="mess" else "☕ Canteen")
            with cc[2]:
                st.write(r["note"] or "Deposit")
            with cc[3]:
                st.write(f"**{money(r['amount'])}**")
            with cc[4]:
                if st.button("×", key=f"del_{r['id']}"):
                    delete_deposit(r["id"])
                    st.rerun()
    else:
        st.info(f"No deposits in {month_label(y,mo)}.")

with d2:
    summary = [
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
    html = '<div class="card"><div class="section-title">⚡ Monthly Summary</div>'
    for label,value in summary:
        html += f'<div class="summary-row"><span>{label}</span><b>{value}</b></div>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

# -----------------------------
# Popup dialogs
# -----------------------------
# Streamlit dialogs render as real modal popups, so the forms no longer
# appear underneath the page content.

@st.dialog("💰 Opening Balance")
def opening_dialog():
    with st.form("opening_dialog_form"):
        o1,o2 = st.columns(2)
        with o1:
            om_raw = st.text_input(
                "🍛 Mess Opening (₹)",
                value=f"{float(month['mess_opening']):.0f}",
                key="opening_mess_input"
            )
        with o2:
            oc_raw = st.text_input(
                "☕ Canteen Opening (₹)",
                value=f"{float(month['canteen_opening']):.0f}",
                key="opening_canteen_input"
            )

        b1,b2 = st.columns(2)
        with b1:
            save = st.form_submit_button(
                "Save Opening Balance",
                type="primary",
                use_container_width=True
            )
        with b2:
            cancel = st.form_submit_button(
                "Cancel",
                use_container_width=True
            )

        if save:
            try:
                om = float(om_raw.replace(",", "").strip() or "0")
                oc = float(oc_raw.replace(",", "").strip() or "0")
                if om < 0 or oc < 0:
                    raise ValueError
            except ValueError:
                st.error("Enter valid non-negative amounts.")
            else:
                set_opening(mk, om, oc)
                st.session_state.opening_open = False
                st.rerun()

        if cancel:
            st.session_state.opening_open = False
            st.rerun()


@st.dialog("🍽️ Meal Entry")
def meal_dialog():
    ds = st.session_state.get("meal_date", today.isoformat())
    existing = meal_by_date.get(ds)

    with st.form("meal_dialog_form"):
        f1,f2 = st.columns(2)
        with f1:
            selected_date = st.date_input(
                "Date",
                value=date.fromisoformat(ds)
            )
        with f2:
            note = st.text_input(
                "Note",
                value=existing["note"] if existing else "",
                placeholder="Optional"
            )

        q1,q2 = st.columns(2)
        with q1:
            cm = st.checkbox(
                "☕ Canteen Morning",
                value=bool(existing["canteen_morning"]) if existing else False
            )
            ce = st.checkbox(
                "☕ Canteen Evening",
                value=bool(existing["canteen_evening"]) if existing else False
            )
        with q2:
            mm = st.checkbox(
                "🍛 Mess Morning",
                value=bool(existing["mess_morning"]) if existing else False
            )
            mn = st.checkbox(
                "🌙 Mess Night",
                value=bool(existing["mess_night"]) if existing else False
            )

        b1,b2 = st.columns(2)
        with b1:
            save = st.form_submit_button(
                "Save Meal",
                type="primary",
                use_container_width=True
            )
        with b2:
            cancel = st.form_submit_button(
                "Cancel",
                use_container_width=True
            )

        if save:
            if selected_date.strftime("%Y-%m") != mk:
                st.error(f"Meal date must be inside {month_label(y,mo)}.")
            else:
                save_meal(
                    selected_date.isoformat(),
                    mm, mn, cm, ce, note
                )
                st.session_state.meal_open = False
                st.rerun()

        if cancel:
            st.session_state.meal_open = False
            st.rerun()


@st.dialog("💳 Add Money")
def money_dialog():
    acc = st.session_state.get("money_account", "mess")
    ds = st.session_state.get("money_date", today.isoformat())

    with st.form("money_dialog_form"):
        f1,f2 = st.columns(2)
        with f1:
            account = st.selectbox(
                "Account",
                ["mess","canteen"],
                index=0 if acc == "mess" else 1
            )
        with f2:
            selected_date = st.date_input(
                "Date",
                value=date.fromisoformat(ds)
            )

        f3,f4 = st.columns(2)
        with f3:
            amount_raw = st.text_input(
                "Amount (₹)",
                value="",
                placeholder="e.g. 1000",
                key="money_amount_input"
            )
        with f4:
            note = st.text_input(
                "Note",
                placeholder="e.g. August payment"
            )

        b1,b2 = st.columns(2)
        with b1:
            save = st.form_submit_button(
                "Add Money",
                type="primary",
                use_container_width=True
            )
        with b2:
            cancel = st.form_submit_button(
                "Cancel",
                use_container_width=True
            )

        if save:
            try:
                amount = float(amount_raw.replace(",", "").strip() or "0")
            except ValueError:
                amount = 0
            if amount <= 0:
                st.error("Enter a valid amount.")
            elif selected_date.strftime("%Y-%m") != mk:
                st.error(f"Deposit date must be inside {month_label(y,mo)}.")
            else:
                add_deposit(
                    selected_date.isoformat(),
                    account,
                    amount,
                    note
                )
                st.session_state.money_open = False
                st.rerun()

        if cancel:
            st.session_state.money_open = False
            st.rerun()


# Open only the requested popup.
if st.session_state.get("opening_open"):
    opening_dialog()

if st.session_state.get("meal_open"):
    meal_dialog()

if st.session_state.get("money_open"):
    money_dialog()

st.markdown(
    '<div style="text-align:center;color:#687287;font-size:10px;padding:22px 0 4px">'
    "Pallab's Hostel Ledger · Supabase PostgreSQL · Ultra Fast · Popup Forms</div>",
    unsafe_allow_html=True
)
