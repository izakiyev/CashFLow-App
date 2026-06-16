import customtkinter as ctk
from datetime import datetime, timedelta
from ui.theme import THEME, FONTS
from ui.components.topbar import Topbar
from ui.components.kpi_card import KPICard
from ui.components.chart_frame import ChartFrame
from ui.modals.add_transaction import AddTransactionModal
from services.transaction_service import (
    get_dashboard_summary, get_transactions,
    get_spending_by_category, get_daily_spending_trend,
    get_monthly_series, get_projected_balance
)
from services.account_service import get_accounts, get_currency_exposure
from services.planned_service import get_planned_payments, confirm_planned_payment as mark_as_paid
from services.budget_service import get_budget_summary
from services.currency_service import format_currency
from ui.utils.thread_worker import ThreadWorker




class AccountMiniRow(ctk.CTkFrame):
    def __init__(self, master, acc, max_balance, currency="AZN", **kwargs):
        super().__init__(master, fg_color=THEME["bg_tertiary"], corner_radius=8, **kwargs)
        self.pack_propagate(False)

        # Dot
        dot = ctk.CTkFrame(self, width=12, height=12, corner_radius=6, fg_color=acc['color'])
        dot.pack(side="left", padx=(12, 10), pady=14)

        # Info
        info = ctk.CTkFrame(self, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True, pady=10)
        ctk.CTkLabel(info, text=acc['name'], font=FONTS["body"], text_color=THEME["text_primary"],
                     anchor="w").pack(fill="x")
        ctk.CTkLabel(info, text=acc['type'], font=FONTS["small"], text_color=THEME["text_tertiary"],
                     anchor="w").pack(fill="x", pady=(2, 0))

        # Balance
        bal_color = THEME["green"] if acc['balance'] >= 0 else THEME["red"]
        bal = ctk.CTkFrame(self, fg_color="transparent")
        bal.pack(side="right", padx=(10, 16), pady=10)
        ctk.CTkLabel(bal, text=format_currency(acc['balance'], currency),
                     font=FONTS["body"], text_color=bal_color, anchor="e").pack(fill="x")
        
        # Micro progress bar based on max balance across all accounts
        ratio = (acc['balance'] / max_balance) if max_balance > 0 and acc['balance'] > 0 else 0
        pb_bg = ctk.CTkFrame(bal, height=4, fg_color=THEME["border"], corner_radius=2)
        pb_bg.pack(fill="x", pady=(4, 0))
        if ratio > 0:
            pb_fill = ctk.CTkFrame(pb_bg, height=4, width=max(4, int(100 * ratio)), 
                                   fg_color=acc['color'], corner_radius=2)
            pb_fill.pack(side="left", fill="y")


class TxMiniRow(ctk.CTkFrame):
    def __init__(self, master, tx, on_click=None, **kwargs):
        super().__init__(master, fg_color=THEME["bg_tertiary"], corner_radius=8, **kwargs)
        self.pack_propagate(False)
        
        date_str = tx['date'].strftime("%b %d") if tx['date'] else "—"
        type_color = THEME["green"] if tx['type'] == 'income' else (THEME["blue"] if tx['type'] == 'transfer' else THEME["red"])
        
        # Indicator strip
        strip = ctk.CTkFrame(self, width=4, fg_color=type_color, corner_radius=2)
        strip.pack(side="left", fill="y", padx=(8, 12), pady=8)

        # Main Info
        info = ctk.CTkFrame(self, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True, pady=10)
        ctk.CTkLabel(info, text=tx['description'] or "—", font=FONTS["body"], text_color=THEME["text_primary"],
                     anchor="w").pack(fill="x")
        ctk.CTkLabel(info, text=date_str, font=FONTS["small"], text_color=THEME["text_tertiary"],
                     anchor="w").pack(fill="x")

        # Amount
        sign = "+" if tx['type'] == 'income' else ("-" if tx['type'] == 'expense' else "")
        ctk.CTkLabel(self, text=format_currency(tx['amount'], tx.get('currency', 'AZN'), sign),
                     font=FONTS["body"], text_color=type_color, anchor="e").pack(side="right", padx=(10, 16))

        # Make clickable if callback provided
        if on_click:
            for widget in [self, info, strip]:
                widget.bind("<Button-1>", lambda e: on_click(tx))
                widget.configure(cursor="hand2")
            self.bind("<Enter>", lambda e: self.configure(fg_color=THEME["border"]))
            self.bind("<Leave>", lambda e: self.configure(fg_color=THEME["bg_tertiary"]))


class PlannedMiniRow(ctk.CTkFrame):
    def __init__(self, master, p, on_pay, **kwargs):
        super().__init__(master, fg_color=THEME["bg_tertiary"], corner_radius=8, **kwargs)
        self.pack_propagate(False)
        
        date_str = p.due_date.strftime("%b %d") if p.due_date else "—"
        is_overdue = p.due_date and p.due_date < datetime.now() and p.status != "paid"
        
        status_color = THEME["red"] if is_overdue else THEME["blue"]
        # Fix #4: status_text was dead — now displayed as a badge
        status_text = "⚠ Overdue" if is_overdue else "Upcoming"

        info = ctk.CTkFrame(self, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True, padx=16, pady=10)
        ctk.CTkLabel(info, text=p.description or "—", font=FONTS["body"], text_color=THEME["text_primary"],
                     anchor="w").pack(fill="x")
        
        cat_name = getattr(p, 'category_name', None) or "Uncategorized"
        ctk.CTkLabel(info, text=f"Due: {date_str}  •  {cat_name}", font=FONTS["small"], text_color=status_color,
                     anchor="w").pack(fill="x")

        amt = float(p.amount)
        if hasattr(p, 'edv_amount') and p.edv_amount:
            amt += float(p.edv_amount)

        amt_f = ctk.CTkFrame(self, fg_color="transparent")
        amt_f.pack(side="right", padx=(10, 8))

        ctk.CTkLabel(amt_f, text=format_currency(amt, p.currency), font=FONTS["body"],
                     text_color=THEME["text_primary"], anchor="e").pack(fill="x")
        
        if hasattr(p, 'edv_amount') and p.edv_amount:
             ctk.CTkLabel(amt_f, text="+ VAT included", font=FONTS["small"],
                          text_color=THEME["text_tertiary"], anchor="e").pack(fill="x")
        
        if p.status != "paid":
            btn = ctk.CTkButton(self, text="Pay", width=50, height=28, corner_radius=6,
                                fg_color=THEME["green"], hover_color=THEME["green_dark"],
                                text_color="white", font=FONTS["small"], command=lambda: on_pay(p.id))
            btn.pack(side="right", padx=(0, 16))


class DashboardPage(ctk.CTkFrame):
    # Preset date ranges
    PRESETS = {
        "This Month": lambda: DashboardPage._this_month(),
        "Last Month": lambda: DashboardPage._last_month(),
        "Last 3 Months": lambda: DashboardPage._last_n_months(3),
        "This Year": lambda: DashboardPage._this_year(),
        "All Time": lambda: (None, None),
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
        end = end.replace(hour=23, minute=59, second=59, microsecond=999999)
        start = datetime(end.year, end.month, 1)
        return start, end

    @staticmethod
    def _last_n_months(n):
        """Accurate calendar-aware month arithmetic."""
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
        # Span from Jan 1st to Dec 31st to include future transactions in the current year
        return datetime(now.year, 1, 1), datetime(now.year, 12, 31, 23, 59, 59)

    def __init__(self, master, company_id, navigate=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.company_id = company_id
        self.navigate = navigate  # Callback for page navigation (Feature #3)
        self._date_from, self._date_to = self._this_month()  # Default: This Month
        self._current_donut_parent_id = None  # For drill-down chart
        self._current_donut_parent_name = None

        self.topbar = Topbar(self, title="Dashboard")
        self.topbar.pack(fill="x")
        self.topbar.add_action("+ New Transaction", self._add_transaction, primary=True)

        self._build_date_filter()

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=20, pady=10)

        self._build_kpis()
        self._build_charts_section()
        self._build_bottom_section()

        self.refresh()

    def _build_date_filter(self):
        """Date range filter bar below topbar."""
        bar = ctk.CTkFrame(self, fg_color=THEME["bg_secondary"], corner_radius=0, height=44)
        bar.pack(fill="x", padx=0, pady=0)
        bar.pack_propagate(False)

        inner = ctk.CTkFrame(bar, fg_color="transparent")
        inner.pack(side="left", padx=20, pady=6)

        ctk.CTkLabel(inner, text="Period:", font=FONTS["small"],
                     text_color=THEME["text_tertiary"]).pack(side="left", padx=(0, 8))

        self._preset_var = ctk.StringVar(value="This Month")
        self._filter_buttons = {}
        for label in self.PRESETS:
            is_active = (label == "This Month")
            btn = ctk.CTkButton(
                inner, text=label, height=28, font=FONTS["small"],
                fg_color=THEME["blue"] if is_active else THEME["bg_tertiary"],
                hover_color=THEME["blue"] if is_active else THEME["border"],
                text_color="white" if is_active else THEME["text_primary"],
                command=lambda l=label: self._apply_preset(l)
            )
            btn.pack(side="left", padx=3)
            self._filter_buttons[label] = btn

        # Live range display
        self._range_lbl = ctk.CTkLabel(bar, text="", font=FONTS["small"],
                                        text_color=THEME["text_tertiary"])
        self._range_lbl.pack(side="right", padx=20)
        self._update_range_label()

    def _apply_preset(self, label):
        self._date_from, self._date_to = self.PRESETS[label]()
        # Update button highlights using the dict (fix #9)
        for lbl, btn in self._filter_buttons.items():
            is_active = (lbl == label)
            btn.configure(
                fg_color=THEME["blue"] if is_active else THEME["bg_tertiary"],
                hover_color=THEME["blue"] if is_active else THEME["border"],
                text_color="white" if is_active else THEME["text_primary"]
            )
        self._update_range_label()
        self.refresh()

    def _update_range_label(self):
        if self._date_from and self._date_to:
            self._range_lbl.configure(
                text=f"{self._date_from.strftime('%d %b %Y')}  →  {self._date_to.strftime('%d %b %Y')}"
            )
        else:
            self._range_lbl.configure(text="All Time")

    def _add_transaction(self):
        AddTransactionModal(self.winfo_toplevel(), self.company_id, self.refresh)

    def _on_donut_click(self, cat_data):
        """Called when user clicks a wedge. Drills into subcategories."""
        cat_id = cat_data.get("id")
        if cat_id is None:
            return  # Can't drill into uncategorized
        self._current_donut_parent_id = cat_id
        self._current_donut_parent_name = cat_data.get("name", "")
        self.refresh()

    def _donut_go_back(self):
        """Called when user clicks Back — returns to top-level view."""
        self._current_donut_parent_id = None
        self._current_donut_parent_name = None
        self.refresh()

    def _build_kpis(self):
        # Row 1: core financials
        self.kpi_frame = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.kpi_frame.pack(fill="x", pady=(0, 12))
        for i in range(4): self.kpi_frame.grid_columnconfigure(i, weight=1)

        self.card_balance = KPICard(self.kpi_frame, "Total Balance", "₼0.00")
        self.card_balance.grid(row=0, column=0, sticky="ew", padx=6)

        self.card_income = KPICard(self.kpi_frame, "Income (Period)", "₼0.00")
        self.card_income.grid(row=0, column=1, sticky="ew", padx=6)

        self.card_expense = KPICard(self.kpi_frame, "Expenses (Period)", "₼0.00")
        self.card_expense.grid(row=0, column=2, sticky="ew", padx=6)

        self.card_net = KPICard(self.kpi_frame, "Net Profit (Period)", "₼0.00")
        self.card_net.grid(row=0, column=3, sticky="ew", padx=6)

        # Row 2: analytics + projected balance
        self.stat_frame = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.stat_frame.pack(fill="x", pady=(0, 12))
        for i in range(5): self.stat_frame.grid_columnconfigure(i, weight=1)

        self.card_top_cat = KPICard(self.stat_frame, "Top Category", "None")
        self.card_top_cat.grid(row=0, column=0, sticky="ew", padx=6)

        self.card_avg_spend = KPICard(self.stat_frame, "Avg Daily Spend", "₼0.00")
        self.card_avg_spend.grid(row=0, column=1, sticky="ew", padx=6)

        self.card_savings = KPICard(self.stat_frame, "Savings Rate", "0%")
        self.card_savings.grid(row=0, column=2, sticky="ew", padx=6)

        self.card_budget = KPICard(self.stat_frame, "Budget Health", "…")
        self.card_budget.grid(row=0, column=3, sticky="ew", padx=6)

        # Feature #2: Projected Balance card
        self.card_projected = KPICard(self.stat_frame, "Projected Balance", "₼0.00")
        self.card_projected.grid(row=0, column=4, sticky="ew", padx=6)

    def _build_charts_section(self):
        # ── Row 1: Bar Chart & Donut Chart ──
        row1 = ctk.CTkFrame(self.scroll, fg_color="transparent")
        row1.pack(fill="x", pady=10)
        row1.grid_columnconfigure(0, weight=6)
        row1.grid_columnconfigure(1, weight=4)

        # Cashflow Line Chart Container
        chart_c = ctk.CTkFrame(row1, fg_color=THEME["bg_secondary"], corner_radius=12,
                                border_width=1, border_color=THEME["border"])
        chart_c.grid(row=0, column=0, sticky="nsew", padx=6)
        self.cashflow_label = ctk.CTkLabel(chart_c, text="Cash Flow", font=FONTS["heading"],
                     text_color=THEME["text_primary"])
        self.cashflow_label.pack(anchor="w", padx=20, pady=(20, 0))
        self.chart_cashflow = ChartFrame(chart_c, height=280)
        self.chart_cashflow.pack(fill="both", expand=True, padx=20, pady=(10, 20))

        # Donut Chart Container
        donut_c = ctk.CTkFrame(row1, fg_color=THEME["bg_secondary"], corner_radius=12,
                                border_width=1, border_color=THEME["border"])
        donut_c.grid(row=0, column=1, sticky="nsew", padx=6)
        
        donut_header = ctk.CTkFrame(donut_c, fg_color="transparent")
        donut_header.pack(fill="x", padx=20, pady=(20, 0))
        self.donut_title_lbl = ctk.CTkLabel(donut_header, text="Spending Breakdown",
                     font=FONTS["heading"], text_color=THEME["text_primary"])
        self.donut_title_lbl.pack(side="left")
        self.donut_back_btn = ctk.CTkButton(
            donut_header, text="← Back", width=60, height=24,
            fg_color="transparent", text_color=THEME["blue"],
            hover_color=THEME["bg_tertiary"], font=FONTS["small"],
            command=self._donut_go_back
        )
        # Hidden by default — shown during drill-down
        self.chart_donut = ChartFrame(donut_c, height=280)
        self.chart_donut.pack(fill="both", expand=True, padx=20, pady=(10, 20))

        # ── Row 2: Line Chart & Accounts ──
        row2 = ctk.CTkFrame(self.scroll, fg_color="transparent")
        row2.pack(fill="x", pady=10)
        row2.grid_columnconfigure(0, weight=6)
        row2.grid_columnconfigure(1, weight=4)

        # Line Chart Container
        line_c = ctk.CTkFrame(row2, fg_color=THEME["bg_secondary"], corner_radius=12,
                               border_width=1, border_color=THEME["border"])
        line_c.grid(row=0, column=0, sticky="nsew", padx=6)
        ctk.CTkLabel(line_c, text="Daily Spending Trend (Cumulative)", font=FONTS["heading"],
                     text_color=THEME["text_primary"]).pack(anchor="w", padx=20, pady=(20, 0))
        self.chart_line = ChartFrame(line_c, height=280)
        self.chart_line.pack(fill="both", expand=True, padx=20, pady=(10, 20))

        # Accounts Container — Feature #3: View All + Feature #4: Currency Exposure
        acc_c = ctk.CTkFrame(row2, fg_color=THEME["bg_secondary"], corner_radius=12,
                             border_width=1, border_color=THEME["border"])
        acc_c.grid(row=0, column=1, sticky="nsew", padx=6)

        acc_header = ctk.CTkFrame(acc_c, fg_color="transparent")
        acc_header.pack(fill="x", padx=20, pady=(20, 0))
        ctk.CTkLabel(acc_header, text="Your Accounts", font=FONTS["heading"],
                     text_color=THEME["text_primary"]).pack(side="left")
        ctk.CTkButton(acc_header, text="View All →", width=80, height=24,
                      fg_color="transparent", text_color=THEME["blue"],
                      hover_color=THEME["bg_tertiary"], font=FONTS["small"],
                      command=self._go_accounts).pack(side="right")

        self.acc_list = ctk.CTkScrollableFrame(acc_c, fg_color="transparent", height=180)
        self.acc_list.pack(fill="x", padx=10, pady=(8, 0))

        # Feature #4: Currency Exposure section
        ctk.CTkLabel(acc_c, text="Currency Exposure", font=FONTS["small"],
                     text_color=THEME["text_tertiary"]).pack(anchor="w", padx=20, pady=(10, 4))
        self.exposure_frame = ctk.CTkFrame(acc_c, fg_color="transparent")
        self.exposure_frame.pack(fill="x", padx=16, pady=(0, 16))

    def _build_bottom_section(self):
        bot = ctk.CTkFrame(self.scroll, fg_color="transparent")
        bot.pack(fill="x", pady=(10, 30))
        bot.grid_columnconfigure(0, weight=1)
        bot.grid_columnconfigure(1, weight=1)

        # ── Recent Transactions — Feature #3: header with View All ──
        tx_c = ctk.CTkFrame(bot, fg_color=THEME["bg_secondary"], corner_radius=12,
                            border_width=1, border_color=THEME["border"])
        tx_c.grid(row=0, column=0, sticky="nsew", padx=6)

        tx_header = ctk.CTkFrame(tx_c, fg_color="transparent")
        tx_header.pack(fill="x", padx=20, pady=(20, 10))
        ctk.CTkLabel(tx_header, text="Recent Transactions", font=FONTS["heading"],
                     text_color=THEME["text_primary"]).pack(side="left")
        ctk.CTkButton(tx_header, text="View All →", width=80, height=24,
                      fg_color="transparent", text_color=THEME["blue"],
                      hover_color=THEME["bg_tertiary"], font=FONTS["small"],
                      command=self._go_transactions).pack(side="right")

        self.tx_list = ctk.CTkScrollableFrame(tx_c, fg_color="transparent", height=260)
        self.tx_list.pack(fill="both", expand=True, padx=10, pady=(0, 20))

        # ── Upcoming Planned ──
        up_c = ctk.CTkFrame(bot, fg_color=THEME["bg_secondary"], corner_radius=12,
                            border_width=1, border_color=THEME["border"])
        up_c.grid(row=0, column=1, sticky="nsew", padx=6)
        ctk.CTkLabel(up_c, text="Upcoming Payments", font=FONTS["heading"],
                     text_color=THEME["text_primary"]).pack(anchor="w", padx=20, pady=(20, 10))
        self.up_list = ctk.CTkScrollableFrame(up_c, fg_color="transparent", height=260)
        self.up_list.pack(fill="both", expand=True, padx=10, pady=(0, 20))

    def refresh(self):
        if not self.company_id: return
        ThreadWorker(self, self._fetch_data, on_success=self._update_ui)

    def _fetch_data(self):
        """Heavy data fetching in background thread — uses current date range."""
        df, dt = self._date_from, self._date_to
        summ = get_dashboard_summary(self.company_id, date_from=df, date_to=dt)
        
        # Decide between daily or monthly points for Cashflow chart
        show_daily = False
        if df and dt:
            days_span = (dt - df).days
            if days_span <= 93:  # up to ~3 months
                show_daily = True
                
        if show_daily:
            from services.transaction_service import get_daily_cashflow_series
            labels, inc_series, exp_series = get_daily_cashflow_series(self.company_id, date_from=df, date_to=dt)
        else:
            labels, inc_series, exp_series = get_monthly_series(self.company_id, date_from=df, date_to=dt)
            
        cat_data = get_spending_by_category(
            self.company_id, date_from=df, date_to=dt,
            parent_category_id=self._current_donut_parent_id
        )
        days, cumulative = get_daily_spending_trend(self.company_id, date_from=df, date_to=dt)

        accounts = get_accounts(self.company_id)
        recent_filters = {"date_from": df, "date_to": dt} if df else {}
        recent_txs = get_transactions(self.company_id, recent_filters, limit=10)

        planned = get_planned_payments(self.company_id)
        pending = [p for p in planned if p.status == "pending"][:8]

        # Feature #2: Projected balance
        projected = get_projected_balance(self.company_id)
        # Feature #4: Currency exposure
        exposure = get_currency_exposure(self.company_id)

        return {
            "summ": summ,
            "cashflow_chart": (labels, inc_series, exp_series, show_daily),
            "donut_chart": cat_data,
            "line_chart": (days, cumulative),
            "accounts": accounts,
            "recent_txs": recent_txs,
            "pending_planned": pending,
            "budget_summ": get_budget_summary(self.company_id),
            "projected": projected,
            "exposure": exposure,
        }

    def _update_ui(self, data):
        """Update UI components with fetched data (runs on main thread)."""
        # Fix #3: Guard against TclError if widget was destroyed before data arrived
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return

        summ = data['summ']
        bc = summ.get('base_currency', 'AZN')

        # 1. KPIs — with semantic colors
        self.card_balance.update_data(format_currency(summ['total_balance'], bc))
        self.card_income.update_data(format_currency(summ['total_income'], bc),
                                     value_color=THEME["green"])
        self.card_expense.update_data(format_currency(summ['total_expenses'], bc),
                                      value_color=THEME["red"])
        net = summ['net_profit']
        self.card_net.update_data(format_currency(net, bc),
                                  delta_positive=(net >= 0),
                                  value_color=THEME["green"] if net >= 0 else THEME["red"])
        self.card_top_cat.update_data(summ['top_expense_category'] or "None")
        self.card_avg_spend.update_data(format_currency(summ['avg_daily_spend'], bc))
        self.card_savings.update_data(f"{summ['savings_rate']:.1f}%",
                                       delta_positive=(summ['savings_rate'] > 0))
        b_summ = data['budget_summ']
        if b_summ['total_budgeted'] > 0:
            pct = (b_summ['remaining'] / b_summ['total_budgeted']) * 100
            self.card_budget.update_data(f"{pct:.0f}% Left", delta_positive=(pct > 15))
        else:
            self.card_budget.update_data("Not Set")

        # Feature #2: Projected Balance KPI
        proj = data['projected']
        proj_val = proj['projected_balance']
        self.card_projected.update_data(
            format_currency(proj_val, bc),
            delta_positive=(proj_val >= 0),
            value_color=THEME["green"] if proj_val >= 0 else THEME["red"]
        )

        # 2. Charts
        labels, inc_series, exp_series, is_daily = data['cashflow_chart']
        
        # Update title based on resolution
        if is_daily:
            self.cashflow_label.configure(text="Daily Cash Flow")
        else:
            self.cashflow_label.configure(text="Monthly Cash Flow")
            
        self.chart_cashflow.draw_multi_line_chart(
            labels, 
            {
                "Income": {"values": inc_series, "color": THEME["green"]},
                "Expense": {"values": exp_series, "color": THEME["red"]}
            }
        )
        
        # Update donut chart — toggle drill-down Back button
        if self._current_donut_parent_id:
            self.donut_title_lbl.configure(
                text=f"Spending: {self._current_donut_parent_name}"
            )
            self.donut_back_btn.pack(side="right")
        else:
            self.donut_title_lbl.configure(text="Spending Breakdown")
            self.donut_back_btn.pack_forget()
            
        self.chart_donut.draw_donut_chart(
            data['donut_chart'],
            on_click=self._on_donut_click if not self._current_donut_parent_id else None
        )
        days, cumulative = data['line_chart']
        self.chart_line.draw_line_chart(days, cumulative, "Cumulative Spend", color=THEME["red"])

        # 3. Accounts List
        for w in self.acc_list.winfo_children(): w.destroy()
        accounts = data['accounts']
        if accounts:
            # Fix #6: use abs() so bars work even when all balances are negative
            max_bal = max(abs(a['balance']) for a in accounts) if accounts else 1
            for acc in accounts:
                # Fix #1: pass the account's own currency, not the default "AZN"
                row = AccountMiniRow(self.acc_list, acc, max_bal,
                                     currency=acc['currency'], height=56)
                row.pack(fill="x", padx=6, pady=3)
        else:
            ctk.CTkLabel(self.acc_list, text="No accounts found.", font=FONTS["body"],
                         text_color=THEME["text_tertiary"]).pack(pady=20)

        # Feature #4: Currency Exposure breakdown
        for w in self.exposure_frame.winfo_children(): w.destroy()
        for item in data['exposure']:
            row_f = ctk.CTkFrame(self.exposure_frame, fg_color="transparent")
            row_f.pack(fill="x", pady=2)
            curr_color = THEME["green"] if item['balance'] >= 0 else THEME["red"]
            ctk.CTkLabel(row_f, text=item['currency'], font=FONTS["small"],
                         text_color=THEME["text_secondary"], width=50).pack(side="left")
            ctk.CTkLabel(row_f, text=format_currency(item['balance'], item['currency']),
                         font=FONTS["small"], text_color=curr_color).pack(side="right")

        # 4. Transactions List — Feature #3: clickable rows
        for w in self.tx_list.winfo_children(): w.destroy()
        txs = data['recent_txs']
        if txs:
            for tx in txs:
                row = TxMiniRow(self.tx_list, tx, on_click=self._open_tx_edit, height=56)
                row.pack(fill="x", padx=6, pady=4)
        else:
            ctk.CTkLabel(self.tx_list, text="No recent transactions.", font=FONTS["body"],
                         text_color=THEME["text_tertiary"]).pack(pady=40)

        # 5. Planned List
        for w in self.up_list.winfo_children(): w.destroy()
        pending = data['pending_planned']
        if pending:
            for p in pending:
                row = PlannedMiniRow(self.up_list, p, self._mark_paid, height=56)
                row.pack(fill="x", padx=6, pady=4)
        else:
            ctk.CTkLabel(self.up_list, text="No upcoming payments.", font=FONTS["body"],
                         text_color=THEME["text_tertiary"]).pack(pady=40)

    # ── Navigation helpers (Feature #3) ────────────────────────────────────────
    def _go_transactions(self):
        app = self.winfo_toplevel()
        if hasattr(app, 'show_page'):
            app.show_page("transactions")

    def _go_accounts(self):
        app = self.winfo_toplevel()
        if hasattr(app, 'show_page'):
            app.show_page("accounts")

    def _open_tx_edit(self, tx):
        from ui.modals.edit_transaction import EditTransactionModal
        EditTransactionModal(self.winfo_toplevel(), tx['id'], self.company_id, self.refresh)

    def _mark_paid(self, pid):
        if mark_as_paid(pid):
            self.refresh()