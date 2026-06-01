import sqlite3
import os
import json
from pathlib import Path

# Load the active database path from settings
appdata = os.environ.get('LOCALAPPDATA', os.environ.get('APPDATA', str(Path.home())))
settings_path = Path(appdata) / 'KTIB_CashFlow' / 'settings.json'

db_path = str(Path(appdata) / 'KTIB_CashFlow' / 'ktib_cashflow.db')
if settings_path.exists():
    with open(settings_path) as f:
        custom = json.load(f).get('db_path')
    if custom:
        db_path = custom

print(f'Patching: {db_path}')
conn = sqlite3.connect(db_path)
cur = conn.cursor()

patches = {
    'companies': [
        ("ai_api_key",  "TEXT",    "''"),
        ("ai_model",    "TEXT",    "'gemini-2.5-flash'"),
        ("ai_enabled",  "INTEGER", "1"),
    ],
    'transactions': [
        ("status",              "TEXT",    "'confirmed'"),
        ("edv_amount",          "INTEGER", "0"),
        ("edv_account_id",      "INTEGER", "NULL"),
        ("base_amount",         "INTEGER", "NULL"),
        ("base_edv_amount",     "INTEGER", "NULL"),
        ("account_amount",      "INTEGER", "NULL"),
        ("to_account_amount",   "INTEGER", "NULL"),
        ("edv_account_amount",  "INTEGER", "NULL"),
    ],
    'planned_payments': [
        ("currency",        "TEXT",    "'AZN'"),
        ("edv_amount",      "INTEGER", "0"),
        ("edv_account_id",  "INTEGER", "NULL"),
    ],
    'categories': [
        ("parent_id", "INTEGER", "NULL"),
    ],
}

for table, columns in patches.items():
    cur.execute(f'PRAGMA table_info({table})')
    existing = [r[1] for r in cur.fetchall()]
    for col_name, col_type, default in columns:
        if col_name not in existing:
            sql = f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type} DEFAULT {default}"
            cur.execute(sql)
            print(f'  Added {table}.{col_name}')
        else:
            print(f'  OK    {table}.{col_name}')

conn.commit()
conn.close()
print('\nAll done — database is fully up to date!')
