import os
import customtkinter as ctk
from datetime import datetime, timedelta
from tkinter import filedialog
from ui.theme import THEME, FONTS
from ui.components.topbar import Topbar
from ui.components.data_table import DataTable
from ui.components.chart_frame import ChartFrame
from services.report_service import get_pl_statement, get_balance_summary
from services.currency_service import format_currency
from services.export_service import export_pdf, export_excel
from ui.components.toast import Toast
from ui.utils.thread_worker import ThreadWorker

class KPIFrame(ctk.CTkFrame):
    def __init__(self, master, title, amount, color, currency="AZN", **kwargs):
        super().__init__(master, fg_color=THEME["bg_secondary"], corner_radius=10, 
                         border_width=1, border_color=THEME["border"], **kwargs)
        
        lbl_title = ctk.CTkLabel(self, text=title, font=FONTS["body"], text_color=THEME["text_secondary"])
        lbl_title.pack(anchor="w", padx=16, pady=(12, 0))
        
        self.lbl_amount = ctk.CTkLabel(self, text=format_currency(amount, currency), font=FONTS["title"], text_color=color)
        self.lbl_amount.pack(anchor="w", padx=16, pady=(0, 16))

    def update_val(self, amount, color, currency="AZN"):
        if isinstance(amount, (int, float)):
            text = format_currency(amount, currency)
        else:
            text = str(amount)
        self.lbl_amount.configure(text=text, text_color=color)


class ReportsPage(ctk.CTkFrame):
    PRESETS = {
        "This Month": lambda: ReportsPage._this_month(),
        "Last Month": lambda: ReportsPage._last_month(),
        "Last 3 Months": lambda: ReportsPage._last_n_months(3),
        "This Year": lambda: ReportsPage._this_year(),
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
        
        # State
        self.current_export_title = "Report"
        self.current_export_headers = []
        self.current_export_data = []
        self.current_tab = "pl"
        
        self._date_from, self._date_to = self._this_month()

        self.topbar = Topbar(self, title="Financial Reports")
        self.topbar.pack(fill="x")
        self.topbar.add_action("Export PDF", self._export_pdf)
        self.topbar.add_action("Export Excel", self._export_excel)

        # Tabs
        self.tab_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.tab_frame.pack(fill="x", padx=24, pady=10)

        self.btn_pl = ctk.CTkButton(self.tab_frame, text="P&L Statement", width=140,
                                    font=FONTS["heading"], fg_color=THEME["bg_secondary"], 
                                    text_color=THEME["text_primary"], hover_color=THEME["border"],
                                    command=lambda: self._set_tab("pl"))
        self.btn_pl.pack(side="left", padx=(0, 10))
        
        self.btn_bal = ctk.CTkButton(self.tab_frame, text="Balance Summary", width=140,
                                     font=FONTS["heading"], fg_color=THEME["bg_secondary"], 
                                     text_color=THEME["text_primary"], hover_color=THEME["border"],
                                     command=lambda: self._set_tab("bal"))
        self.btn_bal.pack(side="left")

        # Date Filter Bar (Hidden for Balance Summary)
        self.date_bar = ctk.CTkFrame(self, fg_color=THEME["bg_secondary"], corner_radius=10, border_width=1, border_color=THEME["border"])
        self.date_bar.pack(fill="x", padx=24, pady=(0, 16))
        self._build_date_filter(self.date_bar)

        # KPI Row
        self.kpi_row = ctk.CTkFrame(self, fg_color="transparent")
        self.kpi_row.pack(fill="x", padx=24, pady=(0, 16))
        self.kpi_row.grid_columnconfigure((0,1,2), weight=1)

        self.kpi1 = KPIFrame(self.kpi_row, "KPI 1", 0, THEME["text_primary"])
        self.kpi1.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        
        self.kpi2 = KPIFrame(self.kpi_row, "KPI 2", 0, THEME["text_primary"])
        self.kpi2.grid(row=0, column=1, sticky="ew", padx=5)
        
        self.kpi3 = KPIFrame(self.kpi_row, "KPI 3", 0, THEME["text_primary"])
        self.kpi3.grid(row=0, column=2, sticky="ew", padx=(5, 0))

        # Main content area
        self.content_area = ctk.CTkFrame(self, fg_color="transparent")
        self.content_area.pack(fill="both", expand=True, padx=24, pady=(0, 24))
        self.content_area.grid_columnconfigure(0, weight=3)
        self.content_area.grid_columnconfigure(1, weight=2)
        self.content_area.grid_rowconfigure(0, weight=1)

        # Table wrapper
        self.table_frame = ctk.CTkFrame(self.content_area, fg_color=THEME["bg_secondary"], 
                                        corner_radius=10, border_width=1, border_color=THEME["border"])
        self.table_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.table_label = ctk.CTkLabel(self.table_frame, text="Details", font=FONTS["heading"])
        self.table_label.pack(anchor="w", padx=16, pady=(16, 8))
        self.table_container = ctk.CTkFrame(self.table_frame, fg_color="transparent")
        self.table_container.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        # Chart wrapper
        self.chart_wrapper = ctk.CTkFrame(self.content_area, fg_color=THEME["bg_secondary"], 
                                          corner_radius=10, border_width=1, border_color=THEME["border"])
        self.chart_wrapper.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        self.chart_label = ctk.CTkLabel(self.chart_wrapper, text="Visual Breakdown", font=FONTS["heading"])
        self.chart_label.pack(anchor="w", padx=16, pady=(16, 0))
        
        # We replace the ChartFrame on each render to prevent overlapping
        self.chart_frame = ChartFrame(self.chart_wrapper)
        self.chart_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self._set_tab("pl")

    def _build_date_filter(self, parent):
        inner = ctk.CTkFrame(parent, fg_color="transparent")
        inner.pack(side="left", padx=10, pady=6)

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

        self._range_lbl = ctk.CTkLabel(parent, text="", font=FONTS["small"], text_color=THEME["text_tertiary"])
        self._range_lbl.pack(side="right", padx=16)
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

    def _set_tab(self, r_type):
        self.current_tab = r_type
        if r_type == "pl":
            self.btn_pl.configure(fg_color=THEME["blue"], text_color="white", hover_color=THEME["blue_light"])
            self.btn_bal.configure(fg_color=THEME["bg_secondary"], text_color=THEME["text_primary"], hover_color=THEME["border"])
            self.date_bar.pack(fill="x", padx=24, pady=(0, 16), after=self.tab_frame)
        else:
            self.btn_pl.configure(fg_color=THEME["bg_secondary"], text_color=THEME["text_primary"], hover_color=THEME["border"])
            self.btn_bal.configure(fg_color=THEME["blue"], text_color="white", hover_color=THEME["blue_light"])
            self.date_bar.pack_forget()
        
        self.refresh()

    def refresh(self):
        if not self.company_id: return
        try:
            if not self.winfo_exists(): return
        except Exception: return

        # UI Loading state
        for w in self.table_container.winfo_children(): w.destroy()
        
        self.chart_frame.destroy()
        self.chart_frame = ChartFrame(self.chart_wrapper)
        self.chart_frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(self.table_container, text="Loading report...", 
                     font=FONTS["body"], text_color=THEME["text_tertiary"]).pack(pady=40)
        
        self.kpi1.update_val("...", THEME["text_tertiary"], "")
        self.kpi2.update_val("...", THEME["text_tertiary"], "")
        self.kpi3.update_val("...", THEME["text_tertiary"], "")

        ThreadWorker(self, self._fetch_data, on_success=self._update_ui)

    def _fetch_data(self):
        if self.current_tab == "pl":
            return {"type": "pl", "data": get_pl_statement(self.company_id, self._date_from, self._date_to)}
        else:
            return {"type": "bal", "data": get_balance_summary(self.company_id)}

    def _update_ui(self, payload):
        try:
            if not self.winfo_exists(): return
        except Exception: return

        for w in self.table_container.winfo_children(): w.destroy()
        
        r_type = payload["type"]
        data = payload["data"]

        if r_type == "pl":
            self._render_pl(data)
        else:
            self._render_bal(data)

    def _render_pl(self, pl):
        self.table_label.configure(text="Profit & Loss Statement")
        bc = pl.get('base_currency', 'AZN')
        
        self.kpi1.update_val(pl['total_income'], THEME["green"], bc)
        self.kpi2.update_val(pl['total_expenses'], THEME["red"], bc)
        self.kpi3.update_val(pl['net_profit'], THEME["green"] if pl['net_profit'] >= 0 else THEME["red"], bc)

        self.current_export_title = f"Profit & Loss Statement ({self._range_lbl.cget('text')})"
        self.current_export_headers = ["Type", "Category", "Amount"]
        self.current_export_data = []

        table = DataTable(self.table_container, ["Category", "Amount"])
        table.pack(fill="both", expand=True)
        
        table.add_row(["INCOME", ""], color=THEME["text_tertiary"])
        for i in pl['income']: 
            table.add_row([i['name'], format_currency(i['amount'], bc)])
            self.current_export_data.append({"Type": "Income", "Category": i['name'], "Amount": format_currency(i['amount'], bc)})
            
        table.add_row(["EXPENSES", ""], color=THEME["text_tertiary"])
        for e in pl['expenses']: 
            table.add_row([e['name'], format_currency(e['amount'], bc)])
            self.current_export_data.append({"Type": "Expense", "Category": e['name'], "Amount": format_currency(e['amount'], bc)})
            
        self.current_export_data.append({"Type": "TOTAL", "Category": "Net Profit", "Amount": format_currency(pl['net_profit'], bc)})

        chart_data = pl['expenses'] if pl['expenses'] else pl['income']
        for d in chart_data:
            if not d.get("color"): d["color"] = THEME["blue"]
        
        self.chart_label.configure(text="Expense Breakdown" if pl['expenses'] else "Income Breakdown")
        self.chart_frame.draw_donut_chart(chart_data)

    def _render_bal(self, bal):
        self.table_label.configure(text="Account Balances")
        bc = bal.get('base_currency', 'AZN')
        
        self.kpi1.update_val(len(bal['accounts']), THEME["text_primary"], "")
        self.kpi2.update_val(bal['total'], THEME["blue"], bc)
        self.kpi3.update_val("—", THEME["text_tertiary"], "")

        self.current_export_title = "Balance Summary"
        self.current_export_headers = ["Account", "Type", "Balance"]
        self.current_export_data = []

        table = DataTable(self.table_container, ["Account", "Type", "Balance"])
        table.pack(fill="both", expand=True)
        
        for a in bal['accounts']:
            table.add_row([a['name'], a['type'], format_currency(a['balance'], a['currency'])])
            self.current_export_data.append({"Account": a['name'], "Type": a['type'], "Balance": format_currency(a['balance'], a['currency'])})

        self.chart_label.configure(text="Balance Distribution")
        chart_data = [{"name": a['name'], "amount": a['balance'], "color": a.get("color", THEME["blue"])} for a in bal['accounts']]
        self.chart_frame.draw_donut_chart(chart_data)

    def _export_pdf(self):
        if not self.current_export_data: return
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
            initialfile=f"{self.current_export_title.replace(' ', '_').replace('/', '-')}.pdf",
            title="Export PDF"
        )
        if path:
            res = export_pdf(path, self.current_export_title, self.current_export_data, self.current_export_headers)
            if res: Toast(self.winfo_toplevel(), f"PDF saved: {os.path.basename(res)}", type="success")

    def _export_excel(self):
        if not self.current_export_data: return
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
            initialfile=f"{self.current_export_title.replace(' ', '_').replace('/', '-')}.xlsx",
            title="Export Excel"
        )
        if path:
            res = export_excel(path, self.current_export_data, self.current_export_headers)
            if res: Toast(self.winfo_toplevel(), f"Excel saved: {os.path.basename(res)}", type="success")
