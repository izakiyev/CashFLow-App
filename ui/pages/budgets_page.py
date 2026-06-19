import customtkinter as ctk
from ui.theme import THEME, FONTS
from services.budget_service import get_budgets, set_budget, get_budget_summary
from datetime import datetime
from ui.components.toast import Toast
from ui.modals.edit_budget import EditBudgetModal
from ui.utils.thread_worker import ThreadWorker
from ui.components.empty_state import EmptyState
from ui.components.loading_state import LoadingState

class BudgetsPage(ctk.CTkFrame):
    def __init__(self, master, company_id, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.company_id = company_id
        
        now = datetime.now()
        self.current_month = now.month
        self.current_year = now.year
        self.period_type = "monthly"
        
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=30, pady=(30, 20))
        
        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(side="left")
        
        ctk.CTkLabel(title_frame, text="Budgets", font=FONTS["title"], 
                     text_color=THEME["text_primary"]).pack(anchor="w")
        ctk.CTkLabel(title_frame, text="Track your spending limits", 
                     font=FONTS["body"], text_color=THEME["text_tertiary"]).pack(anchor="w")

        # Period Selector
        period_frame = ctk.CTkFrame(header, fg_color=THEME["bg_secondary"], corner_radius=8)
        period_frame.pack(side="right", padx=10)
        
        self.period_seg_var = ctk.StringVar(value="Monthly")
        self.period_seg = ctk.CTkSegmentedButton(period_frame, variable=self.period_seg_var, 
                                                 values=["Monthly", "Yearly"],
                                                 command=self._on_period_type_change)
        self.period_seg.pack(side="left", padx=10, pady=5)
        
        months = ["January", "February", "March", "April", "May", "June", 
                  "July", "August", "September", "October", "November", "December"]
        self.month_var = ctk.StringVar(value=months[self.current_month - 1])
        self.month_dropdown = ctk.CTkOptionMenu(period_frame, variable=self.month_var, values=months,
                                                width=120, command=self._on_period_change)
        self.month_dropdown.pack(side="left", padx=5, pady=5)
        
        years = [str(y) for y in range(2023, 2030)]
        self.year_var = ctk.StringVar(value=str(self.current_year))
        self.year_dropdown = ctk.CTkOptionMenu(period_frame, variable=self.year_var, values=years,
                                               width=80, command=self._on_period_change)
        self.year_dropdown.pack(side="left", padx=(0, 5), pady=5)

        # Summary Row
        self.summary_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.summary_frame.pack(fill="x", padx=30, pady=(0, 20))
        
        # Budget List wrapper
        self.list_wrapper = ctk.CTkFrame(self, fg_color="transparent")
        self.list_wrapper.pack(fill="both", expand=True, padx=20, pady=0)
        
        # Loading State component created dynamically when needed


        self.scroll = ctk.CTkScrollableFrame(self.list_wrapper, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True)

    def refresh(self):
        if not self.company_id: return
        try:
            if not self.winfo_exists(): return
        except Exception: return

        # 1. Update Period Variables
        months = ["January", "February", "March", "April", "May", "June", 
                  "July", "August", "September", "October", "November", "December"]
        self.current_month = months.index(self.month_var.get()) + 1
        self.current_year = int(self.year_var.get())
        self.period_type = self.period_seg_var.get().lower()

        # Show loading states
        for widget in self.summary_frame.winfo_children(): widget.destroy()
        for widget in self.scroll.winfo_children(): widget.destroy()
        
        self._add_summary_card(self.summary_frame, "Total Budget", "...", THEME["text_tertiary"])
        self._add_summary_card(self.summary_frame, "Total Spent", "...", THEME["text_tertiary"])
        self._add_summary_card(self.summary_frame, "Remaining", "...", THEME["text_tertiary"])
        
        self.scroll.pack_forget()
        if hasattr(self, '_loading_state'):
            self._loading_state.destroy()
        self._loading_state = LoadingState(self.list_wrapper, text="Loading budgets...")
        self._loading_state.pack(pady=40)

        ThreadWorker(self, self._fetch_data, on_success=self._update_ui)

    def _fetch_data(self):
        summary = get_budget_summary(self.company_id, self.current_month, self.current_year, self.period_type)
        budgets = get_budgets(self.company_id, self.current_month, self.current_year, self.period_type)
        return {"summary": summary, "budgets": budgets}

    def _update_ui(self, data):
        try:
            if not self.winfo_exists(): return
        except Exception: return

        if hasattr(self, '_loading_state'):
            self._loading_state.destroy()
        self.scroll.pack(fill="both", expand=True)

        for widget in self.summary_frame.winfo_children(): widget.destroy()
        for widget in self.scroll.winfo_children(): widget.destroy()

        summary = data["summary"]
        self._add_summary_card(self.summary_frame, "Total Budget", f"{summary['total_budgeted']:,.2f}", THEME["blue"])
        self._add_summary_card(self.summary_frame, "Total Spent", f"{summary['total_actual']:,.2f}", THEME["red"] if summary['status'] == "over_budget" else THEME["text_primary"])
        self._add_summary_card(self.summary_frame, "Remaining", f"{summary['remaining']:,.2f}", THEME["green"])

        budgets = data["budgets"]

        # Only show rows that are meaningful: have a budget set OR have actual spending
        visible = [b for b in budgets if b['budgeted_amount'] > 0 or b['actual_amount'] > 0]

        if not visible:
            EmptyState(self.scroll, icon="📊",
                       title="No activity this period",
                       subtitle="No expenses or budgets found for the selected period. Set a budget or add transactions to get started.").pack(fill="both", expand=True, pady=40)
            return

        # Group by parent, only rendering parents that are themselves visible
        # or that have visible children
        children = [b for b in visible if b['parent_id'] is not None]
        child_parent_ids = {c['parent_id'] for c in children}

        parents = [b for b in visible if b['parent_id'] is None]
        # Also include parents that have visible children even if they themselves have 0/0
        all_parent_ids = {p['category_id'] for p in parents}
        for b in budgets:
            if b['parent_id'] is None and b['category_id'] in child_parent_ids and b['category_id'] not in all_parent_ids:
                parents.append(b)
                all_parent_ids.add(b['category_id'])

        # Sort parents by actual spending descending for better UX
        parents.sort(key=lambda x: x['actual_amount'], reverse=True)

        for p in parents:
            self._add_budget_item(self.scroll, p)
            p_children = [c for c in children if c['parent_id'] == p['category_id']]
            p_children.sort(key=lambda x: x['actual_amount'], reverse=True)
            for c in p_children:
                self._add_budget_item(self.scroll, c, is_sub=True)

    def _add_summary_card(self, parent, label, value, color):
        card = ctk.CTkFrame(parent, fg_color=THEME["bg_secondary"], corner_radius=12, height=100)
        card.pack(side="left", fill="both", expand=True, padx=10)
        card.pack_propagate(False)
        
        ctk.CTkLabel(card, text=label, font=FONTS["small"], text_color=THEME["text_tertiary"]).pack(pady=(15, 0))
        ctk.CTkLabel(card, text=value, font=("Inter", 24, "bold"), text_color=color).pack()

    def _add_budget_item(self, parent, data, is_sub=False):
        row = ctk.CTkFrame(parent, fg_color=THEME["bg_primary"] if not is_sub else "transparent", 
                           corner_radius=10, border_width=1 if not is_sub else 0, border_color=THEME["border"])
        row.pack(fill="x", padx=10, pady=5)
        
        content = ctk.CTkFrame(row, fg_color="transparent")
        content.pack(fill="x", padx=20, pady=15)
        
        # Left: Info
        info = ctk.CTkFrame(content, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True)
        
        if is_sub:
            ctk.CTkLabel(info, text="└─", font=FONTS["body"], text_color=THEME["text_tertiary"]).pack(side="left", padx=(0, 5))

        # Color dot
        ctk.CTkFrame(info, width=12, height=12, corner_radius=6, 
                     fg_color=data['category_color']).pack(side="left", padx=(0, 10))
        
        ctk.CTkLabel(info, text=data['category_name'], font=FONTS["heading"] if not is_sub else FONTS["body"], 
                     text_color=THEME["text_primary"]).pack(side="left")

        # Right: Budget controls
        controls = ctk.CTkFrame(content, fg_color="transparent")
        controls.pack(side="right")
        
        budgeted = data['budgeted_amount']
        actual = data['actual_amount']
        has_budget = budgeted > 0
        percent = (actual / budgeted) if has_budget else (1.0 if actual > 0 else 0)
        
        # Progress Bar
        bar_frame = ctk.CTkFrame(controls, fg_color="transparent")
        bar_frame.pack(side="left", padx=20)
        
        if not has_budget and actual > 0:
            # Unbudgeted spending — show solid red bar as a warning
            bar_color = THEME["red"]
        else:
            bar_color = THEME["red"] if percent > 1 else (THEME["amber"] if percent > 0.8 else THEME["green"])
        
        progress = ctk.CTkProgressBar(bar_frame, width=200, height=8, fg_color=THEME["bg_tertiary"], progress_color=bar_color)
        progress.set(min(1.0, percent))
        progress.pack()
        
        if has_budget:
            label_text = f"{actual:,.0f} / {budgeted:,.0f} {data['currency']}"
            label_color = THEME["red"] if percent > 1 else THEME["text_tertiary"]
        else:
            label_text = f"{actual:,.0f} {data['currency']}  —  No budget set"
            label_color = THEME["red"]
        
        ctk.CTkLabel(bar_frame, text=label_text,
                     font=FONTS["small"], text_color=label_color).pack()

        # Edit Button
        ctk.CTkButton(controls, text="Set Budget", width=80, height=28, font=FONTS["small"],
                      fg_color=THEME["bg_secondary"], hover_color=THEME["border"],
                      command=lambda: self._edit_budget(data)).pack(side="right")

    def _on_period_type_change(self, value):
        if value == "Yearly":
            self.month_dropdown.pack_forget()
        else:
            self.month_dropdown.pack(side="left", padx=5, pady=5, before=self.year_dropdown)
        self.refresh()

    def _on_period_change(self, _):
        self.refresh()

    def _edit_budget(self, data):
        EditBudgetModal(
            self.winfo_toplevel(),
            company_id=self.company_id,
            category_id=data['category_id'],
            category_name=data['category_name'],
            current_amount=data['budgeted_amount'],
            current_period_type=self.period_type,
            current_month=self.current_month,
            current_year=self.current_year,
            on_success=self.refresh
        )
