import customtkinter as ctk
from ui.theme import DARK, THEME, FONTS
from services.auth_service import get_current_user, set_active_company
from services.company_service import get_company, get_all_companies
from services.account_service import get_accounts

class Sidebar(ctk.CTkFrame):
    def __init__(self, master, nav_callback, **kwargs):
        super().__init__(master, width=220, corner_radius=0, fg_color=THEME["sidebar_bg"], **kwargs)
        self.nav_callback = nav_callback
        self.grid_propagate(False)
        self.buttons = {}
        
        user = get_current_user()
        company = get_company(user["company_id"]) if user else None
        
        # Build company map for the dropdown
        self.all_companies = get_all_companies()
        self.company_map = {c["name"]: c["id"] for c in self.all_companies}
        company_names = list(self.company_map.keys())
        
        company_name = company["name"] if company else (company_names[0] if company_names else "Acme Corp")
        user_name = user["name"] if user else "Demo User"

        # Logo
        self.logo_label = ctk.CTkLabel(self, text="KTIB Cash Flow", font=FONTS["title"], text_color=THEME["green"])
        self.logo_label.pack(pady=(20, 10), padx=20, anchor="w")

        # Company Picker
        dropdown_options = company_names + ["➕ Create Workspace..."] if company_names else ["Acme Corp", "➕ Create Workspace..."]
        
        self.company_var = ctk.StringVar(value=company_name)
        self.company_picker = ctk.CTkOptionMenu(self, variable=self.company_var, values=dropdown_options,
                                                fg_color=THEME["sidebar_hover"], button_color=THEME["sidebar_hover"],
                                                button_hover_color=THEME["sidebar_hover"], text_color=THEME["sidebar_text_active"],
                                                dropdown_fg_color=THEME["sidebar_bg"], dropdown_text_color=THEME["sidebar_text_active"],
                                                dropdown_hover_color=THEME["sidebar_hover"],
                                                command=self._on_company_change)
        self.company_picker.pack(padx=20, pady=(0, 20), fill="x")

        self.divider = ctk.CTkFrame(self, height=1, fg_color=THEME["sidebar_hover"])
        self.divider.pack(fill="x", padx=20, pady=(0, 10))

        # Bottom Area (pack first with side="bottom" to pin it)
        self.bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.bottom_frame.pack(side="bottom", fill="x", padx=20, pady=20)

        self.user_label = ctk.CTkLabel(self.bottom_frame, text=user_name, font=FONTS["body"],
                                        text_color=THEME["sidebar_text"])
        self.user_label.pack(side="left")

        # Scrollable area for navigation
        self.nav_scrollable = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        self.nav_scrollable.pack(side="top", expand=True, fill="both")

        # Groups
        self._add_group("OVERVIEW")
        self._add_nav_item("📊 Dashboard", "dashboard")
        self._add_nav_item("🌊 Cash Flow", "cashflow")

        self._add_group("ACCOUNTING")
        self._add_nav_item("💳 Transactions", "transactions")
        self._add_nav_item("🏦 Accounts", "accounts")
        
        # Load Accounts as sub-items if company is set
        if company:
            from services.currency_service import format_currency
            accounts = get_accounts(company["id"])
            for acc in accounts:
                bal_str = format_currency(acc['balance'], acc['currency'])
                self._add_sub_nav_item(f"   • {acc['name']} ({bal_str})", "transactions", initial_account_id=acc['id'])
                
        self._add_nav_item("📅 Planned Payments", "planned")

        self._add_group("ANALYTICS")
        self._add_nav_item("📊 Budgets", "budgets")
        self._add_nav_item("📈 Reports", "reports")
        self._add_nav_item("🏷️ Categories", "categories")

        self._add_group("SETTINGS")
        self._add_nav_item("⚙️ Settings", "settings")
        self._add_nav_item("🤖 AI Assistant", "ai")

    def _add_group(self, name):
        lbl = ctk.CTkLabel(self.nav_scrollable, text=name, font=FONTS["small"], text_color=THEME["sidebar_text"])
        lbl.pack(anchor="w", padx=20, pady=(15, 5))

    def _add_nav_item(self, label, page_id):
        btn = ctk.CTkButton(self.nav_scrollable, text=label, font=FONTS["body"],
                            fg_color="transparent", text_color=THEME["sidebar_text"],
                            anchor="w", hover_color=THEME["sidebar_hover"],
                            command=lambda p=page_id: self._on_nav_click(p))
        btn.pack(pady=2, padx=10, fill="x")
        self.buttons[page_id] = btn

    def _add_sub_nav_item(self, label, page_id, **kwargs):
        btn = ctk.CTkButton(self.nav_scrollable, text=label, font=FONTS["small"],
                            fg_color="transparent", text_color=THEME["sidebar_text"],
                            anchor="w", hover_color=THEME["sidebar_hover"],
                            command=lambda p=page_id, kw=kwargs: self._on_sub_nav_click(p, **kw))
        btn.pack(pady=1, padx=(10, 10), fill="x")
        # We add it to self.buttons so it can still be 'active' if needed, 
        # or we could skip it. Let's just track it for visual consistency if they click it.
        # But since they all map to "transactions", it might highlight all of them.
        # Better to just let the main 'transactions' button handle the highlight.

    def _on_sub_nav_click(self, page_id, **kwargs):
        self.set_active(page_id)
        self.nav_callback(page_id, **kwargs)

    def _on_nav_click(self, page_id):
        self.set_active(page_id)
        self.nav_callback(page_id)

    def set_active(self, page_id):
        for pid, btn in self.buttons.items():
            if pid == page_id:
                btn.configure(fg_color=THEME["sidebar_hover"], text_color=THEME["sidebar_text_active"], hover_color=THEME["sidebar_hover"])
            else:
                btn.configure(fg_color="transparent", text_color=THEME["sidebar_text"], hover_color=THEME["sidebar_hover"])

    def _on_company_change(self, selected_name):
        if selected_name == "➕ Create Workspace...":
            # Revert the dropdown visual selection back to the current company
            current_user = get_current_user()
            current_company = get_company(current_user["company_id"]) if current_user else None
            current_name = current_company["name"] if current_company else list(self.company_map.keys())[0]
            self.company_var.set(current_name)
            
            # Open the Add Workspace Modal
            from ui.modals.add_workspace import AddWorkspaceModal
            AddWorkspaceModal(self.master, on_success=self._on_workspace_created)
            return

        company_id = self.company_map.get(selected_name)
        if company_id:
            set_active_company(company_id)
            self.master.event_generate("<<CompanyChanged>>")

    def _on_workspace_created(self, new_company_id):
        set_active_company(new_company_id)
        self.master.event_generate("<<CompanyChanged>>")
