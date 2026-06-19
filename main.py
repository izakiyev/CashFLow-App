import sys
import os
import shutil
import logging
import warnings
from tkinter import messagebox
from datetime import datetime

# Suppress non-critical matplotlib layout warnings (e.g. tight_layout with external legends)
warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib")

# Ensure app directory is in the python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import LOG_PATH, DB_PATH, BACKUP_DIR
from ui.app import KTIBCashFlowApp
from database.migrations import run_migrations
from database.seed import seed_database

def setup_logging():
    from logging.handlers import RotatingFileHandler
    
    logger = logging.getLogger("")
    logger.setLevel(logging.INFO)
    
    # Rotating file handler
    file_handler = RotatingFileHandler(
        LOG_PATH, maxBytes=5*1024*1024, backupCount=3
    )
    file_format = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)
    
    # Console handler
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console_format = logging.Formatter("%(levelname)s: %(message)s")
    console.setFormatter(console_format)
    logger.addHandler(console)

def backup_database():
    """Creates a timestamped backup of the SQLite database on each launch.
    Keeps only the 7 most recent backups to limit disk usage.
    """
    logger = logging.getLogger("KTIB_CashFlow")
    if not DB_PATH.exists():
        return  # Nothing to back up yet (first launch)
    try:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = BACKUP_DIR / f"ktib_cashflow_{stamp}.db"
        shutil.copy2(DB_PATH, dest)
        logger.info(f"Database backed up to {dest}")

        # Prune old backups — keep only the 7 most recent
        backups = sorted(BACKUP_DIR.glob("ktib_cashflow_*.db"))
        for old in backups[:-7]:
            old.unlink()
            logger.info(f"Pruned old backup: {old.name}")
    except Exception as e:
        logger.warning(f"Database backup failed (non-fatal): {e}")

def check_online_access():
    import urllib.request
    import json
    import tkinter as tk
    import time
    
    # We use the raw URL WITHOUT the commit hash and add a timestamp to bypass GitHub's 5-minute cache
    base_url = "https://gist.githubusercontent.com/izakiyev/588ff634cfff86bd3d45afb85cf19beb/raw/gistfile1.txt"
    url = f"{base_url}?t={int(time.time())}"
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            if data.get("status") != "active":
                msg = data.get("message", "Access revoked by administrator.")
                
                # Show error before main GUI starts
                root = tk.Tk()
                root.withdraw()
                messagebox.showerror("Access Denied", msg)
                sys.exit(1)
    except Exception as e:
        # If no internet, we fail OPEN (allow access) to prevent locking out valid offline users
        logging.getLogger("KTIB_CashFlow").warning(f"Could not verify online access (offline mode assumed): {e}")

def main():
    setup_logging()
    logger = logging.getLogger("KTIB_CashFlow")
    
    try:
        logger.info("Starting KTIB Cash Flow application...")
        
        # 0. Check online kill-switch
        check_online_access()
        
        # 1. Initialize DB and run migrations
        run_migrations()
        
        # 2. Back up the database before touching it this session
        backup_database()

        # 3. Seed default user/company if missing
        seed_database()

        # 3. Launch GUI
        logger.info("Launching GUI...")
        app = KTIBCashFlowApp()
        app.mainloop()
    except Exception as e:
        logger.exception(f"A fatal error occurred: {e}")
        messagebox.showerror("Critical Error", f"The application failed to start:\n\n{e}")
        sys.exit(1)

if __name__ == "__main__":
    main()