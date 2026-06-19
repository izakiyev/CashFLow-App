import customtkinter as ctk
from decimal import Decimal, InvalidOperation
from datetime import datetime
from ui.theme import THEME, FONTS
from ui.components.modal import Modal
from services.planned_service import create_planned_payment
from services.account_service import get_accounts
from services.category_service import get_categories
from services.project_service import get_projects
from ui.components.toast import Toast
from config import CURRENCIES


class AddPlannedModal(Modal):
    def __init__(self, master, company_id, on_success, **kwargs):
        super().__init__(master, title="New Planned Payment", width=500, height=700, **kwargs)
        self.company_id = company_id
        self.on_success = on_success
        self.type_var = ctk.StringVar(value="expense")
        self.accounts = get_accounts(company_id)   # list of dicts
        self.categories = []
        self.projects = get_projects(company_id, status_filter="active")
        self._build_ui()

    def _build_ui(self):
        # ── Type Selector ──────────────────────────────────────────────────
        type_frame = ctk.CTkFrame(self.content_frame, fg_color=THEME["bg_tertiary"], corner_radius=8)
        type_frame.pack(fill="x", pady=(0, 16))

        btn_cfg = dict(height=34, corner_radius=6, font=FONTS["body"], border_width=0)
        inactive = dict(fg_color="transparent", text_color=THEME["text_secondary"],
                        hover_color=THEME["border"])

        self.btn_income = ctk.CTkButton(type_frame, text="↑  Income",
                                        command=lambda: self._set_type("income"),
                                        **btn_cfg, **inactive)
        self.btn_income.pack(side="left", expand=True, padx=6, pady=6)

        self.btn_expense = ctk.CTkButton(type_frame, text="↓  Expense",
                                         command=lambda: self._set_type("expense"),
                                         **btn_cfg, **inactive)
        self.btn_expense.pack(side="left", expand=True, padx=(0, 6), pady=6)

        # ── Form ────────────────────────────────────────────────────────────
        self.form_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.form_frame.pack(fill="both", expand=True)

        # 1. Main Info Section
        self._section_header("General Details")
        self.desc_entry   = self._field("Description", "e.g. Office Rent")
        
        # Amount + Currency Row
        amt_curr_row = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        amt_curr_row.pack(fill="x", pady=5)
        ctk.CTkLabel(amt_curr_row, text="Amount", width=110, anchor="w", font=FONTS["body"]).pack(side="left")
        
        self.amount_entry = ctk.CTkEntry(amt_curr_row, placeholder_text="0.00", font=FONTS["heading"], height=38)
        self.amount_entry.pack(side="left", fill="x", expand=True)
        
        self.currency_var = ctk.StringVar(value=self.accounts[0]['currency'] if self.accounts else "AZN")
        curr_menu = ctk.CTkOptionMenu(amt_curr_row, variable=self.currency_var, values=CURRENCIES, width=80, height=38)
        curr_menu.pack(side="left", padx=(10, 0))

        self.category_var = ctk.StringVar(value="Loading...")
        self.category_dropdown = self._dropdown_field("Category", self.category_var, ["Loading..."])

        self.project_var = ctk.StringVar(value="— None —")
        project_names = ["— None —"] + [p["name"] for p in self.projects] if self.projects else ["— None —"]
        self.project_dropdown = self._dropdown_field("Project", self.project_var, project_names)

        # 2. Timing Section
        self._section_header("Schedule")
        
        # Date with Quick Buttons
        date_row = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        date_row.pack(fill="x", pady=5)
        ctk.CTkLabel(date_row, text="Due Date", width=110, anchor="w", font=FONTS["body"]).pack(side="left")
        
        date_input_f = ctk.CTkFrame(date_row, fg_color="transparent")
        date_input_f.pack(side="left", fill="x", expand=True)
        
        self.date_entry = ctk.CTkEntry(date_input_f, placeholder_text="YYYY-MM-DD", font=FONTS["body"])
        self.date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.date_entry.pack(fill="x")
        
        # Quick Date Buttons
        btn_f = ctk.CTkFrame(date_input_f, fg_color="transparent")
        btn_f.pack(fill="x", pady=(5, 0))
        
        def _set_d(days):
            from datetime import timedelta
            self.date_entry.delete(0, 'end')
            self.date_entry.insert(0, (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d"))

        q_btn_cfg = dict(width=60, height=24, font=FONTS["small"], fg_color=THEME["bg_tertiary"], text_color=THEME["text_secondary"])
        ctk.CTkButton(btn_f, text="Today", command=lambda: _set_d(0), **q_btn_cfg).pack(side="left", padx=(0, 5))
        ctk.CTkButton(btn_f, text="+7d", command=lambda: _set_d(7), **q_btn_cfg).pack(side="left", padx=5)
        ctk.CTkButton(btn_f, text="+30d", command=lambda: _set_d(30), **q_btn_cfg).pack(side="left", padx=5)

        self.recurring_var = ctk.StringVar(value="none")
        self._dropdown_field("Recurring", self.recurring_var, ["none", "weekly", "monthly", "yearly"])

        # 3. Fiscal Section
        self._section_header("Payment & Tax")
        
        self.account_var = ctk.StringVar()
        acc_names = [a['name'] for a in self.accounts]
        if acc_names: self.account_var.set(acc_names[0])
        self.account_dropdown = self._dropdown_field("Target Account", self.account_var, acc_names or ["—"])

        # EDV Row
        edv_row = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        edv_row.pack(fill="x", pady=5)
        ctk.CTkLabel(edv_row, text="EDV (VAT)", width=110, anchor="w", font=FONTS["body"]).pack(side="left")
        
        self.edv_amount_entry = ctk.CTkEntry(edv_row, placeholder_text="0.00", font=FONTS["body"])
        self.edv_amount_entry.pack(side="left", fill="x", expand=True)
        
        ctk.CTkButton(edv_row, text="18%", width=46, height=32, font=FONTS["small"],
                      fg_color=THEME["bg_tertiary"], text_color=THEME["text_primary"],
                      command=self._calc_edv).pack(side="left", padx=(10, 0))

        self.edv_account_var = ctk.StringVar()
        if acc_names: self.edv_account_var.set(acc_names[0])
        self.edv_account_dropdown = self._dropdown_field("EDV Account", self.edv_account_var, acc_names or ["—"], small=True)

        # ── Footer ──────────────────────────────────────────────────────────
        footer = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        footer.pack(fill="x", pady=(20, 0))

        ctk.CTkButton(footer, text="Cancel", fg_color=THEME["bg_secondary"],
                      hover_color=THEME["border"], text_color=THEME["text_primary"],
                      font=FONTS["body"], height=42,
                      command=self.destroy).pack(side="left", expand=True, padx=(0, 5))

        self.submit_btn = ctk.CTkButton(footer, text="Create Plan ✓",
                                        fg_color=THEME["green"], hover_color=THEME["green_dark"],
                                        font=FONTS["body"], height=42,
                                        command=self._submit)
        self.submit_btn.pack(side="right", expand=True, padx=(5, 0))

        # Initial Load
        self._set_type("expense")

    # ─── Helpers ──────────────────────────────────────────────────────────────
    def _calc_edv(self):
        try:
            amt_raw = self.amount_entry.get().strip().replace(",", "")
            if not amt_raw: return
            amt = Decimal(amt_raw)
            edv = amt * Decimal("0.18")
            self.edv_amount_entry.delete(0, 'end')
            self.edv_amount_entry.insert(0, f"{edv:.2f}")
        except Exception:
            pass

    # ─── UI Helpers ──────────────────────────────────────────────────────────
    def _section_header(self, title):
        lbl = ctk.CTkLabel(self.form_frame, text=title.upper(), font=FONTS["small"], 
                           text_color=THEME["text_tertiary"], anchor="w")
        lbl.pack(fill="x", pady=(8, 4))

    def _field(self, label, placeholder="", value=""):
        row = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        row.pack(fill="x", pady=3)
        ctk.CTkLabel(row, text=label, width=110, anchor="w", font=FONTS["body"]).pack(side="left")
        entry = ctk.CTkEntry(row, placeholder_text=placeholder, font=FONTS["body"])
        if value: entry.insert(0, value)
        entry.pack(side="left", fill="x", expand=True)
        return entry

    def _dropdown_field(self, label, variable, values, small=False):
        row = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        row.pack(fill="x", pady=3)
        font = FONTS["small"] if small else FONTS["body"]
        ctk.CTkLabel(row, text=label, width=110, anchor="w", font=font).pack(side="left")
        
        dropdown = ctk.CTkOptionMenu(row, variable=variable, values=values, font=font, height=28 if small else 32)
        dropdown.pack(side="left", fill="x", expand=True)
        return dropdown

    def _set_type(self, type_str):
        self.type_var.set(type_str)
        inactive = dict(fg_color="transparent", text_color=THEME["text_secondary"])
        self.btn_income.configure(**inactive)
        self.btn_expense.configure(**inactive)

        if type_str == "income":
            self.btn_income.configure(fg_color=THEME["green"], text_color="white")
            self.submit_btn.configure(fg_color=THEME["green"], hover_color=THEME["green_dark"])
        else:
            self.btn_expense.configure(fg_color=THEME["red"], text_color="white")
            self.submit_btn.configure(fg_color=THEME["red"], hover_color="#a02020")

        self._load_categories()

    def _load_categories(self):
        cats = get_categories(self.company_id, type_filter=self.type_var.get())
        
        # Build hierarchy
        parents = {c.id: c for c in cats if c.parent_id is None}
        children = [c for c in cats if c.parent_id is not None]
        
        display_options = []
        self.cat_map = {} # map display name to category object
        
        # Add parents and their children
        for pid, p in parents.items():
            display_options.append(p.name)
            self.cat_map[p.name] = p
            for c in [x for x in children if x.parent_id == pid]:
                display_name = f"{p.name} > {c.name}"
                display_options.append(display_name)
                self.cat_map[display_name] = c
                
        # Add children whose parents were not found in the type filter (if any)
        for c in children:
            display_name = f"? > {c.name}"
            if display_name not in self.cat_map and not any(p.id == c.parent_id for p in parents.values()):
                 display_options.append(display_name)
                 self.cat_map[display_name] = c

        if display_options:
            self.category_dropdown.configure(values=display_options)
            self.category_var.set(display_options[0])
        else:
            self.category_dropdown.configure(values=["— None —"])
            self.category_var.set("— None —")

    # ─── Submit ───────────────────────────────────────────────────────────────
    def _submit(self):
        try:
            raw = self.amount_entry.get().strip().replace(",", "")
            try:
                amount = Decimal(raw)
            except InvalidOperation:
                raise ValueError("Enter a valid numeric amount")
            if amount <= 0:
                raise ValueError("Amount must be greater than zero")

            desc = self.desc_entry.get().strip()
            if not desc:
                raise ValueError("Description is required")

            date_str = self.date_entry.get().strip()
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                raise ValueError("Due date must be YYYY-MM-DD format")

            acc_name = self.account_var.get()
            acc = next((a for a in self.accounts if a['name'] == acc_name), None)
            if not acc:
                raise ValueError("Please select a valid account")

            # Process EDV
            edv_raw = self.edv_amount_entry.get().strip().replace(",", "")
            edv_amount = Decimal("0")
            if edv_raw:
                try:
                    edv_amount = Decimal(edv_raw)
                except InvalidOperation:
                    raise ValueError("Invalid EDV amount")

            edv_acc_name = self.edv_account_var.get()
            edv_acc = next((a for a in self.accounts if a['name'] == edv_acc_name), None)
            edv_acc_id = edv_acc['id'] if (edv_acc and edv_amount > 0) else None

            data = {
                "company_id":     self.company_id,
                "account_id":     acc['id'],
                "type":           self.type_var.get(),
                "amount":         amount,
                "description":    desc,
                "due_date":       dt,
                "recurring":      self.recurring_var.get(),
                "status":         "pending",
                "currency":       self.currency_var.get(),
                "edv_amount":     edv_amount,
                "edv_account_id": edv_acc_id,
            }

            cat_name = self.category_var.get()
            cat = self.cat_map.get(cat_name)
            if cat:
                data["category_id"] = cat.id

            proj_name = self.project_var.get()
            if proj_name != "— None —":
                proj = next((p for p in self.projects if p["name"] == proj_name), None)
                if proj:
                    data["project_id"] = proj["id"]

            create_planned_payment(data)
            Toast(self.master, "Planned payment added ✓", type="success")
            self.on_success()
            self.destroy()

        except ValueError as e:
            Toast(self, str(e), type="error")
        except Exception as e:
            Toast(self, f"Error: {e}", type="error")
