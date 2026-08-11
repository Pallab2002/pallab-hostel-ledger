# Pallab Hostel Ledger — Ultra Fast

## Streamlit Secrets

Use only:

```toml
SUPABASE_DB_URL = "YOUR_COMPLETE_SESSION_POOLER_CONNECTION_STRING"
```

Do NOT put the password separately in app.py.

## Important

The connection string should be the complete Supabase Session Pooler URL, for example:

```text
postgresql://postgres.PROJECT_REF:PASSWORD@aws-0-ap-south-1.pooler.supabase.com:5432/postgres
```

Replace `PASSWORD` with your actual Supabase database password.

## Deploy

1. Replace your GitHub `app.py`.
2. Keep `requirements.txt`.
3. Keep the existing Streamlit Secret.
4. Commit changes.
5. Wait for Streamlit Cloud to redeploy.

This version keeps the same core tracker but minimizes database round trips.
