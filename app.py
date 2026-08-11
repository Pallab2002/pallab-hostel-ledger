from datetime import date
import calendar
import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor

# ============================================================
# Pallab's Hostel Ledger — ULTRA FAST
# Streamlit + Supabase PostgreSQL
#
# Performance design:
# - One cached DB connection per Streamlit process
# - No CREATE TABLE on every rerun
# - One query for monthly meals
# - One query for monthly deposits
# - No DB query inside calendar loop
# - Read results cached briefly
# - Cache invalidated after writes
# ============================================================

st.set_page_config(
    page_title="Pallab's Hostel Ledger",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ------------------------------------------------------------
# DATABASE
# ------------------------------------------------------------

@st.cache_resource
def get_db():
    """Create and reuse one PostgreSQL connection."""
    return psycopg2.connect(
        st.secrets["SUPABASE_DB_URL"],
        cursor_factory=RealDictCursor,
        sslmode="require",
        connect_timeout=8,
        keepalives=1,
        keepalives_idle=30,
        keepalives_interval=10,
        keepalives_count=3,
    )

def db():
    con = get_db()

    # Reconnect automatically if the cached connection went stale.
    try:
        if con.closed:
            get_db.clear()
            con = get_db()
        else:
            with con.cursor() as cur:
                cur.execute("SELECT 1")
    except Exception:
        try:
            con.close()
        except Exception:
            pass
        get_db.clear()
        con = get_db()

    return con


@st.cache_resource
def init_db_once():
    """Run table/index setup only once per app process."""
    con = get_db()

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

            CREATE INDEX IF NOT EXISTS idx_meals_date
                ON meals(date);

            CREATE INDEX IF NOT EXISTS idx_deposits_date
                ON deposits(date);

            CREATE INDEX IF NOT EXISTS idx_deposits_account_date
                ON deposits(account, date);
        """)

    con.commit()
    return True


# Run only once.
init_db_once()


# ------------------------------------------------------------
# CACHE CONTROL
# ------------------------------------------------------------

def invalidate_data():
    get_month.clear()
    get_meals.clear()
    get_deposits.clear()


# ------------------------------------------------------------
# READ FUNCTIONS
# ------------------------------------------------------------

@st.cache_data(ttl=20, show_spinner=False)
def get_month(month_key):
    con = db()

    with con.cursor() as cur:
        cur.execute(
            "SELECT * FROM month_settings WHERE month=%s",
            (month_key,),
        )
        row = cur.fetchone()

        if row is None:
            cur.execute(
                """
                INSERT INTO month_settings(month)
                VALUES (%s)
                ON CONFLICT(month) DO NOTHING
                """,
                (month_key,),
            )
            con.commit()

            cur.execute(
                "SELECT * FROM month_settings WHERE month=%s",
                (month_key,),
            )
            row = cur.fetchone()

    return row


@st.cache_data(ttl=20, show_spinner=False)
def get_meals(month_key):
    con = db()

    with con.cursor() as cur:
        cur.execute(
            """
            SELECT
                date,
                mess_morning,
                mess_night,
                canteen_morning,
                canteen_evening,
                note
            FROM meals
            WHERE date >= %s::date
              AND date < (%s::date + INTERVAL '1 month')
            ORDER BY date
            """,
            (month_key + "-01", month_key + "-01"),
        )
        return cur.fetchall()


@st.cache_data(ttl=20, show_spinner=False)
def get_deposits(month_key):
    con = db()

    with con.cursor() as cur:
        cur.execute(
            """
            SELECT id, date, account, amount, note
            FROM deposits
            WHERE date >= %s::date
              AND date < (%s::date + INTERVAL '1 month')
            ORDER BY date DESC, id DESC
            """,
            (month_key + "-01", month_key + "-01"),
        )
        return cur.fetchall()


# ------------------------------------------------------------
# WRITE FUNCTIONS
# ------------------------------------------------------------

def set_opening(month_key, mess, canteen):
    con = db()

    with con.cursor() as cur:
        cur.execute(
            """
            INSERT INTO month_settings(
                month, mess_opening, canteen_opening
            )
            VALUES (%s,%s,%s)
            ON CONFLICT(month) DO UPDATE SET
                mess_opening=EXCLUDED.mess_opening,
                canteen_opening=EXCLUDED.canteen_opening
            """,
            (month_key, float(mess), float(canteen)),
        )

    con.commit()
    invalidate_data()


def save_meal(ds, mm, mn, cm, ce, note):
    con = db()

    with con.cursor() as cur:
        cur.execute(
            """
            INSERT INTO meals(
                date,
                mess_morning,
                mess_night,
                canteen_morning,
                canteen_evening,
                note
            )
            VALUES (%s,%s,%s,%s,%s,%s)

            ON CONFLICT(date) DO UPDATE SET
                mess_morning=EXCLUDED.mess_morning,
                mess_night=EXCLUDED.mess_night,
                canteen_morning=EXCLUDED.canteen_morning,
                canteen_evening=EXCLUDED.canteen_evening,
                note=EXCLUDED.note
            """,
            (
                ds,
                bool(mm),
                bool(mn),
                bool(cm),
                bool(ce),
                note.strip(),
            ),
        )

    con.commit()
    invalidate_data()


def add_deposit(ds, account, amount, note):
    con = db()

    with con.cursor() as cur:
        cur.execute(
            """
            INSERT INTO deposits(date, account, amount, note)
            VALUES (%s,%s,%s,%s)
            """,
            (
                ds,
                account,
                float(amount),
                note.strip() or "Deposit",
            ),
        )

    con.commit()
    invalidate_data()


def delete_deposit(deposit_id):
    con = db()

    with con.cursor() as cur:
        cur.execute(
            "DELETE FROM deposits WHERE id=%s",
            (int(deposit_id),),
        )

    con.commit()
    invalidate_data()


# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------

def month_key(y, m):
    return f"{y:04d}-{m:02d}"


def month_label(y, m):
    return date(y, m, 1).strftime("%B %Y")


def money(value):
    return f"₹{float(value or 0):,.0f}"


def counts(rows):
    out = {
        "mm": 0,
        "mn": 0,
        "cm": 0,
        "ce": 0,
    }

    for row in rows:
        out["mm"] += int(bool(row["mess_morning"]))
        out["mn"] += int(bool(row["mess_night"]))
        out["cm"] += int(bool(row["canteen_morning"]))
        out["ce"] += int(bool(row["canteen_evening"]))

    return out


# ------------------------------------------------------------
# SESSION STATE
# ------------------------------------------------------------

today = date.today()

if "view_year" not in st.session_state:
    st.session_state.view_year = today.year
    st.session_state.view_month = today.month

y = st.session_state.view_year
mo = st.session_state.view_month
mk = month_key(y, mo)

# ------------------------------------------------------------
# LOAD MONTH DATA
# ------------------------------------------------------------

month = get_month(mk)
meals = get_meals(mk)
deposits = get_deposits(mk)

# IMPORTANT:
# Build this dictionary once.
# The calendar never calls PostgreSQL.
meal_map = {
    str(row["date"]): row
    for row in meals
}

cnt = counts(meals)

mess_dep = sum(
    float(row["amount"])
    for row in deposits
    if row["account"] == "mess"
)

canteen_dep = sum(
    float(row["amount"])
    for row in deposits
    if row["account"] == "canteen"
)

mess_balance = float(month["mess_opening"]) + mess_dep
canteen_balance = float(month["canteen_opening"]) + canteen_dep


# ------------------------------------------------------------
# CSS
# ------------------------------------------------------------

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

html, body, [class*="css"] {
    font-family: Inter, system-ui, sans-serif;
}

.stApp {
    background:
        radial-gradient(circle at 8% 2%, rgba(124,92,255,.14), transparent 27%),
        radial-gradient(circle at 93% 9%, rgba(33,173,156,.10), transparent 25%),
        linear-gradient(145deg,#090d14,#111722 55%,#0c1018);
    color:#edf1fa;
}

.block-container {
    max-width:1240px;
    padding-top:1rem;
    padding-bottom:2rem;
}

.hero,
.card,
.metric {
    background:rgba(21,27,39,.94);
    border:1px solid #293243;
    border-radius:20px;
    box-shadow:0 14px 38px rgba(0,0,0,.20);
}

.hero {
    padding:24px 26px;
    background:linear-gradient(135deg,#111827,#1c2234);
}

.hero-title {
    font-size:30px;
    font-weight:900;
}

.hero-sub,
.muted {
    color:#929caf;
    font-size:12px;
}

.live {
    color:#6fe0d0;
    margin-left:7px;
}

.card {
    padding:17px;
}

.section-title {
    font-size:18px;
    font-weight:900;
}

.balance {
    font-size:32px;
    font-weight:900;
}

.purple { color:#9d7cff; }
.teal { color:#21c1ad; }
.orange { color:#f2a34b; }

.metric {
    padding:14px;
    min-height:90px;
}

.metric-label {
    color:#929caf;
    font-size:11px;
}

.metric-value {
    font-size:25px;
    font-weight:900;
    margin-top:6px;
}

.account-mess {
    background:linear-gradient(135deg,#151b2b,#1a1930);
}

.account-cant {
    background:linear-gradient(135deg,#142321,#132a28);
}

.chip {
    display:inline-block;
    background:#202638;
    border:1px solid #39445a;
    padding:8px 11px;
    border-radius:10px;
    font-size:12px;
    margin-right:5px;
}

.dow {
    text-align:center;
    color:#858fa4;
    font-size:10px;
    font-weight:800;
    padding:5px;
}

.day {
    min-height:88px;
    background:linear-gradient(145deg,#171e2a,#121822);
    border:1px solid #2a3343;
    border-radius:13px;
    padding:7px;
}

.day.today {
    outline:2px solid #6657b7;
}

.daynum {
    font-weight:900;
    font-size:12px;
}

.mark {
    display:inline-block;
    margin:6px 3px 0 0;
    padding:4px 5px;
    border-radius:6px;
    background:#282145;
    color:#c9bdff;
    font-size:9px;
    font-weight:900;
}

.mark.c {
    background:#342719;
    color:#ffc985;
}

.summary-row {
    display:flex;
    justify-content:space-between;
    padding:9px 0;
    border-bottom:1px solid #2a3243;
    font-size:12px;
}

div[data-testid="stButton"] > button {
    border-radius:11px;
    border:1px solid #30394a;
    background:#1d2432;
    color:#edf1fa;
    font-weight:800;
}

button[kind="primary"],
div[data-testid="stButton"] button[kind="primary"] {
    background:linear-gradient(135deg,#7659f2,#9d72ff)!important;
    border:0!important;
}

input,
textarea,
[data-baseweb="select"] > div {
    background:#111722!important;
    color:#edf1fa!important;
}

@media(max-width:700px) {
    .block-container {
        padding:.6rem .5rem!important;
    }

    .hero {
        padding:16px;
        border-radius:18px;
    }

    .hero-title {
        font-size:21px;
    }

    .metric {
        min-height:75px;
        padding:10px;
    }

    .metric-value {
        font-size:20px;
    }

    .card {
        padding:13px;
    }

    .day {
        min-height:57px;
        padding:4px;
    }

    .daynum {
        font-size:10px;
    }

    .mark {
        font-size:7px;
        padding:2px 3px;
    }

    .dow {
        font-size:8px;
    }
}
</style>
""",
    unsafe_allow_html=True,
)


# ------------------------------------------------------------
# HEADER
# ------------------------------------------------------------

st.markdown(
    f"""
<div class="hero">
    <div class="hero-title">🍽️ Pallab's Hostel Ledger</div>
    <div class="hero-sub">
        Shared hostel account · monthly records · fast Supabase database
        <span class="live">● LIVE</span>
    </div>
</div>
""",
    unsafe_allow_html=True,
)


# ------------------------------------------------------------
# ACTION BUTTONS
# ------------------------------------------------------------

a1, a2, a3, a4, a5 = st.columns(
    [1, 1, 1, 1, 1.15]
)

with a1:
    if st.button("＋ Meal", use_container_width=True, type="primary"):
        st.session_state.meal_open = True
        st.session_state.meal_date = today.isoformat()

with a2:
    if st.button("🍛 Mess Money", use_container_width=True):
        st.session_state.money_open = True
        st.session_state.money_account = "mess"
        st.session_state.money_date = today.isoformat()

with a3:
    if st.button("☕ Canteen Money", use_container_width=True):
        st.session_state.money_open = True
        st.session_state.money_account = "canteen"
        st.session_state.money_date = today.isoformat()

with a4:
    if st.button("📌 Opening", use_container_width=True):
        st.session_state.opening_open = True

with a5:
    st.button("🌙", use_container_width=True)


# ------------------------------------------------------------
# MONTH NAVIGATION
# ------------------------------------------------------------

c1, c2, c3, c4 = st.columns(
    [1, 1.6, 1, 1]
)

with c1:
    if st.button("‹ Previous", use_container_width=True):
        if mo == 1:
            y -= 1
            mo = 12
        else:
            mo -= 1

        st.session_state.view_year = y
        st.session_state.view_month = mo
        st.rerun()

with c2:
    st.markdown(
        f"""
        <div style="
            text-align:center;
            font-size:21px;
            font-weight:900;
            padding:8px
        ">
            {month_label(y, mo)}
        </div>
        """,
        unsafe_allow_html=True,
    )

with c3:
    if st.button("Next ›", use_container_width=True):
        if mo == 12:
            y += 1
            mo = 1
        else:
            mo += 1

        st.session_state.view_year = y
        st.session_state.view_month = mo
        st.rerun()

with c4:
    if st.button("Today", use_container_width=True):
        st.session_state.view_year = today.year
        st.session_state.view_month = today.month
        st.rerun()


# ------------------------------------------------------------
# OPENING BALANCE
# ------------------------------------------------------------

st.markdown(
    f"""
<div class="card">
    <div style="
        display:flex;
        justify-content:space-between;
        gap:15px;
        flex-wrap:wrap;
    ">
        <div>
            <div class="section-title">
                💰 Opening Balance — {month_label(y,mo)}
            </div>
            <div class="muted">
                Manual opening balance · included in available balance.
            </div>
        </div>

        <div>
            <span class="chip">
                🍛 Mess
                <b class="purple">{money(month["mess_opening"])}</b>
            </span>

            <span class="chip">
                ☕ Canteen
                <b class="teal">{money(month["canteen_opening"])}</b>
            </span>
        </div>
    </div>
</div>
""",
    unsafe_allow_html=True,
)


# ------------------------------------------------------------
# TOP METRICS
# ------------------------------------------------------------

metrics = [
    ("🍛 Mess Available", money(mess_balance), "purple"),
    ("☕ Canteen Available", money(canteen_balance), "teal"),
    ("🍛 Mess Meals", cnt["mm"] + cnt["mn"], "purple"),
    ("☕ Canteen Counts", cnt["cm"] + cnt["ce"], "orange"),
]

for col, (label, value, color) in zip(
    st.columns(4),
    metrics
):
    with col:
        st.markdown(
            f"""
            <div class="metric">
                <div class="metric-label">{label}</div>
                <div class="metric-value {color}">
                    {value}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ------------------------------------------------------------
# ACCOUNT CARDS
# ------------------------------------------------------------

a, b = st.columns(2)

with a:
    st.markdown(
        f"""
        <div class="card account-mess">
            <h3>🍛 Mess — selected month</h3>
            <div class="balance purple">
                {money(mess_balance)}
            </div>
            <div class="muted">
                Opening <b>{money(month["mess_opening"])}</b>
                + Deposits <b>{money(mess_dep)}</b>
                · Meals {cnt["mm"] + cnt["mn"]}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with b:
    st.markdown(
        f"""
        <div class="card account-cant">
            <h3>☕ Canteen — selected month</h3>
            <div class="balance teal">
                {money(canteen_balance)}
            </div>
            <div class="muted">
                Opening <b>{money(month["canteen_opening"])}</b>
                + Deposits <b>{money(canteen_dep)}</b>
                · Counts {cnt["cm"] + cnt["ce"]}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ------------------------------------------------------------
# CALENDAR
# ------------------------------------------------------------

st.markdown(
    "<div class='card' style='margin-top:14px'>",
    unsafe_allow_html=True,
)

h1, h2 = st.columns([4, 1])

with h1:
    st.markdown(
        f"""
        <div class="section-title">📅 Daily Meals</div>
        <div class="muted">
            Edit meal counts for {month_label(y,mo)}.
            No meal price is used.
        </div>
        """,
        unsafe_allow_html=True,
    )

with h2:
    if st.button(
        "＋ Add Meal",
        use_container_width=True,
        type="primary"
    ):
        st.session_state.meal_open = True
        st.session_state.meal_date = today.isoformat()


for col, name in zip(
    st.columns(7),
    ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
):
    with col:
        st.markdown(
            f"<div class='dow'>{name}</div>",
            unsafe_allow_html=True,
        )


offset = date(y, mo, 1).weekday()
days = calendar.monthrange(y, mo)[1]

cells = [None] * offset + list(range(1, days + 1))

while len(cells) % 7:
    cells.append(None)


for start in range(0, len(cells), 7):

    for col, day_num in zip(
        st.columns(7),
        cells[start:start + 7]
    ):

        with col:

            if day_num is None:
                st.markdown(
                    "<div style='height:88px'></div>",
                    unsafe_allow_html=True,
                )
                continue

            ds = f"{mk}-{day_num:02d}"

            # No DB query here.
            row = meal_map.get(ds)

            marks = []

            if row:
                if row["mess_morning"]:
                    marks.append('<span class="mark">MM</span>')

                if row["mess_night"]:
                    marks.append('<span class="mark">MN</span>')

                if row["canteen_morning"]:
                    marks.append('<span class="mark c">CM</span>')

                if row["canteen_evening"]:
                    marks.append('<span class="mark c">CE</span>')

            if not marks:
                marks = [
                    '<span class="muted" style="font-size:9px">'
                    'Tap to add'
                    '</span>'
                ]

            today_class = " today" if ds == today.isoformat() else ""

            st.markdown(
                f"""
                <div class="day{today_class}">
                    <div class="daynum">{day_num}</div>
                    {''.join(marks)}
                </div>
                """,
                unsafe_allow_html=True,
            )

            if st.button(
                "Edit",
                key=f"edit_{ds}",
                use_container_width=True
            ):
                st.session_state.meal_open = True
                st.session_state.meal_date = ds
                st.rerun()


st.markdown("</div>", unsafe_allow_html=True)


# ------------------------------------------------------------
# MONTHLY COUNTS
# ------------------------------------------------------------

m1, m2 = st.columns(2)

with m1:
    st.markdown(
        f"""
        <div class="card">
            <div class="section-title">
                🍛 Mess — this month
            </div>

            <div class="summary-row">
                <span>Morning</span>
                <b>{cnt["mm"]}</b>
            </div>

            <div class="summary-row">
                <span>Night</span>
                <b>{cnt["mn"]}</b>
            </div>

            <div class="summary-row">
                <span>Total meals</span>
                <b>{cnt["mm"] + cnt["mn"]}</b>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with m2:
    st.markdown(
        f"""
        <div class="card">
            <div class="section-title">
                ☕ Canteen — this month
            </div>

            <div class="summary-row">
                <span>Morning</span>
                <b>{cnt["cm"]}</b>
            </div>

            <div class="summary-row">
                <span>Evening</span>
                <b>{cnt["ce"]}</b>
            </div>

            <div class="summary-row">
                <span>Total counts</span>
                <b>{cnt["cm"] + cnt["ce"]}</b>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ------------------------------------------------------------
# DEPOSITS
# ------------------------------------------------------------

d1, d2 = st.columns([1.2, .8])

with d1:

    st.markdown(
        f"""
        <div class="card">
            <div class="section-title">
                💳 Deposits — {month_label(y,mo)}
            </div>

            <div class="muted">
                Only deposits for the selected month are shown.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if deposits:

        for row in deposits:

            cc = st.columns(
                [1.15, 1, 1.4, .8, .35]
            )

            cc[0].write(
                date.fromisoformat(
                    str(row["date"])
                ).strftime("%d %b %Y")
            )

            cc[1].write(
                "🍛 Mess"
                if row["account"] == "mess"
                else "☕ Canteen"
            )

            cc[2].write(
                row["note"] or "Deposit"
            )

            cc[3].write(
                f"**{money(row['amount'])}**"
            )

            if cc[4].button(
                "×",
                key=f"delete_{row['id']}"
            ):
                delete_deposit(row["id"])
                st.rerun()

    else:
        st.info(
            f"No deposits in {month_label(y,mo)}."
        )


# ------------------------------------------------------------
# MONTHLY SUMMARY
# ------------------------------------------------------------

with d2:

    summary = [
        ("🍛 Mess meals", cnt["mm"] + cnt["mn"]),
        ("☕ Canteen counts", cnt["cm"] + cnt["ce"]),
        ("🍛 Mess morning", cnt["mm"]),
        ("🍛 Mess night", cnt["mn"]),
        ("☕ Canteen morning", cnt["cm"]),
        ("☕ Canteen evening", cnt["ce"]),
        ("🍛 Mess opening", money(month["mess_opening"])),
        ("☕ Canteen opening", money(month["canteen_opening"])),
        ("🍛 Mess deposits", money(mess_dep)),
        ("☕ Canteen deposits", money(canteen_dep)),
        ("🍛 Mess balance", money(mess_balance)),
        ("☕ Canteen balance", money(canteen_balance)),
    ]

    st.markdown(
        """
        <div class="card">
            <div class="section-title">
                ⚡ Monthly Summary
            </div>
        """,
        unsafe_allow_html=True,
    )

    for label, value in summary:
        st.markdown(
            f"""
            <div class="summary-row">
                <span>{label}</span>
                <b>{value}</b>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )


# ------------------------------------------------------------
# OPENING FORM
# ------------------------------------------------------------

if st.session_state.get("opening_open"):

    with st.form("opening_form"):

        st.markdown(
            f"### 💰 Opening Balance — {month_label(y,mo)}"
        )

        o1, o2 = st.columns(2)

        with o1:
            mess_opening = st.number_input(
                "🍛 Mess Opening Balance (₹)",
                min_value=0.0,
                value=float(month["mess_opening"]),
                step=1.0,
            )

        with o2:
            canteen_opening = st.number_input(
                "☕ Canteen Opening Balance (₹)",
                min_value=0.0,
                value=float(month["canteen_opening"]),
                step=1.0,
            )

        b1, b2 = st.columns(2)

        with b1:
            if st.form_submit_button(
                "Save Opening Balance",
                type="primary"
            ):
                set_opening(
                    mk,
                    mess_opening,
                    canteen_opening
                )
                st.session_state.opening_open = False
                st.rerun()

        with b2:
            if st.form_submit_button("Cancel"):
                st.session_state.opening_open = False
                st.rerun()


# ------------------------------------------------------------
# MEAL FORM
# ------------------------------------------------------------

if st.session_state.get("meal_open"):

    ds = st.session_state.get(
        "meal_date",
        today.isoformat()
    )

    existing = meal_map.get(ds)

    with st.form("meal_form"):

        st.markdown(
            f"### 🍽️ Meals — {month_label(y,mo)}"
        )

        f1, f2 = st.columns(2)

        with f1:
            selected_date = st.date_input(
                "Date",
                value=date.fromisoformat(ds)
            )

        with f2:
            note = st.text_input(
                "Note",
                value=(
                    existing["note"]
                    if existing else ""
                ),
                placeholder="Optional"
            )

        q1, q2 = st.columns(2)

        with q1:
            canteen_morning = st.checkbox(
                "☕ Canteen Morning",
                value=(
                    bool(existing["canteen_morning"])
                    if existing else False
                )
            )

            canteen_evening = st.checkbox(
                "☕ Canteen Evening",
                value=(
                    bool(existing["canteen_evening"])
                    if existing else False
                )
            )

        with q2:
            mess_morning = st.checkbox(
                "🍛 Mess Morning",
                value=(
                    bool(existing["mess_morning"])
                    if existing else False
                )
            )

            mess_night = st.checkbox(
                "🌙 Mess Night",
                value=(
                    bool(existing["mess_night"])
                    if existing else False
                )
            )

        b1, b2 = st.columns(2)

        with b1:

            if st.form_submit_button(
                "Save Meal",
                type="primary"
            ):

                if (
                    selected_date.strftime("%Y-%m")
                    != mk
                ):
                    st.error(
                        f"Meal date must be inside "
                        f"{month_label(y,mo)}."
                    )

                else:

                    save_meal(
                        selected_date.isoformat(),
                        mess_morning,
                        mess_night,
                        canteen_morning,
                        canteen_evening,
                        note,
                    )

                    st.session_state.meal_open = False
                    st.rerun()

        with b2:

            if st.form_submit_button("Cancel"):
                st.session_state.meal_open = False
                st.rerun()


# ------------------------------------------------------------
# MONEY FORM
# ------------------------------------------------------------

if st.session_state.get("money_open"):

    account_default = st.session_state.get(
        "money_account",
        "mess"
    )

    money_date = st.session_state.get(
        "money_date",
        today.isoformat()
    )

    with st.form("money_form"):

        st.markdown("### 💳 Monthly Money")

        f1, f2 = st.columns(2)

        with f1:
            account = st.selectbox(
                "Account",
                ["mess", "canteen"],
                index=(
                    0
                    if account_default == "mess"
                    else 1
                )
            )

        with f2:
            selected_date = st.date_input(
                "Date",
                value=date.fromisoformat(money_date)
            )

        f3, f4 = st.columns(2)

        with f3:
            amount = st.number_input(
                "Amount (₹)",
                min_value=0.0,
                step=10.0,
                value=0.0,
            )

        with f4:
            note = st.text_input(
                "Note",
                placeholder="e.g. August payment"
            )

        current_deposit = (
            mess_dep
            if account == "mess"
            else canteen_dep
        )

        st.markdown(
            f"""
            <div class="card">
                This month:
                <b>{money(current_deposit)}</b>
            </div>
            """,
            unsafe_allow_html=True,
        )

        b1, b2 = st.columns(2)

        with b1:

            if st.form_submit_button(
                "Add Money",
                type="primary"
            ):

                if amount <= 0:

                    st.error(
                        "Enter a valid amount."
                    )

                elif (
                    selected_date.strftime("%Y-%m")
                    != mk
                ):

                    st.error(
                        f"Deposit date must be inside "
                        f"{month_label(y,mo)}."
                    )

                else:

                    add_deposit(
                        selected_date.isoformat(),
                        account,
                        amount,
                        note,
                    )

                    st.session_state.money_open = False
                    st.rerun()

        with b2:

            if st.form_submit_button("Cancel"):
                st.session_state.money_open = False
                st.rerun()


# ------------------------------------------------------------
# FOOTER
# ------------------------------------------------------------

st.markdown(
    """
    <div style="
        text-align:center;
        color:#687287;
        font-size:10px;
        padding:22px 0 4px;
    ">
        Pallab's Hostel Ledger · Supabase PostgreSQL · Ultra Fast
    </div>
    """,
    unsafe_allow_html=True,
)
