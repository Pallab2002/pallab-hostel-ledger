# Pallab's Hostel Ledger — Ultra Fast + Popup UI

This version fixes:
- Literal HTML appearing on the page.
- Slow calendar caused by per-day database queries.
- Opening Balance, Meal, and Money forms appearing underneath the page.

New behavior:
- Opening Balance opens in a Streamlit modal popup.
- + Meal opens in a modal popup.
- Calendar Edit opens in a modal popup.
- Mess Money / Canteen Money opens in a modal popup.
- Successful opening-balance save shows a toast notification.
- Successful meal save shows a toast notification.
- Successful money addition shows a toast notification.
- Successful deposit deletion shows a toast notification.
- Notifications survive the rerun after the database operation.
- Monthly reads are cached and the calendar uses an in-memory date lookup.

Keep the Supabase secret as:

```toml
SUPABASE_DB_URL = "postgresql://postgres.PROJECT_REF:URL_ENCODED_PASSWORD@aws-0-ap-south-1.pooler.supabase.com:5432/postgres"
```

Do not put the database password into app.py.
