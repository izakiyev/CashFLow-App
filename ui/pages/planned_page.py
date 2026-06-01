import customtkinter as ctk
from datetime import datetime, timedelta
from ui.theme import THEME, FONTS
from ui.components.topbar import Topbar
from ui.components.kpi_card import KPICard
from ui.components.data_table import DataTable
from ui.components.search_bar import SearchBar
from services.planned_service import get_planned_payments, delete_planned_payment, confirm_planned_payment
from services.currency_service import format_currency
from ui.modals.add_planned import AddPlannedModal
from ui.modals.confirm_dialog import ConfirmDialog
from ui.components.toast import Toast
from ui.utils.thread_worker import ThreadWorker
import csv

class PlannedPage(ctk.CTkFrame):
    def __init__(self, master, company_id, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.company_id = company_id
        
        # State
        self.filters = {
            "search": "",
            "type": "All",
            "status": "All"
        }

        self.topbar = Topbar(self, title="Planned Payments")
        self.topbar.pack(fill="x")
        self.topbar.add_action("Export CSV", self._export_csv)
        self.topbar.add_action("+ New Planned Payment", self._add_planned, primary=True)

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=20, pady=10)

        self._build_kpis()
        self._build_filter_bar()
        self._build_table()
        self.refresh()

    def _add_planned(self):
        AddPlannedModal(self.winfo_toplevel(), self.company_id, self.refresh)

    def _build_kpis(self):
        self.kpi_frame = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.kpi_frame.pack(fill="x", pady=(0, 20))
        for i in range(4): self.kpi_frame.grid_columnconfigure(i, weight=1)
        
        self.card_inc = KPICard(self.kpi_frame, "Pending Receivables", "₼0.00")
        self.card_inc.grid(row=0, column=0, sticky="ew", padx=5)
        
        self.card_exp = KPICard(self.kpi_frame, "Pending Payables", "₼0.00")
        self.card_exp.grid(row=0, column=1, sticky="ew", padx=5)
        
        self.card_overdue = KPICard(self.kpi_frame, "Overdue Payments", "0")
        self.card_overdue.grid(row=0, column=2, sticky="ew", padx=5)
        
        self.card_upcoming = KPICard(self.kpi_frame, "Upcoming (7 Days)", "0")
        self.card_upcoming.grid(row=0, column=3, sticky="ew", padx=5)

    def _build_filter_bar(self):
        bar = ctk.CTkFrame(self.scroll, fg_color=THEME["bg_secondary"], corner_radius=10,
                           border_width=1, border_color=THEME["border"])
        bar.pack(fill="x", pady=(0, 10))

        self.search_bar = SearchBar(bar, self._on_search)
        self.search_bar.pack(side="left", padx=10, pady=8)

        self.type_seg = ctk.CTkSegmentedButton(
            bar, values=["All", "Income", "Expense", "Transfer"],
            command=self._on_type_filter, font=FONTS["body"]
        )
        self.type_seg.set("All")
        self.type_seg.pack(side="left", padx=10)

        self.status_seg = ctk.CTkSegmentedButton(
            bar, values=["All", "Pending", "Overdue", "Paid"],
            command=self._on_status_filter, font=FONTS["body"]
        )
        self.status_seg.set("All")
        self.status_seg.pack(side="left", padx=10)

        self.count_lbl = ctk.CTkLabel(bar, text="", font=FONTS["small"], text_color=THEME["text_tertiary"])
        self.count_lbl.pack(side="right", padx=16)

    def _build_table(self):
        container = ctk.CTkFrame(self.scroll, fg_color=THEME["bg_secondary"], corner_radius=8,
                                 border_width=1, border_color=THEME["border"])
        container.pack(fill="both", expand=True, pady=10)
        self.table = DataTable(container, ["Due Date", "Category", "Description", "Amount", "Currency", "Status", "Actions"])
        self.table.pack(fill="both", expand=True, padx=10, pady=10)

    # ─── Filter Actions ───────────────────────────────────────────────────────
    def _on_search(self, query):
        if hasattr(self, '_search_after_id') and self._search_after_id:
            try:
                self.after_cancel(self._search_after_id)
            except Exception:
                pass
        self.filters["search"] = query.lower()
        self._search_after_id = self.after(400, self.refresh)

    def _on_type_filter(self, val):
        self.filters["type"] = val
        self.refresh()

    def _on_status_filter(self, val):
        self.filters["status"] = val
        self.refresh()

    def _export_csv(self):
        if not hasattr(self, "_last_data") or not self._last_data:
            Toast(self.winfo_toplevel(), "No data to export", type="info")
            return

        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV files", "*.csv")],
            initialfile=f"planned_payments_{datetime.now().strftime('%Y%m%d')}.csv"
        )
        if not path:
            return

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "due_date", "type", "description", "category", "amount", "currency", "status", "recurring"
            ])
            writer.writeheader()
            for p in self._last_data:
                writer.writerow({
                    "due_date": p.due_date.strftime("%Y-%m-%d"),
                    "type": p.type,
                    "description": p.description,
                    "category": getattr(p, 'category_name', None) or 'Uncategorized',
                    "amount": float(p.amount),
                    "currency": p.currency,
                    "status": p.status,
                    "recurring": getattr(p, 'recurring', 'none')
                })
        Toast(self.winfo_toplevel(), f"Exported {len(self._last_data)} items", type="success")

    # ─── Async Load ───────────────────────────────────────────────────────────
    def refresh(self):
        if not self.company_id: return
        try:
            if not self.winfo_exists(): return
        except Exception: return
        
        self.table.clear_rows()
        self.count_lbl.configure(text="Loading...")
        
        ThreadWorker(self, self._fetch_data, on_success=self._update_ui)

    def _fetch_data(self):
        planned = get_planned_payments(self.company_id)
        
        from database.session import get_session
        from database.models import Company
        with get_session() as session:
            comp = session.get(Company, self.company_id)
            bc = comp.currency if comp else "AZN"
            
        return {"planned": planned, "base_currency": bc}

    def _update_ui(self, data):
        try:
            if not self.winfo_exists(): return
        except Exception: return

        planned = data["planned"]
        bc = data["base_currency"]
        
        from services.currency_service import convert_to_base
        
        now = datetime.now()
        seven_days = now + timedelta(days=7)
        
        inc = 0.0
        exp = 0.0
        overdue_count = 0
        upcoming_count = 0
        
        filtered_planned = []
        
        for p in planned:
            # 1. KPI Calculations (unfiltered, based on all pending data)
            is_overdue = p.due_date < now and p.status != 'paid'
            if p.status != 'paid':
                amt_base = float(convert_to_base(p.amount, p.currency, bc))
                if p.type == 'income': inc += amt_base
                elif p.type == 'expense': exp += amt_base
                
                if is_overdue:
                    overdue_count += 1
                elif now <= p.due_date <= seven_days:
                    upcoming_count += 1

            # 2. Apply UI Filters
            cat_name = getattr(p, 'category_name', None) or "Uncategorized"
            desc = p.description or ""
            
            if self.filters["search"]:
                q = self.filters["search"]
                if q not in cat_name.lower() and q not in desc.lower():
                    continue
                    
            if self.filters["type"] != "All" and self.filters["type"].lower() != p.type:
                continue
                
            status_filter = self.filters["status"].lower()
            if status_filter != "all":
                if status_filter == "overdue" and not is_overdue:
                    continue
                elif status_filter == "pending" and (p.status != "pending" or is_overdue):
                    continue
                elif status_filter == "paid" and p.status != "paid":
                    continue
                    
            filtered_planned.append(p)
            
            # 3. Add to Table
            due_date_str = p.due_date.strftime("%Y-%m-%d")
            
            def make_badge(master, status=p.status, overdue=is_overdue):
                bg = THEME["blue_light"]
                fg = THEME["blue"]
                if status == 'paid':
                    bg = THEME["green_light"]
                    fg = THEME["green_dark"]
                elif overdue:
                    bg = THEME["red_light"]
                    fg = THEME["red"]
                elif status == 'pending':
                    bg = THEME["amber_light"]
                    fg = THEME["amber"]
                
                f = ctk.CTkFrame(master, fg_color=bg, corner_radius=6)
                ctk.CTkLabel(f, text=status.upper() if not overdue else "OVERDUE", 
                             font=FONTS["small"], text_color=fg, height=22).pack(padx=10, pady=2)
                return f

            def make_actions(master, p_obj=p):
                f = ctk.CTkFrame(master, fg_color="transparent")
                if p_obj.status == "pending":
                    btn_confirm = ctk.CTkButton(f, text="Confirm", width=80, height=24, 
                                             fg_color=THEME["amber"], hover_color=THEME["amber_dark"],
                                             font=FONTS["small"], command=lambda: self._handle_confirm(p_obj))
                    btn_confirm.pack(side="left", padx=(0, 5))
                    
                btn_del = ctk.CTkButton(f, text="🗑 Delete", width=60, height=24, 
                                        fg_color=THEME["red"], hover_color="#a02020",
                                        font=FONTS["small"], command=lambda: self._handle_delete(p_obj))
                btn_del.pack(side="left")
                return f
                
            self.table.add_row(
                [due_date_str, cat_name, desc, format_currency(p.amount, p.currency), p.currency, make_badge, make_actions],
                color=THEME["red"] if is_overdue else THEME["text_primary"]
            )

        self._last_data = filtered_planned
        self.count_lbl.configure(text=f"{len(filtered_planned)} items found")

        # Update KPIs
        self.card_inc.update_data(format_currency(inc, bc))
        self.card_exp.update_data(format_currency(exp, bc))
        self.card_overdue.update_data(str(overdue_count))
        self.card_upcoming.update_data(str(upcoming_count))

    def _handle_confirm(self, p):
        def do_confirm():
            if confirm_planned_payment(p.id):
                Toast(self.master, "Payment confirmed & moved to Ledger", type="success")
                self.refresh()
        ConfirmDialog(self.winfo_toplevel(), title="Confirm Payment",
                      message="This will move the payment to the main ledger as 'Confirmed'. Balance will not be updated until marked as 'Paid' there. Proceed?", 
                      on_confirm=do_confirm)

    def _handle_delete(self, p):
        def do_delete():
            if delete_planned_payment(p.id):
                Toast(self.master, "Planned payment deleted", type="success")
                self.refresh()
        ConfirmDialog(self.winfo_toplevel(), title="Delete Planned Payment",
                      message="Are you sure you want to delete this planned payment?", 
                      on_confirm=do_delete)
