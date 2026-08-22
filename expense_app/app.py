import os
from datetime import date

import pandas as pd
import streamlit as st
from supabase import create_client

st.set_page_config(page_title="Monthly Expense Tracker", page_icon="💰", layout="wide")


def get_supabase():
    url = st.secrets.get("SUPABASE_URL", os.getenv("SUPABASE_URL"))
    key = st.secrets.get("SUPABASE_KEY", os.getenv("SUPABASE_KEY"))
    if not url or not key:
        st.error("Supabase is not configured. Add SUPABASE_URL and SUPABASE_KEY to Streamlit secrets.")
        st.stop()
    return create_client(url, key)


sb = get_supabase()

st.title("💰 Monthly Expense Tracker")
st.caption("A web version of your Excel tracker — data is saved in Supabase.")

month_value = st.date_input("Month", value=date.today().replace(day=1), format="YYYY-MM-DD")
month_key = month_value.strftime("%Y-%m")

settings = sb.table("monthly_settings").select("*").eq("month_key", month_key).limit(1).execute().data
if not settings:
    sb.table("monthly_settings").insert({"month_key": month_key, "salary": 0}).execute()
    settings = sb.table("monthly_settings").select("*").eq("month_key", month_key).limit(1).execute().data

salary = float(settings[0]["salary"] or 0)

with st.sidebar:
    st.header("Monthly Inputs")
    salary_new = st.number_input("Monthly Salary", min_value=0.0, value=salary, step=500.0)
    if st.button("Save Salary", use_container_width=True):
        sb.table("monthly_settings").update({"salary": salary_new}).eq("month_key", month_key).execute()
        st.success("Salary saved")
        st.rerun()


def load_table(name: str) -> pd.DataFrame:
    rows = sb.table(name).select("*").eq("month_key", month_key).order("sort_order").execute().data
    return pd.DataFrame(rows)


def upsert_rows(table_name: str, records: list[dict], conflict_columns: str):
    if records:
        sb.table(table_name).upsert(records, on_conflict=conflict_columns).execute()


banks = load_table("bank_accounts")
investments = load_table("investments")
recoverables = load_table("recoverables")
expenses = load_table("expenses")

bank_total = float(banks["opening_balance"].sum()) if not banks.empty else 0.0
investment_total = float(investments["amount"].sum()) if not investments.empty else 0.0
recoverable_total = float(recoverables.loc[~recoverables["recovered"], "amount"].sum()) if not recoverables.empty else 0.0
expense_budget = float(expenses["budget"].sum()) if not expenses.empty else 0.0
expense_actual = float(expenses["actual"].sum()) if not expenses.empty else 0.0
salary_balance = salary_new - investment_total - expense_actual
closing_bank = bank_total + salary_balance
potential_closing = closing_bank + recoverable_total

m1, m2, m3, m4 = st.columns(4)
m1.metric("Opening Bank Balance", f"₹{bank_total:,.0f}")
m2.metric("Salary", f"₹{salary_new:,.0f}")
m3.metric("Actual Expenses", f"₹{expense_actual:,.0f}")
m4.metric("Closing Bank Balance", f"₹{closing_bank:,.0f}")

st.divider()

c1, c2 = st.columns(2)
with c1:
    st.subheader("Bank Balances")
    if not banks.empty:
        st.dataframe(
            banks[["account_name", "opening_balance"]].rename(
                columns={"account_name": "Account", "opening_balance": "Opening Balance"}
            ),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No bank accounts yet.")

with c2:
    st.subheader("Investments")
    if not investments.empty:
        st.dataframe(
            investments[["investment_name", "amount"]].rename(
                columns={"investment_name": "Investment", "amount": "Amount"}
            ),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No investments yet.")

st.subheader("Recoverable Payments")
if not recoverables.empty:
    display_rec = recoverables[["person_name", "amount", "recovered"]].rename(
        columns={"person_name": "Person", "amount": "Amount", "recovered": "Recovered"}
    )
    st.dataframe(display_rec, use_container_width=True, hide_index=True)
    st.caption(f"Outstanding recoverables: ₹{recoverable_total:,.0f}")
else:
    st.info("No recoverable payments yet.")

st.subheader("Monthly Expenses")
if not expenses.empty:
    chart_df = expenses[["category", "budget", "actual"]].copy()
    chart_df["variance"] = chart_df["budget"] - chart_df["actual"]
    st.dataframe(
        chart_df.rename(
            columns={
                "category": "Category",
                "budget": "Budget",
                "actual": "Actual",
                "variance": "Remaining Budget",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )
    st.bar_chart(chart_df.set_index("category")[["budget", "actual"]])
else:
    st.info("No expense categories yet.")

p1, p2, p3, p4 = st.columns(4)
p1.metric("Budget", f"₹{expense_budget:,.0f}")
p2.metric("Actual", f"₹{expense_actual:,.0f}")
p3.metric("Budget Remaining", f"₹{expense_budget - expense_actual:,.0f}")
p4.metric("Potential Closing", f"₹{potential_closing:,.0f}")

st.divider()
st.subheader("Edit Data")

with st.expander("Bank accounts", expanded=False):
    if banks.empty:
        bank_edit = pd.DataFrame(columns=["Account", "Opening Balance"])
    else:
        bank_edit = banks[["account_name", "opening_balance"]].rename(columns={"account_name": "Account", "opening_balance": "Opening Balance"})
    bank_edit = st.data_editor(bank_edit, num_rows="dynamic", use_container_width=True, key="bank_editor")
    if st.button("Save bank accounts"):
        records = []
        for i, row in bank_edit.fillna("").iterrows():
            name = str(row.get("Account", "")).strip()
            if name:
                records.append({"month_key": month_key, "account_name": name, "opening_balance": float(row.get("Opening Balance", 0) or 0), "sort_order": i + 1})
        upsert_rows("bank_accounts", records, "month_key,account_name")
        st.success("Bank accounts saved")
        st.rerun()

with st.expander("Investments", expanded=False):
    inv_edit = investments[["investment_name", "amount"]].rename(columns={"investment_name": "Investment", "amount": "Amount"}) if not investments.empty else pd.DataFrame(columns=["Investment", "Amount"])
    inv_edit = st.data_editor(inv_edit, num_rows="dynamic", use_container_width=True, key="investment_editor")
    if st.button("Save investments"):
        records = []
        for i, row in inv_edit.fillna("").iterrows():
            name = str(row.get("Investment", "")).strip()
            if name:
                records.append({"month_key": month_key, "investment_name": name, "amount": float(row.get("Amount", 0) or 0), "sort_order": i + 1})
        upsert_rows("investments", records, "month_key,investment_name")
        st.success("Investments saved")
        st.rerun()

with st.expander("Recoverable payments", expanded=False):
    rec_edit = recoverables[["person_name", "amount", "recovered"]].rename(columns={"person_name": "Person", "amount": "Amount", "recovered": "Recovered"}) if not recoverables.empty else pd.DataFrame(columns=["Person", "Amount", "Recovered"])
    rec_edit = st.data_editor(rec_edit, num_rows="dynamic", use_container_width=True, key="recoverable_editor")
    if st.button("Save recoverables"):
        records = []
        for _, row in rec_edit.fillna("").iterrows():
            name = str(row.get("Person", "")).strip()
            if name:
                records.append({"month_key": month_key, "person_name": name, "amount": float(row.get("Amount", 0) or 0), "recovered": bool(row.get("Recovered", False))})
        upsert_rows("recoverables", records, "month_key,person_name")
        st.success("Recoverables saved")
        st.rerun()

with st.expander("Monthly expenses", expanded=True):
    exp_edit = expenses[["category", "budget", "actual"]].rename(columns={"category": "Category", "budget": "Budget", "actual": "Actual"}) if not expenses.empty else pd.DataFrame(columns=["Category", "Budget", "Actual"])
    exp_edit = st.data_editor(exp_edit, num_rows="dynamic", use_container_width=True, key="expense_editor")
    if st.button("Save monthly expenses"):
        records = []
        for i, row in exp_edit.fillna("").iterrows():
            name = str(row.get("Category", "")).strip()
            if name:
                records.append({"month_key": month_key, "category": name, "budget": float(row.get("Budget", 0) or 0), "actual": float(row.get("Actual", 0) or 0), "sort_order": i + 1})
        upsert_rows("expenses", records, "month_key,category")
        st.success("Expenses saved")
        st.rerun()

st.caption("Tip: use the month selector to maintain a separate record for each month.")
