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
st.caption("Supabase-backed version of the Excel tracker")

month_value = st.date_input("Month", value=date.today().replace(day=1), format="YYYY-MM-DD")
month_key = month_value.strftime("%Y-%m")

# Ensure a monthly header record exists.
settings = sb.table("monthly_settings").select("*").eq("month_key", month_key).limit(1).execute().data
if not settings:
    sb.table("monthly_settings").insert({"month_key": month_key, "salary": 0}).execute()
    settings = sb.table("monthly_settings").select("*").eq("month_key", month_key).limit(1).execute().data

salary = float(settings[0]["salary"] or 0)

with st.sidebar:
    st.header("Monthly inputs")
    salary_new = st.number_input("Monthly Salary", min_value=0.0, value=salary, step=500.0)
    if st.button("Save salary", use_container_width=True):
        sb.table("monthly_settings").update({"salary": salary_new}).eq("month_key", month_key).execute()
        st.success("Salary saved")
        st.rerun()


def load_table(name: str, columns: str = "*") -> pd.DataFrame:
    rows = sb.table(name).select(columns).eq("month_key", month_key).order("sort_order").execute().data
    return pd.DataFrame(rows)


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
m4.metric("Closing Bank Balance", f"₹{closing_closing:,.0f}" if False else f"₹{closing_bank:,.0f}")

st.divider()

c1, c2 = st.columns(2)
with c1:
    st.subheader("Bank Balances")
    if not banks.empty:
        st.dataframe(banks[["account_name", "opening_balance"]].rename(columns={"account_name": "Account", "opening_balance": "Opening Balance"}), use_container_width=True, hide_index=True)
    else:
        st.info("No bank accounts yet.")
with c2:
    st.subheader("Investments")
    if not investments.empty:
        st.dataframe(investments[["investment_name", "amount"]].rename(columns={"investment_name": "Investment", "amount": "Amount"}), use_container_width=True, hide_index=True)
    else:
        st.info("No investments yet.")

st.subheader("Recoverable Payments")
if not recoverables.empty:
    display_rec = recoverables[["person_name", "amount", "recovered"]].rename(columns={"person_name": "Person", "amount": "Amount", "recovered": "Recovered"})
    st.dataframe(display_rec, use_container_width=True, hide_index=True)
    st.caption(f"Outstanding recoverables: ₹{recoverable_total:,.0f}")
else:
    st.info("No recoverable payments yet.")

st.subheader("Monthly Expenses")
if not expenses.empty:
    chart_df = expenses[["category", "budget", "actual"]].copy()
    chart_df["variance"] = chart_df["budget"] - chart_df["actual"]
    st.dataframe(
        chart_df.rename(columns={"category": "Category", "budget": "Budget", "actual": "Actual", "variance": "Remaining Budget"}),
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
st.write("The next step is to add create/edit/delete forms for bank accounts, investments, recoverables, and expense categories.")
