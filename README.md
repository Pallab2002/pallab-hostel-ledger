# Pallab's Hostel Ledger — Ultra Fast Fixed

## Files
- `app.py` — corrected ultra-fast Streamlit app
- `requirements.txt` — dependencies

## Streamlit Secret
Use only:

```toml
SUPABASE_DB_URL = "postgresql://postgres.PROJECT_REF:URL_ENCODED_PASSWORD@aws-0-ap-south-1.pooler.supabase.com:5432/postgres"
```

Keep the password out of `app.py`.

## Important
The previous UI issue where `<div>`, `<span>`, and `<b>` appeared as literal text was caused by the HTML being interpreted as Markdown code blocks. This version builds the HTML without leading indentation and passes `unsafe_allow_html=True`.

The calendar no longer queries PostgreSQL once per date. The selected month's meals and deposits are loaded in two SQL queries and stored in an in-memory lookup. Writes clear the monthly cache.

If the first page load is still slow while subsequent navigation is fast, that remaining delay is likely Streamlit Cloud cold-start rather than the database.
