# Pallab's Hostel Ledger — Streamlit + SQLite

This is the shared-database version of the uploaded v20 HTML tracker.

## Features

- Dark hostel-ledger UI
- Monthly calendar
- Mess: Morning + Night
- Canteen: Morning + Evening
- Separate Mess/Canteen deposits
- Manual monthly opening balances
- Month-by-month independent records
- Opening balance + deposits = available balance
- Meal counts do not change money balance
- New Meal starts on today's live date with all four meal options unchecked
- Editing an existing date loads its saved meal selections
- New Money starts on today's live date
- SQLite shared database

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

The SQLite database is created automatically as `hostel_ledger.db`.

## Deploy

For a simple public deployment, put `app.py` and `requirements.txt` in a GitHub repository and deploy the repository with Streamlit Community Cloud.

### Important persistence note

SQLite is suitable for a small/shared hostel tracker. On some hosted platforms, local files can be reset or replaced during redeploys/restarts. If you need guaranteed permanent cloud storage for multiple users, replace SQLite with a hosted PostgreSQL/Supabase database.

## Data model

- `month_settings` — monthly Mess/Canteen opening balances
- `meals` — one record per date
- `deposits` — Mess/Canteen money entries
