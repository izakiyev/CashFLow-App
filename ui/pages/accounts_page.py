import customtkinter as ctk
from ui.theme import THEME, FONTS
from ui.components.topbar import Topbar
from services.account_service import get_accounts, get_accounts_summary, delete_account
from services.currency_service import format_currency
from ui.modals.add_account import AddAccountModal
from ui.components.chart_frame import ChartFrame
from ui.modals.confirm_dialog import ConfirmDialog
from ui.components.toast import Toast
from ui.utils.thread_worker import ThreadWorker

ACCOUNT_TYPES = ["All", "Bank", "Cash", "Credit Card", "Investment", "Other"]


class AccountCard(ctk.CTkFrame):
    """Premium hoverable account card."""
    def __init__(self, master, account: dict, on_delete, on_edit, **kwargs):
        super().__init__(master, fg_color=THEME["bg_secondary"], corner_radius=12,
                         border_width=1, border_color=THEME["border"], **kwargs)
        self.account = account
        self.on_delete = on_delete
        self.on_edit = on_edit

        # Coloured accent bar at top
        accent = ctk.CTkFrame(self, fg_color=account["color"] or THEME["blue"], height=5, corner_radius=0)
        accent.pack(fill="x", side="top")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=14)

        # Top row: name + type badge
        top_row = ctk.CTkFrame(body, fg_color="transparent")
        top_row.pack(fill="x")

        ctk.CTkLabel(top_row, text=account["name"], font=FONTS["heading"],
                     text_color=THEME["text_primary"]).pack(side="left")

        badge = ctk.CTkFrame(top_row, fg_color=THEME["bg_tertiary"], corner_radius=6)
        badge.pack(side="right")
        ctk.CTkLabel(badge, text=account["type"].upper(), font=FONTS["small"],
                     text_color=THEME["text_secondary"]).pack(padx=8, pady=3)

        # Balance — show with the account's own currency symbol
        bal = account["balance"]
        bal_color = THEME["green"] if bal >= 0 else THEME["red"]
        ctk.CTkLabel(body, text=format_currency(bal, account['currency']),
                     font=FONTS["title"], text_color=bal_color).pack(anchor="w", pady=(10, 0))

        # Currency label if non-base
        ctk.CTkLabel(body, text=account["currency"], font=FONTS["small"],
                     text_color=THEME["text_tertiary"]).pack(anchor="w")

        # Identifier (e.g., account number)
        if account.get("identifier"):
            ctk.CTkLabel(body, text=account["identifier"], font=FONTS["small"],
                         text_color=THEME["text_tertiary"]).pack(anchor="w")

        # Actions row
        actions = ctk.CTkFrame(body, fg_color="transparent")
        actions.pack(fill="x", pady=(14, 0))

        ctk.CTkButton(actions, text="🗑 Delete", width=80, height=28, font=FONTS["small"],
                      fg_color="transparent", text_color=THEME["red"],
                      hover_color=THEME["red_light"],
                      command=lambda: self.on_delete(account["id"])).pack(side="right")

        ctk.CTkButton(actions, text="✏️ Edit", width=70, height=28, font=FONTS["small"],
                      fg_color="transparent", text_color=THEME["blue"],
                      hover_color=THEME["bg_tertiary"],
                      command=lambda: self.on_edit(account)).pack(side="right", padx=(0, 5))

        # Hover effect
        for widget in [self, body, top_row, actions]:
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)

    def _on_enter(self, _):
        self.configure(border_color=THEME["blue"])

    def _on_leave(self, _):
        self.configure(border_color=THEME["border"])


class AccountsPage(ctk.CTkFrame):
    def __init__(self, master, company_id, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.company_id = company_id
        self._active_type_filter = "All"
        self._active_search = ""
        self._show_archived = False

        self.topbar = Topbar(self, title="Accounts")
        self.topbar.pack(fill="x")
        self.topbar.add_action("+ Add Account", self._add_account, primary=True)

        self._build_filter_bar()

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=20, pady=10)

        # KPI row
        self.kpi_row = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.kpi_row.pack(fill="x", pady=(0, 20))
        for i in range(4):
            self.kpi_row.grid_columnconfigure(i, weight=1)

        self.kpi_assets = self._make_kpi(self.kpi_row, "Total Assets",       THEME["green"], 0)
        self.kpi_liab   = self._make_kpi(self.kpi_row, "Total Liabilities",   THEME["red"],   1)
        self.kpi_net    = self._make_kpi(self.kpi_row, "Net Worth",            THEME["blue"],  2)
        self.kpi_count  = self._make_kpi(self.kpi_row, "Active Accounts",     THEME["text_primary"], 3)

        # Split layout: cards left, chart right
        self.split = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.split.pack(fill="both", expand=True)
        self.split.grid_columnconfigure(0, weight=2)
        self.split.grid_columnconfigure(1, weight=1)
        self.split.grid_rowconfigure(0, weight=1)

        # Cards grid
        self.cards_frame = ctk.CTkFrame(self.split, fg_color="transparent")
        self.cards_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        for i in range(2):
            self.cards_frame.grid_columnconfigure(i, weight=1)

        # Chart panel
        self.chart_panel = ctk.CTkFrame(self.split, fg_color=THEME["bg_secondary"],
                                         corner_radius=10, border_width=1, border_color=THEME["border"])
        self.chart_panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        ctk.CTkLabel(self.chart_panel, text="Asset Distribution",
                     font=FONTS["heading"], text_color=THEME["text_primary"]).pack(anchor="w", padx=16, pady=(16, 4))
        self.chart = ChartFrame(self.chart_panel)
        self.chart.pack(fill="both", expand=True, padx=10, pady=10)

        self.refresh()

    # ─── Filter Bar ───────────────────────────────────────────────────────────
    def _build_filter_bar(self):
        bar = ctk.CTkFrame(self, fg_color=THEME["bg_secondary"], corner_radius=0, height=44)
        bar.pack(fill="x", padx=0, pady=0)
        bar.pack_propagate(False)

        inner = ctk.CTkFrame(bar, fg_color="transparent")
        inner.pack(side="left", padx=20, pady=6)

        from ui.components.search_bar import SearchBar
        self.search_bar = SearchBar(inner, self._on_search)
        self.search_bar.pack(side="left", padx=(0, 15))

        ctk.CTkLabel(inner, text="Type:", font=FONTS["small"],
                     text_color=THEME["text_tertiary"]).pack(side="left", padx=(0, 8))

        self._type_btns = {}
        for atype in ACCOUNT_TYPES:
            is_active = (atype == "All")
            btn = ctk.CTkButton(
                inner, text=atype, height=28, font=FONTS["small"],
                fg_color=THEME["blue"] if is_active else THEME["bg_tertiary"],
                hover_color=THEME["blue"] if is_active else THEME["border"],
                text_color=THEME["text_primary"],
                command=lambda t=atype: self._apply_type_filter(t)
            )
            btn.pack(side="left", padx=3)
            self._type_btns[atype] = btn

        # Archived toggle on the right
        self._archived_btn = ctk.CTkButton(
            bar, text="Show Archived", height=28, font=FONTS["small"], width=120,
            fg_color=THEME["bg_tertiary"], hover_color=THEME["border"],
            text_color=THEME["text_tertiary"],
            command=self._toggle_archived
        )
        self._archived_btn.pack(side="right", padx=20)

    def _apply_type_filter(self, atype):
        self._active_type_filter = atype
        for t, btn in self._type_btns.items():
            is_active = (t == atype)
            btn.configure(
                fg_color=THEME["blue"] if is_active else THEME["bg_tertiary"],
                hover_color=THEME["blue"] if is_active else THEME["border"]
            )
        self.refresh()

    def _on_search(self, query):
        if hasattr(self, '_search_after_id') and self._search_after_id:
            try:
                self.after_cancel(self._search_after_id)
            except Exception:
                pass
        self._active_search = query.lower()
        self._search_after_id = self.after(400, self.refresh)

    def _toggle_archived(self):
        self._show_archived = not self._show_archived
        if self._show_archived:
            self._archived_btn.configure(
                text="Hide Archived", fg_color=THEME["amber"],
                hover_color=THEME["amber_light"], text_color=THEME["text_primary"]
            )
        else:
            self._archived_btn.configure(
                text="Show Archived", fg_color=THEME["bg_tertiary"],
                hover_color=THEME["border"], text_color=THEME["text_tertiary"]
            )
        self.refresh()

    # ─── Helpers ──────────────────────────────────────────────────────────────
    def _make_kpi(self, parent, title, color, col):
        card = ctk.CTkFrame(parent, fg_color=THEME["bg_secondary"], corner_radius=10,
                             border_width=1, border_color=THEME["border"])
        card.grid(row=0, column=col, sticky="ew", padx=5)
        ctk.CTkLabel(card, text=title, font=FONTS["body"],
                     text_color=THEME["text_secondary"]).pack(anchor="w", padx=16, pady=(12, 0))
        lbl = ctk.CTkLabel(card, text="—", font=FONTS["title"], text_color=color)
        lbl.pack(anchor="w", padx=16, pady=(0, 14))
        return lbl

    def _add_account(self):
        AddAccountModal(self.winfo_toplevel(), self.company_id, self.refresh)

    # ─── Async Data & Render ──────────────────────────────────────────────────
    def refresh(self):
        if not self.company_id:
            return
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
            
        # Clear current rows and show loading
        for w in self.cards_frame.winfo_children():
            w.destroy()
            
        self._loading_lbl = ctk.CTkLabel(
            self.cards_frame, text="Loading accounts...",
            font=FONTS["body"], text_color=THEME["text_tertiary"]
        )
        self._loading_lbl.grid(row=0, column=0, columnspan=2, pady=40)
        
        ThreadWorker(self, self._fetch_data, on_success=self._update_ui)

    def _fetch_data(self):
        accounts = get_accounts(self.company_id, include_archived=self._show_archived)
        summary = get_accounts_summary(self.company_id)
        return {"accounts": accounts, "summary": summary}

    def _update_ui(self, data):
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return

        accounts = data["accounts"]
        summary = data["summary"]
        bc = summary["base_currency"]

        # ── KPIs (correctly currency-converted) ──
        self.kpi_assets.configure(text=format_currency(summary["assets"], bc),
                                  text_color=THEME["green"])
        self.kpi_liab.configure(text=format_currency(summary["liabilities"], bc),
                                text_color=THEME["red"])
        net = summary["net_worth"]
        self.kpi_net.configure(text=format_currency(net, bc),
                               text_color=THEME["green"] if net >= 0 else THEME["red"])
        self.kpi_count.configure(text=str(summary["count"]),
                                 text_color=THEME["text_primary"])

        # ── Apply type & search filter ──
        filtered = accounts
        if self._active_type_filter != "All":
            filtered = [a for a in filtered if a["type"].lower() == self._active_type_filter.lower()]
            
        if self._active_search:
            filtered = [
                a for a in filtered 
                if self._active_search in a["name"].lower() or 
                   (a.get("identifier") and self._active_search in a["identifier"].lower())
            ]

        # ── Clear and re-render cards ──
        for w in self.cards_frame.winfo_children():
            w.destroy()

        if not filtered:
            ctk.CTkLabel(self.cards_frame, text="No accounts found.",
                         font=FONTS["body"], text_color=THEME["text_tertiary"]).grid(
                             row=0, column=0, columnspan=2, pady=40)
        else:
            row, col = 0, 0
            for acc in filtered:
                card = AccountCard(
                    self.cards_frame, account=acc,
                    on_delete=self._prompt_delete,
                    on_edit=self._prompt_edit
                )
                # Archived accounts get a muted visual style
                if acc.get("is_archived"):
                    card.configure(border_color=THEME["text_tertiary"], fg_color=THEME["bg_tertiary"])

                card.grid(row=row, column=col, sticky="ew", padx=8, pady=8)
                col += 1
                if col > 1:
                    col = 0
                    row += 1

        # ── Donut chart: only positive-balance active accounts ──
        positive = [a for a in accounts if a["balance"] > 0 and not a.get("is_archived")]
        if positive:
            chart_data = [{"name": a["name"], "amount": a["balance"], "color": a["color"] or THEME["blue"]}
                          for a in positive]
            self.chart.draw_donut_chart(chart_data)
        else:
            self.chart.draw_donut_chart([])

    def _prompt_edit(self, account):
        from ui.modals.edit_account import EditAccountModal
        EditAccountModal(self.winfo_toplevel(), account, self.refresh)

    def _prompt_delete(self, acc_id):
        def do_delete():
            if delete_account(acc_id):
                Toast(self.winfo_toplevel(), "Account deleted", type="success")
                self.refresh()
            else:
                Toast(self.winfo_toplevel(), "Cannot delete: account has transactions", type="error")

        ConfirmDialog(self.winfo_toplevel(),
                      title="Delete Account",
                      message="Are you sure you want to delete this account?\n\n(Note: This will only work if the account has zero transactions.)",
                      on_confirm=do_delete)
