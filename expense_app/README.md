# Monthly Expense Tracker Web App

Streamlit + Supabase expense tracker based on the `Monthly Expense Tracker.xlsx` workbook.

## Planned stack
- Streamlit frontend
- Supabase PostgreSQL for persistent data
- GitHub for source control
- Streamlit Community Cloud for deployment

## Workbook model
- Opening bank balances
- Monthly salary and investments
- Recoverable payments
- Budget vs actual monthly expenses
- Automatic totals and percentages

## Local setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

Create Streamlit secrets for `SUPABASE_URL` and `SUPABASE_KEY` before connecting to the database.
