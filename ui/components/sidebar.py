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
        ("projects",      "▪  Projects",           "📁"),
    ]),
    ("ANALYTICS", [
        ("budgets",       "▪  Budgets",            "📊"),
        ("reports",       "▪  Reports",            "📈"),
        ("categories",    "▪  Clients",         "🏷️"),
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

    def __init__(self, master, label, icon, on_click, collapsed=False, **kwargs):
        super().__init__(master, fg_color="transparent", corner_radius=6,
                         height=38, **kwargs)
        self.pack_propagate(False)
        self._on_click = on_click
        self._active = False
        self._label_text = label

        # Left indicator bar
        self._bar = ctk.CTkFrame(self, width=3, corner_radius=2,
                                  fg_color="transparent")
        self._bar.pack(side="left", fill="y", padx=(6, 0), pady=6)

        # Icon label
        self._icon_lbl = ctk.CTkLabel(self, text=icon, font=("Segoe UI Emoji", 14),
                                       text_color=THEME["sidebar_text"], width=28)
        self._icon_lbl.pack(side="left", padx=(6, 2))

        # Text label (only in expanded mode)
        if not collapsed:
            self._text_lbl = ctk.CTkLabel(self, text=label, font=FONTS["body"],
                                           text_color=THEME["sidebar_text"], anchor="w")
            self._text_lbl.pack(side="left", fill="x", expand=True)
        else:
            self._text_lbl = None

        # Bindings
        clickables = [self, self._bar, self._icon_lbl]
        if self._text_lbl:
            clickables.append(self._text_lbl)
        for w in clickables:
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
            if self._text_lbl:
                self._text_lbl.configure(text_color=THEME["sidebar_text_active"],
                                          font=("Inter", 13, "bold"))
            self._icon_lbl.configure(text_color=THEME["sidebar_text_active"])
        else:
            self.configure(fg_color="transparent")
            self._bar.configure(fg_color="transparent")
            if self._text_lbl:
                self._text_lbl.configure(text_color=THEME["sidebar_text"],
                                          font=FONTS["body"])
            self._icon_lbl.configure(text_color=THEME["sidebar_text"])


class Sidebar(ctk.CTkFrame):
    EXPANDED_WIDTH = 248
    COLLAPSED_WIDTH = 64

    # Class-level state so collapse persists across rebuilds
    _is_collapsed = False

    def __init__(self, master, nav_callback, **kwargs):
        collapsed = Sidebar._is_collapsed
        width = self.COLLAPSED_WIDTH if collapsed else self.EXPANDED_WIDTH

        super().__init__(master, width=width, corner_radius=0,
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
        logo_row.pack(fill="x", padx=12, pady=(18, 10))

        self._toggle_btn = ctk.CTkButton(
            logo_row, text="☰" if collapsed else "≡",
            width=32, height=32, corner_radius=8,
            fg_color="transparent", hover_color=THEME["sidebar_hover"],
            text_color=THEME["sidebar_text"], font=("Inter", 18, "bold"),
            command=self._toggle_collapse)
        self._toggle_btn.pack(side="left", padx=(0, 6))

        if not collapsed:
            ctk.CTkLabel(logo_row, text="KTIB CashFlow", font=("Inter", 17, "bold"),
                         text_color=THEME["sidebar_text_active"]).pack(side="left")
            ctk.CTkLabel(logo_row, text="PRO", font=("Inter", 9, "bold"),
                         text_color=THEME["green"],
                         fg_color="#1a3a26", corner_radius=4,
                         padx=5, pady=2).pack(side="left", padx=(6, 0), pady=10)

        # ── Company Picker (expanded only) ────────────────────────────────────
        if not collapsed:
            dropdown_options = (company_names + ["➕ Create Workspace..."]
                                if company_names else ["Workspace", "➕ Create Workspace..."])

            picker_outer = ctk.CTkFrame(self, fg_color=THEME["sidebar_hover"],
                                         corner_radius=6)
            picker_outer.pack(fill="x", padx=16, pady=(0, 4))

            ctk.CTkLabel(picker_outer, text="WORKSPACE", font=("Inter", 9, "bold"),
                         text_color=THEME["sidebar_text"]).pack(anchor="w", padx=12, pady=(4, 0))

            self.company_var = ctk.StringVar(value=company_name)
            self.company_picker = ctk.CTkOptionMenu(
                picker_outer, variable=self.company_var, values=dropdown_options,
                height=26, font=("Inter", 11, "bold"), corner_radius=4,
                fg_color=THEME["sidebar_hover"], button_color=THEME["sidebar_hover"],
                button_hover_color=THEME["sidebar_hover"],
                text_color=THEME["sidebar_text_active"],
                dropdown_fg_color=THEME["sidebar_bg"],
                dropdown_text_color=THEME["sidebar_text_active"],
                dropdown_hover_color=THEME["sidebar_hover"],
                command=self._on_company_change)
            self.company_picker.pack(fill="x", padx=6, pady=(0, 4))

            # ── Badges ────────────────────────────────────────────────────────
            if company:
                self._build_balance_badge(company)
                self._build_projected_badge(company)

        # ── Divider ───────────────────────────────────────────────────────────
        ctk.CTkFrame(self, height=1, fg_color=THEME["sidebar_hover"]).pack(
            fill="x", padx=16 if not collapsed else 8, pady=(4, 0))

        # ── User Profile (bottom) ─────────────────────────────────────────────
        self.bottom_frame = ctk.CTkFrame(self, fg_color=THEME["sidebar_hover"],
                                          corner_radius=6)
        self.bottom_frame.pack(side="bottom", fill="x",
                               padx=16 if not collapsed else 8,
                               pady=(4, 8))

        initials = "".join(p[0].upper() for p in user_name.split()[:2]) or "U"
        avatar = ctk.CTkFrame(self.bottom_frame, width=24, height=24,
                               corner_radius=12, fg_color=THEME["blue"])
        avatar.pack(side="left", padx=(8, 6) if not collapsed else (4, 4), pady=6)
        avatar.pack_propagate(False)
        ctk.CTkLabel(avatar, text=initials, font=("Inter", 9, "bold"),
                     text_color="white").place(relx=0.5, rely=0.5, anchor="center")

        if not collapsed:
            text_f = ctk.CTkFrame(self.bottom_frame, fg_color="transparent")
            text_f.pack(side="left", fill="both", expand=True, pady=4)

            self.user_label = ctk.CTkLabel(text_f, text=user_name, font=("Inter", 11, "bold"),
                                            text_color=THEME["sidebar_text_active"], anchor="w", height=12)
            self.user_label.pack(fill="x")

            role = user.get("role", "Admin").title() if user else "Admin"
            ctk.CTkLabel(text_f, text=role, font=("Inter", 9),
                         text_color=THEME["green"], anchor="w", height=12).pack(fill="x", pady=(0, 2))

            # Online dot
            online_f = ctk.CTkFrame(self.bottom_frame, fg_color="transparent")
            online_f.pack(side="right", padx=8)
            ctk.CTkFrame(online_f, width=6, height=6, corner_radius=3,
                          fg_color=THEME["green"]).pack(pady=6)
        else:
            # Still need user_label for app.py compatibility
            self.user_label = ctk.CTkLabel(self.bottom_frame, text="", height=0)

        # ── Scrollable Nav ────────────────────────────────────────────────────
        self.nav_scrollable = ctk.CTkScrollableFrame(
            self, fg_color="transparent", corner_radius=0,
            scrollbar_button_color=THEME["sidebar_hover"],
            scrollbar_button_hover_color=THEME["sidebar_hover"])
        self.nav_scrollable.pack(side="top", expand=True, fill="both", pady=(4, 0))

        # Build navigation
        for group_name, items in NAV_GROUPS:
            if not collapsed:
                self._add_group(group_name)
            for page_id, label, icon in items:
                self._add_nav_item(page_id, label, icon, collapsed)

                # Inject account sub-rows after "accounts" (expanded only)
                if not collapsed and page_id == "accounts" and company:
                    accounts = get_accounts(company["id"])
                    for acc in accounts:
                        self._add_account_item(acc, "transactions")

    # ── Collapse / Expand ─────────────────────────────────────────────────────
    def _toggle_collapse(self):
        Sidebar._is_collapsed = not Sidebar._is_collapsed
        if hasattr(self.master, "rebuild_sidebar"):
            self.master.rebuild_sidebar()

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

        badge = ctk.CTkFrame(self, fg_color="#12332a", corner_radius=6)
        badge.pack(fill="x", padx=16, pady=(0, 4))

        ctk.CTkLabel(badge, text="TOTAL BALANCE", font=("Inter", 9, "bold"),
                     text_color=THEME["green"]).pack(anchor="w", padx=12, pady=(4, 0))
        ctk.CTkLabel(badge, text=bal_str, font=("Inter", 14, "bold"),
                     text_color=THEME["sidebar_text_active"]).pack(anchor="w", padx=12, pady=(0, 4))

    def _build_projected_badge(self, company):
        from services.currency_service import format_currency
        from services.transaction_service import get_projected_balance
        try:
            proj = get_projected_balance(company["id"])
            bc = proj.get("base_currency", "AZN")
            val_30d = proj.get("projected_balance_30d", 0)
            val_90d = proj.get("projected_balance_90d", 0)
            self._str_30 = format_currency(val_30d, bc)
            self._str_90 = format_currency(val_90d, bc)
        except Exception:
            self._str_30 = "—"
            self._str_90 = "—"

        badge = ctk.CTkFrame(self, fg_color="#312213", corner_radius=6)
        badge.pack(fill="x", padx=16, pady=(0, 4))

        top_row = ctk.CTkFrame(badge, fg_color="transparent")
        top_row.pack(fill="x", padx=12, pady=(4, 0))
        
        ctk.CTkLabel(top_row, text="PROJECTION", font=("Inter", 9, "bold"),
                     text_color=THEME["amber"]).pack(side="left")
                     
        self.proj_var = ctk.StringVar(value="30 Days")
        menu = ctk.CTkOptionMenu(top_row, variable=self.proj_var, values=["30 Days", "90 Days"],
                                 width=60, height=20, font=("Inter", 9, "bold"),
                                 fg_color="#312213", button_color="#312213",
                                 button_hover_color="#312213",
                                 text_color=THEME["amber"],
                                 dropdown_fg_color="#312213",
                                 dropdown_text_color=THEME["amber"],
                                 command=self._on_proj_change)
        menu.pack(side="right")

        self.proj_val_label = ctk.CTkLabel(badge, text=self._str_30, font=("Inter", 14, "bold"),
                                           text_color=THEME["sidebar_text_active"])
        self.proj_val_label.pack(anchor="w", padx=12, pady=(0, 4))

    def _on_proj_change(self, choice):
        if hasattr(self, "proj_val_label") and self.proj_val_label.winfo_exists():
            if choice == "30 Days":
                self.proj_val_label.configure(text=getattr(self, "_str_30", "—"))
            else:
                self.proj_val_label.configure(text=getattr(self, "_str_90", "—"))

    # ── Nav Builders ──────────────────────────────────────────────────────────
    def _add_group(self, name):
        ctk.CTkLabel(self.nav_scrollable, text=name,
                     font=("Inter", 10, "bold"),
                     text_color=THEME["sidebar_text"]).pack(
            anchor="w", padx=24, pady=(18, 4))

    def _add_nav_item(self, page_id, label, icon, collapsed=False):
        display = label.replace("▪  ", "")
        btn = SidebarNavButton(self.nav_scrollable, display, icon,
                               on_click=lambda p=page_id: self._on_nav_click(p),
                               collapsed=collapsed)
        btn.pack(fill="x", padx=12 if not collapsed else 4, pady=2)
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
