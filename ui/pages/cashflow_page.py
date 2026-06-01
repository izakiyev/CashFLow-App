import customtkinter as ctk
from datetime import datetime
from ui.theme import THEME, FONTS
from ui.components.topbar import Topbar
from ui.components.kpi_card import KPICard
from ui.components.chart_frame import ChartFrame
from ui.components.data_table import DataTable
from services.transaction_service import get_dashboard_summary, get_monthly_series
from services.report_service import get_pl_statement, get_vat_report, get_cash_flow_forecast, get_fx_gain_loss
from services.ai_service import AIService
from services.currency_service import format_currency
from ui.utils.thread_worker import ThreadWorker
from ui.components.toast import Toast
import os
import csv



class CashFlowPage(ctk.CTkFrame):
    PRESETS = {
        "This Month": lambda: CashFlowPage._this_month(),
        "Last Month": lambda: CashFlowPage._last_month(),
        "Last 3 Months": lambda: CashFlowPage._last_n_months(3),
        "This Year": lambda: CashFlowPage._this_year(),
        "All Time": lambda: (None, None),
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
        last_month_end = first - timedelta(days=1)
        last_month_start = datetime(last_month_end.year, last_month_end.month, 1)
        return last_month_start, last_month_end

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
        self.ai_service = AIService(company_id=self.company_id)
        self._date_from, self._date_to = self._this_month()

        self.topbar = Topbar(self, title="Cash Flow Analysis")
        self.topbar.pack(fill="x")

        self._build_date_filter()

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=20, pady=10)

        self._build_ai_insights()
        self._build_kpis()
        self._build_bar_chart()
        self._build_forecast()
        self._build_vat_summary()
        self._build_donut_charts()
        self._build_table()
        
        self.refresh()

    def _build_date_filter(self):
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

    def _build_ai_insights(self):
        self.ai_frame = ctk.CTkFrame(self.scroll, fg_color=THEME["bg_secondary"], corner_radius=12,
                                     border_width=1, border_color=THEME["blue"])
        self.ai_frame.pack(fill="x", pady=(0, 20), padx=6)
        
        header = ctk.CTkFrame(self.ai_frame, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(15, 5))
        
        ctk.CTkLabel(header, text="✨ AI Financial Auditor", font=FONTS["heading"],
                     text_color=THEME["blue"]).pack(side="left")
        
        self.ai_text = ctk.CTkLabel(self.ai_frame, text="Analyzing your finances... 🤖", 
                                    font=FONTS["body"], text_color=THEME["text_secondary"],
                                    justify="left", wraplength=1000)
        self.ai_text.pack(fill="x", padx=20, pady=(0, 20), anchor="w")

    def _build_kpis(self):
# ... existing _build_kpis ...
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

    def _build_bar_chart(self):
        container = ctk.CTkFrame(self.scroll, fg_color=THEME["bg_secondary"], corner_radius=12,
                                 border_width=1, border_color=THEME["border"])
        container.pack(fill="x", pady=10, padx=6)
        
        header = ctk.CTkFrame(container, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 0))
        ctk.CTkLabel(header, text="Monthly Cash Flow Overview", font=FONTS["heading"],
                     text_color=THEME["text_primary"]).pack(side="left")
        
        self.bar_chart = ChartFrame(container, height=280)
        self.bar_chart.pack(fill="both", expand=True, padx=20, pady=(10, 20))

    def _build_forecast(self):
        container = ctk.CTkFrame(self.scroll, fg_color=THEME["bg_secondary"], corner_radius=12,
                                 border_width=1, border_color=THEME["border"])
        container.pack(fill="x", pady=10, padx=6)
        
        header = ctk.CTkFrame(container, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 0))
        ctk.CTkLabel(header, text="Cash Position Forecast (90 Days)", font=FONTS["heading"],
                     text_color=THEME["text_primary"]).pack(side="left")
        
        self.forecast_chart = ChartFrame(container, height=300)
        self.forecast_chart.pack(fill="both", expand=True, padx=20, pady=(10, 20))

    def _build_vat_summary(self):
        container = ctk.CTkFrame(self.scroll, fg_color=THEME["bg_secondary"], corner_radius=12,
                                 border_width=1, border_color=THEME["border"])
        container.pack(fill="x", pady=10, padx=6)
        
        header = ctk.CTkFrame(container, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 0))
        ctk.CTkLabel(header, text="Fiscal & Currency Performance", font=FONTS["heading"],
                     text_color=THEME["text_primary"]).pack(side="left")
        
        # Internal Row for cards
        row = ctk.CTkFrame(container, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=20)
        for i in range(4): row.grid_columnconfigure(i, weight=1)

        self.vat_collected = KPICard(row, "VAT Collected (In)", "₼0.00")
        self.vat_collected.grid(row=0, column=0, sticky="ew", padx=10)
        
        self.vat_paid = KPICard(row, "VAT Paid (Out)", "₼0.00")
        self.vat_paid.grid(row=0, column=1, sticky="ew", padx=10)
        
        self.vat_net = KPICard(row, "Net VAT Liability", "₼0.00")
        self.vat_net.grid(row=0, column=2, sticky="ew", padx=10)

        self.fx_performance = KPICard(row, "FX Gain/Loss", "₼0.00")
        self.fx_performance.grid(row=0, column=3, sticky="ew", padx=10)

    def _build_donut_charts(self):
# ... existing _build_donut_charts ...
        row = ctk.CTkFrame(self.scroll, fg_color="transparent")
        row.pack(fill="x", pady=10)
        row.grid_columnconfigure(0, weight=1)
        row.grid_columnconfigure(1, weight=1)

        def _make_donut(parent, title, col):
            c = ctk.CTkFrame(parent, fg_color=THEME["bg_secondary"], corner_radius=12,
                             border_width=1, border_color=THEME["border"])
            c.grid(row=0, column=col, sticky="nsew", padx=6)
            ctk.CTkLabel(c, text=title, font=FONTS["heading"], text_color=THEME["text_primary"]
                         ).pack(anchor="w", padx=20, pady=(20, 0))
            chart = ChartFrame(c, height=240)
            chart.pack(fill="both", expand=True, padx=20, pady=(10, 20))
            return chart

        self.inc_donut = _make_donut(row, "Income Distribution", 0)
        self.exp_donut = _make_donut(row, "Expense Distribution", 1)

    def _build_table(self):
        container = ctk.CTkFrame(self.scroll, fg_color=THEME["bg_secondary"], corner_radius=12,
                                 border_width=1, border_color=THEME["border"])
        container.pack(fill="x", pady=(20, 30), padx=6)
        header = ctk.CTkFrame(container, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))
        ctk.CTkLabel(header, text="Cash Flow Breakdown", font=FONTS["heading"],
                     text_color=THEME["text_primary"]).pack(side="left")
        
        ctk.CTkButton(header, text="⬇ Export CSV", width=100, height=28,
                      fg_color=THEME["bg_tertiary"], hover_color=THEME["border"],
                      text_color=THEME["text_primary"], font=FONTS["small"],
                      command=self._export_csv).pack(side="right")
                     
        self.table = DataTable(container, ["Period", "Income", "Expenses", "Net Flow", "Margin"])
        self.table.pack(fill="both", expand=True, padx=16, pady=(0, 20))

    def refresh(self):
        if not self.company_id: return
        self.ai_text.configure(text="Analyzing your finances... 🤖")
        ThreadWorker(self, self._fetch_data, on_success=self._update_ui)

    def _fetch_data(self):
        df, dt = self._date_from, self._date_to
        
        summ = get_dashboard_summary(self.company_id, date_from=df, date_to=dt)
        pl = get_pl_statement(self.company_id, date_from=df, date_to=dt)
        months, inc_series, exp_series = get_monthly_series(self.company_id, date_from=df, date_to=dt)
        vat = get_vat_report(self.company_id, date_from=df, date_to=dt)
        f_dates, f_balances = get_cash_flow_forecast(self.company_id)
        fx = get_fx_gain_loss(self.company_id, date_from=df, date_to=dt)

        return {
            "summ": summ, "pl": pl, "monthly": (months, inc_series, exp_series),
            "vat": vat, "forecast": (f_dates, f_balances), "fx": fx, 
        }

    def _fetch_ai_insight(self, ai_summary):
        return self.ai_service.get_financial_insights(ai_summary)

    def _update_ai_insight(self, insights):
        try:
            if self.winfo_exists():
                self.ai_text.configure(text=insights)
        except Exception:
            pass

    def _update_ui(self, data):
        try:
            if not self.winfo_exists(): return
        except Exception:
            return

        from services.company_service import get_company
        comp = get_company(self.company_id)
        ai_enabled = comp.get("ai_enabled", True) if comp else True
        
        # 1. Start AI Insights Async
        if ai_enabled:
            self.ai_frame.pack(fill="x", pady=(0, 20), padx=6, before=self.kpi_frame)
            summ = data['summ']
            fx = data['fx']
            ai_summary = f"Total Income: {summ['total_income']}, Expenses: {summ['total_expenses']}, "
            ai_summary += f"Net: {summ['net_profit']}, FX Performance: {fx['total_gain_loss']}, "
            ai_summary += f"Top Expense: {summ.get('top_expense_category', 'N/A')}"
            ThreadWorker(self, lambda: self._fetch_ai_insight(ai_summary), on_success=self._update_ai_insight)
        else:
            self.ai_frame.pack_forget()

        # 2. Update KPIs
# ...
        summ = data['summ']
        bc = summ.get('base_currency', 'AZN')
        self.card_income.update_data(format_currency(summ['total_income'], bc))
        self.card_expense.update_data(format_currency(summ['total_expenses'], bc))
        self.card_net.update_data(format_currency(summ['net_profit'], bc), delta_positive=(summ['net_profit'] >= 0))
        
        margin = (summ['net_profit'] / summ['total_income'] * 100) if summ['total_income'] > 0 else 0
        self.card_margin.update_data(f"{margin:.1f}%", delta_positive=(margin > 0))

        # 3. Update Forecast
        f_dates, f_balances = data['forecast']
        self.forecast_chart.draw_line_chart(f_dates, f_balances, f"Balance ({bc})", color=THEME["blue"])

        # 4. Update Fiscal & FX
        v = data['vat']
        self.vat_collected.update_data(format_currency(v['collected'], bc))
        self.vat_paid.update_data(format_currency(v['paid'], bc))
        self.vat_net.update_data(format_currency(v['net'], bc), delta_positive=(v['net'] >= 0))
        
        fx = data['fx']
        self.fx_performance.update_data(format_currency(fx['total_gain_loss'], bc), 
                                         delta_positive=(fx['total_gain_loss'] >= 0))

        # 4. Update Donut Charts
        pl = data['pl']
        def _c(color_val):
            return color_val[1] if isinstance(color_val, (list, tuple)) else color_val
        
        colors = [_c(THEME["green"]), _c(THEME["blue"]), "#F59E0B", "#8B5CF6", "#EC4899", "#14B8A6"]
        inc_data = [{"name": item["name"], "amount": item["amount"], "color": item.get("color") or colors[i % len(colors)]} 
                    for i, item in enumerate(pl['income'])]
        if not inc_data: inc_data = [{"name": "No Data", "amount": 1, "color": _c(THEME["border"])}]
        self.inc_donut.draw_donut_chart(inc_data)
        
        exp_colors = [_c(THEME["red"]), "#F97316", "#D946EF", "#06B6D4", "#6366F1", "#F43F5E"]
        exp_data = [{"name": item["name"], "amount": item["amount"], "color": item.get("color") or exp_colors[i % len(exp_colors)]} 
                    for i, item in enumerate(pl['expenses'])]
        if not exp_data: exp_data = [{"name": "No Data", "amount": 1, "color": _c(THEME["border"])}]
        self.exp_donut.draw_donut_chart(exp_data)

        # 5. Draw Bar Chart
        months, inc_series, exp_series = data['monthly']
        self.bar_chart.draw_bar_chart(months, {"Income": inc_series, "Expense": exp_series})

        # 6. Populate Table
        self.table.clear_rows()
        for i in range(len(months)-1, -1, -1):
            period = months[i]
            inc = inc_series[i]
            exp = exp_series[i]
            net = inc - exp
            m_margin = f"{(net / inc * 100):.1f}%" if inc > 0 else "0.0%"
            
            self.table.add_row([
                period,
                format_currency(inc, bc),
                format_currency(exp, bc),
                format_currency(net, bc),
                m_margin
            ])

    def _export_csv(self):
        try:
            home = os.path.expanduser("~")
            docs_dir = os.path.join(home, "Documents")
            if not os.path.exists(docs_dir):
                docs_dir = home
            
            filename = f"cash_flow_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            filepath = os.path.join(docs_dir, filename)

            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Period", "Income", "Expenses", "Net Flow", "Margin"])
                
                # Fetch data directly from the DataTable's stored rows
                for row_widgets in self.table.rows:
                    row_data = [w.cget("text") if hasattr(w, "cget") else "" for w in row_widgets]
                    if row_data and row_data[0] != "Period":
                        writer.writerow(row_data)
                            
            Toast(self.winfo_toplevel(), f"Exported to Documents/{filename}", type="success")
        except Exception as e:
            Toast(self.winfo_toplevel(), f"Export failed: {e}", type="error")
