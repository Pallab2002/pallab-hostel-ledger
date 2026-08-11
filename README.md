# Pallab Hostel Ledger — Fast Supabase

Use this `app.py` with:

```toml
SUPABASE_DB_URL = "YOUR_COMPLETE_SESSION_POOLER_CONNECTION_STRING"
```

Performance changes:
- One database query for all meals in the selected month.
- No database query inside the calendar day loop.
- 30-second caching for read operations.
- Cache is cleared after every write.
