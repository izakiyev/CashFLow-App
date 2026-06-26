import customtkinter as ctk
from datetime import datetime, timedelta
from ui.theme import THEME, FONTS
from ui.components.topbar import Topbar
from ui.components.search_bar import SearchBar
from ui.components.toast import Toast
from ui.components.badge import Badge
from ui.components.empty_state import EmptyState
from ui.components.loading_state import LoadingState
from ui.modals.add_transaction import AddTransactionModal
from ui.modals.edit_transaction import EditTransactionModal
from ui.modals.confirm_dialog import ConfirmDialog
from services.transaction_service import get_transactions, delete_transaction, get_filtered_transactions_summary, pay_transaction
from services.account_service import get_accounts
from services.category_service import get_categories
from services.project_service import get_projects
from services.currency_service import format_currency
from ui.utils.thread_worker import ThreadWorker
from ui.components.kpi_card import KPICard
import csv
import os

PAGE_SIZE = 25  # Number of transactions to load per page


class TransactionRow(ctk.CTkFrame):
    """Premium, hoverable transaction row card with perfect grid alignment."""
    def __init__(self, master, tx: dict, accounts_map: dict, on_edit, on_delete, on_pay, **kwargs):
        super().__init__(master, fg_color=THEME["bg_secondary"], corner_radius=8,
                         border_width=1, border_color=THEME["border"], **kwargs)
        
        self.tx = tx
        self.on_edit = on_edit
        self.on_delete = on_delete
        self.on_pay = on_pay

        # Column configuration for perfect alignment
        self.grid_columnconfigure(0, minsize=24)   # Indicator + padding
        self.grid_columnconfigure(1, minsize=140)  # Date
        self.grid_columnconfigure(2, weight=1)     # Info (expands)
        self.grid_columnconfigure(3, minsize=180)  # Badges
        self.grid_columnconfigure(4, minsize=140)  # Amount
        self.grid_columnconfigure(5, minsize=100)  # Actions

        self.rowconfigure(0, weight=1, minsize=96)

        # ── Col 0: Indicator ──
        type_color = THEME["green"] if tx['type'] == 'income' else (THEME["blue"] if tx['type'] == 'transfer' else THEME["red"])
        # Add height=10 so it doesn't default to 200px tall
        self.indicator = ctk.CTkFrame(self, width=4, height=10, fg_color=type_color, corner_radius=2)
        self.indicator.grid(row=0, column=0, sticky="ns", padx=(8, 12), pady=12)

        # ── Col 1: Date ──
        date_str = tx['date'].strftime("%d %b %Y") if tx['date'] else "—"
        date_color = THEME["text_tertiary"]
        if tx.get('status') != 'paid' and tx.get('date'):
            now_date = datetime.now().date()
            tx_date = tx['date'].date()
            if tx_date < now_date:
                days_late = (now_date - tx_date).days
                date_str = f"⚠ {date_str}\n({days_late} gün gecikib)"
                date_color = THEME["red"]

        self.date_lbl = ctk.CTkLabel(self, text=date_str, font=FONTS["small"],
                                text_color=date_color, anchor="w", justify="left")
        self.date_lbl.grid(row=0, column=1, sticky="ew", padx=(0, 10))

        # ── Col 2: Info (Description + Account) ──
        self.info_f = ctk.CTkFrame(self, fg_color="transparent")
        self.info_f.grid(row=0, column=2, sticky="ew", padx=5, pady=12)

        self.desc_lbl = ctk.CTkLabel(self.info_f, text=tx['description'] or "—", font=FONTS["heading"],
                                text_color=THEME["text_primary"], anchor="w", justify="left")
        self.desc_lbl.pack(fill="x")

        if tx.get('note'):
            self.note_lbl = ctk.CTkLabel(self.info_f, text=tx['note'], font=FONTS["small"],
                                    text_color=THEME["text_secondary"], anchor="w", justify="left")
            self.note_lbl.pack(fill="x", pady=(0, 2))

        account_name = tx.get('account_name') or accounts_map.get(tx['account_id'], "Unknown Account")
        cat_name = tx['category_name'] if tx.get('category_name') else "Uncategorized"
        self.sub_lbl = ctk.CTkLabel(self.info_f, text=f"{account_name}  •  {cat_name}",
                     font=FONTS["small"], text_color=THEME["text_tertiary"], anchor="w")
        self.sub_lbl.pack(fill="x")

        # ── Col 3: Badges ──
        self.badges_f = ctk.CTkFrame(self, fg_color="transparent")
        self.badges_f.grid(row=0, column=3, sticky="e", padx=10)
        
        status = tx.get('status', 'confirmed')
        self.badge_status = Badge(self.badges_f, text=status)
        self.badge_status.pack(side="right", padx=4)
        
        self.badge_type = Badge(self.badges_f, text=tx['type'])
        self.badge_type.pack(side="right", padx=4)

        # ── Col 4: Amount ──
        sign = "+" if tx['type'] == 'income' else ("-" if tx['type'] == 'expense' else "")
        amount_color = THEME["green"] if tx['type'] == 'income' else (THEME["text_primary"] if tx['type'] == 'transfer' else THEME["red"])

        self.amt_f = ctk.CTkFrame(self, fg_color="transparent")
        self.amt_f.grid(row=0, column=4, sticky="e", padx=10)

        self.amount_lbl = ctk.CTkLabel(self.amt_f, text=format_currency(tx['amount'], tx.get('currency', 'AZN'), sign),
                                  font=FONTS["heading"], text_color=amount_color, anchor="e")
        self.amount_lbl.pack(fill="x")

        if tx.get('edv_amount'):
            edv_txt = f"+ {tx['edv_amount']:.2f} VAT"
            self.edv_lbl = ctk.CTkLabel(self.amt_f, text=edv_txt, font=FONTS["small"],
                         text_color=THEME["text_tertiary"], anchor="e")
            self.edv_lbl.pack(fill="x")

        # ── Col 5: Actions ──
        self.actions_f = ctk.CTkFrame(self, fg_color="transparent", width=100, height=36)
        self.actions_f.grid_propagate(False)
        self.actions_f.pack_propagate(False)
        self.actions_f.grid(row=0, column=5, sticky="e", padx=10)

        self.del_btn = ctk.CTkButton(self.actions_f, text="🗑", width=32, height=32, corner_radius=8,
                                fg_color="transparent", hover_color=THEME["red_light"],
                                text_color=THEME["red"], font=FONTS["heading"],
                                command=lambda: self.on_delete(tx['id']))

        if tx.get('status') == 'confirmed':
            self.pay_btn = ctk.CTkButton(self.actions_f, text="Pay", width=46, height=32, corner_radius=8,
                                   fg_color=THEME["green"], hover_color=THEME["green_dark"],
                                   text_color="white", font=FONTS["small"], command=lambda: self.on_pay(tx['id']))

        # ── Click-to-Edit & Hover Binding ──
        # Gather all widgets that should trigger the row click/hover
        self._interactive_widgets = [
            self, self.indicator, self.date_lbl, self.info_f, self.desc_lbl, 
            self.sub_lbl, self.badges_f, self.badge_status, self.badge_type,
            self.amt_f, self.amount_lbl
        ]
        if hasattr(self, 'note_lbl'):
            self._interactive_widgets.append(self.note_lbl)
        if hasattr(self, 'edv_lbl'):
            self._interactive_widgets.append(self.edv_lbl)

        for w in self._interactive_widgets:
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)
            w.bind("<Button-1>", lambda e: self.on_edit(self.tx['id']))
            try:
                w.configure(cursor="hand2")
            except Exception:
                pass # Frame might not support cursor

    def _on_enter(self, _):
        self.configure(fg_color=THEME["bg_tertiary"], border_color=THEME["blue"])
        # Reveal actions
        self.del_btn.pack(side="right", padx=(0, 0))
        if hasattr(self, 'pay_btn'):
            self.pay_btn.pack(side="right", padx=4)
        
    def _on_leave(self, e):
        # Prevent flickering if mouse is still inside the boundaries
        x, y = self.winfo_pointerxy()
        widget_x = self.winfo_rootx()
        widget_y = self.winfo_rooty()
        if (widget_x <= x <= widget_x + self.winfo_width()) and (widget_y <= y <= widget_y + self.winfo_height()):
            return
            
        self.configure(fg_color=THEME["bg_secondary"], border_color=THEME["border"])
        # Hide actions
        self.del_btn.pack_forget()
        if hasattr(self, 'pay_btn'):
            self.pay_btn.pack_forget()


class TransactionsPage(ctk.CTkFrame):

    PRESETS = {
        "This Month":   lambda: TransactionsPage._this_month(),
        "Last Month":   lambda: TransactionsPage._last_month(),
        "Last 3 Months": lambda: TransactionsPage._last_n_months(3),
        "This Year":    lambda: TransactionsPage._this_year(),
        "Next Month":   lambda: TransactionsPage._next_month(),
        "Next 3 Months": lambda: TransactionsPage._next_n_months(3),
        "All Time":     lambda: (None, None),
    }

    @staticmethod
    def _next_month():
        from datetime import timedelta
        now = datetime.now()
        start = (now.replace(day=1) + timedelta(days=32)).replace(day=1)
        end = (start + timedelta(days=32)).replace(day=1) - timedelta(microseconds=1)
        return start, end

    @staticmethod
    def _next_n_months(n):
        from datetime import timedelta
        now = datetime.now()
        month = now.month + n
        year = now.year
        while month > 12:
            month -= 12
            year += 1
        next_month = month + 1
        next_year = year
        if next_month > 12:
            next_month = 1
            next_year += 1
        end = datetime(next_year, next_month, 1) - timedelta(microseconds=1)
        return now, end

    @staticmethod
    def _this_month():
        now = datetime.now()
        return datetime(now.year, now.month, 1), now

    @staticmethod
    def _last_month():
        now = datetime.now()
        first = datetime(now.year, now.month, 1)
        end = first - timedelta(days=1)
        end = end.replace(hour=23, minute=59, second=59, microsecond=999999)
        return datetime(end.year, end.month, 1), end

    @staticmethod
    def _last_n_months(n):
        now = datetime.now()
        month = now.month - n
        year = now.year
        while month <= 0:
            month += 12
            year -= 1
        return datetime(year, month, 1), now

    @staticmethod
    def _this_year():
        now = datetime.now()
        return datetime(now.year, 1, 1), now

    def __init__(self, master, company_id, initial_account_id=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.company_id = company_id
        self.filters = {}
        if initial_account_id:
            self.filters['account_id'] = initial_account_id
            
        self._accounts_map = {}
        self._current_offset = 0
        self._date_from, self._date_to = self._this_month()
        self._cached_summ = None
        self._cached_summ_dates = (None, None)

        self.topbar = Topbar(self, title="Transactions")
        self.topbar.pack(fill="x")
        self.topbar.add_action("⛶ Focus Mode", self._toggle_focus)
        self.topbar.add_action("⬇ Export CSV", self._export_csv)
        self.topbar.add_action("+ New Transaction", self._add_transaction, primary=True, shortcut="Ctrl+N")

        self.top_section = ctk.CTkFrame(self, fg_color="transparent")
        self.top_section.pack(fill="x")

        self._build_date_filter(self.top_section)
        self._build_kpi_row(self.top_section)
        self._build_filter_bar()
        self._build_list()
        self.refresh()
        
        self._is_focused = False

    def _toggle_focus(self):
        if self._is_focused:
            self.top_section.pack(fill="x", before=self.filter_bar_container)
            self._is_focused = False
        else:
            self.top_section.pack_forget()
            self._is_focused = True

    # ─── Date Filter ──────────────────────────────────────────────────────────
    def _build_date_filter(self, parent):
        bar = ctk.CTkFrame(parent, fg_color=THEME["bg_secondary"], corner_radius=0, height=44)
        bar.pack(fill="x", padx=0, pady=0)
        bar.pack_propagate(False)

        inner = ctk.CTkFrame(bar, fg_color="transparent")
        inner.pack(side="left", padx=20, pady=6)

        ctk.CTkLabel(inner, text="Period:", font=FONTS["small"],
                     text_color=THEME["text_tertiary"]).pack(side="left", padx=(0, 8))

        self._preset_menu = ctk.CTkOptionMenu(
            inner, values=list(self.PRESETS.keys()),
            command=self._apply_preset,
            font=FONTS["small"],
            fg_color=THEME["bg_tertiary"], button_color=THEME["border"],
            button_hover_color=THEME["border"], text_color=THEME["text_primary"],
            dropdown_fg_color=THEME["bg_secondary"],
            height=28, width=140
        )
        self._preset_menu.set("This Month")
        self._preset_menu.pack(side="left", padx=(0, 6))

        self._custom_btn = ctk.CTkButton(
            inner, text="Custom", height=28, font=FONTS["small"],
            fg_color=THEME["bg_tertiary"],
            hover_color=THEME["border"],
            text_color=THEME["text_primary"],
            command=self._open_custom_date_modal
        )
        self._custom_btn.pack(side="left", padx=0)

        self._range_lbl = ctk.CTkLabel(bar, text="", font=FONTS["small"], text_color=THEME["text_tertiary"])
        self._range_lbl.pack(side="right", padx=20)
        self._update_range_label()

    def _apply_preset(self, label):
        if label != "Custom":
            self._date_from, self._date_to = self.PRESETS[label]()
            self._preset_menu.set(label)
            self._custom_btn.configure(
                fg_color=THEME["bg_tertiary"],
                hover_color=THEME["border"],
                text_color=THEME["text_primary"]
            )
        else:
            self._preset_menu.set("Custom Range")
            self._custom_btn.configure(
                fg_color=THEME["blue"],
                hover_color=THEME["blue"],
                text_color="white"
            )
        self._update_range_label()
        self.refresh()

    def _open_custom_date_modal(self):
        from ui.modals.custom_date import CustomDateModal
        def on_custom_dates(d_from, d_to):
            self._date_from = d_from
            self._date_to = d_to
            self._apply_preset("Custom")
            
        CustomDateModal(self.winfo_toplevel(), on_success=on_custom_dates)

    def _update_range_label(self):
        if self._date_from and self._date_to:
            self._range_lbl.configure(text=f"{self._date_from.strftime('%d %b %Y')}  →  {self._date_to.strftime('%d %b %Y')}")
        else:
            self._range_lbl.configure(text="All Time")

    # ─── Header KPIs ──────────────────────────────────────────────────────────
    def _build_kpi_row(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=(10, 0))
        for i in range(4):
            row.grid_columnconfigure(i, weight=1)

        self.kpi_income  = KPICard(row, "Filtered Income", "₼0.00", accent_color=THEME["green"])
        self.kpi_income.grid(row=0, column=0, sticky="ew", padx=8)

        self.kpi_expense = KPICard(row, "Filtered Expenses", "₼0.00", accent_color=THEME["red"])
        self.kpi_expense.grid(row=0, column=1, sticky="ew", padx=8)

        self.kpi_net     = KPICard(row, "Filtered Net", "₼0.00", accent_color=THEME["blue"])
        self.kpi_net.grid(row=0, column=2, sticky="ew", padx=8)
        
        # ── Custom dual-value KPI card for VAT ──
        vat_card = ctk.CTkFrame(row, fg_color=THEME["bg_secondary"], corner_radius=10,
                                border_width=1, border_color=THEME["border"], height=108)
        vat_card.grid(row=0, column=3, sticky="ew", padx=8)
        vat_card.pack_propagate(False)

        # Colored top accent line (Amber for VAT)
        ctk.CTkFrame(vat_card, height=3, corner_radius=0,
                     fg_color=THEME["amber"]).pack(fill="x", side="top")

        vat_body = ctk.CTkFrame(vat_card, fg_color="transparent")
        vat_body.pack(fill="both", expand=True, padx=16, pady=(10, 12))

        ctk.CTkLabel(vat_body, text="FILTERED VAT", font=("Inter", 10, "bold"), text_color=THEME["text_tertiary"]).pack(anchor="w")
        
        self.kpi_vat_total = ctk.CTkLabel(vat_body, text="₼0.00", font=("Inter", 20, "bold"), text_color=THEME["text_primary"])
        self.kpi_vat_total.pack(anchor="w", pady=(4, 0))

        vat_sub = ctk.CTkFrame(vat_body, fg_color="transparent")
        vat_sub.pack(fill="x", pady=(4, 0))
        
        self.kpi_vat_inc = ctk.CTkLabel(vat_sub, text="↑ ₼0.00", font=("Inter", 11, "bold"), text_color=THEME["green"])
        self.kpi_vat_inc.pack(side="left", padx=(0, 10))
        
        self.kpi_vat_exp = ctk.CTkLabel(vat_sub, text="↓ ₼0.00", font=("Inter", 11, "bold"), text_color=THEME["red"])
        self.kpi_vat_exp.pack(side="left")

    # ─── Filter bar ───────────────────────────────────────────────────────────
    def _build_filter_bar(self):
        self.filter_bar_container = ctk.CTkFrame(self, fg_color=THEME["bg_secondary"], corner_radius=10,
                           border_width=1, border_color=THEME["border"])
        self.filter_bar_container.pack(fill="x", padx=20, pady=10)

        # ── Row 1: Live Search + result count ────────────────────────────────
        row1 = ctk.CTkFrame(self.filter_bar_container, fg_color="transparent")
        row1.pack(fill="x", padx=12, pady=(10, 4))

        self.search_bar = SearchBar(row1, self._on_search, width=400)
        self.search_bar.pack(side="left")

        self.count_lbl = ctk.CTkLabel(row1, text="", font=FONTS["small"],
                                      text_color=THEME["text_tertiary"])
        self.count_lbl.pack(side="right", padx=8)

        # ── Row 2: Type + Status ──────────────────────────────────────────────
        row2 = ctk.CTkFrame(self.filter_bar_container, fg_color="transparent")
        row2.pack(fill="x", padx=12, pady=(0, 4))

        ctk.CTkLabel(row2, text="Type:", font=FONTS["small"],
                     text_color=THEME["text_tertiary"]).pack(side="left", padx=(0, 4))
        self.type_seg = ctk.CTkSegmentedButton(
            row2, values=["All", "Income", "Expense", "Transfer"],
            command=self._on_type_filter, font=FONTS["small"],
            height=28
        )
        self.type_seg.set("All")
        self.type_seg.pack(side="left", padx=(0, 16))

        ctk.CTkLabel(row2, text="Status:", font=FONTS["small"],
                     text_color=THEME["text_tertiary"]).pack(side="left", padx=(0, 4))
        self.status_seg = ctk.CTkSegmentedButton(
            row2, values=["All", "Paid", "Confirmed", "Pending", "Qaime Gözleyir"],
            command=self._on_status_filter, font=FONTS["small"],
            height=28
        )
        self.status_seg.set("All")
        self.status_seg.pack(side="left", padx=(0, 16))

        ctk.CTkLabel(row2, text="Client:", font=FONTS["small"],
                     text_color=THEME["text_tertiary"]).pack(side="left", padx=(0, 4))
        self.category_menu = ctk.CTkComboBox(
            row2, values=["All Clients"], font=FONTS["small"],
            fg_color=THEME["bg_tertiary"], border_color=THEME["border"],
            button_color=THEME["border"], button_hover_color=THEME["border"],
            text_color=THEME["text_primary"], dropdown_fg_color=THEME["bg_secondary"],
            height=28, width=160,
            command=self._on_category_filter
        )
        self.category_menu.set("All Clients")
        self.category_menu.pack(side="left", padx=(0, 16))
        self._category_id_map = {}  # label -> id

        ctk.CTkLabel(row2, text="Project:", font=FONTS["small"],
                     text_color=THEME["text_tertiary"]).pack(side="left", padx=(0, 4))
        self.project_menu = ctk.CTkOptionMenu(
            row2, values=["All Projects"], font=FONTS["small"],
            fg_color=THEME["bg_tertiary"], button_color=THEME["border"],
            button_hover_color=THEME["border"], text_color=THEME["text_primary"],
            dropdown_fg_color=THEME["bg_secondary"],
            height=28, width=140,
            command=self._on_project_filter
        )
        self.project_menu.pack(side="left", padx=(0, 16))
        self._project_id_map = {}  # label -> id

        self.clear_btn = ctk.CTkButton(
            row2, text="✕ Clear Filters", height=28, font=FONTS["small"],
            fg_color="transparent", border_width=1, border_color=THEME["border"],
            text_color=THEME["text_secondary"], hover_color=THEME["bg_tertiary"],
            command=self._clear_filters
        )
        self.clear_btn.pack(side="right")

    # ─── Scrollable list ──────────────────────────────────────────────────────
    def _build_list(self):
        self.list_outer = ctk.CTkFrame(self, fg_color=THEME["bg_secondary"], corner_radius=10,
                                       border_width=1, border_color=THEME["border"])
        self.list_outer.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        header = ctk.CTkFrame(self.list_outer, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(12, 0))
        
        # Match the exact grid layout of TransactionRow for perfect alignment
        header.grid_columnconfigure(0, minsize=24)   # Indicator space
        header.grid_columnconfigure(1, minsize=140)  # Date
        header.grid_columnconfigure(2, weight=1)     # Info
        header.grid_columnconfigure(3, minsize=180)  # Badges
        header.grid_columnconfigure(4, minsize=140)  # Amount
        header.grid_columnconfigure(5, minsize=100)  # Actions

        cols = [
            (1, "DATE", "w", (0, 10)),
            (2, "DESCRIPTION / ACCOUNT", "w", 5),
            (3, "TYPE / STATUS", "e", 10),
            (4, "AMOUNT", "e", 10),
            (5, "", "e", 10),
        ]
        for col, text, anchor, padx in cols:
            ctk.CTkLabel(header, text=text, font=FONTS["small"], text_color=THEME["text_tertiary"],
                         anchor=anchor).grid(row=0, column=col, sticky="ew", padx=padx)

        sep = ctk.CTkFrame(self.list_outer, height=1, fg_color=THEME["border"])
        sep.pack(fill="x", padx=16, pady=(8, 0))

        self.rows_scroll = ctk.CTkScrollableFrame(self.list_outer, fg_color="transparent")
        self.rows_scroll.pack(fill="both", expand=True, padx=8, pady=8)

    # ─── Actions ──────────────────────────────────────────────────────────────
    def _add_transaction(self):
        AddTransactionModal(self.winfo_toplevel(), self.company_id, self.refresh)

    def _export_csv(self):
        # Fetch ALL rows for this filter set (no limit)
        full_filters = dict(self.filters)
        if self._date_from and self._date_to:
            full_filters['date_from'] = self._date_from
            full_filters['date_to'] = self._date_to

        txs = get_transactions(self.company_id, full_filters)
        if not txs:
            Toast(self.winfo_toplevel(), "No transactions to export", type="info")
            return

        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile=f"transactions_{datetime.now().strftime('%Y%m%d')}.csv"
        )
        if not path:
            return

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "date", "description", "account", "category", "type",
                "amount", "currency", "vat_edv", "status", "note", "counterparty"
            ])
            writer.writeheader()
            for tx in txs:
                writer.writerow({
                    "date":         tx['date'].strftime("%Y-%m-%d") if tx['date'] else "",
                    "description":  tx.get('description', ''),
                    "account":      tx.get('account_name', ''),
                    "category":     tx.get('category_name', 'Uncategorized') or 'Uncategorized',
                    "type":         tx.get('type', ''),
                    "amount":       float(tx['amount']),
                    "currency":     tx.get('currency', ''),
                    "vat_edv":      float(tx.get('edv_amount', 0)),
                    "status":       tx.get('status', ''),
                    "note":         tx.get('note', ''),
                    "counterparty": tx.get('counterparty', ''),
                })
        Toast(self.winfo_toplevel(), f"Exported {len(txs)} transactions", type="success")

    def _on_search(self, query):
        # Debounce: cancel previous scheduled search and schedule a new one
        if hasattr(self, '_search_after_id') and self._search_after_id:
            try:
                self.after_cancel(self._search_after_id)
            except Exception:
                pass
        self.filters['search'] = query
        self._search_after_id = self.after(350, self.refresh)

    def _on_type_filter(self, val):
        self.filters['type'] = val
        self.refresh()

    def _on_status_filter(self, val):
        self.filters['status'] = val
        self.refresh()

    def _on_account_filter(self, label):
        if label == "All Accounts":
            self.filters.pop('account_id', None)
        else:
            self.filters['account_id'] = self._account_id_map.get(label)
        self.refresh()

    def _on_category_filter(self, label):
        if label == "All Clients":
            self.filters.pop('category_id', None)
        else:
            self.filters['category_id'] = self._category_id_map.get(label)
        self.refresh()

    def _on_project_filter(self, label):
        if label == "All Projects":
            self.filters.pop('project_id', None)
        else:
            self.filters['project_id'] = self._project_id_map.get(label)
        self.refresh()

    def _clear_filters(self):
        self.filters = {}
        self.search_bar.clear()
        self.type_seg.set("All")
        self.status_seg.set("All")
        self.category_menu.set("All Clients")
        self.project_menu.set("All Projects")
        self.refresh()

    def _prompt_delete(self, tx_id):
        def do_delete():
            if delete_transaction(tx_id):
                Toast(self.winfo_toplevel(), "Transaction deleted", type="success")
                self.refresh()
            else:
                Toast(self.winfo_toplevel(), "Failed to delete", type="error")
        ConfirmDialog(self.winfo_toplevel(), title="Delete Transaction",
                      message="Permanently delete this transaction?\nThe account balance will be reversed.",
                      on_confirm=do_delete)

    def _edit_tx(self, tx_id):
        EditTransactionModal(self.winfo_toplevel(), tx_id, self.company_id, self.refresh)

    def _pay_tx(self, tx_id):
        def do_pay():
            if pay_transaction(tx_id):
                Toast(self.winfo_toplevel(), "Transaction marked as PAID", type="success")
                self.refresh()
            else:
                Toast(self.winfo_toplevel(), "Failed to process payment", type="error")
        ConfirmDialog(self.winfo_toplevel(), title="Mark as Paid",
                      message="This will update the status to PAID and deduct/add the amount to your account balance. Proceed?",
                      on_confirm=do_pay)

    # ─── Async Refresh ────────────────────────────────────────────────────────
    def refresh(self):
        """Full refresh: resets to page 1 and reloads all data."""
        if not self.company_id:
            return
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
        self._current_offset = 0
        # Clear current rows immediately for visual feedback
        for w in self.rows_scroll.winfo_children():
            w.destroy()
        # Show loading indicator
        self._loading_state = LoadingState(self.rows_scroll)
        self._loading_state.pack(pady=50)

        ThreadWorker(self, self._fetch_data, on_success=self._update_ui)

    def _load_more(self):
        """Load the next PAGE_SIZE transactions and append them."""
        if not self.company_id:
            return
        # Remove the "Load More" button while loading
        if hasattr(self, '_load_more_btn') and self._load_more_btn.winfo_exists():
            self._load_more_btn.destroy()

        ThreadWorker(self, self._fetch_more_data, on_success=self._append_rows)

    def _build_active_filters(self):
        """Merge date range into the filter dict for service calls."""
        f = dict(self.filters)
        if self._date_from and self._date_to:
            f['date_from'] = self._date_from
            f['date_to'] = self._date_to
        return f

    def _fetch_data(self):
        """Background thread: fetch accounts, KPI summary, and first page of transactions."""
        f = self._build_active_filters()
        accounts = get_accounts(self.company_id)
        categories = get_categories(self.company_id)
        projects = get_projects(self.company_id, status_filter="active")
        accounts_map = {a['id']: a['name'] for a in accounts}

        # Compute KPIs based on ALL active filters
        self._cached_summ = get_filtered_transactions_summary(self.company_id, f)

        txs = get_transactions(self.company_id, f, limit=PAGE_SIZE, offset=0)
        return {
            "accounts_map": accounts_map, 
            "accounts": accounts, 
            "categories": categories,
            "projects": projects,
            "summ": self._cached_summ, 
            "txs": txs
        }

    def _fetch_more_data(self):
        """Background thread: fetch the next page of transactions."""
        f = self._build_active_filters()
        txs = get_transactions(self.company_id, f, limit=PAGE_SIZE, offset=self._current_offset)
        return {"txs": txs}

    def _update_ui(self, data):
        """Main thread: render the first page of results."""
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return

        # Update accounts map
        self._accounts_map = data["accounts_map"]

        categories = data.get("categories", [])
        if categories:
            # Build hierarchy
            cat_dict = {c.id: c for c in categories}
            self._category_id_map = {}
            for c in categories:
                label = c.name
                if c.parent_id and c.parent_id in cat_dict:
                    label = f"{cat_dict[c.parent_id].name} > {c.name}"
                self._category_id_map[label] = c.id
            
            # Sort labels alphabetically
            labels = ["All Clients"] + sorted(self._category_id_map.keys())
            current = self.category_menu.get()
            self.category_menu.configure(values=labels)
            if current not in labels:
                self.category_menu.set("All Clients")

        # Populate project dropdown
        projects = data.get("projects", [])
        if projects:
            self._project_id_map = {p['name']: p['id'] for p in projects}
            labels = ["All Projects"] + sorted(self._project_id_map.keys())
            current = self.project_menu.get()
            self.project_menu.configure(values=labels)
            
            active_proj_id = self.filters.get('project_id')
            if active_proj_id:
                for label, p_id in self._project_id_map.items():
                    if p_id == active_proj_id:
                        self.project_menu.set(label)
                        break
            elif current not in labels:
                self.project_menu.set("All Projects")

        # Update KPIs (date-filtered)
        summ = data["summ"]
        bc = summ.get('base_currency', 'AZN')
        self.kpi_income.update_data(format_currency(summ['total_income'], bc), value_color=THEME["green"])
        self.kpi_expense.update_data(format_currency(summ['total_expenses'], bc), value_color=THEME["red"])
        net = summ['net_profit']
        self.kpi_net.update_data(format_currency(net, bc),
                                 delta_positive=(net >= 0),
                                 value_color=THEME["green"] if net >= 0 else THEME["red"])
        
        i_vat = summ.get('income_vat', 0.0)
        e_vat = summ.get('expense_vat', 0.0)
        total_vat = i_vat + e_vat
        self.kpi_vat_total.configure(text=format_currency(total_vat, bc))
        self.kpi_vat_inc.configure(text=f"↑ {format_currency(i_vat, bc)}")
        self.kpi_vat_exp.configure(text=f"↓ {format_currency(e_vat, bc)}")

        # Clear rows (including any loading label)
        for w in self.rows_scroll.winfo_children():
            w.destroy()

        txs = data["txs"]
        self._current_offset = len(txs)

        self.count_lbl.configure(text=f"{len(txs)} transaction{'s' if len(txs) != 1 else ''} loaded")

        if not txs:
            empty = EmptyState(
                self.rows_scroll,
                icon="📋",
                title="No transactions found",
                subtitle="Try adjusting your filters or date range."
            )
            empty.pack(fill="both", expand=True, pady=20)
            return

        def _on_done():
            if len(txs) == PAGE_SIZE:
                self._show_load_more_btn()

        self._render_rows(txs, on_complete=_on_done)

    def _append_rows(self, data):
        """Main thread: append the next page of rows to the existing list."""
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return

        txs = data["txs"]
        if not txs:
            return

        self._current_offset += len(txs)
        total_loaded = self._current_offset
        has_more = len(txs) == PAGE_SIZE
        suffix = "" if has_more else " (all loaded)"
        self.count_lbl.configure(text=f"{total_loaded} transactions{suffix}")

        def _on_done():
            if has_more:
                self._show_load_more_btn()

        self._render_rows(txs, on_complete=_on_done)

    def _render_rows(self, txs, chunk_size=5, on_complete=None):
        """Render a list of transaction rows into the scrollable frame using chunking to prevent UI freeze."""
        if not txs:
            if on_complete: on_complete()
            return

        def _render_chunk(index):
            try:
                if not self.winfo_exists():
                    return
            except Exception:
                return

            end = min(index + chunk_size, len(txs))
            for i in range(index, end):
                tx = txs[i]
                row = TransactionRow(
                    self.rows_scroll, tx=tx,
                    accounts_map=self._accounts_map,
                    on_edit=self._edit_tx,
                    on_delete=self._prompt_delete,
                    on_pay=self._pay_tx
                )
                row.pack(fill="x", pady=4)
            
            if end < len(txs):
                self.after(15, _render_chunk, end)
            elif on_complete:
                on_complete()

        _render_chunk(0)

    def _show_load_more_btn(self):
        """Render a styled 'Load More' button at the bottom of the list."""
        self._load_more_btn = ctk.CTkButton(
            self.rows_scroll,
            text=f"↓  Load More  ({self._current_offset} loaded)",
            height=40, font=("Inter", 13, "bold"),
            fg_color=THEME["bg_secondary"],
            hover_color=THEME["bg_tertiary"],
            text_color=THEME["blue"],
            border_width=1, border_color=THEME["border"],
            corner_radius=8,
            command=self._load_more
        )
        self._load_more_btn.pack(fill="x", padx=20, pady=(8, 20))
