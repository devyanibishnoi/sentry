# Registry of valid actions and their expected argument types, and the
# schema of fields available on `alert` inside an `on` block. Semantic
# analysis (sentry/semantics.py) checks the AST against these tables.

ACTIONS = {
    "isolate_host": ["string"],
    "notify_soc": ["string"],
    "block_ip": ["string"],
    "quarantine_file": ["string"],
    "disable_user": ["string"],
}

ALERT_SCHEMA = {
    "host": "string",
    "id": "string",
    "confidence": "number",
    "severity": "string",
    "user": "string",
}
