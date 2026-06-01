import os
import json
from decimal import Decimal
from pathlib import Path
from config import APP_DIR

CONFIG_FILE = APP_DIR / "currency_rates.json"

DEFAULT_RATES = {
    "USD": 1.0,
    "EUR": 0.92,
    "GBP": 0.79,
    "AZN": 1.70,
    "RUB": 92.50,
    "TRY": 32.20,
    "UAH": 41.50,  # Ukrainian Hryvnia — update via Settings > Currencies
}

def load_rates():
    if not os.path.exists(CONFIG_FILE):
        save_rates(DEFAULT_RATES)
        return DEFAULT_RATES
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return DEFAULT_RATES

def save_rates(rates_dict):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(rates_dict, f, indent=4)
    except Exception as e:
        print(f"Failed to save currency rates: {e}")

def get_rate(from_currency, to_currency):
    """
    Returns the exchange rate to convert from `from_currency` to `to_currency`.
    Defaults to 1.0 if the currency is not found.
    """
    rates = load_rates()
    from_rate = Decimal(str(rates.get(from_currency, 1.0)))
    to_rate = Decimal(str(rates.get(to_currency, 1.0)))
    
    return to_rate / from_rate

def convert_to_base(amount, from_currency, base_currency="AZN"):
    """
    Converts an amount from a given currency to the base currency.
    """
    amt = Decimal(str(amount))
    rate = get_rate(from_currency, base_currency)
    return amt * rate

def format_currency(amount, currency_code="AZN", sign=""):
    """
    Formats an amount into a localized string with the proper currency symbol.
    """
    symbols = {
        "USD": "$",
        "EUR": "€",
        "GBP": "£",
        "AZN": "₼",
        "JPY": "¥",
        "RUB": "₽",
        "TRY": "₺"
    }
    sym = symbols.get(currency_code.upper(), currency_code.upper() + " ")
    return f"{sign}{sym}{amount:,.2f}"
