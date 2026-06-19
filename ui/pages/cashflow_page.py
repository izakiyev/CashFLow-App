import customtkinter as ctk
from datetime import datetime
from ui.theme import THEME, FONTS
from ui.components.topbar import Topbar
from ui.components.kpi_card import KPICard
from ui.components.chart_frame import ChartFrame
from ui.components.data_table import DataTable
from services.transaction_service import get_dashboard_summary, get_monthly_series, get_daily_cashflow_series
from services.report_service import get_pl_statement, get_vat_report, get_cash_flow_forecast, get_fx_gain_loss
from services.currency_service import format_currency
from ui.utils.thread_worker import ThreadWorker
from ui.components.toast import Toast
import os
import csv


class CashFlowPage(ctk.CTkFrame):
    PRESETS = {
        "This Month":    lambda: CashFlowPage._this_month(),
        "Last Month":    lambda: CashFlowPage._last_month(),
        "Last 3 Months": lambda: CashFlowPage._last_n_months(3),
        "This Year":     lambda: CashFlowPage._this_year(),
        "All Time":      lambda: (None, None),
    }

    @staticmethod
    def _this_month():
        now = datetime.now()
        return datetime(now.year, now.month, 1), now

    @staticmethod
    def _last_month():
        from datetime import timedelta
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
        # Span from Jan 1st to Dec 31st to include future transactions in the current year
        return datetime(now.year, 1, 1), datetime(now.year, 12, 31, 23, 59, 59)

    def __init__(self, master, company_id, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.company_id = company_id
        self._date_from, self._date_to = self._this_month()
        # Cache raw table data for export (instead of reading widget text)
        self._table_raw_data = []
        # Drill-down state for expense donut
        self._current_exp_parent_id = None
        self._current_exp_parent_name = None

        # Drill-down state for income donut
        self._current_inc_parent_id = None
        self._current_inc_parent_name = None

        self.topbar = Topbar(self, title="Cash Flow Analysis")
        self.topbar.pack(fill="x")

        self._build_date_filter()

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=20, pady=10)

        self._build_kpis()
        self._build_chart()
        self._build_forecast()
        self._build_vat_summary()
        self._build_donut_charts()
        self._build_table()

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
                text_color="white" if is_active else THEME["text_primary"],
                command=lambda l=label: self._apply_preset(l)
            )
            btn.pack(side="left", padx=3)
            self._filter_buttons[label] = btn

        btn_custom = ctk.CTkButton(
            inner, text="Custom", height=28, font=FONTS["small"],
            fg_color=THEME["bg_tertiary"],
            hover_color=THEME["border"],
            text_color=THEME["text_primary"],
            command=self._open_custom_date_modal
        )
        btn_custom.pack(side="left", padx=3)
        self._filter_buttons["Custom"] = btn_custom

        self._range_lbl = ctk.CTkLabel(bar, text="", font=FONTS["small"], text_color=THEME["text_tertiary"])
        self._range_lbl.pack(side="right", padx=20)
        self._update_range_label()

    def _apply_preset(self, label):
        if label != "Custom":
            self._date_from, self._date_to = self.PRESETS[label]()
        for lbl, btn in self._filter_buttons.items():
            is_active = (lbl == label)
            btn.configure(
                fg_color=THEME["blue"] if is_active else THEME["bg_tertiary"],
                hover_color=THEME["blue"] if is_active else THEME["border"],
                text_color="white" if is_active else THEME["text_primary"]
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
            self._range_lbl.configure(
                text=f"{self._date_from.strftime('%d %b %Y')}  →  {self._date_to.strftime('%d %b %Y')}"
            )
        else:
            self._range_lbl.configure(text="All Time")

    # ─── UI Build ─────────────────────────────────────────────────────────────

    def _build_kpis(self):
        self.kpi_frame = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.kpi_frame.pack(fill="x", pady=(0, 20))
        for i in range(4):
            self.kpi_frame.grid_columnconfigure(i, weight=1)

        self.card_income = KPICard(self.kpi_frame, "Total Income", "₼0.00")
        self.card_income.grid(row=0, column=0, sticky="ew", padx=6)

        self.card_expense = KPICard(self.kpi_frame, "Total Expenses", "₼0.00")
        self.card_expense.grid(row=0, column=1, sticky="ew", padx=6)

        self.card_net = KPICard(self.kpi_frame, "Net Cash Flow", "₼0.00")
        self.card_net.grid(row=0, column=2, sticky="ew", padx=6)

        self.card_margin = KPICard(self.kpi_frame, "Operating Margin", "0.0%")
        self.card_margin.grid(row=0, column=3, sticky="ew", padx=6)

    def _build_chart(self):
        container = ctk.CTkFrame(self.scroll, fg_color=THEME["bg_secondary"], corner_radius=12,
                                 border_width=1, border_color=THEME["border"])
        container.pack(fill="x", pady=10, padx=6)

        header = ctk.CTkFrame(container, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 0))

        self.chart_title_lbl = ctk.CTkLabel(header, text="Cash Flow Trend", font=FONTS["heading"],
                                            text_color=THEME["text_primary"])
        self.chart_title_lbl.pack(side="left")

        self.trend_chart = ChartFrame(container, height=280)
        self.trend_chart.pack(fill="both", expand=True, padx=20, pady=(10, 20))

    def _build_forecast(self):
        container = ctk.CTkFrame(self.scroll, fg_color=THEME["bg_secondary"], corner_radius=12,
                                 border_width=1, border_color=THEME["border"])
        container.pack(fill="x", pady=10, padx=6)

        header = ctk.CTkFrame(container, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 0))
        ctk.CTkLabel(header, text="Cash Position Forecast (90 Days)", font=FONTS["heading"],
                     text_color=THEME["text_primary"]).pack(side="left")

        self.forecast_chart = ChartFrame(container, height=280)
        self.forecast_chart.pack(fill="both", expand=True, padx=20, pady=(10, 20))

    def _build_vat_summary(self):
        container = ctk.CTkFrame(self.scroll, fg_color=THEME["bg_secondary"], corner_radius=12,
                                 border_width=1, border_color=THEME["border"])
        container.pack(fill="x", pady=10, padx=6)

        header = ctk.CTkFrame(container, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 0))
        ctk.CTkLabel(header, text="Fiscal & Currency Performance", font=FONTS["heading"],
                     text_color=THEME["text_primary"]).pack(side="left")

        row = ctk.CTkFrame(container, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=20)
        for i in range(4):
            row.grid_columnconfigure(i, weight=1)

        self.vat_collected  = KPICard(row, "VAT Collected (In)", "₼0.00")
        self.vat_collected.grid(row=0, column=0, sticky="ew", padx=10)

        self.vat_paid = KPICard(row, "VAT Paid (Out)", "₼0.00")
        self.vat_paid.grid(row=0, column=1, sticky="ew", padx=10)

        self.vat_net = KPICard(row, "Net VAT Liability", "₼0.00")
        self.vat_net.grid(row=0, column=2, sticky="ew", padx=10)

        self.fx_performance = KPICard(row, "FX Gain/Loss", "₼0.00")
        self.fx_performance.grid(row=0, column=3, sticky="ew", padx=10)

    def _build_donut_charts(self):
        row = ctk.CTkFrame(self.scroll, fg_color="transparent")
        row.pack(fill="x", pady=10)
        row.grid_columnconfigure(0, weight=1)
        row.grid_columnconfigure(1, weight=1)

        # ── Income Donut (with drill-down) ────────────────────────────
        inc_c = ctk.CTkFrame(row, fg_color=THEME["bg_secondary"], corner_radius=12,
                             border_width=1, border_color=THEME["border"])
        inc_c.grid(row=0, column=0, sticky="nsew", padx=6)
        
        inc_header = ctk.CTkFrame(inc_c, fg_color="transparent")
        inc_header.pack(fill="x", padx=20, pady=(20, 0))
        self.inc_donut_title_lbl = ctk.CTkLabel(inc_header, text="Income Distribution",
                     font=FONTS["heading"], text_color=THEME["text_primary"])
        self.inc_donut_title_lbl.pack(side="left")
        self.inc_donut_back_btn = ctk.CTkButton(
            inc_header, text="\u2190 Back", width=60, height=24,
            fg_color="transparent", text_color=THEME["blue"],
            hover_color=THEME["bg_tertiary"], font=FONTS["small"],
            command=self._inc_donut_go_back
        )
        self.inc_donut = ChartFrame(inc_c, height=240)
        self.inc_donut.pack(fill="both", expand=True, padx=20, pady=(10, 20))

        # ── Expense Donut (with drill-down) ─────────────────────────────────
        exp_c = ctk.CTkFrame(row, fg_color=THEME["bg_secondary"], corner_radius=12,
                             border_width=1, border_color=THEME["border"])
        exp_c.grid(row=0, column=1, sticky="nsew", padx=6)

        exp_header = ctk.CTkFrame(exp_c, fg_color="transparent")
        exp_header.pack(fill="x", padx=20, pady=(20, 0))
        self.exp_donut_title_lbl = ctk.CTkLabel(exp_header, text="Expense Distribution",
                     font=FONTS["heading"], text_color=THEME["text_primary"])
        self.exp_donut_title_lbl.pack(side="left")
        self.exp_donut_back_btn = ctk.CTkButton(
            exp_header, text="\u2190 Back", width=60, height=24,
            fg_color="transparent", text_color=THEME["blue"],
            hover_color=THEME["bg_tertiary"], font=FONTS["small"],
            command=self._exp_donut_go_back
        )
        # Hidden by default
        self.exp_donut = ChartFrame(exp_c, height=240)
        self.exp_donut.pack(fill="both", expand=True, padx=20, pady=(10, 20))

    def _build_table(self):
        container = ctk.CTkFrame(self.scroll, fg_color=THEME["bg_secondary"], corner_radius=12,
                                 border_width=1, border_color=THEME["border"])
        container.pack(fill="x", pady=(20, 30), padx=6)

        header = ctk.CTkFrame(container, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))
        ctk.CTkLabel(header, text="Cash Flow Breakdown", font=FONTS["heading"],
                     text_color=THEME["text_primary"]).pack(side="left")

        ctk.CTkButton(header, text="\u2b07 Export CSV", width=110, height=28,
                      fg_color=THEME["bg_tertiary"], hover_color=THEME["border"],
                      text_color=THEME["text_primary"], font=FONTS["small"],
                      command=self._export_csv).pack(side="right")

        self.table = DataTable(container, ["Period", "Income", "Expenses", "Net Flow", "Margin"])
        self.table.pack(fill="both", expand=True, padx=16, pady=(0, 20))

    def _on_exp_donut_click(self, cat_data):
        """Called when user clicks an expense wedge."""
        cat_id = cat_data.get("id")
        if cat_id is None:
            return
        self._current_exp_parent_id = cat_id
        self._current_exp_parent_name = cat_data.get("name", "")
        self.refresh()

    def _exp_donut_go_back(self):
        """Return to top-level expense breakdown."""
        self._current_exp_parent_id = None
        self._current_exp_parent_name = None
        self.refresh()

    def _on_inc_donut_click(self, cat_data):
        """Called when user clicks an income wedge."""
        cat_id = cat_data.get("id")
        if cat_id is None:
            return
        self._current_inc_parent_id = cat_id
        self._current_inc_parent_name = cat_data.get("name", "")
        self.refresh()

    def _inc_donut_go_back(self):
        """Return to top-level income breakdown."""
        self._current_inc_parent_id = None
        self._current_inc_parent_name = None
        self.refresh()

    # ─── Data Fetching ────────────────────────────────────────────────────────

    def refresh(self):
        if not self.company_id:
            return
        ThreadWorker(self, self._fetch_data, on_success=self._update_ui)

    def _fetch_data(self):
        df, dt = self._date_from, self._date_to

        summ = get_dashboard_summary(self.company_id, date_from=df, date_to=dt)
        pl   = get_pl_statement(self.company_id, date_from=df, date_to=dt)

        # Smart resolution: daily for ≤90 days, monthly otherwise
        show_daily = bool(df and dt and (dt - df).days <= 90)
        if show_daily:
            labels, inc_series, exp_series = get_daily_cashflow_series(
                self.company_id, date_from=df, date_to=dt)
        else:
            labels, inc_series, exp_series = get_monthly_series(
                self.company_id, date_from=df, date_to=dt)

        vat              = get_vat_report(self.company_id, date_from=df, date_to=dt)
        f_dates, f_bals  = get_cash_flow_forecast(self.company_id)
        fx               = get_fx_gain_loss(self.company_id, date_from=df, date_to=dt)

        from services.transaction_service import get_spending_by_category
        exp_cat_data = get_spending_by_category(
            self.company_id, date_from=df, date_to=dt,
            parent_category_id=self._current_exp_parent_id,
            tx_type='expense'
        )
        
        inc_cat_data = get_spending_by_category(
            self.company_id, date_from=df, date_to=dt,
            parent_category_id=self._current_inc_parent_id,
            tx_type='income'
        )

        return {
            "summ": summ, "pl": pl,
            "chart_data": (labels, inc_series, exp_series, show_daily),
            "vat": vat, "forecast": (f_dates, f_bals), "fx": fx,
            "exp_cat_data": exp_cat_data,
            "inc_cat_data": inc_cat_data,
        }

    # ─── UI Update ────────────────────────────────────────────────────────────

    def _update_ui(self, data):
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return

        # ── KPIs ───────────────────────────────────────────────────────────
        summ = data["summ"]
        bc   = summ.get("base_currency", "AZN")

        self.card_income.update_data(format_currency(summ["total_income"], bc),
                                     value_color=THEME["green"])
        self.card_expense.update_data(format_currency(summ["total_expenses"], bc),
                                      value_color=THEME["red"])
        net = summ["net_profit"]
        self.card_net.update_data(format_currency(net, bc),
                                  delta_positive=(net >= 0),
                                  value_color=THEME["green"] if net >= 0 else THEME["red"])
        margin = (net / summ["total_income"] * 100) if summ["total_income"] > 0 else 0
        self.card_margin.update_data(f"{margin:.1f}%", delta_positive=(margin > 0))

        # ── Forecast Chart ─────────────────────────────────────────────────
        f_dates, f_bals = data["forecast"]
        self.forecast_chart.draw_line_chart(f_dates, f_bals, f"Balance ({bc})",
                                             color=THEME["blue"])

        # ── VAT & FX ───────────────────────────────────────────────────────
        v = data["vat"]
        self.vat_collected.update_data(format_currency(v["collected"], bc),
                                       value_color=THEME["green"])
        self.vat_paid.update_data(format_currency(v["paid"], bc),
                                  value_color=THEME["red"])
        self.vat_net.update_data(format_currency(v["net"], bc),
                                 delta_positive=(v["net"] >= 0),
                                 value_color=THEME["green"] if v["net"] >= 0 else THEME["red"])

        fx = data["fx"]
        self.fx_performance.update_data(
            format_currency(fx["total_gain_loss"], bc),
            delta_positive=(fx["total_gain_loss"] >= 0),
            value_color=THEME["green"] if fx["total_gain_loss"] >= 0 else THEME["red"]
        )

        # ── Expense Donut — with drill-down ─────────────────────────────────
        exp_cat_data = data["exp_cat_data"]
        exp_palette = [THEME["red"], "#F97316", "#D946EF", "#06B6D4", "#6366F1", "#F43F5E"]
        # Merge color if not set
        for i, item in enumerate(exp_cat_data):
            if not item.get("color") or item["color"] == "#888888":
                item["color"] = exp_palette[i % len(exp_palette)]

        if not exp_cat_data:
            exp_cat_data = [{"id": None, "name": "No Data", "amount": 1, "color": THEME["border"]}]

        if self._current_exp_parent_id:
            self.exp_donut_title_lbl.configure(
                text=f"Expenses: {self._current_exp_parent_name}"
            )
            self.exp_donut_back_btn.pack(side="right")
        else:
            self.exp_donut_title_lbl.configure(text="Expense Distribution")
            self.exp_donut_back_btn.pack_forget()

        self.exp_donut.draw_donut_chart(
            exp_cat_data,
            on_click=self._on_exp_donut_click if not self._current_exp_parent_id else None
        )

        # ── Income Donut (with drill-down) ─────────────────────────────────────
        inc_cat_data = data["inc_cat_data"]
        inc_palette = [THEME["green"], THEME["blue"], "#F59E0B", "#8B5CF6", "#EC4899", "#14B8A6"]
        
        for i, item in enumerate(inc_cat_data):
            if not item.get("color") or item["color"] == "#888888":
                item["color"] = inc_palette[i % len(inc_palette)]

        if not inc_cat_data:
            inc_cat_data = [{"id": None, "name": "No Data", "amount": 1, "color": THEME["border"]}]

        if self._current_inc_parent_id:
            self.inc_donut_title_lbl.configure(
                text=f"Income: {self._current_inc_parent_name}"
            )
            self.inc_donut_back_btn.pack(side="right")
        else:
            self.inc_donut_title_lbl.configure(text="Income Distribution")
            self.inc_donut_back_btn.pack_forget()

        self.inc_donut.draw_donut_chart(
            inc_cat_data,
            on_click=self._on_inc_donut_click if not self._current_inc_parent_id else None
        )

        # ── Trend Chart ────────────────────────────────────────────────────
        labels, inc_series, exp_series, show_daily = data["chart_data"]
        self.chart_title_lbl.configure(
            text="Daily Cash Flow Trend" if show_daily else "Monthly Cash Flow Overview"
        )
        self.trend_chart.draw_multi_line_chart(
            labels,
            {"Income": inc_series, "Expense": exp_series},
            [THEME["green"], THEME["red"]]
        )

        # ── Breakdown Table ────────────────────────────────────────────────
        self.table.clear_rows()
        self._table_raw_data = []

        for i in range(len(labels) - 1, -1, -1):
            period = labels[i]
            inc    = inc_series[i]
            exp    = exp_series[i]
            net_v  = inc - exp
            m_margin = f"{(net_v / inc * 100):.1f}%" if inc > 0 else "0.0%"

            row = [period, format_currency(inc, bc),
                   format_currency(exp, bc), format_currency(net_v, bc), m_margin]
            self._table_raw_data.append(row)

            # Color the net column green/red
            net_color = THEME["green"] if net_v >= 0 else THEME["red"]
            self.table.add_row(row, color=net_color if net_v != 0 else None)

    # ─── Export ───────────────────────────────────────────────────────────────

    def _export_csv(self):
        if not self._table_raw_data:
            Toast(self.winfo_toplevel(), "No data to export for this period.", type="info")
            return
        try:
            home     = os.path.expanduser("~")
            docs_dir = os.path.join(home, "Documents")
            if not os.path.exists(docs_dir):
                docs_dir = home

            filename = f"cash_flow_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            filepath = os.path.join(docs_dir, filename)

            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Period", "Income", "Expenses", "Net Flow", "Margin"])
                writer.writerows(self._table_raw_data)

            Toast(self.winfo_toplevel(), f"Exported → Documents/{filename}", type="success")
        except Exception as e:
            Toast(self.winfo_toplevel(), f"Export failed: {e}", type="error")
