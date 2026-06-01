from pathlib import Path
from decimal import ROUND_HALF_UP, Decimal

APP_NAME        = "KTIB Cash Flow"
APP_VERSION     = "1.0.0"
APP_BUILD_DATE  = "2025-01"
MIN_PYTHON      = (3, 11)

import os
import sys

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)

# Paths — all relative to user home
if os.name == 'nt':
    # Windows
    appdata = os.environ.get('LOCALAPPDATA', os.environ.get('APPDATA', str(Path.home())))
    APP_DIR = Path(appdata) / "KTIB_CashFlow"
else:
    # Linux/Mac
    APP_DIR = Path.home() / ".local" / "share" / "KTIB_CashFlow"

SETTINGS_PATH   = APP_DIR / "settings.json"
LOG_PATH        = APP_DIR / "ktib_cashflow.log"
EXPORT_DIR      = APP_DIR / "exports"
BACKUP_DIR      = APP_DIR / "backups"

# Ensure base directories exist
APP_DIR.mkdir(parents=True, exist_ok=True)
EXPORT_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

import json

# Settings Loader
def load_app_settings():
    try:
        if os.path.exists(SETTINGS_PATH):
            with open(SETTINGS_PATH, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load app settings ({e}). Using defaults.")
    return {}

def save_app_settings(settings):
    try:
        with open(SETTINGS_PATH, 'w') as f:
            json.dump(settings, f, indent=4)
    except Exception as e:
        print(f"Failed to save settings: {e}")

_settings = load_app_settings()
_custom_db = _settings.get("db_path")

if _custom_db and os.path.exists(os.path.dirname(_custom_db)):
    DB_PATH = Path(_custom_db)
else:
    DB_PATH = APP_DIR / "ktib_cashflow.db"

# DB
ALEMBIC_INI     = Path(__file__).parent / "alembic.ini"
DB_URL          = f"sqlite:///{DB_PATH}"

# Money
MONEY_PRECISION = Decimal("0.01")
ROUNDING        = ROUND_HALF_UP

# Auth (Windows Auto-Login)

# UI
MIN_WIDTH       = 1200
MIN_HEIGHT      = 700
DEFAULT_WIDTH   = 1440
DEFAULT_HEIGHT  = 860
SIDEBAR_WIDTH   = 220
ITEMS_PER_PAGE  = 25
CHART_MONTHS    = 6

# Supported values
CURRENCIES      = ["USD", "EUR", "GBP", "AZN", "TRY", "UAH"]
ACCOUNT_TYPES   = ["Bank", "Cash", "E-wallet", "Crypto", "Card"]
TX_TYPES        = ["income", "expense", "transfer"]
RECURRING       = ["none", "weekly", "monthly", "yearly"]
PLANNED_STATUS  = ["pending", "paid", "overdue"]

CATEGORY_COLORS = [
    "#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", 
    "#EC4899", "#06B6D4", "#F97316", "#6366F1", "#14B8A6",
    "#FACC15", "#A855F7", "#D946EF", "#FB7185", "#2DD4BF"
]
