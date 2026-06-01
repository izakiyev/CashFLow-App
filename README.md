# KTIB Cash Flow — Financial Management

A production-ready desktop cash flow management application built with Python.

## Features
- **Dashboard**: Track overall financial health, upcoming payments, and recent transactions.
- **Cash Flow Analysis**: Visualize income vs expenses dynamically.
- **Transactions Management**: Add, edit, and filter transactions across multiple accounts.
- **Accounts**: Manage balances for Bank, Cash, E-Wallet, and Crypto accounts.
- **Planned Payments**: Track upcoming and recurring bills/invoices.
- **Reports**: Generate P&L and Balance summaries. Export to PDF & Excel.
- **Dark Mode**: Modern dark-mode UI out of the box using CustomTkinter.

## Prerequisites
- Python 3.11+
- Windows, macOS, or Linux

## Setup & Installation
1. Clone the repository and navigate to the project directory.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python main.py
   ```

## Building Executables
Use PyInstaller to build a standalone executable:

**Windows**:
```bash
pyinstaller build.spec --clean
```
**macOS**:
```bash
pyinstaller build.spec --clean --windowed
```
**Linux**:
```bash
pyinstaller build.spec --clean
```

## Important Files
- **Database**: Auto-creates `ktib_cashflow.db` locally. Delete this file to reset all data.
- **Logs**: Errors and events are logged to `ktib_cashflow.log`.

## License
MIT License
