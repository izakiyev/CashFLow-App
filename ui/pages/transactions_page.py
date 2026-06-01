import customtkinter as ctk
from datetime import datetime, timedelta
from ui.theme import THEME, FONTS
from ui.components.topbar import Topbar
from ui.components.search_bar import SearchBar
from ui.components.toast import Toast
from ui.modals.add_transaction import AddTransactionModal
from ui.modals.edit_transaction import EditTransactionModal
from ui.modals.confirm_dialog import ConfirmDialog
from services.transaction_service import get_transactions, delete_transaction, get_dashboard_summary, pay_transaction
from services.account_service import get_accounts
from services.currency_service import format_currency
from ui.utils.thread_worker import ThreadWorker
import csv
import os

PAGE_SIZE = 100  # Number of transactions to load per page


class TransactionRow(ctk.CTkFrame):
    """Premium, hoverable transaction row card."""
    def __init__(self, master, tx: dict, accounts_map: dict, on_edit, on_delete, on_pay, **kwargs):
        super().__init__(master, fg_color=THEME["bg_secondary"], corner_radius=8,
                         border_width=1, border_color=THEME["border"], height=72, **kwargs)
        self.pack_propagate(False)
        self.tx = tx
        self.on_edit = on_edit
        self.on_delete = on_delete
        self.on_pay = on_pay

        # Left: type color indicator
        type_color = THEME["green"] if tx['type'] == 'income' else (THEME["blue"] if tx['type'] == 'transfer' else THEME["red"])
        indicator = ctk.CTkFrame(self, width=4, fg_color=type_color, corner_radius=2)
        indicator.pack(side="left", fill="y", padx=(8, 12), pady=12)

        # Date column
        date_str = tx['date'].strftime("%d %b %Y") if tx['date'] else "—"
        date_lbl = ctk.CTkLabel(self, text=date_str, font=FONTS["small"],
                                text_color=THEME["text_tertiary"], width=90, anchor="w")
        date_lbl.pack(side="left", padx=(0, 10))

        # Description + account container
        info_f = ctk.CTkFrame(self, fg_color="transparent")
        info_f.pack(side="left", fill="x", expand=True, padx=5)

        desc_lbl = ctk.CTkLabel(info_f, text=tx['description'] or "—", font=FONTS["heading"],
                                text_color=THEME["text_primary"], anchor="w",
                                wraplength=400, justify="left")
        desc_lbl.pack(fill="x")

        # Note (if exists)
        if tx.get('note'):
            note_lbl = ctk.CTkLabel(info_f, text=tx['note'], font=FONTS["small"],
                                    text_color=THEME["text_secondary"], anchor="w",
                                    wraplength=400, justify="left")
            note_lbl.pack(fill="x", pady=(0, 2))

        account_name = tx.get('account_name') or accounts_map.get(tx['account_id'], "Unknown Account")
        cat_name = tx['category_name'] if tx.get('category_name') else "Uncategorized"

        ctk.CTkLabel(info_f, text=f"{account_name}  •  {cat_name}",
                     font=FONTS["small"], text_color=THEME["text_tertiary"], anchor="w").pack(fill="x")

        # Action buttons (Rightmost)
        del_btn = ctk.CTkButton(self, text="🗑", width=32, height=32, corner_radius=8,
                                fg_color="transparent", hover_color=THEME["red_light"],
                                text_color=THEME["red"], font=FONTS["heading"],
                                command=lambda: self.on_delete(tx['id']))
        del_btn.pack(side="right", padx=(0, 8))

        edit_btn = ctk.CTkButton(self, text="✏️", width=32, height=32, corner_radius=8,
                                 fg_color="transparent", hover_color=THEME["bg_tertiary"],
                                 text_color=THEME["blue"], font=FONTS["heading"],
                                 command=lambda: self.on_edit(tx['id']))
        edit_btn.pack(side="right", padx=2)

        # Pay Button (if confirmed)
        if tx.get('status') == 'confirmed':
            pay_btn = ctk.CTkButton(self, text="Pay", width=50, height=32, corner_radius=8,
                                   fg_color=THEME["green"], hover_color=THEME["green_dark"],
                                   font=FONTS["small"], command=lambda: self.on_pay(tx['id']))
            pay_btn.pack(side="right", padx=2)

        # Amount
        sign = "+" if tx['type'] == 'income' else ("-" if tx['type'] == 'expense' else "")
        amount_color = THEME["green"] if tx['type'] == 'income' else (THEME["text_primary"] if tx['type'] == 'transfer' else THEME["red"])

        amt_f = ctk.CTkFrame(self, fg_color="transparent")
        amt_f.pack(side="right", padx=(10, 15))

        amount_lbl = ctk.CTkLabel(amt_f, text=format_currency(tx['amount'], tx.get('currency', 'AZN'), sign),
                                  font=FONTS["heading"], text_color=amount_color, width=120, anchor="e")
        amount_lbl.pack(fill="x")

        if tx.get('edv_amount'):
            edv_txt = f"+ {tx['edv_amount']:.2f} VAT"
            ctk.CTkLabel(amt_f, text=edv_txt, font=FONTS["small"],
                         text_color=THEME["text_tertiary"], anchor="e").pack(fill="x")

        # Type badge
        badge_f = ctk.CTkFrame(self, fg_color=self._badge_bg(tx['type']), corner_radius=6)
        badge_f.pack(side="right", padx=10)
        ctk.CTkLabel(badge_f, text=tx['type'].upper(), font=FONTS["small"],
                     text_color=type_color).pack(padx=10, pady=3)

        # Status badge
        status = tx.get('status', 'confirmed')
        status_color = THEME["green"] if status == 'paid' else THEME["amber"]
        status_bg = THEME["green_light"] if status == 'paid' else THEME["amber_light"]

        status_f = ctk.CTkFrame(self, fg_color=status_bg, corner_radius=6)
        status_f.pack(side="right", padx=5)
        ctk.CTkLabel(status_f, text=status.upper(), font=FONTS["small"],
                     text_color=status_color).pack(padx=8, pady=3)

        # Hover binding
        for w in [self, indicator, info_f, desc_lbl]:
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)

    def _badge_bg(self, tx_type):
        if tx_type == 'income':   return THEME["green_light"]
        if tx_type == 'expense':  return THEME["red_light"]
        return THEME["blue_light"]

    def _on_enter(self, _):
        self.configure(fg_color=THEME["bg_tertiary"])

    def _on_leave(self, _):
        self.configure(fg_color=THEME["bg_secondary"])


class TransactionsPage(ctk.CTkFrame):

    PRESETS = {
        "This Month":   lambda: TransactionsPage._this_month(),
        "Last Month":   lambda: TransactionsPage._last_month(),
        "Last 3 Months": lambda: TransactionsPage._last_n_months(3),
        "This Year":    lambda: TransactionsPage._this_year(),
        "All Time":     lambda: (None, None),
    }

    @staticmethod
    def _this_month():
        now = datetime.now()
        return datetime(now.year, now.month, 1), now

    @staticmethod
    def _last_month():
        now = datetime.now()
        first = datetime(now.year, now.month, 1)
        end = first - timedelta(days=1)
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

    def __init__(self, master, company_id, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.company_id = company_id
        self.filters = {}
        self._accounts_map = {}
        self._current_offset = 0
        self._date_from, self._date_to = self._this_month()

        self.topbar = Topbar(self, title="Transactions")
        self.topbar.pack(fill="x")
        self.topbar.add_action("Export CSV", self._export_csv)
        self.topbar.add_action("+ New Transaction", self._add_transaction, primary=True)

        self._build_date_filter()
        self._build_kpi_row()
        self._build_filter_bar()
        self._build_list()
        self.refresh()

    # ─── Date Filter ──────────────────────────────────────────────────────────
    def _build_date_filter(self):
        bar = ctk.CTkFrame(self, fg_color=THEME["bg_secondary"], corner_radius=0, height=44)
        bar.pack(fill="x", padx=0, pady=0)
        bar.pack_propagate(False)

        inner = ctk.CTkFrame(bar, fg_color="transparent")
        inner.pack(side="left", padx=20, pady=6)

        ctk.CTkLabel(inner, text="Period:", font=FONTS["small"],
                     text_color=THEME["text_tertiary"]).pack(side="left", padx=(0, 8))

        self._filter_buttons = {}
        for label in self.PRESETS:
            is_active = (label == "This Month")
            btn = ctk.CTkButton(
                inner, text=label, height=28, font=FONTS["small"],
                fg_color=THEME["blue"] if is_active else THEME["bg_tertiary"],
                hover_color=THEME["blue"] if is_active else THEME["border"],
                text_color=THEME["text_primary"],
                command=lambda l=label: self._apply_preset(l)
            )
            btn.pack(side="left", padx=3)
            self._filter_buttons[label] = btn

        self._range_lbl = ctk.CTkLabel(bar, text="", font=FONTS["small"], text_color=THEME["text_tertiary"])
        self._range_lbl.pack(side="right", padx=20)
        self._update_range_label()

    def _apply_preset(self, label):
        self._date_from, self._date_to = self.PRESETS[label]()
        for lbl, btn in self._filter_buttons.items():
            is_active = (lbl == label)
            btn.configure(
                fg_color=THEME["blue"] if is_active else THEME["bg_tertiary"],
                hover_color=THEME["blue"] if is_active else THEME["border"]
            )
        self._update_range_label()
        self.refresh()

    def _update_range_label(self):
        if self._date_from and self._date_to:
            self._range_lbl.configure(text=f"{self._date_from.strftime('%d %b %Y')}  →  {self._date_to.strftime('%d %b %Y')}")
        else:
            self._range_lbl.configure(text="All Time")

    # ─── Header KPIs ──────────────────────────────────────────────────────────
    def _build_kpi_row(self):
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(10, 0))
        for i in range(3):
            row.grid_columnconfigure(i, weight=1)

        def kpi_card(parent, title, col):
            card = ctk.CTkFrame(parent, fg_color=THEME["bg_secondary"], corner_radius=10,
                                border_width=1, border_color=THEME["border"])
            card.grid(row=0, column=col, sticky="ew", padx=5)
            ctk.CTkLabel(card, text=title, font=FONTS["body"], text_color=THEME["text_secondary"]
                         ).pack(anchor="w", padx=16, pady=(10, 0))
            lbl_v = ctk.CTkLabel(card, text="₼0.00", font=FONTS["title"], text_color=THEME["text_primary"])
            lbl_v.pack(anchor="w", padx=16, pady=(0, 12))
            return lbl_v

        self.kpi_income  = kpi_card(row, "Total Income",   0)
        self.kpi_expense = kpi_card(row, "Total Expenses", 1)
        self.kpi_net     = kpi_card(row, "Net",            2)

    # ─── Filter bar ───────────────────────────────────────────────────────────
    def _build_filter_bar(self):
        bar = ctk.CTkFrame(self, fg_color=THEME["bg_secondary"], corner_radius=10,
                           border_width=1, border_color=THEME["border"])
        bar.pack(fill="x", padx=20, pady=10)

        self.search_bar = SearchBar(bar, self._on_search)
        self.search_bar.pack(side="left", padx=10, pady=8)

        self.type_seg = ctk.CTkSegmentedButton(
            bar, values=["All", "Income", "Expense", "Transfer"],
            command=self._on_type_filter, font=FONTS["body"]
        )
        self.type_seg.set("All")
        self.type_seg.pack(side="left", padx=10)

        self.status_seg = ctk.CTkSegmentedButton(
            bar, values=["All", "Paid", "Confirmed"],
            command=self._on_status_filter, font=FONTS["body"]
        )
        self.status_seg.set("All")
        self.status_seg.pack(side="left", padx=10)

        self.count_lbl = ctk.CTkLabel(bar, text="", font=FONTS["small"],
                                      text_color=THEME["text_tertiary"])
        self.count_lbl.pack(side="right", padx=16)

    # ─── Scrollable list ──────────────────────────────────────────────────────
    def _build_list(self):
        self.list_outer = ctk.CTkFrame(self, fg_color=THEME["bg_secondary"], corner_radius=10,
                                       border_width=1, border_color=THEME["border"])
        self.list_outer.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        header = ctk.CTkFrame(self.list_outer, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(12, 0))
        for text, anchor, expand in [
            ("DATE",        "w", False),
            ("DESCRIPTION / ACCOUNT", "w", True),
            ("TYPE",        "e", False),
            ("AMOUNT",      "e", False),
            ("",            "e", False),
        ]:
            ctk.CTkLabel(header, text=text, font=FONTS["small"], text_color=THEME["text_tertiary"],
                         anchor=anchor).pack(side="left", expand=expand, fill="x",
                                             padx=(0 if expand else 8))

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
        self._search_after_id = self.after(400, self.refresh)

    def _on_type_filter(self, val):
        self.filters['type'] = val
        self.refresh()

    def _on_status_filter(self, val):
        self.filters['status'] = val
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
        self._loading_lbl = ctk.CTkLabel(
            self.rows_scroll, text="Loading transactions...",
            font=FONTS["body"], text_color=THEME["text_tertiary"]
        )
        self._loading_lbl.pack(pady=40)

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
        accounts_map = {a['id']: a['name'] for a in accounts}
        summ = get_dashboard_summary(
            self.company_id,
            date_from=f.get('date_from'),
            date_to=f.get('date_to')
        )
        txs = get_transactions(self.company_id, f, limit=PAGE_SIZE, offset=0)
        return {"accounts_map": accounts_map, "summ": summ, "txs": txs}

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

        # Update KPIs (date-filtered)
        summ = data["summ"]
        bc = summ.get('base_currency', 'AZN')
        self.kpi_income.configure(text=format_currency(summ['total_income'], bc), text_color=THEME["green"])
        self.kpi_expense.configure(text=format_currency(summ['total_expenses'], bc), text_color=THEME["red"])
        net = summ['net_profit']
        self.kpi_net.configure(text=format_currency(net, bc),
                               text_color=THEME["green"] if net >= 0 else THEME["red"])

        # Clear rows (including any loading label)
        for w in self.rows_scroll.winfo_children():
            w.destroy()

        txs = data["txs"]
        self._current_offset = len(txs)

        self.count_lbl.configure(text=f"{len(txs)} transaction{'s' if len(txs) != 1 else ''} loaded")

        if not txs:
            ctk.CTkLabel(self.rows_scroll, text="No transactions found for this period.",
                         font=FONTS["body"], text_color=THEME["text_tertiary"]).pack(pady=40)
            return

        self._render_rows(txs)

        # Show "Load More" if we got a full page (there might be more)
        if len(txs) == PAGE_SIZE:
            self._show_load_more_btn()

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

        self._render_rows(txs)

        if has_more:
            self._show_load_more_btn()

    def _render_rows(self, txs):
        """Render a list of transaction rows into the scrollable frame."""
        for tx in txs:
            row = TransactionRow(
                self.rows_scroll, tx=tx,
                accounts_map=self._accounts_map,
                on_edit=self._edit_tx,
                on_delete=self._prompt_delete,
                on_pay=self._pay_tx
            )
            row.pack(fill="x", pady=4)

    def _show_load_more_btn(self):
        """Render a 'Load More' button at the bottom of the list."""
        self._load_more_btn = ctk.CTkButton(
            self.rows_scroll,
            text=f"Load More  (showing {self._current_offset}, click for next {PAGE_SIZE})",
            height=40, font=FONTS["body"],
            fg_color=THEME["bg_tertiary"], hover_color=THEME["border"],
            text_color=THEME["text_primary"],
            command=self._load_more
        )
        self._load_more_btn.pack(fill="x", padx=10, pady=(8, 16))
