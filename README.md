# Pallab's Hostel Ledger — Streamlit + Supabase

This version keeps the existing UI and replaces SQLite with Supabase PostgreSQL.

## Streamlit Cloud Secrets

Add this under App → Settings → Secrets:

```toml
SUPABASE_DB_URL = "YOUR_SESSION_POOLER_CONNECTION_STRING"
```

Do not put the password or connection string in `app.py` or GitHub.

The app automatically creates:
- month_settings
- meals
- deposits

The original v20 meal history is seeded only when the Supabase `meals` table is empty.
