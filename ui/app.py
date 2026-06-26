import customtkinter as ctk
from ui.theme import DARK, LIGHT
from ui.components.sidebar import Sidebar
from ui.pages.dashboard_page import DashboardPage
from ui.pages.cashflow_page import CashFlowPage
from ui.pages.transactions_page import TransactionsPage
from ui.pages.accounts_page import AccountsPage
from ui.pages.planned_page import PlannedPage
from ui.pages.reports_page import ReportsPage
from ui.pages.categories_page import CategoriesPage
from ui.pages.budgets_page import BudgetsPage
from ui.pages.projects_page import ProjectsPage
from ui.pages.settings_page import SettingsPage
from ui.pages.ai_assistant_page import AIAssistantPage
from ui.pages.setup_page import SetupWorkspaceScreen
from services.auth_service import auto_login, get_current_user, logout
from ui.modals.add_transaction import AddTransactionModal
from ui.components.command_palette import CommandPalette


class KTIBCashFlowApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("KTIB Cash Flow — Financial Management")
        self.geometry("1400x800")
        self.minsize(1200, 700)
        ctk.set_appearance_mode("Light")
        self._theme = "Light"
        
        # Set window icon
        from config import get_resource_path
        import os
        icon_path = get_resource_path(os.path.join("assets", "logo.ico"))
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)

        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        self.sidebar_frame = None
        self.main_container = ctk.CTkFrame(self, corner_radius=0, fg_color=LIGHT["bg_primary"])
        self.main_container.grid(row=0, column=0, columnspan=2, sticky="nsew")
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)
        
        # Keyboard Shortcuts
        self.bind("<Control-n>", self._shortcut_new_transaction)
        self.bind("<Control-t>", lambda e: self.show_page("transactions"))
        self.bind("<Control-d>", lambda e: self.show_page("dashboard"))
        self.bind("<Control-r>", lambda e: self.show_page("reports"))
        self.bind("<Control-k>", self._open_command_palette)
        self.bind("<Control-q>", lambda e: self.quit())
        
        # Presentation Mode / Zoom Scaling
        self.current_scaling = 1.0
        self.bind("<Control-equal>", self._zoom_in)
        self.bind("<Control-minus>", self._zoom_out)
        self.bind("<Control-0>", self._zoom_reset)
        self.bind("<Control-KP_Add>", self._zoom_in)
        self.bind("<Control-KP_Subtract>", self._zoom_out)
        
        self.current_page_name = "dashboard"
        
        # Global event: refresh entire app when company settings (e.g., currency) change
        self.bind("<<CompanyChanged>>", lambda e: self.show_page(self.current_page_name))
        # Global event: redirect to setup screen when all workspaces have been deleted
        self.bind("<<ShowSetup>>", lambda e: self._show_setup())

        user = auto_login()

        # Show onboarding if no user at all, or user exists but has no workspace
        if not user or not user.get("company_id"):
            self._show_setup()
        else:
            self.show_page(self.current_page_name)

    def _show_setup(self):
        """Show the manual workspace setup / onboarding screen."""
        for widget in self.main_container.winfo_children():
            widget.destroy()
        if self.sidebar_frame:
            self.sidebar_frame.destroy()
            self.sidebar_frame = None

        # Expand main_container to fill the full window
        self.main_container.grid(row=0, column=0, columnspan=2, sticky="nsew")

        setup = SetupWorkspaceScreen(self.main_container, on_complete=self._on_setup_complete)
        setup.pack(fill="both", expand=True)

    def _on_setup_complete(self):
        """Called by SetupWorkspaceScreen after user successfully creates a workspace."""
        self.show_page("dashboard")

    def _on_theme_change(self, value):
        """Called by SettingsPage when user changes theme."""
        self._theme = value
        is_dark = (value == "Dark") or (value == "System" and ctk.get_appearance_mode() == "Dark")
        bg = DARK["bg_primary"] if is_dark else LIGHT["bg_primary"]
        self.configure(fg_color=bg)
        self.main_container.configure(fg_color=bg)

    def _shortcut_new_transaction(self, event):
        user = get_current_user()
        if user and user.get("company_id"):
            AddTransactionModal(self, user["company_id"], self._refresh_current_page)

    def _refresh_current_page(self):
        if hasattr(self, 'current_page') and hasattr(self.current_page, 'refresh'):
            self.current_page.refresh()

    def _open_command_palette(self, event=None):
        """Open the Ctrl+K command palette."""
        user = get_current_user()
        if not user or not user.get("company_id"):
            return
        CommandPalette(self, nav_callback=self.show_page,
                       action_callback=self._handle_palette_action)

    def _handle_palette_action(self, action):
        """Handle non-navigation actions from the command palette."""
        if action == "new_tx":
            self._shortcut_new_transaction(None)

    def show_page(self, page_name, **kwargs):
        user = get_current_user()

        # If user has no active workspace, redirect to setup
        if not user or not user.get("company_id"):
            self._show_setup()
            return
            
        # Clear main container
        for widget in self.main_container.winfo_children():
            widget.destroy()
            
        self.rebuild_sidebar()
        self.main_container.grid(row=0, column=1, columnspan=1, sticky="nsew")

        # Route pages
        self.current_page_name = page_name
        if page_name == "dashboard":
            self.current_page = DashboardPage(self.main_container, user["company_id"])
        elif page_name == "cashflow":
            self.current_page = CashFlowPage(self.main_container, user["company_id"])
        elif page_name == "transactions":
            self.current_page = TransactionsPage(self.main_container, user["company_id"], **kwargs)
        elif page_name == "accounts":
            self.current_page = AccountsPage(self.main_container, user["company_id"])
        elif page_name == "planned":
            self.current_page = PlannedPage(self.main_container, user["company_id"])
        elif page_name == "reports":
            self.current_page = ReportsPage(self.main_container, user["company_id"])
        elif page_name == "categories":
            self.current_page = CategoriesPage(self.main_container, user["company_id"])
        elif page_name == "budgets":
            self.current_page = BudgetsPage(self.main_container, user["company_id"])
        elif page_name == "projects":
            self.current_page = ProjectsPage(self.main_container, user["company_id"])
        elif page_name == "settings":
            self.current_page = SettingsPage(self.main_container, user["company_id"],
                                             on_theme_change=self._on_theme_change)
        elif page_name == "ai":
            self.current_page = AIAssistantPage(self.main_container, user["company_id"])
            
        self.current_page.pack(fill="both", expand=True)

    def rebuild_sidebar(self):
        user = get_current_user()
        if not user:
            return
        if self.sidebar_frame:
            self.sidebar_frame.destroy()
        self.sidebar_frame = Sidebar(self, self.show_page)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.set_active(getattr(self, 'current_page_name', 'dashboard'))
        self.sidebar_frame.user_label.configure(text=user.get("name", "Demo User"))

    # ── Presentation Mode Zoom ───────────────────────────────────────────────
    def _zoom_in(self, event=None):
        self.current_scaling = min(2.5, self.current_scaling + 0.1)
        ctk.set_widget_scaling(self.current_scaling)
        
    def _zoom_out(self, event=None):
        self.current_scaling = max(0.5, self.current_scaling - 0.1)
        ctk.set_widget_scaling(self.current_scaling)

    def _zoom_reset(self, event=None):
        self.current_scaling = 1.0
        ctk.set_widget_scaling(self.current_scaling)