import customtkinter as ctk
from datetime import datetime, timedelta
from ui.theme import THEME, FONTS
from ui.components.topbar import Topbar
from ui.components.kpi_card import KPICard
from ui.components.chart_frame import ChartFrame
from ui.components.mini_rows import AccountMiniRow, TxMiniRow, PlannedMiniRow
from ui.modals.add_transaction import AddTransactionModal
from services.transaction_service import (
    get_dashboard_summary, get_transactions,
    get_spending_by_category, get_daily_spending_trend,
    get_monthly_series, get_projected_balance
)
from services.account_service import get_accounts, get_currency_exposure
from services.budget_service import get_budget_summary
from services.currency_service import format_currency
from services.report_service import get_ar_ap_pipeline
from ui.utils.thread_worker import ThreadWorker
from ui.components.empty_state import EmptyState
from ui.components.loading_state import LoadingState


class DashboardPage(ctk.CTkFrame):
    # Preset date ranges
    PRESETS = {
        "This Month": lambda: DashboardPage._this_month(),
        "Last Month": lambda: DashboardPage._last_month(),
        "Last 3 Months": lambda: DashboardPage._last_n_months(3),
        "This Year": lambda: DashboardPage._this_year(),
        "Next Month": lambda: DashboardPage._next_month(),
        "Next 3 Months": lambda: DashboardPage._next_n_months(3),
        "All Time": lambda: (None, None),
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
        start = datetime(end.year, end.month, 1)
        return start, end

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
        return datetime(now.year, 1, 1), datetime(now.year, 12, 31, 23, 59, 59)

    def __init__(self, master, company_id, navigate=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.company_id = company_id
        self.navigate = navigate
        self._date_from, self._date_to = self._this_month()
        
        self._current_donut_parent_id = None
        self._current_donut_parent_name = None
        self._current_donut_parent_id_inc = None
        self._current_donut_parent_name_inc = None
        self._status_filter = "All"

        # Render chunks state
        self._render_queues = {"acc": [], "tx": [], "up": []}
        self._max_bal = 1

        self.topbar = Topbar(self, title="Dashboard")
        self.topbar.pack(fill="x")
        self.topbar.add_action("+ New Transaction", self._add_transaction, primary=True, shortcut="Ctrl+N")

        self._build_date_filter()

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=20, pady=10)

        self._build_kpis()
        self._build_charts_section()
        self._build_bottom_section()

        self.refresh()

    def _build_date_filter(self):
        bar = ctk.CTkFrame(self, fg_color=THEME["bg_secondary"], corner_radius=0, height=44)
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

        ctk.CTkLabel(inner, text="Status:", font=FONTS["small"],
                     text_color=THEME["text_tertiary"]).pack(side="left", padx=(15, 8))

        self._status_menu = ctk.CTkOptionMenu(
            inner, values=["All", "Paid", "Pending"],
            command=self._apply_status,
            font=FONTS["small"],
            fg_color=THEME["bg_tertiary"], button_color=THEME["border"],
            button_hover_color=THEME["border"], text_color=THEME["text_primary"],
            dropdown_fg_color=THEME["bg_secondary"],
            height=28, width=100
        )
        self._status_menu.set("All")
        self._status_menu.pack(side="left", padx=(0, 6))

        self._custom_btn = ctk.CTkButton(
            inner, text="Custom", height=28, font=FONTS["small"],
            fg_color=THEME["bg_tertiary"],
            hover_color=THEME["border"],
            text_color=THEME["text_primary"],
            command=self._open_custom_date_modal
        )
        self._custom_btn.pack(side="left", padx=0)

        self._range_lbl = ctk.CTkLabel(bar, text="", font=FONTS["small"],
                                        text_color=THEME["text_tertiary"])
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

    def _apply_status(self, label):
        self._status_filter = label
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
            self._range_lbl.configure(
                text=f"{self._date_from.strftime('%d %b %Y')}  →  {self._date_to.strftime('%d %b %Y')}"
            )
        else:
            self._range_lbl.configure(text="All Time")

    def _add_transaction(self):
        AddTransactionModal(self.winfo_toplevel(), self.company_id, self.refresh)

    # ── Zero Latency Chart Drill-Downs ──

    def _on_donut_click(self, cat_data):
        cat_id = cat_data.get("id")
        if cat_id is None:
            return
        self._current_donut_parent_id = cat_id
        self._current_donut_parent_name = cat_data.get("name", "")
        # Don't refresh whole page, just fetch chart data
        ThreadWorker(self, self._fetch_donut_data, on_success=self._update_donut)

    def _donut_go_back(self):
        self._current_donut_parent_id = None
        self._current_donut_parent_name = None
        ThreadWorker(self, self._fetch_donut_data, on_success=self._update_donut)

    def _on_donut_inc_click(self, cat_data):
        cat_id = cat_data.get("id")
        if cat_id is None:
            return
        self._current_donut_parent_id_inc = cat_id
        self._current_donut_parent_name_inc = cat_data.get("name", "")
        ThreadWorker(self, self._fetch_donut_inc_data, on_success=self._update_donut_inc)

    def _donut_inc_go_back(self):
        self._current_donut_parent_id_inc = None
        self._current_donut_parent_name_inc = None
        ThreadWorker(self, self._fetch_donut_inc_data, on_success=self._update_donut_inc)

    def _fetch_donut_data(self):
        return get_spending_by_category(
            self.company_id, date_from=self._date_from, date_to=self._date_to,
            parent_category_id=self._current_donut_parent_id, tx_type='expense',
            status=self._status_filter
        )

    def _fetch_donut_inc_data(self):
        return get_spending_by_category(
            self.company_id, date_from=self._date_from, date_to=self._date_to,
            parent_category_id=self._current_donut_parent_id_inc, tx_type='income',
            status=self._status_filter
        )

    def _update_donut(self, data):
        try:
            if not self.winfo_exists(): return
        except Exception: return
        
        if self._current_donut_parent_id:
            self.donut_title_lbl.configure(text=f"Spending: {self._current_donut_parent_name}")
            self.donut_back_btn.pack(side="right")
        else:
            self.donut_title_lbl.configure(text="Spending Breakdown")
            self.donut_back_btn.pack_forget()
            
        self.chart_donut.draw_donut_chart(data, on_click=self._on_donut_click if not self._current_donut_parent_id else None)
        self._last_data['donut_chart'] = data

    def _update_donut_inc(self, data):
        try:
            if not self.winfo_exists(): return
        except Exception: return
        
        if self._current_donut_parent_id_inc:
            self.donut_inc_title_lbl.configure(text=f"Income: {self._current_donut_parent_name_inc}")
            self.donut_inc_back_btn.pack(side="right")
        else:
            self.donut_inc_title_lbl.configure(text="Income Breakdown")
            self.donut_inc_back_btn.pack_forget()
            
        self.chart_donut_inc.draw_donut_chart(data, on_click=self._on_donut_inc_click if not self._current_donut_parent_id_inc else None)
        self._last_data['donut_inc_chart'] = data

    # ── Builders ──

    def _build_kpis(self):
        self.kpi_frame = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.kpi_frame.pack(fill="x", pady=(0, 12))
        for i in range(4): self.kpi_frame.grid_columnconfigure(i, weight=1)

        self.card_balance = KPICard(self.kpi_frame, "Total Balance", "₼0.00", accent_color=THEME["blue"])
        self.card_balance.grid(row=0, column=0, sticky="ew", padx=6)

        self.card_income = KPICard(self.kpi_frame, "Income (Period)", "₼0.00", accent_color=THEME["green"])
        self.card_income.grid(row=0, column=1, sticky="ew", padx=6)

        self.card_expense = KPICard(self.kpi_frame, "Expenses (Period)", "₼0.00", accent_color=THEME["red"])
        self.card_expense.grid(row=0, column=2, sticky="ew", padx=6)

        self.card_net = KPICard(self.kpi_frame, "Net Profit (Period)", "₼0.00", accent_color=THEME["amber"])
        self.card_net.grid(row=0, column=3, sticky="ew", padx=6)

        self.stat_frame = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.stat_frame.pack(fill="x", pady=(0, 12))
        for i in range(5): self.stat_frame.grid_columnconfigure(i, weight=1)

        self.card_top_cat = KPICard(self.stat_frame, "Top Client", "None", accent_color="#8B5CF6")
        self.card_top_cat.grid(row=0, column=0, sticky="ew", padx=6)

        self.card_avg_spend = KPICard(self.stat_frame, "Avg Daily Spend", "₼0.00", accent_color=THEME["red"])
        self.card_avg_spend.grid(row=0, column=1, sticky="ew", padx=6)

        self.card_savings = KPICard(self.stat_frame, "Savings Rate", "0%", accent_color=THEME["green"])
        self.card_savings.grid(row=0, column=2, sticky="ew", padx=6)

        self.card_budget = KPICard(self.stat_frame, "Budget Health", "…", accent_color=THEME["amber"])
        self.card_budget.grid(row=0, column=3, sticky="ew", padx=6)

        self.proj_frame = ctk.CTkFrame(self.stat_frame, height=108, corner_radius=10,
                                       fg_color=THEME["bg_secondary"],
                                       border_width=1, border_color=THEME["border"])
        self.proj_frame.pack_propagate(False)
        self.proj_frame.grid(row=0, column=4, sticky="ew", padx=6)
        
        ctk.CTkFrame(self.proj_frame, height=3, corner_radius=0, fg_color=THEME["blue"]).pack(fill="x", side="top")
        
        p_body = ctk.CTkFrame(self.proj_frame, fg_color="transparent")
        p_body.pack(fill="both", expand=True, padx=16, pady=(10, 12))
        
        p_head = ctk.CTkFrame(p_body, fg_color="transparent")
        p_head.pack(fill="x")
        ctk.CTkLabel(p_head, text="PROJECTED", font=("Inter", 10, "bold"), 
                     text_color=THEME["text_tertiary"]).pack(side="left")
        
        self.proj_var = ctk.StringVar(value="30 Days")
        self.proj_dropdown = ctk.CTkOptionMenu(
            p_head, values=["30 Days", "90 Days", "All Time"],
            variable=self.proj_var,
            width=75, height=20, font=("Inter", 10),
            fg_color=THEME["bg_tertiary"], button_color=THEME["bg_tertiary"],
            text_color=THEME["text_primary"], dropdown_font=("Inter", 10),
            command=self._on_proj_change
        )
        self.proj_dropdown.pack(side="right")
        
        self.lbl_proj_val = ctk.CTkLabel(p_body, text="₼0.00", font=("Inter", 20, "bold"), text_color=THEME["text_primary"])
        self.lbl_proj_val.pack(anchor="w", pady=(4, 0))

    def _build_charts_section(self):
        row1 = ctk.CTkFrame(self.scroll, fg_color="transparent")
        row1.pack(fill="x", pady=10)
        row1.grid_columnconfigure(0, weight=1)
        row1.grid_columnconfigure(1, weight=1)

        donut_inc_c = ctk.CTkFrame(row1, fg_color=THEME["bg_secondary"], corner_radius=12,
                                border_width=1, border_color=THEME["border"])
        donut_inc_c.grid(row=0, column=0, sticky="nsew", padx=6)
        
        donut_inc_header = ctk.CTkFrame(donut_inc_c, fg_color="transparent")
        donut_inc_header.pack(fill="x", padx=20, pady=(20, 0))
        self.donut_inc_title_lbl = ctk.CTkLabel(donut_inc_header, text="Income Breakdown",
                     font=FONTS["heading"], text_color=THEME["text_primary"])
        self.donut_inc_title_lbl.pack(side="left")
        self.donut_inc_back_btn = ctk.CTkButton(
            donut_inc_header, text="← Back", width=60, height=24,
            fg_color="transparent", text_color=THEME["blue"],
            hover_color=THEME["bg_tertiary"], font=FONTS["small"],
            command=self._donut_inc_go_back
        )
        # Initially hidden
        
        ctk.CTkButton(
            donut_inc_header, text="⛶", width=30, height=24,
            fg_color="transparent", text_color=THEME["text_tertiary"],
            hover_color=THEME["bg_tertiary"], font=FONTS["small"],
            command=lambda: self._expand_chart("donut_inc")
        ).pack(side="right", padx=(0, 4))
        
        self.chart_donut_inc = ChartFrame(donut_inc_c, height=280)
        self.chart_donut_inc.pack(fill="both", expand=True, padx=20, pady=(10, 20))

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
        
        ctk.CTkButton(
            donut_header, text="⛶", width=30, height=24,
            fg_color="transparent", text_color=THEME["text_tertiary"],
            hover_color=THEME["bg_tertiary"], font=FONTS["small"],
            command=lambda: self._expand_chart("donut_exp")
        ).pack(side="right", padx=(0, 4))
        
        self.chart_donut = ChartFrame(donut_c, height=280)
        self.chart_donut.pack(fill="both", expand=True, padx=20, pady=(10, 20))

        row_cashflow = ctk.CTkFrame(self.scroll, fg_color="transparent")
        row_cashflow.pack(fill="x", pady=10)
        row_cashflow.grid_columnconfigure(0, weight=1)

        chart_c = ctk.CTkFrame(row_cashflow, fg_color=THEME["bg_secondary"], corner_radius=12,
                                border_width=1, border_color=THEME["border"])
        chart_c.grid(row=0, column=0, sticky="nsew", padx=6)
        chart_header = ctk.CTkFrame(chart_c, fg_color="transparent")
        chart_header.pack(fill="x", padx=20, pady=(20, 0))
        self.cashflow_label = ctk.CTkLabel(chart_header, text="Cash Flow", font=FONTS["heading"],
                     text_color=THEME["text_primary"])
        self.cashflow_label.pack(side="left")
        
        ctk.CTkButton(
            chart_header, text="⛶", width=30, height=24,
            fg_color="transparent", text_color=THEME["text_tertiary"],
            hover_color=THEME["bg_tertiary"], font=FONTS["small"],
            command=lambda: self._expand_chart("cashflow")
        ).pack(side="right")
        
        self.chart_cashflow = ChartFrame(chart_c, height=280)
        self.chart_cashflow.pack(fill="both", expand=True, padx=20, pady=(10, 20))

        row_arap = ctk.CTkFrame(self.scroll, fg_color="transparent")
        row_arap.pack(fill="x", pady=10)
        row_arap.grid_columnconfigure(0, weight=1)

        arap_c = ctk.CTkFrame(row_arap, fg_color=THEME["bg_secondary"], corner_radius=12,
                              border_width=1, border_color=THEME["border"])
        arap_c.grid(row=0, column=0, sticky="nsew", padx=6)

        arap_header = ctk.CTkFrame(arap_c, fg_color="transparent")
        arap_header.pack(fill="x", padx=20, pady=(20, 0))
        ctk.CTkLabel(arap_header, text="AR / AP Pipeline  —  Pending Cash Flow",
                     font=FONTS["heading"], text_color=THEME["text_primary"]).pack(side="left")

        ctk.CTkButton(
            arap_header, text="View Details →", width=100, height=24,
            fg_color="transparent", text_color=THEME["blue"],
            hover_color=THEME["bg_tertiary"], font=FONTS["small"],
            command=self._go_reports
        ).pack(side="right", padx=(0, 4))

        ctk.CTkButton(
            arap_header, text="⧶", width=30, height=24,
            fg_color="transparent", text_color=THEME["text_tertiary"],
            hover_color=THEME["bg_tertiary"], font=FONTS["small"],
            command=lambda: self._expand_chart("arap")
        ).pack(side="right", padx=(0, 4))

        self._arap_kpi_bar = ctk.CTkFrame(arap_c, fg_color="transparent")
        self._arap_kpi_bar.pack(fill="x", padx=20, pady=(8, 0))

        self._arap_lbl_in  = ctk.CTkLabel(self._arap_kpi_bar, text="↗ Income: —",
                                           font=FONTS["small"], text_color=THEME["green"])
        self._arap_lbl_in.pack(side="left", padx=(0, 24))
        self._arap_lbl_out = ctk.CTkLabel(self._arap_kpi_bar, text="↘ Expense: —",
                                           font=FONTS["small"], text_color=THEME["red"])
        self._arap_lbl_out.pack(side="left", padx=(0, 24))
        self._arap_lbl_net = ctk.CTkLabel(self._arap_kpi_bar, text="≈ Net: —",
                                           font=FONTS["small"], text_color=THEME["blue"])
        self._arap_lbl_net.pack(side="left")

        self.chart_arap = ChartFrame(arap_c, height=220)
        self.chart_arap.pack(fill="both", expand=True, padx=20, pady=(6, 20))

        row2 = ctk.CTkFrame(self.scroll, fg_color="transparent")
        row2.pack(fill="x", pady=10)
        row2.grid_columnconfigure(0, weight=6)
        row2.grid_columnconfigure(1, weight=4)

        line_c = ctk.CTkFrame(row2, fg_color=THEME["bg_secondary"], corner_radius=12,
                                border_width=1, border_color=THEME["border"])
        line_c.grid(row=0, column=0, sticky="nsew", padx=6)
        line_header = ctk.CTkFrame(line_c, fg_color="transparent")
        line_header.pack(fill="x", padx=20, pady=(20, 0))
        ctk.CTkLabel(line_header, text="Daily Spending Trend (Cumulative)", font=FONTS["heading"],
                     text_color=THEME["text_primary"]).pack(side="left")
                     
        ctk.CTkButton(
            line_header, text="⛶", width=30, height=24,
            fg_color="transparent", text_color=THEME["text_tertiary"],
            hover_color=THEME["bg_tertiary"], font=FONTS["small"],
            command=lambda: self._expand_chart("line")
        ).pack(side="right")
        
        self.chart_line = ChartFrame(line_c, height=280)
        self.chart_line.pack(fill="both", expand=True, padx=20, pady=(10, 20))

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

        ctk.CTkLabel(acc_c, text="Currency Exposure", font=FONTS["small"],
                     text_color=THEME["text_tertiary"]).pack(anchor="w", padx=20, pady=(10, 4))
        self.exposure_frame = ctk.CTkFrame(acc_c, fg_color="transparent")
        self.exposure_frame.pack(fill="x", padx=16, pady=(0, 16))

    def _build_bottom_section(self):
        bot = ctk.CTkFrame(self.scroll, fg_color="transparent")
        bot.pack(fill="x", pady=(10, 30))
        bot.grid_columnconfigure(0, weight=1)
        bot.grid_columnconfigure(1, weight=1)

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

        up_c = ctk.CTkFrame(bot, fg_color=THEME["bg_secondary"], corner_radius=12,
                            border_width=1, border_color=THEME["border"])
        up_c.grid(row=0, column=1, sticky="nsew", padx=6)
        ctk.CTkLabel(up_c, text="Pending Transactions", font=FONTS["heading"],
                     text_color=THEME["text_primary"]).pack(anchor="w", padx=20, pady=(20, 10))
        self.up_list = ctk.CTkScrollableFrame(up_c, fg_color="transparent", height=260)
        self.up_list.pack(fill="both", expand=True, padx=10, pady=(0, 20))

    def refresh(self):
        if not self.company_id: return
        
        for card in [self.card_balance, self.card_income, self.card_expense, self.card_net,
                     self.card_top_cat, self.card_avg_spend, self.card_savings, self.card_budget]:
            card.set_loading()
        
        for container in [self.acc_list, self.tx_list, self.up_list]:
            for w in container.winfo_children(): w.destroy()
            LoadingState(container).pack(fill="both", expand=True, pady=20)
            
        ThreadWorker(self, self._fetch_data, on_success=self._update_ui)

    def _fetch_data(self):
        df, dt = self._date_from, self._date_to
        summ = get_dashboard_summary(self.company_id, date_from=df, date_to=dt, status=self._status_filter)
        
        show_daily = False
        if df and dt:
            days_span = (dt - df).days
            if days_span <= 93:
                show_daily = True
                
        if show_daily:
            from services.transaction_service import get_daily_cashflow_series
            labels, inc_series, exp_series = get_daily_cashflow_series(self.company_id, date_from=df, date_to=dt, status=self._status_filter)
        else:
            labels, inc_series, exp_series = get_monthly_series(self.company_id, date_from=df, date_to=dt, status=self._status_filter)
            
        cat_data = get_spending_by_category(
            self.company_id, date_from=df, date_to=dt,
            parent_category_id=self._current_donut_parent_id,
            tx_type='expense', status=self._status_filter
        )
        cat_data_inc = get_spending_by_category(
            self.company_id, date_from=df, date_to=dt,
            parent_category_id=self._current_donut_parent_id_inc,
            tx_type='income', status=self._status_filter
        )
        days, cumulative = get_daily_spending_trend(self.company_id, date_from=df, date_to=dt)

        accounts = get_accounts(self.company_id)
        recent_filters = {"date_from": df, "date_to": dt} if df else {}
        recent_txs = get_transactions(self.company_id, recent_filters, limit=10)

        pending_txs = get_transactions(self.company_id, filters={"status": "pending"}, limit=10)
        pending_txs += get_transactions(self.company_id, filters={"status": "unpaid"}, limit=10)
        seen_ids = set()
        pending_deduped = []
        for tx in sorted(pending_txs, key=lambda x: x['date'] or datetime.min):
            if tx['id'] not in seen_ids:
                seen_ids.add(tx['id'])
                pending_deduped.append(tx)

        projected = get_projected_balance(self.company_id)
        exposure = get_currency_exposure(self.company_id)
        arap = get_ar_ap_pipeline(self.company_id)

        return {
            "summ": summ,
            "cashflow_chart": (labels, inc_series, exp_series, show_daily),
            "donut_chart": cat_data,
            "donut_inc_chart": cat_data_inc,
            "line_chart": (days, cumulative),
            "accounts": accounts,
            "recent_txs": recent_txs,
            "pending_planned": pending_deduped,
            "budget_summ": get_budget_summary(self.company_id),
            "projected": projected,
            "exposure": exposure,
            "arap": arap,
        }

    def _update_ui(self, data):
        try:
            if not self.winfo_exists(): return
        except Exception: return
            
        self._last_data = data
        summ = data['summ']
        bc = summ.get('base_currency', 'AZN')

        labels, inc_series, exp_series, is_daily = data['cashflow_chart']

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

        self._proj_data = data['projected']
        self._on_proj_change(self.proj_var.get())

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
        
        if self._current_donut_parent_id:
            self.donut_title_lbl.configure(text=f"Spending: {self._current_donut_parent_name}")
            self.donut_back_btn.pack(side="right")
        else:
            self.donut_title_lbl.configure(text="Spending Breakdown")
            self.donut_back_btn.pack_forget()
            
        self.chart_donut.draw_donut_chart(
            data['donut_chart'],
            on_click=self._on_donut_click if not self._current_donut_parent_id else None
        )

        if self._current_donut_parent_id_inc:
            self.donut_inc_title_lbl.configure(text=f"Income: {self._current_donut_parent_name_inc}")
            self.donut_inc_back_btn.pack(side="right")
        else:
            self.donut_inc_title_lbl.configure(text="Income Breakdown")
            self.donut_inc_back_btn.pack_forget()
            
        self.chart_donut_inc.draw_donut_chart(
            data['donut_inc_chart'],
            on_click=self._on_donut_inc_click if not self._current_donut_parent_id_inc else None
        )
        
        days, cumulative = data['line_chart']
        self.chart_line.draw_line_chart(days, cumulative, "Cumulative Spend", color=THEME["red"])

        arap = data.get('arap', {})
        if arap and arap.get('labels'):
            bc_arap  = arap.get('base_currency', 'AZN')
            ar  = arap['ar']
            ap  = arap['ap']
            total_ar  = sum(ar)
            total_ap  = sum(ap)
            net_arap       = total_ar - total_ap
            net_color = THEME["blue"] if net_arap >= 0 else THEME["red"]
            self._arap_lbl_in.configure( text=f"↗ Income: {format_currency(total_ar, bc_arap)}")
            self._arap_lbl_out.configure(text=f"↘ Expense: {format_currency(total_ap, bc_arap)}")
            self._arap_lbl_net.configure(text=f"≈ Net: {format_currency(net_arap, bc_arap)}",
                                         text_color=net_color)
            try:
                self.chart_arap.draw_bar_chart(
                    x_labels=arap['labels'],
                    data_series={
                        "Expected Income":  ar,
                        "Expected Expense": ap,
                    },
                    series_colors={
                        "Expected Income":  THEME["green"],
                        "Expected Expense": THEME["red"],
                    }
                )
            except Exception as e:
                pass

        # Prepare chunk rendering
        self._render_queues = {
            "acc": data['accounts'],
            "tx": data['recent_txs'],
            "up": data['pending_planned']
        }
        
        for w in self.acc_list.winfo_children(): w.destroy()
        for w in self.tx_list.winfo_children(): w.destroy()
        for w in self.up_list.winfo_children(): w.destroy()
        
        accounts = data['accounts']
        self._max_bal = max(abs(a['balance']) for a in accounts) if accounts else 1

        for w in self.exposure_frame.winfo_children(): w.destroy()
        for item in data['exposure']:
            row_f = ctk.CTkFrame(self.exposure_frame, fg_color="transparent")
            row_f.pack(fill="x", pady=2)
            curr_color = THEME["green"] if item['balance'] >= 0 else THEME["red"]
            ctk.CTkLabel(row_f, text=item['currency'], font=FONTS["small"],
                         text_color=THEME["text_secondary"], width=50).pack(side="left")
            ctk.CTkLabel(row_f, text=format_currency(item['balance'], item['currency']),
                         font=FONTS["small"], text_color=curr_color).pack(side="right")

        # Start chunk renderer
        self.after(10, self._render_chunk)

    def _render_chunk(self):
        """Asynchronously renders list items 3 at a time to prevent UI freezes."""
        try:
            if not self.winfo_exists(): return
        except Exception: return
        
        processed = 0
        chunk_size = 3
        
        # Accounts
        if self._render_queues["acc"]:
            acc = self._render_queues["acc"].pop(0)
            row = AccountMiniRow(self.acc_list, acc, self._max_bal, currency=acc['currency'], height=56)
            row.pack(fill="x", padx=6, pady=3)
            processed += 1
            
        # Transactions
        if processed < chunk_size and self._render_queues["tx"]:
            tx = self._render_queues["tx"].pop(0)
            row = TxMiniRow(self.tx_list, tx, on_click=self._open_tx_edit, height=56)
            row.pack(fill="x", padx=6, pady=4)
            processed += 1
            
        # Pending
        if processed < chunk_size and self._render_queues["up"]:
            up = self._render_queues["up"].pop(0)
            row = TxMiniRow(self.up_list, up, on_click=self._open_tx_edit, height=56)
            row.pack(fill="x", padx=6, pady=4)
            processed += 1
            
        if any(self._render_queues.values()):
            self.after(10, self._render_chunk)
        else:
            # Check empty states
            if not self._max_bal and len(self.acc_list.winfo_children()) == 0:
                EmptyState(self.acc_list, icon="🏦", title="No accounts", subtitle="Add an account to get started.").pack(fill="both", expand=True)
            if len(self.tx_list.winfo_children()) == 0:
                EmptyState(self.tx_list, icon="💳", title="No recent transactions", subtitle="Transactions for this period will appear here.").pack(fill="both", expand=True)
            if len(self.up_list.winfo_children()) == 0:
                EmptyState(self.up_list, icon="✅", title="No pending transactions", subtitle="All transactions have been paid.").pack(fill="both", expand=True)

    def _go_transactions(self):
        app = self.winfo_toplevel()
        if hasattr(app, 'show_page'):
            app.show_page("transactions")

    def _go_accounts(self):
        app = self.winfo_toplevel()
        if hasattr(app, 'show_page'):
            app.show_page("accounts")

    def _go_reports(self):
        app = self.winfo_toplevel()
        if hasattr(app, 'show_page'):
            app.show_page("reports")

    def _open_tx_edit(self, tx):
        from ui.modals.edit_transaction import EditTransactionModal
        EditTransactionModal(self.winfo_toplevel(), tx['id'], self.company_id, self.refresh)

    def _on_proj_change(self, choice):
        if not hasattr(self, '_proj_data'): return
        bc = self._proj_data['base_currency']
        
        if choice == "30 Days":
            val = self._proj_data['projected_balance_30d']
        elif choice == "90 Days":
            val = self._proj_data['projected_balance_90d']
        else:
            val = self._proj_data['projected_balance_all']
            
        color = THEME["green"] if val >= 0 else THEME["red"]
        self.lbl_proj_val.configure(text=format_currency(val, bc), text_color=color)

    def _expand_chart(self, chart_id):
        from ui.modals.expanded_chart_modal import ExpandedChartModal
        if not hasattr(self, '_last_data'): return
        
        data = self._last_data
        
        if chart_id == "donut_exp":
            kwargs = {"data": data['donut_chart'], "on_click": self._on_donut_click if not self._current_donut_parent_id else None}
            ExpandedChartModal(self.winfo_toplevel(), "Expanded Spending Breakdown", "donut", kwargs)
        elif chart_id == "donut_inc":
            kwargs = {"data": data['donut_inc_chart'], "on_click": self._on_donut_inc_click if not self._current_donut_parent_id_inc else None}
            ExpandedChartModal(self.winfo_toplevel(), "Expanded Income Breakdown", "donut", kwargs)
        elif chart_id == "cashflow":
            labels, inc_series, exp_series, is_daily = data['cashflow_chart']
            kwargs = {
                "x_labels": labels, 
                "data_series": {
                    "Income": {"values": inc_series, "color": THEME["green"]},
                    "Expense": {"values": exp_series, "color": THEME["red"]}
                }
            }
            ExpandedChartModal(self.winfo_toplevel(), "Expanded Cash Flow", "multi_line", kwargs)
        elif chart_id == "line":
            days, cumulative = data['line_chart']
            kwargs = {"days": days, "values": cumulative, "label": "Cumulative Spend", "color": THEME["red"]}
            ExpandedChartModal(self.winfo_toplevel(), "Expanded Daily Spending Trend", "line", kwargs)
        elif chart_id == "arap":
            arap = data.get('arap', {})
            if arap and arap.get('labels'):
                kwargs = {
                    "x_labels": arap['labels'],
                    "data_series": {
                        "Expected Income":  arap['ar'],
                        "Expected Expense": arap['ap'],
                    },
                    "series_colors": {
                        "Expected Income":  THEME["green"],
                        "Expected Expense": THEME["red"],
                    }
                }
                ExpandedChartModal(self.winfo_toplevel(), "AR / AP Pipeline", "bar", kwargs)