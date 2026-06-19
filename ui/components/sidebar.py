import customtkinter as ctk
from ui.theme import DARK, THEME, FONTS
from services.auth_service import get_current_user, set_active_company
from services.company_service import get_company, get_all_companies
from services.account_service import get_accounts

# ─── Nav item definition ──────────────────────────────────────────────────────
NAV_GROUPS = [
    ("OVERVIEW", [
        ("dashboard",     "▪  Dashboard",        "📊"),
        ("cashflow",      "▪  Cash Flow",         "🌊"),
    ]),
    ("ACCOUNTING", [
        ("transactions",  "▪  Transactions",      "💳"),
        ("accounts",      "▪  Accounts",           "🏦"),
        ("planned",       "▪  Planned Payments",   "📅"),
        ("projects",      "▪  Projects",           "📁"),
    ]),
    ("ANALYTICS", [
        ("budgets",       "▪  Budgets",            "📊"),
        ("reports",       "▪  Reports",            "📈"),
        ("categories",    "▪  Categories",         "🏷️"),
    ]),
    ("SETTINGS", [
        ("settings",      "▪  Settings",           "⚙️"),
        ("ai",            "▪  AI Assistant",       "🤖"),
    ]),
]


class SidebarAccountRow(ctk.CTkFrame):
    """A rich, clickable row showing an account with color dot and balance."""

    def __init__(self, master, acc, on_click=None, **kwargs):
        super().__init__(master, fg_color="transparent", corner_radius=6,
                         height=34, **kwargs)
        self.pack_propagate(False)

        from ui.theme import validate_hex_color
        from services.currency_service import format_currency

        color = validate_hex_color(acc.get("color", THEME["blue"]), THEME["blue"])
        bal = acc.get("balance", 0)
        bal_color = THEME["green"] if bal >= 0 else THEME["red"]

        # Left indent line (visual child feel)
        indent = ctk.CTkFrame(self, width=1, fg_color=THEME["sidebar_hover"])
        indent.pack(side="left", fill="y", padx=(22, 0))

        dot = ctk.CTkFrame(self, width=7, height=7, corner_radius=4, fg_color=color)
        dot.pack(side="left", padx=(8, 6), pady=14)

        lbl_name = ctk.CTkLabel(self, text=acc["name"], font=FONTS["small"],
                                text_color=THEME["sidebar_text"], anchor="w")
        lbl_name.pack(side="left", fill="x", expand=True)

        bal_str = format_currency(bal, acc["currency"])
        lbl_bal = ctk.CTkLabel(self, text=bal_str, font=("Inter", 10, "normal"),
                               text_color=bal_color, anchor="e")
        lbl_bal.pack(side="right", padx=(0, 10))

        # Hover + click
        _all = [self, indent, dot, lbl_name, lbl_bal]
        for w in _all:
            w.bind("<Enter>", lambda e: self.configure(fg_color=THEME["sidebar_hover"]))
            w.bind("<Leave>", lambda e: self.configure(fg_color="transparent"))
            if on_click:
                w.bind("<Button-1>", lambda e: on_click())
                w.configure(cursor="hand2")


class SidebarNavButton(ctk.CTkFrame):
    """Nav button with a colored left-border indicator when active."""

    def __init__(self, master, label, icon, on_click, **kwargs):
        super().__init__(master, fg_color="transparent", corner_radius=6,
                         height=38, **kwargs)
        self.pack_propagate(False)
        self._on_click = on_click
        self._active = False

        # Left indicator bar
        self._bar = ctk.CTkFrame(self, width=3, corner_radius=2,
                                  fg_color="transparent")
        self._bar.pack(side="left", fill="y", padx=(6, 0), pady=6)

        # Icon label
        self._icon_lbl = ctk.CTkLabel(self, text=icon, font=("Segoe UI Emoji", 14),
                                       text_color=THEME["sidebar_text"], width=28)
        self._icon_lbl.pack(side="left", padx=(6, 2))

        # Text label
        self._text_lbl = ctk.CTkLabel(self, text=label, font=FONTS["body"],
                                       text_color=THEME["sidebar_text"], anchor="w")
        self._text_lbl.pack(side="left", fill="x", expand=True)

        # Bindings
        for w in [self, self._bar, self._icon_lbl, self._text_lbl]:
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)
            w.bind("<Button-1>", lambda e: self._on_click())
            w.configure(cursor="hand2")

    def _on_enter(self, e):
        if not self._active:
            self.configure(fg_color=THEME["sidebar_hover"])

    def _on_leave(self, e):
        if not self._active:
            self.configure(fg_color="transparent")

    def set_active(self, active: bool):
        self._active = active
        if active:
            self.configure(fg_color=THEME["sidebar_hover"])
            self._bar.configure(fg_color=THEME["green"])
            self._text_lbl.configure(text_color=THEME["sidebar_text_active"],
                                      font=("Inter", 13, "bold"))
            self._icon_lbl.configure(text_color=THEME["sidebar_text_active"])
        else:
            self.configure(fg_color="transparent")
            self._bar.configure(fg_color="transparent")
            self._text_lbl.configure(text_color=THEME["sidebar_text"],
                                      font=FONTS["body"])
            self._icon_lbl.configure(text_color=THEME["sidebar_text"])


class Sidebar(ctk.CTkFrame):
    def __init__(self, master, nav_callback, **kwargs):
        super().__init__(master, width=248, corner_radius=0,
                         fg_color=THEME["sidebar_bg"], **kwargs)
        self.nav_callback = nav_callback
        self.grid_propagate(False)
        self.pack_propagate(False)
        self._nav_widgets: dict[str, SidebarNavButton] = {}

        user = get_current_user()
        company = get_company(user["company_id"]) if user else None

        self.all_companies = get_all_companies()
        self.company_map = {c["name"]: c["id"] for c in self.all_companies}
        company_names = list(self.company_map.keys())

        company_name = (company["name"] if company
                        else (company_names[0] if company_names else "Workspace"))
        user_name = user["name"] if user else "Demo User"

        # ── Logo ─────────────────────────────────────────────────────────────
        logo_row = ctk.CTkFrame(self, fg_color="transparent")
        logo_row.pack(fill="x", padx=20, pady=(22, 14))

        logo_dot = ctk.CTkFrame(logo_row, width=10, height=10,
                                 corner_radius=5, fg_color=THEME["green"])
        logo_dot.pack(side="left", padx=(0, 8), pady=8)
        ctk.CTkLabel(logo_row, text="KTIB CashFlow", font=("Inter", 20, "bold"),
                     text_color=THEME["sidebar_text_active"]).pack(side="left")
        ctk.CTkLabel(logo_row, text="PRO", font=("Inter", 9, "bold"),
                     text_color=THEME["green"],
                     fg_color="#1a3a26", corner_radius=4,
                     padx=5, pady=2).pack(side="left", padx=(6, 0), pady=10)

        # ── Company Picker ────────────────────────────────────────────────────
        dropdown_options = (company_names + ["➕ Create Workspace..."]
                            if company_names else ["Workspace", "➕ Create Workspace..."])

        picker_outer = ctk.CTkFrame(self, fg_color=THEME["sidebar_hover"],
                                     corner_radius=10)
        picker_outer.pack(fill="x", padx=16, pady=(0, 8))

        ctk.CTkLabel(picker_outer, text="WORKSPACE", font=("Inter", 9, "bold"),
                     text_color=THEME["sidebar_text"]).pack(anchor="w", padx=12, pady=(8, 0))

        self.company_var = ctk.StringVar(value=company_name)
        self.company_picker = ctk.CTkOptionMenu(
            picker_outer, variable=self.company_var, values=dropdown_options,
            height=32, font=FONTS["body"], corner_radius=6,
            fg_color=THEME["sidebar_hover"], button_color=THEME["sidebar_hover"],
            button_hover_color=THEME["sidebar_hover"],
            text_color=THEME["sidebar_text_active"],
            dropdown_fg_color=THEME["sidebar_bg"],
            dropdown_text_color=THEME["sidebar_text_active"],
            dropdown_hover_color=THEME["sidebar_hover"],
            command=self._on_company_change)
        self.company_picker.pack(fill="x", padx=4, pady=(0, 8))

        # ── Total Balance Badge ───────────────────────────────────────────────
        if company:
            self._build_balance_badge(company)

        # ── Divider ───────────────────────────────────────────────────────────
        ctk.CTkFrame(self, height=1, fg_color=THEME["sidebar_hover"]).pack(
            fill="x", padx=16, pady=(4, 0))

        # ── User Profile (bottom) ─────────────────────────────────────────────
        self.bottom_frame = ctk.CTkFrame(self, fg_color=THEME["sidebar_hover"],
                                          corner_radius=10)
        self.bottom_frame.pack(side="bottom", fill="x", padx=16, pady=18)

        initials = "".join(p[0].upper() for p in user_name.split()[:2]) or "U"
        avatar = ctk.CTkFrame(self.bottom_frame, width=36, height=36,
                               corner_radius=18, fg_color=THEME["blue"])
        avatar.pack(side="left", padx=(12, 10), pady=10)
        avatar.pack_propagate(False)
        ctk.CTkLabel(avatar, text=initials, font=("Inter", 13, "bold"),
                     text_color="white").place(relx=0.5, rely=0.5, anchor="center")

        text_f = ctk.CTkFrame(self.bottom_frame, fg_color="transparent")
        text_f.pack(side="left", fill="both", expand=True, pady=10)

        self.user_label = ctk.CTkLabel(text_f, text=user_name, font=("Inter", 13, "bold"),
                                        text_color=THEME["sidebar_text_active"], anchor="w")
        self.user_label.pack(fill="x")

        role = user.get("role", "Admin").title() if user else "Admin"
        ctk.CTkLabel(text_f, text=role, font=FONTS["small"],
                     text_color=THEME["green"], anchor="w").pack(fill="x")

        # Online dot
        online_f = ctk.CTkFrame(self.bottom_frame, fg_color="transparent")
        online_f.pack(side="right", padx=12)
        ctk.CTkFrame(online_f, width=8, height=8, corner_radius=4,
                      fg_color=THEME["green"]).pack(pady=20)

        # ── Scrollable Nav ────────────────────────────────────────────────────
        self.nav_scrollable = ctk.CTkScrollableFrame(
            self, fg_color="transparent", corner_radius=0,
            scrollbar_button_color=THEME["sidebar_hover"],
            scrollbar_button_hover_color=THEME["sidebar_hover"])
        self.nav_scrollable.pack(side="top", expand=True, fill="both", pady=(4, 0))

        # Build navigation
        for group_name, items in NAV_GROUPS:
            self._add_group(group_name)
            for page_id, label, icon in items:
                self._add_nav_item(page_id, label, icon)

                # Inject account sub-rows after "accounts"
                if page_id == "accounts" and company:
                    accounts = get_accounts(company["id"])
                    for acc in accounts:
                        self._add_account_item(acc, "transactions")

    # ── Balance Badge ─────────────────────────────────────────────────────────
    def _build_balance_badge(self, company):
        from services.currency_service import format_currency, convert_to_base
        try:
            accounts = get_accounts(company["id"])
            bc = company.get("currency", "AZN")
            total = sum(
                float(convert_to_base(a["balance"], a["currency"], bc))
                for a in accounts
            )
            bal_str = format_currency(total, bc)
        except Exception:
            bal_str = "—"

        badge = ctk.CTkFrame(self, fg_color="#12332a", corner_radius=8)
        badge.pack(fill="x", padx=16, pady=(0, 8))

        ctk.CTkLabel(badge, text="TOTAL BALANCE", font=("Inter", 9, "bold"),
                     text_color=THEME["green"]).pack(anchor="w", padx=12, pady=(8, 0))
        ctk.CTkLabel(badge, text=bal_str, font=("Inter", 18, "bold"),
                     text_color=THEME["sidebar_text_active"]).pack(anchor="w", padx=12, pady=(2, 10))

    # ── Nav Builders ──────────────────────────────────────────────────────────
    def _add_group(self, name):
        ctk.CTkLabel(self.nav_scrollable, text=name,
                     font=("Inter", 10, "bold"),
                     text_color=THEME["sidebar_text"]).pack(
            anchor="w", padx=24, pady=(18, 4))

    def _add_nav_item(self, page_id, label, icon):
        # Strip the bullet prefix for display
        display = label.replace("▪  ", "")
        btn = SidebarNavButton(self.nav_scrollable, display, icon,
                               on_click=lambda p=page_id: self._on_nav_click(p))
        btn.pack(fill="x", padx=12, pady=2)
        self._nav_widgets[page_id] = btn

    # Keep backward compat so app.py's set_active still works
    @property
    def buttons(self):
        return {}

    def _add_account_item(self, acc, page_id):
        row = SidebarAccountRow(
            self.nav_scrollable, acc,
            on_click=lambda: self._on_sub_nav_click(page_id, initial_account_id=acc["id"]))
        row.pack(fill="x", padx=(12, 12), pady=1)

    # ── Callbacks ─────────────────────────────────────────────────────────────
    def _on_nav_click(self, page_id):
        self.set_active(page_id)
        self.nav_callback(page_id)

    def _on_sub_nav_click(self, page_id, **kwargs):
        self.set_active(page_id)
        self.nav_callback(page_id, **kwargs)

    def set_active(self, page_id):
        for pid, btn in self._nav_widgets.items():
            btn.set_active(pid == page_id)

    def _on_company_change(self, selected_name):
        if selected_name == "➕ Create Workspace...":
            current_user = get_current_user()
            current_company = get_company(current_user["company_id"]) if current_user else None
            current_name = (current_company["name"] if current_company
                            else list(self.company_map.keys())[0])
            self.company_var.set(current_name)
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
