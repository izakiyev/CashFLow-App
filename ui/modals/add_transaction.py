import customtkinter as ctk
from decimal import Decimal, InvalidOperation
from datetime import datetime
from ui.theme import THEME, FONTS
from ui.components.modal import Modal
from services.transaction_service import create_transaction
from services.account_service import get_accounts
from services.category_service import get_categories
from services.project_service import get_projects
from services.company_service import get_company
from services.currency_service import convert_to_base
from ui.components.toast import Toast


class AddTransactionModal(Modal):
    def __init__(self, master, company_id, on_success, **kwargs):
        super().__init__(master, title="New Transaction", width=500, height=700, **kwargs)
        self.company_id = company_id
        self.on_success = on_success
        self.type_var = ctk.StringVar(value="income")

        self.accounts = get_accounts(company_id)  # list of dicts
        self.categories = []
        self.projects = get_projects(company_id, status_filter="active")

        company = get_company(company_id)
        self.base_currency = company['currency'] if company else "AZN"

        self._build_ui()

    def _build_ui(self):
        # ── Type Selector ──────────────────────────────────────────────────
        type_frame = ctk.CTkFrame(self.content_frame, fg_color=THEME["bg_tertiary"], corner_radius=8)
        type_frame.pack(fill="x", pady=(0, 16))

        btn_cfg = dict(height=34, corner_radius=6, font=FONTS["body"], border_width=0)
        inactive = dict(fg_color="transparent", text_color=THEME["text_secondary"],
                        hover_color=THEME["border"])

        self.btn_income = ctk.CTkButton(type_frame, text="↑  Income",
                                        command=lambda: self._set_type("income"), **btn_cfg, **inactive)
        self.btn_income.pack(side="left", expand=True, padx=6, pady=6)

        self.btn_expense = ctk.CTkButton(type_frame, text="↓  Expense",
                                         command=lambda: self._set_type("expense"), **btn_cfg, **inactive)
        self.btn_expense.pack(side="left", expand=True, padx=(0, 6), pady=6)

        self.btn_transfer = ctk.CTkButton(type_frame, text="⇄  Transfer",
                                          command=lambda: self._set_type("transfer"), **btn_cfg, **inactive)
        self.btn_transfer.pack(side="left", expand=True, padx=(0, 6), pady=6)

        # ── Form ────────────────────────────────────────────────────────────
        self.form_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.form_frame.pack(fill="both", expand=True)

        # Big amount field
        ctk.CTkLabel(self.form_frame, text="Amount", font=FONTS["small"],
                     text_color=THEME["text_tertiary"]).pack(anchor="w")
        # Container for amount + currency
        amt_container = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        amt_container.pack(fill="x", pady=(2, 12))

        self.currency_var = ctk.StringVar(value="AZN")
        self.amount_entry = ctk.CTkEntry(amt_container, placeholder_text="0.00",
                                         font=("Inter", 26, "bold"), height=52)
        self.amount_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.currency_dropdown = ctk.CTkOptionMenu(amt_container, variable=self.currency_var,
                                                   values=["AZN", "USD", "EUR", "RUB", "TRY", "GBP"],
                                                   width=90, height=52, font=FONTS["heading"])
        self.currency_dropdown.pack(side="right")

        self.desc_entry = self._field("Description", "e.g. Client payment")

        # Account
        self.acc_row = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        self.acc_row.pack(fill="x", pady=5)
        ctk.CTkLabel(self.acc_row, text="Account", width=110, anchor="w",
                     font=FONTS["body"]).pack(side="left")
        
        self.account_var = ctk.StringVar()
        acc_names = [a['name'] for a in self.accounts]
        if acc_names:
            self.account_var.set(acc_names[0])
            self.currency_var.set(self.accounts[0]['currency'])
        
        self.account_dropdown = ctk.CTkOptionMenu(self.acc_row, variable=self.account_var,
                                                   values=acc_names or ["—"], font=FONTS["body"])
        self.account_dropdown.pack(side="left", fill="x", expand=True)

        # Category row
        self.cat_row = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        ctk.CTkLabel(self.cat_row, text="Category", width=110, anchor="w",
                     font=FONTS["body"]).pack(side="left")
        self.category_var = ctk.StringVar(value="Loading...")
        self.category_dropdown = ctk.CTkOptionMenu(self.cat_row, variable=self.category_var,
                                                   values=["Loading..."], font=FONTS["body"])
        self.category_dropdown.pack(side="left", fill="x", expand=True)

        # Project row
        self.project_row = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        ctk.CTkLabel(self.project_row, text="Project", width=110, anchor="w",
                     font=FONTS["body"]).pack(side="left")
        self.project_var = ctk.StringVar(value="— None —")
        project_names = ["— None —"] + [p["name"] for p in self.projects] if self.projects else ["— None —"]
        self.project_dropdown = ctk.CTkOptionMenu(self.project_row, variable=self.project_var,
                                                  values=project_names, font=FONTS["body"])
        self.project_dropdown.pack(side="left", fill="x", expand=True)

        # To Account row (transfer only)
        self.to_acc_row = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        ctk.CTkLabel(self.to_acc_row, text="To Account", width=110, anchor="w",
                     font=FONTS["body"]).pack(side="left")
        self.to_account_var = ctk.StringVar()
        if len(acc_names) > 1:
            self.to_account_var.set(acc_names[1])
        self.to_account_dropdown = ctk.CTkOptionMenu(self.to_acc_row, variable=self.to_account_var,
                                                     values=acc_names or ["—"], font=FONTS["body"])
        self.to_account_dropdown.pack(side="left", fill="x", expand=True)
        self.to_acc_row.pack_forget()

        self.date_entry = self._field("Date", "YYYY-MM-DD",
                                      value=datetime.now().strftime("%Y-%m-%d"))
        
        # Status row
        self.status_row = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        self.status_row.pack(fill="x", pady=5)
        ctk.CTkLabel(self.status_row, text="Status", width=110, anchor="w",
                     font=FONTS["body"]).pack(side="left")
        self.status_var = ctk.StringVar(value="paid")
        self.status_dropdown = ctk.CTkOptionMenu(self.status_row, variable=self.status_var,
                                                 values=["paid", "confirmed", "pending", "Qaime Gözleyir"], font=FONTS["body"])
        self.status_dropdown.pack(side="left", fill="x", expand=True)

        self.note_entry = self._field("Note (opt.)", "Any additional info")

        # EDV row
        self.edv_row = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        self.edv_row.pack(fill="x", pady=5)
        ctk.CTkLabel(self.edv_row, text=f"EDV ({self.base_currency})", width=110, anchor="w", font=FONTS["body"]).pack(side="left")
        
        self.edv_entry = ctk.CTkEntry(self.edv_row, placeholder_text="0.00", font=FONTS["body"])
        self.edv_entry.pack(side="left", fill="x", expand=True)

        def auto_calc_edv():
            try:
                raw = self.amount_entry.get().strip().replace(",", "")
                if not raw: return
                amt = Decimal(raw)
                curr = self.currency_var.get()
                # Convert amt from transaction currency to base currency
                base_amt = convert_to_base(amt, curr, self.base_currency)
                edv = base_amt * Decimal("0.18")
                self.edv_entry.delete(0, 'end')
                self.edv_entry.insert(0, f"{edv:,.2f}")
            except Exception:
                pass

        ctk.CTkButton(self.edv_row, text="18%", width=40, font=FONTS["small"],
                      fg_color=THEME["bg_secondary"], hover_color=THEME["border"],
                      text_color=THEME["text_primary"], command=auto_calc_edv).pack(side="right", padx=(5, 0))

        # EDV Account row
        self.edv_acc_row = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        self.edv_acc_row.pack(fill="x", pady=5)
        ctk.CTkLabel(self.edv_acc_row, text="EDV Account", width=110, anchor="w", font=FONTS["body"]).pack(side="left")
        self.edv_account_var = ctk.StringVar(value="— None —")
        self.edv_account_dropdown = ctk.CTkOptionMenu(self.edv_acc_row, variable=self.edv_account_var,
                                                      values=["— None —"] + acc_names, font=FONTS["body"])
        self.edv_account_dropdown.pack(side="left", fill="x", expand=True)

        # ── Footer ──────────────────────────────────────────────────────────
        footer = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        footer.pack(fill="x", pady=(12, 0))

        ctk.CTkButton(footer, text="Cancel", fg_color=THEME["bg_secondary"],
                      hover_color=THEME["border"], text_color=THEME["text_primary"],
                      font=FONTS["body"], height=38,
                      command=self.destroy).pack(side="left", expand=True, padx=(0, 5))

        self.submit_btn = ctk.CTkButton(footer, text="Add Transaction ✓",
                                        fg_color=THEME["green"], hover_color=THEME["green_dark"],
                                        font=FONTS["body"], height=38, command=self._submit)
        self.submit_btn.pack(side="right", expand=True, padx=(5, 0))

        self._set_type("income")
        
        # Trace account selection to sync currency
        self.account_var.trace_add("write", self._on_account_change)

    def _on_account_change(self, *args):
        acc_name = self.account_var.get()
        acc = next((a for a in self.accounts if a['name'] == acc_name), None)
        if acc:
            self.currency_var.set(acc['currency'])

    # ─── Helpers ──────────────────────────────────────────────────────────────
    def _field(self, label, placeholder="", value=""):
        row = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        row.pack(fill="x", pady=5)
        ctk.CTkLabel(row, text=label, width=110, anchor="w",
                     font=FONTS["body"]).pack(side="left")
        entry = ctk.CTkEntry(row, placeholder_text=placeholder, font=FONTS["body"])
        if value:
            entry.insert(0, value)
        entry.pack(side="left", fill="x", expand=True)
        return entry

    def _set_type(self, type_str):
        self.type_var.set(type_str)

        inactive = dict(fg_color="transparent", text_color=THEME["text_secondary"])
        self.btn_income.configure(**inactive)
        self.btn_expense.configure(**inactive)
        self.btn_transfer.configure(**inactive)

        if type_str == "income":
            self.btn_income.configure(fg_color=THEME["green"], text_color="white")
            self.submit_btn.configure(fg_color=THEME["green"], hover_color=THEME["green_dark"])
            self.cat_row.pack(fill="x", pady=5, after=self.acc_row)
            self.project_row.pack(fill="x", pady=5, after=self.cat_row)
            self.to_acc_row.pack_forget()
            self.edv_row.pack(fill="x", pady=5)
            self.edv_acc_row.pack(fill="x", pady=5)
            self._load_categories()
        elif type_str == "expense":
            self.btn_expense.configure(fg_color=THEME["red"], text_color="white")
            self.submit_btn.configure(fg_color=THEME["red"], hover_color="#a02020")
            self.cat_row.pack(fill="x", pady=5, after=self.acc_row)
            self.project_row.pack(fill="x", pady=5, after=self.cat_row)
            self.to_acc_row.pack_forget()
            self.edv_row.pack(fill="x", pady=5)
            self.edv_acc_row.pack(fill="x", pady=5)
            self._load_categories()
        else:
            self.btn_transfer.configure(fg_color=THEME["blue"], text_color="white")
            self.submit_btn.configure(fg_color=THEME["blue"], hover_color=THEME["blue_light"])
            self.cat_row.pack_forget()
            self.project_row.pack_forget()
            self.edv_row.pack_forget()
            self.edv_acc_row.pack_forget()
            self.to_acc_row.pack(fill="x", pady=5, after=self.acc_row)

    def _load_categories(self):
        t = self.type_var.get()
        if t == "transfer":
            return
        cats = get_categories(self.company_id, type_filter=t)
        
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
                 # This shouldn't happen much but for robustness
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
            # Validate with Decimal (Golden Rule #1 – no floats for money)
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
                raise ValueError("Date must be in YYYY-MM-DD format")

            t_type = self.type_var.get()
            acc_name = self.account_var.get()
            acc = next((a for a in self.accounts if a['name'] == acc_name), None)
            if not acc:
                raise ValueError("Please select a valid account")

            data = {
                "company_id": self.company_id,
                "account_id": acc['id'],
                "type": t_type,
                "amount": amount,
                "description": desc,
                "note": self.note_entry.get().strip(),
                "date": dt,
                "currency": self.currency_var.get(),
                "status": self.status_var.get().lower(),
                "edv_amount": 0,
                "edv_account_id": None,
            }

            if t_type != "transfer":
                # Parse EDV
                edv_raw = self.edv_entry.get().strip().replace(",", "")
                if edv_raw:
                    try:
                        data["edv_amount"] = Decimal(edv_raw)
                        if data["edv_amount"] < 0: raise ValueError
                    except (InvalidOperation, ValueError):
                        raise ValueError("Invalid EDV amount")
                    
                    edv_acc_name = self.edv_account_var.get()
                    edv_acc = next((a for a in self.accounts if a['name'] == edv_acc_name), None)
                    if edv_acc:
                        data["edv_account_id"] = edv_acc['id']
                    elif data["edv_amount"] > 0:
                        raise ValueError("Please select an account for the EDV portion")

                cat_name = self.category_var.get()
                cat = self.cat_map.get(cat_name)
                if cat: 
                    data["category_id"] = cat.id

                proj_name = self.project_var.get()
                if proj_name != "— None —":
                    proj = next((p for p in self.projects if p["name"] == proj_name), None)
                    if proj:
                        data["project_id"] = proj["id"]
            else:
                to_acc_name = self.to_account_var.get()
                to_acc = next((a for a in self.accounts if a['name'] == to_acc_name), None)
                if not to_acc:
                    raise ValueError("Select a valid destination account")
                if to_acc['id'] == acc['id']:
                    raise ValueError("Cannot transfer to the same account")
                data["to_account_id"] = to_acc['id']

            create_transaction(data)
            Toast(self.master, "Transaction added ✓", type="success")
            self.on_success()
            self.destroy()

        except ValueError as e:
            Toast(self, str(e), type="error")
        except Exception as e:
            Toast(self, f"Unexpected error: {e}", type="error")
