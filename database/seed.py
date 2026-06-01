import logging

logger = logging.getLogger(__name__)

def seed_database():
    """
    No longer auto-seeds a default user or company.
    First-time setup is handled manually via the onboarding screen (SetupWorkspaceScreen).
    This function is kept for backward compatibility with main.py.
    """
    logger.info("Seed step skipped — manual onboarding is required for new users.")
