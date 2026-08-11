from datetime import date
import calendar
import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor

st.set_page_config(page_title="Pallab's Hostel Ledger", page_icon="🍽️",
                   layout="wide", initial_sidebar_state="collapsed")

def db():
    try:
        return psycopg2.connect(
            st.secrets["SUPABASE_DB_URL"],
            cursor_factory=RealDictCursor,
            sslmode="require",
            connect_timeout=10,
        )
    except Exception as e:
        st.error(f"Supabase connection failed: {type(e).__name__}")
        st.stop()

def init_db():
    con=db()
    try:
        with con.cursor() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS month_settings(
                month TEXT PRIMARY KEY, mess_opening NUMERIC NOT NULL DEFAULT 0,
                canteen_opening NUMERIC NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS meals(
                id BIGSERIAL PRIMARY KEY, date DATE NOT NULL UNIQUE,
                mess_morning BOOLEAN NOT NULL DEFAULT FALSE,
                mess_night BOOLEAN NOT NULL DEFAULT FALSE,
                canteen_morning BOOLEAN NOT NULL DEFAULT FALSE,
                canteen_evening BOOLEAN NOT NULL DEFAULT FALSE,
                note TEXT NOT NULL DEFAULT '');
            CREATE TABLE IF NOT EXISTS deposits(
                id BIGSERIAL PRIMARY KEY, date DATE NOT NULL,
                account TEXT NOT NULL CHECK(account IN ('mess','canteen')),
                amount NUMERIC NOT NULL, note TEXT NOT NULL DEFAULT '',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW());""")
        con.commit()
    finally: con.close()

@st.cache_data(ttl=30)
def get_month(mk):
    con=db()
    try:
        with con.cursor() as c:
            c.execute("SELECT * FROM month_settings WHERE month=%s",(mk,))
            r=c.fetchone()
            if not r:
                c.execute("INSERT INTO month_settings(month) VALUES(%s) ON CONFLICT(month) DO NOTHING",(mk,))
                con.commit()
                c.execute("SELECT * FROM month_settings WHERE month=%s",(mk,))
                r=c.fetchone()
            return r
    finally: con.close()

@st.cache_data(ttl=30)
def get_meals(mk):
    con=db()
    try:
        with con.cursor() as c:
            c.execute("""SELECT * FROM meals
                WHERE date >= %s::date AND date < (%s::date + INTERVAL '1 month')
                ORDER BY date""",(mk+"-01",mk+"-01"))
            return c.fetchall()
    finally: con.close()

@st.cache_data(ttl=30)
def get_deposits(mk):
    con=db()
    try:
        with con.cursor() as c:
            c.execute("""SELECT * FROM deposits
                WHERE date >= %s::date AND date < (%s::date + INTERVAL '1 month')
                ORDER BY date DESC,id DESC""",(mk+"-01",mk+"-01"))
            return c.fetchall()
    finally: con.close()

def clear_cache(): st.cache_data.clear()

def set_opening(mk,mess,canteen):
    con=db()
    try:
        with con.cursor() as c:
            c.execute("""INSERT INTO month_settings(month,mess_opening,canteen_opening)
                VALUES(%s,%s,%s) ON CONFLICT(month) DO UPDATE SET
                mess_opening=EXCLUDED.mess_opening,canteen_opening=EXCLUDED.canteen_opening""",
                (mk,float(mess),float(canteen)))
        con.commit()
    finally: con.close()
    clear_cache()

def save_meal(ds,mm,mn,cm,ce,note):
    con=db()
    try:
        with con.cursor() as c:
            c.execute("""INSERT INTO meals(date,mess_morning,mess_night,canteen_morning,canteen_evening,note)
                VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT(date) DO UPDATE SET
                mess_morning=EXCLUDED.mess_morning,mess_night=EXCLUDED.mess_night,
                canteen_morning=EXCLUDED.canteen_morning,canteen_evening=EXCLUDED.canteen_evening,
                note=EXCLUDED.note""",(ds,mm,mn,cm,ce,note.strip()))
        con.commit()
    finally: con.close()
    clear_cache()

def add_deposit(ds,account,amount,note):
    con=db()
    try:
        with con.cursor() as c:
            c.execute("INSERT INTO deposits(date,account,amount,note) VALUES(%s,%s,%s,%s)",
                      (ds,account,float(amount),note.strip() or "Deposit"))
        con.commit()
    finally: con.close()
    clear_cache()

def delete_deposit(i):
    con=db()
    try:
        with con.cursor() as c: c.execute("DELETE FROM deposits WHERE id=%s",(int(i),))
        con.commit()
    finally: con.close()
    clear_cache()

def mk(y,m): return f"{y:04d}-{m:02d}"
def ml(y,m): return date(y,m,1).strftime("%B %Y")
def money(x): return f"₹{float(x or 0):,.0f}"
def counts(rows):
    o={"mm":0,"mn":0,"cm":0,"ce":0}
    for r in rows:
        o["mm"]+=int(bool(r["mess_morning"])); o["mn"]+=int(bool(r["mess_night"]))
        o["cm"]+=int(bool(r["canteen_morning"])); o["ce"]+=int(bool(r["canteen_evening"]))
    return o

init_db()
today=date.today()
if "view_year" not in st.session_state:
    st.session_state.view_year=today.year; st.session_state.view_month=today.month
y=st.session_state.view_year; mo=st.session_state.view_month; month_key=mk(y,mo)
month=get_month(month_key); meals=get_meals(month_key); deposits=get_deposits(month_key)
meal_map={str(r["date"]):r for r in meals}
cnt=counts(meals)
mess_dep=sum(float(r["amount"]) for r in deposits if r["account"]=="mess")
cant_dep=sum(float(r["amount"]) for r in deposits if r["account"]=="canteen")
mess_bal=float(month["mess_opening"])+mess_dep
cant_bal=float(month["canteen_opening"])+cant_dep

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
html,body,[class*="css"]{font-family:Inter,system-ui,sans-serif}.stApp{background:radial-gradient(circle at 8% 2%,rgba(124,92,255,.14),transparent 27%),radial-gradient(circle at 93% 9%,rgba(33,173,156,.10),transparent 25%),linear-gradient(145deg,#090d14,#111722 55%,#0c1018);color:#edf1fa}
.block-container{max-width:1240px;padding-top:1rem}.hero,.card,.metric{background:rgba(21,27,39,.94);border:1px solid #293243;border-radius:20px;box-shadow:0 14px 38px rgba(0,0,0,.2)}
.hero{padding:24px 26px;background:linear-gradient(135deg,#111827,#1c2234)}.hero-title{font-size:30px;font-weight:900}.hero-sub,.muted{color:#929caf;font-size:12px}.live{color:#6fe0d0;margin-left:7px}
.card{padding:17px}.section-title{font-size:18px;font-weight:900}.balance{font-size:32px;font-weight:900}.purple{color:#9d7cff}.teal{color:#21c1ad}.orange{color:#f2a34b}
.metric{padding:14px;min-height:90px}.metric-label{color:#929caf;font-size:11px}.metric-value{font-size:25px;font-weight:900;margin-top:6px}
.account-mess{background:linear-gradient(135deg,#151b2b,#1a1930)}.account-cant{background:linear-gradient(135deg,#142321,#132a28)}
.chip{display:inline-block;background:#202638;border:1px solid #39445a;padding:8px 11px;border-radius:10px;font-size:12px;margin-right:5px}
.dow{text-align:center;color:#858fa4;font-size:10px;font-weight:800;padding:5px}.day{min-height:88px;background:linear-gradient(145deg,#171e2a,#121822);border:1px solid #2a3343;border-radius:13px;padding:7px}.day.today{outline:2px solid #6657b7}.daynum{font-weight:900}.mark{display:inline-block;margin:6px 3px 0 0;padding:4px 5px;border-radius:6px;background:#282145;color:#c9bdff;font-size:9px;font-weight:900}.mark.c{background:#342719;color:#ffc985}
.summary-row{display:flex;justify-content:space-between;padding:9px 0;border-bottom:1px solid #2a3243;font-size:12px}
div[data-testid="stButton"]>button{border-radius:11px;border:1px solid #30394a;background:#1d2432;color:#edf1fa;font-weight:800}
button[kind="primary"],div[data-testid="stButton"] button[kind="primary"]{background:linear-gradient(135deg,#7659f2,#9d72ff)!important;border:0!important}
input,textarea,[data-baseweb="select"]>div{background:#111722!important;color:#edf1fa!important}
@media(max-width:700px){.block-container{padding:.6rem .5rem!important}.hero{padding:16px;border-radius:18px}.hero-title{font-size:21px}.metric{min-height:75px;padding:10px}.metric-value{font-size:20px}.card{padding:13px}.day{min-height:57px;padding:4px}.daynum{font-size:10px}.mark{font-size:7px;padding:2px}.dow{font-size:8px}}
</style>""",unsafe_allow_html=True)

st.markdown(f"""<div class="hero"><div class="hero-title">🍽️ Pallab's Hostel Ledger</div>
<div class="hero-sub">Shared hostel account · monthly records · fast database tracking <span class="live">● LIVE</span></div></div>""",unsafe_allow_html=True)

a1,a2,a3,a4,a5=st.columns([1,1,1,1,1.15])
with a1:
    if st.button("＋ Meal",use_container_width=True,type="primary"): st.session_state.update(meal_open=True,meal_date=today.isoformat())
with a2:
    if st.button("🍛 Mess Money",use_container_width=True): st.session_state.update(money_open=True,money_account="mess",money_date=today.isoformat())
with a3:
    if st.button("☕ Canteen Money",use_container_width=True): st.session_state.update(money_open=True,money_account="canteen",money_date=today.isoformat())
with a4:
    if st.button("📌 Opening",use_container_width=True): st.session_state.opening_open=True
with a5: st.button("🌙",use_container_width=True)

c1,c2,c3,c4=st.columns([1,1.6,1,1])
with c1:
    if st.button("‹ Previous",use_container_width=True):
        mo-=1
        if mo==0:y,mo=y-1,12
        st.session_state.view_year=y;st.session_state.view_month=mo;st.rerun()
with c2: st.markdown(f"<div style='text-align:center;font-size:21px;font-weight:900;padding:8px'>{ml(y,mo)}</div>",unsafe_allow_html=True)
with c3:
    if st.button("Next ›",use_container_width=True):
        mo+=1
        if mo==13:y,mo=y+1,1
        st.session_state.view_year=y;st.session_state.view_month=mo;st.rerun()
with c4:
    if st.button("Today",use_container_width=True): st.session_state.view_year=today.year;st.session_state.view_month=today.month;st.rerun()

st.markdown(f"""<div class="card"><div style="display:flex;justify-content:space-between;gap:15px;flex-wrap:wrap">
<div><div class="section-title">💰 Opening Balance — {ml(y,mo)}</div><div class="muted">Manual opening balance · included in available balance.</div></div>
<div><span class="chip">🍛 Mess <b class="purple">{money(month["mess_opening"])}</b></span><span class="chip">☕ Canteen <b class="teal">{money(month["canteen_opening"])}</b></span></div></div></div>""",unsafe_allow_html=True)

for col,(lab,val,cl) in zip(st.columns(4),[("🍛 Mess Available",money(mess_bal),"purple"),("☕ Canteen Available",money(cant_bal),"teal"),("🍛 Mess Meals",cnt["mm"]+cnt["mn"],"purple"),("☕ Canteen Counts",cnt["cm"]+cnt["ce"],"orange")]):
    with col: st.markdown(f"<div class='metric'><div class='metric-label'>{lab}</div><div class='metric-value {cl}'>{val}</div></div>",unsafe_allow_html=True)

a,b=st.columns(2)
with a: st.markdown(f"<div class='card account-mess'><h3>🍛 Mess — selected month</h3><div class='balance purple'>{money(mess_bal)}</div><div class='muted'>Opening <b>{money(month['mess_opening'])}</b> + Deposits <b>{money(mess_dep)}</b> · Meals {cnt['mm']+cnt['mn']}</div></div>",unsafe_allow_html=True)
with b: st.markdown(f"<div class='card account-cant'><h3>☕ Canteen — selected month</h3><div class='balance teal'>{money(cant_bal)}</div><div class='muted'>Opening <b>{money(month['canteen_opening'])}</b> + Deposits <b>{money(cant_dep)}</b> · Counts {cnt['cm']+cnt['ce']}</div></div>",unsafe_allow_html=True)

st.markdown("<div class='card' style='margin-top:14px'>",unsafe_allow_html=True)
h1,h2=st.columns([4,1])
with h1: st.markdown(f"<div class='section-title'>📅 Daily Meals</div><div class='muted'>Edit meal counts for {ml(y,mo)}. No meal price is used.</div>",unsafe_allow_html=True)
with h2:
    if st.button("＋ Add Meal",use_container_width=True,type="primary"): st.session_state.update(meal_open=True,meal_date=today.isoformat())
for col,name in zip(st.columns(7),["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]):
    with col: st.markdown(f"<div class='dow'>{name}</div>",unsafe_allow_html=True)
cells=[None]*date(y,mo,1).weekday()+list(range(1,calendar.monthrange(y,mo)[1]+1))
while len(cells)%7:cells.append(None)
for start in range(0,len(cells),7):
    for col,d in zip(st.columns(7),cells[start:start+7]):
        with col:
            if d is None: st.markdown("<div style='height:88px'></div>",unsafe_allow_html=True);continue
            ds=f"{month_key}-{d:02d}";row=meal_map.get(ds);marks=[]
            if row:
                if row["mess_morning"]:marks.append('<span class="mark">MM</span>')
                if row["mess_night"]:marks.append('<span class="mark">MN</span>')
                if row["canteen_morning"]:marks.append('<span class="mark c">CM</span>')
                if row["canteen_evening"]:marks.append('<span class="mark c">CE</span>')
            if not marks:marks=['<span class="muted" style="font-size:9px">Tap to add</span>']
            st.markdown(f"<div class='day{' today' if ds==today.isoformat() else ''}'><div class='daynum'>{d}</div>{''.join(marks)}</div>",unsafe_allow_html=True)
            if st.button("Edit",key=f"edit_{ds}",use_container_width=True):st.session_state.update(meal_open=True,meal_date=ds);st.rerun()
st.markdown("</div>",unsafe_allow_html=True)

m1,m2=st.columns(2)
with m1: st.markdown(f"<div class='card'><div class='section-title'>🍛 Mess — this month</div><div class='summary-row'><span>Morning</span><b>{cnt['mm']}</b></div><div class='summary-row'><span>Night</span><b>{cnt['mn']}</b></div><div class='summary-row'><span>Total meals</span><b>{cnt['mm']+cnt['mn']}</b></div></div>",unsafe_allow_html=True)
with m2: st.markdown(f"<div class='card'><div class='section-title'>☕ Canteen — this month</div><div class='summary-row'><span>Morning</span><b>{cnt['cm']}</b></div><div class='summary-row'><span>Evening</span><b>{cnt['ce']}</b></div><div class='summary-row'><span>Total counts</span><b>{cnt['cm']+cnt['ce']}</b></div></div>",unsafe_allow_html=True)

d1,d2=st.columns([1.2,.8])
with d1:
    st.markdown(f"<div class='card'><div class='section-title'>💳 Deposits — {ml(y,mo)}</div><div class='muted'>Only deposits for the selected month are shown.</div></div>",unsafe_allow_html=True)
    if deposits:
        for r in deposits:
            cc=st.columns([1.15,1,1.4,.8,.35]);cc[0].write(date.fromisoformat(str(r["date"])).strftime("%d %b %Y"));cc[1].write("🍛 Mess" if r["account"]=="mess" else "☕ Canteen");cc[2].write(r["note"] or "Deposit");cc[3].write(f"**{money(r['amount'])}**")
            if cc[4].button("×",key=f"del_{r['id']}"):delete_deposit(r["id"]);st.rerun()
    else: st.info(f"No deposits in {ml(y,mo)}.")
with d2:
    rows=[("🍛 Mess meals",cnt["mm"]+cnt["mn"]),("☕ Canteen counts",cnt["cm"]+cnt["ce"]),("🍛 Mess morning",cnt["mm"]),("🍛 Mess night",cnt["mn"]),("☕ Canteen morning",cnt["cm"]),("☕ Canteen evening",cnt["ce"]),("🍛 Mess opening",money(month["mess_opening"])),("☕ Canteen opening",money(month["canteen_opening"])),("🍛 Mess deposits",money(mess_dep)),("☕ Canteen deposits",money(cant_dep)),("🍛 Mess balance",money(mess_bal)),("☕ Canteen balance",money(cant_bal))]
    st.markdown("<div class='card'><div class='section-title'>⚡ Monthly Summary</div>",unsafe_allow_html=True)
    for l,v in rows:st.markdown(f"<div class='summary-row'><span>{l}</span><b>{v}</b></div>",unsafe_allow_html=True)
    st.markdown("</div>",unsafe_allow_html=True)

if st.session_state.get("opening_open"):
    with st.form("opening_form"):
        st.markdown(f"### 💰 Opening Balance — {ml(y,mo)}");o1,o2=st.columns(2)
        with o1:om=st.number_input("🍛 Mess Opening Balance (₹)",min_value=0.,value=float(month["mess_opening"]),step=1.)
        with o2:oc=st.number_input("☕ Canteen Opening Balance (₹)",min_value=0.,value=float(month["canteen_opening"]),step=1.)
        s1,s2=st.columns(2)
        with s1:
            if st.form_submit_button("Save Opening Balance",type="primary"):set_opening(month_key,om,oc);st.session_state.opening_open=False;st.rerun()
        with s2:
            if st.form_submit_button("Cancel"):st.session_state.opening_open=False;st.rerun()

if st.session_state.get("meal_open"):
    ds=st.session_state.get("meal_date",today.isoformat());existing=meal_map.get(ds)
    with st.form("meal_form"):
        st.markdown(f"### 🍽️ Meals — {ml(y,mo)}");f1,f2=st.columns(2)
        with f1:selected_date=st.date_input("Date",value=date.fromisoformat(ds))
        with f2:note=st.text_input("Note",value=(existing["note"] if existing else ""),placeholder="Optional")
        q1,q2=st.columns(2)
        with q1:cmv=st.checkbox("☕ Canteen Morning",value=bool(existing["canteen_morning"]) if existing else False);cev=st.checkbox("☕ Canteen Evening",value=bool(existing["canteen_evening"]) if existing else False)
        with q2:mmv=st.checkbox("🍛 Mess Morning",value=bool(existing["mess_morning"]) if existing else False);mnv=st.checkbox("🌙 Mess Night",value=bool(existing["mess_night"]) if existing else False)
        b1,b2=st.columns(2)
        with b1:
            if st.form_submit_button("Save Meal",type="primary"):
                if selected_date.strftime("%Y-%m")!=month_key:st.error(f"Meal date must be inside {ml(y,mo)}.")
                else:save_meal(selected_date.isoformat(),mmv,mnv,cmv,cev,note);st.session_state.meal_open=False;st.rerun()
        with b2:
            if st.form_submit_button("Cancel"):st.session_state.meal_open=False;st.rerun()

if st.session_state.get("money_open"):
    acc=st.session_state.get("money_account","mess");ds=st.session_state.get("money_date",today.isoformat())
    with st.form("money_form"):
        st.markdown("### 💳 Monthly Money");f1,f2=st.columns(2)
        with f1:account=st.selectbox("Account",["mess","canteen"],index=0 if acc=="mess" else 1)
        with f2:selected_date=st.date_input("Date",value=date.fromisoformat(ds))
        f3,f4=st.columns(2)
        with f3:amount=st.number_input("Amount (₹)",min_value=0.,step=10.,value=0.)
        with f4:note=st.text_input("Note",placeholder="e.g. August payment")
        st.markdown(f"<div class='card'>This month: <b>{money(mess_dep if account=='mess' else cant_dep)}</b></div>",unsafe_allow_html=True)
        b1,b2=st.columns(2)
        with b1:
            if st.form_submit_button("Add Money",type="primary"):
                if amount<=0:st.error("Enter a valid amount.")
                elif selected_date.strftime("%Y-%m")!=month_key:st.error(f"Deposit date must be inside {ml(y,mo)}.")
                else:add_deposit(selected_date.isoformat(),account,amount,note);st.session_state.money_open=False;st.rerun()
        with b2:
            if st.form_submit_button("Cancel"):st.session_state.money_open=False;st.rerun()

st.markdown("<div style='text-align:center;color:#687287;font-size:10px;padding:22px 0'>Pallab's Hostel Ledger · Shared Supabase database · fast monthly tracker</div>",unsafe_allow_html=True)
