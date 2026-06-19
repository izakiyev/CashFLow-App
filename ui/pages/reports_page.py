import os
import customtkinter as ctk
from datetime import datetime
from tkinter import filedialog
from ui.theme import THEME, FONTS
from ui.components.topbar import Topbar
from ui.components.data_table import DataTable
from ui.components.chart_frame import ChartFrame
from ui.components.toast import Toast
from ui.utils.thread_worker import ThreadWorker
from services.report_service import (
    get_pl_statement, get_balance_summary,
    get_vat_report, get_fx_gain_loss, get_cash_flow_forecast
)
from services.currency_service import format_currency
from services.export_service import export_pdf, export_excel


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _kpi_card(master, col, title, icon, color, light):
    card = ctk.CTkFrame(master, fg_color=THEME["bg_secondary"], corner_radius=12,
                        border_width=1, border_color=THEME["border"], height=88)
    card.grid(row=0, column=col, sticky="ew", padx=6)
    card.pack_propagate(False)
    ib = ctk.CTkFrame(card, width=42, height=42, corner_radius=10, fg_color=light)
    ib.pack(side="left", padx=(14, 10), pady=23)
    ib.pack_propagate(False)
    ctk.CTkLabel(ib, text=icon, font=("Inter", 18)).place(relx=0.5, rely=0.5, anchor="center")
    tf = ctk.CTkFrame(card, fg_color="transparent")
    tf.pack(side="left", fill="both", expand=True, pady=(14, 0))
    ctk.CTkLabel(tf, text=title, font=("Inter", 10, "bold"),
                 text_color=THEME["text_tertiary"]).pack(anchor="w")
    val = ctk.CTkLabel(tf, text="—", font=("Inter", 20, "bold"), text_color=color)
    val.pack(anchor="w")
    return val, card


# ─── Main Page ────────────────────────────────────────────────────────────────

class ReportsPage(ctk.CTkFrame):
    PRESETS = {
        "This Month":    lambda: ReportsPage._this_month(),
        "Last Month":    lambda: ReportsPage._last_month(),
        "Last 3 Months": lambda: ReportsPage._last_n_months(3),
        "This Year":     lambda: ReportsPage._this_year(),
        "All Time":      lambda: (None, None),
    }

    @staticmethod
    def _this_month():
        n = datetime.now(); return datetime(n.year, n.month, 1), n

    @staticmethod
    def _last_month():
        n = datetime.now()
        first = datetime(n.year, n.month, 1)
        from datetime import timedelta
        end = (first - timedelta(days=1)).replace(hour=23, minute=59, second=59)
        return datetime(end.year, end.month, 1), end

    @staticmethod
    def _last_n_months(n):
        now = datetime.now()
        m = now.month - n; y = now.year
        while m <= 0: m += 12; y -= 1
        return datetime(y, m, 1), now

    @staticmethod
    def _this_year():
        n = datetime.now(); return datetime(n.year, 1, 1), n

    TABS = [
        ("pl",       "P&L Statement"),
        ("bal",      "Balance"),
        ("vat",      "VAT Report"),
        ("fx",       "FX Gain/Loss"),
        ("forecast", "Cash Forecast"),
    ]

    def __init__(self, master, company_id, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.company_id = company_id
        self.current_tab = "pl"
        self._date_from, self._date_to = self._this_month()
        self._export_title = ""
        self._export_headers = []
        self._export_data = []
        self._tab_btns = {}
        self._build()
        self._set_tab("pl")

    def _build(self):
        # Topbar
        self.topbar = Topbar(self, title="Financial Reports")
        self.topbar.pack(fill="x")
        self.topbar.add_action("⬇ Export PDF",   self._export_pdf)
        self.topbar.add_action("⬇ Export Excel", self._export_excel)

        # Tab bar
        tab_bar = ctk.CTkFrame(self, fg_color=THEME["bg_secondary"],
                               corner_radius=0, border_width=0, height=48)
        tab_bar.pack(fill="x")
        tab_bar.pack_propagate(False)

        inner = ctk.CTkFrame(tab_bar, fg_color="transparent")
        inner.pack(side="left", padx=20, pady=8)

        for key, label in self.TABS:
            btn = ctk.CTkButton(
                inner, text=label, height=32, width=130,
                font=FONTS["small"], corner_radius=8,
                fg_color=THEME["bg_tertiary"], text_color=THEME["text_secondary"],
                hover_color=THEME["border"],
                command=lambda k=key: self._set_tab(k)
            )
            btn.pack(side="left", padx=3)
            self._tab_btns[key] = btn

        # Date filter bar
        self._date_bar = ctk.CTkFrame(self, fg_color=THEME["bg_secondary"],
                                      corner_radius=0, height=40)
        self._date_bar.pack(fill="x")
        self._date_bar.pack_propagate(False)
        self._build_date_filter(self._date_bar)

        # KPI row (4 cards)
        self._kpi_row = ctk.CTkFrame(self, fg_color="transparent")
        self._kpi_row.pack(fill="x", padx=20, pady=12)
        for i in range(4):
            self._kpi_row.grid_columnconfigure(i, weight=1)

        self._kv = {}
        self._kv[0], _ = _kpi_card(self._kpi_row, 0, "KPI 1", "📊", THEME["blue"],  THEME["blue_light"])
        self._kv[1], _ = _kpi_card(self._kpi_row, 1, "KPI 2", "💰", THEME["green"], THEME["green_light"])
        self._kv[2], _ = _kpi_card(self._kpi_row, 2, "KPI 3", "📉", THEME["red"],   THEME["red_light"])
        self._kv[3], _ = _kpi_card(self._kpi_row, 3, "KPI 4", "⚖",  THEME["amber"], THEME["amber_light"])

        # Content (table + chart)
        self._content = ctk.CTkFrame(self, fg_color="transparent")
        self._content.pack(fill="both", expand=True, padx=20, pady=(0, 16))
        self._content.grid_columnconfigure(0, weight=3)
        self._content.grid_columnconfigure(1, weight=2)
        self._content.grid_rowconfigure(0, weight=1)

        # Table panel
        self._tpanel = ctk.CTkFrame(self._content, fg_color=THEME["bg_secondary"],
                                    corner_radius=12, border_width=1, border_color=THEME["border"])
        self._tpanel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        hdr = ctk.CTkFrame(self._tpanel, fg_color="transparent")
        hdr.pack(fill="x", padx=16, pady=(14, 4))
        self._table_title = ctk.CTkLabel(hdr, text="Details", font=FONTS["heading"],
                                         text_color=THEME["text_primary"])
        self._table_title.pack(side="left")
        self._row_count = ctk.CTkLabel(hdr, text="", font=FONTS["small"],
                                       text_color=THEME["text_tertiary"])
        self._row_count.pack(side="right")

        ctk.CTkFrame(self._tpanel, height=1, fg_color=THEME["border"]).pack(fill="x")
        self._table_container = ctk.CTkFrame(self._tpanel, fg_color="transparent")
        self._table_container.pack(fill="both", expand=True, padx=12, pady=12)

        # Chart panel
        self._cpanel = ctk.CTkFrame(self._content, fg_color=THEME["bg_secondary"],
                                    corner_radius=12, border_width=1, border_color=THEME["border"])
        self._cpanel.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        chdr = ctk.CTkFrame(self._cpanel, fg_color="transparent")
        chdr.pack(fill="x", padx=16, pady=(14, 4))
        self._chart_title = ctk.CTkLabel(chdr, text="Visual Breakdown", font=FONTS["heading"],
                                         text_color=THEME["text_primary"])
        self._chart_title.pack(side="left")
        ctk.CTkFrame(self._cpanel, height=1, fg_color=THEME["border"]).pack(fill="x")

        self._chart_frame = ChartFrame(self._cpanel)
        self._chart_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # ── Date Filter ────────────────────────────────────────────────────────────

    def _build_date_filter(self, parent):
        inner = ctk.CTkFrame(parent, fg_color="transparent")
        inner.pack(side="left", padx=16, pady=4)
        ctk.CTkLabel(inner, text="Period:", font=FONTS["small"],
                     text_color=THEME["text_tertiary"]).pack(side="left", padx=(0, 8))
        self._filter_btns = {}
        for label in self.PRESETS:
            active = (label == "This Month")
            b = ctk.CTkButton(
                inner, text=label, height=26, font=FONTS["small"],
                fg_color=THEME["blue"] if active else THEME["bg_tertiary"],
                hover_color=THEME["blue"] if active else THEME["border"],
                text_color="white" if active else THEME["text_primary"],
                command=lambda l=label: self._apply_preset(l)
            )
            b.pack(side="left", padx=2)
            self._filter_btns[label] = b

        ctk.CTkButton(inner, text="Custom", height=26, font=FONTS["small"],
                      fg_color=THEME["bg_tertiary"], hover_color=THEME["border"],
                      text_color=THEME["text_primary"],
                      command=self._open_custom).pack(side="left", padx=2)
        self._filter_btns["Custom"] = None

        self._range_lbl = ctk.CTkLabel(parent, text="", font=FONTS["small"],
                                       text_color=THEME["text_tertiary"])
        self._range_lbl.pack(side="right", padx=16)
        self._update_range_lbl()

    def _apply_preset(self, label):
        if label != "Custom":
            self._date_from, self._date_to = self.PRESETS[label]()
        for lbl, btn in self._filter_btns.items():
            if btn is None: continue
            active = (lbl == label)
            btn.configure(
                fg_color=THEME["blue"] if active else THEME["bg_tertiary"],
                text_color="white" if active else THEME["text_primary"],
                hover_color=THEME["blue"] if active else THEME["border"],
            )
        self._update_range_lbl()
        self.refresh()

    def _open_custom(self):
        from ui.modals.custom_date import CustomDateModal
        def cb(d_from, d_to):
            self._date_from = d_from; self._date_to = d_to
            self._apply_preset("Custom")
        CustomDateModal(self.winfo_toplevel(), on_success=cb)

    def _update_range_lbl(self):
        if self._date_from and self._date_to:
            self._range_lbl.configure(
                text=f"{self._date_from.strftime('%d %b %Y')}  →  {self._date_to.strftime('%d %b %Y')}")
        else:
            self._range_lbl.configure(text="All Time")

    # ── Tab switching ──────────────────────────────────────────────────────────

    def _set_tab(self, key):
        self.current_tab = key
        for k, btn in self._tab_btns.items():
            active = (k == key)
            btn.configure(
                fg_color=THEME["blue"] if active else THEME["bg_tertiary"],
                text_color="white" if active else THEME["text_secondary"],
            )
        # Hide date bar for Balance tab (it's always real-time)
        if key == "bal":
            self._date_bar.pack_forget()
        else:
            self._date_bar.pack(fill="x", after=list(self._tab_btns.values())[0].master.master)
        self.refresh()

    # ── Async refresh ──────────────────────────────────────────────────────────

    def refresh(self):
        if not self.company_id: return
        try:
            if not self.winfo_exists(): return
        except Exception: return

        for w in self._table_container.winfo_children(): w.destroy()
        ctk.CTkLabel(self._table_container, text="Loading…",
                     font=FONTS["body"], text_color=THEME["text_tertiary"]).pack(pady=40)
        for lbl in self._kv.values(): lbl.configure(text="…")

        self._chart_frame.destroy()
        self._chart_frame = ChartFrame(self._cpanel)
        self._chart_frame.pack(fill="both", expand=True, padx=10, pady=10)

        ThreadWorker(self, self._fetch, on_success=self._render)

    def _fetch(self):
        tab = self.current_tab
        if tab == "pl":
            return {"tab": tab, "data": get_pl_statement(self.company_id, self._date_from, self._date_to)}
        if tab == "bal":
            return {"tab": tab, "data": get_balance_summary(self.company_id)}
        if tab == "vat":
            return {"tab": tab, "data": get_vat_report(self.company_id, self._date_from, self._date_to)}
        if tab == "fx":
            return {"tab": tab, "data": get_fx_gain_loss(self.company_id, self._date_from, self._date_to)}
        if tab == "forecast":
            dates, balances = get_cash_flow_forecast(self.company_id, days=90)
            return {"tab": tab, "data": {"dates": dates, "balances": balances}}

    def _render(self, payload):
        try:
            if not self.winfo_exists(): return
        except Exception: return
        for w in self._table_container.winfo_children(): w.destroy()
        tab = payload["tab"]; data = payload["data"]
        dispatch = {
            "pl":       self._render_pl,
            "bal":      self._render_bal,
            "vat":      self._render_vat,
            "fx":       self._render_fx,
            "forecast": self._render_forecast,
        }
        dispatch[tab](data)

    # ── Renderers ──────────────────────────────────────────────────────────────

    def _set_kpis(self, values):
        """values: list of (text, color) tuples, up to 4."""
        for i, (lbl, clr) in enumerate(values):
            self._kv[i].configure(text=lbl, text_color=clr)
        for i in range(len(values), 4):
            self._kv[i].configure(text="—", text_color=THEME["text_tertiary"])

    def _render_pl(self, pl):
        bc = pl.get("base_currency", "AZN")
        net = pl["net_profit"]

        self._table_title.configure(text="Profit & Loss Statement")
        self._chart_title.configure(text="Expense Breakdown")
        self._set_kpis([
            (format_currency(pl["total_income"],   bc), THEME["green"]),
            (format_currency(pl["total_expenses"], bc), THEME["red"]),
            (format_currency(net, bc), THEME["green"] if net >= 0 else THEME["red"]),
            (f"{round(net / pl['total_income'] * 100, 1)}%" if pl["total_income"] else "—",
             THEME["green"] if net >= 0 else THEME["red"]),
        ])

        # Update KPI card titles
        titles = ["TOTAL INCOME", "TOTAL EXPENSES", "NET PROFIT", "MARGIN"]
        for i, t in enumerate(titles):
            card_lbl = self._kv[i].master
            for child in card_lbl.winfo_children():
                if hasattr(child, '_text') or isinstance(child, ctk.CTkLabel):
                    try:
                        if child.cget("font") == ("Inter", 10, "bold"):
                            child.configure(text=t)
                            break
                    except Exception:
                        pass

        # Table
        rows = []
        t = DataTable(self._table_container, ["Category", "Amount", "% Share"])
        t.pack(fill="both", expand=True)

        if pl["income"]:
            t.add_row(["── INCOME ──", "", ""], color=THEME["green"])
            for item in sorted(pl["income"], key=lambda x: x["amount"], reverse=True):
                pct = f"{item['amount'] / pl['total_income'] * 100:.1f}%" if pl["total_income"] else ""
                t.add_row([item["name"], format_currency(item["amount"], bc), pct])
                rows.append({"Section": "Income", "Category": item["name"],
                             "Amount": format_currency(item["amount"], bc)})
            t.add_row(["Total Income", format_currency(pl["total_income"], bc), "100%"],
                      color=THEME["green"])

        if pl["expenses"]:
            t.add_row(["── EXPENSES ──", "", ""], color=THEME["red"])
            for item in sorted(pl["expenses"], key=lambda x: x["amount"], reverse=True):
                pct = f"{item['amount'] / pl['total_expenses'] * 100:.1f}%" if pl["total_expenses"] else ""
                t.add_row([item["name"], format_currency(item["amount"], bc), pct])
                rows.append({"Section": "Expense", "Category": item["name"],
                             "Amount": format_currency(item["amount"], bc)})
            t.add_row(["Total Expenses", format_currency(pl["total_expenses"], bc), "100%"],
                      color=THEME["red"])

        t.add_row(["NET PROFIT / LOSS", format_currency(net, bc), ""],
                  color=THEME["green"] if net >= 0 else THEME["red"])

        self._export_title = "Profit & Loss Statement"
        self._export_headers = ["Section", "Category", "Amount"]
        self._export_data = rows
        self._row_count.configure(text=f"{len(rows)} items")

        chart_data = pl["expenses"] if pl["expenses"] else pl["income"]
        self._chart_frame.draw_donut_chart(chart_data)

    def _render_bal(self, bal):
        bc = bal.get("base_currency", "AZN")
        accs = bal["accounts"]
        self._table_title.configure(text="Account Balances")
        self._chart_title.configure(text="Balance Distribution")
        self._set_kpis([
            (str(len(accs)),                  THEME["blue"]),
            (format_currency(bal["total"], bc), THEME["green"]),
            ("—", THEME["text_tertiary"]),
            ("—", THEME["text_tertiary"]),
        ])

        t = DataTable(self._table_container, ["Account", "Type", "Currency", "Balance"])
        t.pack(fill="both", expand=True)
        rows = []
        for a in sorted(accs, key=lambda x: x["balance"], reverse=True):
            t.add_row([a["name"], a["type"].title(), a["currency"],
                       format_currency(a["balance"], a["currency"])])
            rows.append({"Account": a["name"], "Type": a["type"],
                         "Balance": format_currency(a["balance"], a["currency"])})
        t.add_row(["TOTAL", "", bc, format_currency(bal["total"], bc)],
                  color=THEME["blue"])

        self._export_title = "Balance Summary"
        self._export_headers = ["Account", "Type", "Balance"]
        self._export_data = rows
        self._row_count.configure(text=f"{len(accs)} accounts")

        chart_data = [{"name": a["name"], "amount": a["balance"],
                       "color": a.get("color") or THEME["blue"]} for a in accs]
        self._chart_frame.draw_donut_chart(chart_data)

    def _render_vat(self, vat):
        bc = vat.get("currency", "AZN")
        net = vat["net"]
        self._table_title.configure(text="VAT Report")
        self._chart_title.configure(text="VAT Breakdown")
        self._set_kpis([
            (format_currency(vat["collected"], bc), THEME["green"]),
            (format_currency(vat["paid"],      bc), THEME["red"]),
            (format_currency(net, bc), THEME["green"] if net >= 0 else THEME["red"]),
            ("—", THEME["text_tertiary"]),
        ])

        t = DataTable(self._table_container, ["VAT Type", "Amount"])
        t.pack(fill="both", expand=True)
        rows = [
            {"VAT Type": "VAT Collected (Sales)",  "Amount": format_currency(vat["collected"], bc)},
            {"VAT Type": "VAT Paid (Purchases)",   "Amount": format_currency(vat["paid"],      bc)},
            {"VAT Type": "Net VAT Payable",        "Amount": format_currency(net,              bc)},
        ]
        color_map = [THEME["green"], THEME["red"], THEME["blue"]]
        for row, c in zip(rows, color_map):
            t.add_row(list(row.values()), color=c)

        self._export_title = "VAT Report"
        self._export_headers = ["VAT Type", "Amount"]
        self._export_data = rows
        self._row_count.configure(text="3 lines")

        chart_data = [
            {"name": "Collected", "amount": vat["collected"], "color": THEME["green"]},
            {"name": "Paid",      "amount": vat["paid"],      "color": THEME["red"]},
        ]
        self._chart_frame.draw_donut_chart([d for d in chart_data if d["amount"] > 0])

    def _render_fx(self, fx):
        bc = fx.get("currency", "AZN")
        gl = fx["total_gain_loss"]
        self._table_title.configure(text="FX Gain / Loss")
        self._chart_title.configure(text="FX Summary")
        self._set_kpis([
            (format_currency(abs(gl), bc), THEME["green"] if gl >= 0 else THEME["red"]),
            ("Gain" if gl >= 0 else "Loss", THEME["green"] if gl >= 0 else THEME["red"]),
            ("—", THEME["text_tertiary"]),
            ("—", THEME["text_tertiary"]),
        ])

        t = DataTable(self._table_container, ["Metric", "Value"])
        t.pack(fill="both", expand=True)
        rows = [
            {"Metric": "Net FX Gain/Loss", "Value": format_currency(gl, bc)},
            {"Metric": "Direction",        "Value": "Gain ↑" if gl >= 0 else "Loss ↓"},
        ]
        colors = [THEME["green"] if gl >= 0 else THEME["red"], THEME["text_secondary"]]
        for row, c in zip(rows, colors):
            t.add_row(list(row.values()), color=c)

        note = ctk.CTkLabel(
            self._table_container,
            text="FX Gain/Loss is calculated by comparing the historical recorded base\n"
                 "amount against the current exchange rate equivalent.",
            font=FONTS["small"], text_color=THEME["text_tertiary"],
            justify="left", wraplength=420
        )
        note.pack(anchor="w", padx=4, pady=16)

        self._export_title = "FX Gain/Loss"
        self._export_headers = ["Metric", "Value"]
        self._export_data = rows
        self._row_count.configure(text="")

        # Simple bar chart for FX
        chart_data = [{"name": "FX Result", "amount": abs(gl),
                       "color": THEME["green"] if gl >= 0 else THEME["red"]}]
        self._chart_frame.draw_donut_chart(chart_data)

    def _render_forecast(self, data):
        dates = data["dates"]
        balances = data["balances"]
        self._table_title.configure(text="90-Day Cash Forecast")
        self._chart_title.configure(text="Projected Balance")

        # KPIs: start, end, min, max
        if balances:
            start_b = balances[0]
            end_b   = balances[-1]
            min_b   = min(balances)
            max_b   = max(balances)
        else:
            start_b = end_b = min_b = max_b = 0

        self._set_kpis([
            (format_currency(start_b, "AZN"), THEME["blue"]),
            (format_currency(end_b,   "AZN"), THEME["green"] if end_b >= start_b else THEME["red"]),
            (format_currency(min_b,   "AZN"), THEME["red"]),
            (format_currency(max_b,   "AZN"), THEME["green"]),
        ])

        # Table: weekly snapshots
        t = DataTable(self._table_container, ["Date", "Projected Balance"])
        t.pack(fill="both", expand=True)
        rows = []
        step = max(1, len(dates) // 20)
        for i in range(0, len(dates), step):
            d = dates[i]; b = balances[i]
            c = THEME["green"] if b >= 0 else THEME["red"]
            t.add_row([d, format_currency(b, "AZN")], color=c)
            rows.append({"Date": d, "Projected Balance": format_currency(b, "AZN")})

        self._export_title = "90-Day Cash Forecast"
        self._export_headers = ["Date", "Projected Balance"]
        self._export_data = rows
        self._row_count.configure(text=f"{len(dates)}-day projection")

        # Line chart
        try:
            self._chart_frame.draw_line_chart(
                labels=dates[::7],
                series=[{"label": "Balance", "data": balances[::7], "color": THEME["blue"]}]
            )
        except Exception:
            # Fallback if draw_line_chart not supported
            import tkinter as tk
            ctk.CTkLabel(self._cpanel, text="Chart: line charts require matplotlib",
                         font=FONTS["small"], text_color=THEME["text_tertiary"]).pack(pady=40)

    # ── Exports ────────────────────────────────────────────────────────────────

    def _get_meta(self):
        return {
            "Report": self._export_title,
            "Period": self._range_lbl.cget("text")
        }

    def _export_pdf(self):
        if not self._export_data:
            Toast(self.winfo_toplevel(), "No data to export", type="info"); return
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf", filetypes=[("PDF", "*.pdf")],
            initialfile=f"{self._export_title.replace(' ', '_')}.pdf")
        if path:
            res = export_pdf(path, self._export_title, self._export_data, self._export_headers, meta=self._get_meta())
            if res: Toast(self.winfo_toplevel(), f"PDF saved: {os.path.basename(res)}", type="success")

    def _export_excel(self):
        if not self._export_data:
            Toast(self.winfo_toplevel(), "No data to export", type="info"); return
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")],
            initialfile=f"{self._export_title.replace(' ', '_')}.xlsx")
        if path:
            res = export_excel(path, self._export_data, self._export_headers, title=self._export_title, meta=self._get_meta())
            if res: Toast(self.winfo_toplevel(), f"Excel saved: {os.path.basename(res)}", type="success")
