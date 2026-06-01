import customtkinter as ctk
from decimal import Decimal, InvalidOperation
from datetime import datetime
from ui.theme import THEME, FONTS
from ui.components.modal import Modal
from services.transaction_service import get_transaction, update_transaction
from services.account_service import get_accounts
from services.category_service import get_categories
from services.company_service import get_company
from services.currency_service import convert_to_base
from ui.components.toast import Toast

class EditTransactionModal(Modal):
    def __init__(self, master, tx_id, company_id, on_success, **kwargs):
        super().__init__(master, title="Edit Transaction", width=500, height=700, **kwargs)
        self.tx_id = tx_id
        self.company_id = company_id
        self.on_success = on_success
        self.type_var = ctk.StringVar()
        
        self.accounts = get_accounts(company_id)
        self.categories = []
        
        company = get_company(company_id)
        self.base_currency = company['currency'] if company else "AZN"
        
        self.tx = get_transaction(tx_id)
        if not self.tx:
            Toast(self.master, "Transaction not found", type="error")
            self.destroy()
            return
            
        self._build_ui()
        self._prefill()

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

        ctk.CTkLabel(self.form_frame, text="Amount", font=FONTS["small"],
                     text_color=THEME["text_tertiary"]).pack(anchor="w")
        # Container for amount + currency
        amt_container = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        amt_container.pack(fill="x", pady=(2, 12))

        self.amount_entry = ctk.CTkEntry(amt_container, placeholder_text="0.00",
                                         font=("Inter", 26, "bold"), height=52)
        self.amount_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.currency_var = ctk.StringVar(value="AZN")
        self.currency_dropdown = ctk.CTkOptionMenu(amt_container, variable=self.currency_var,
                                                   values=["AZN", "USD", "EUR", "RUB", "TRY", "GBP"],
                                                   width=90, height=52, font=FONTS["heading"])
        self.currency_dropdown.pack(side="right")

        self.desc_entry = self._field("Description", "e.g. Client payment")

        # Account
        self.acc_row = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        self.acc_row.pack(fill="x", pady=5)
        ctk.CTkLabel(self.acc_row, text="Account", width=110, anchor="w", font=FONTS["body"]).pack(side="left")
        
        self.account_var = ctk.StringVar()
        acc_names = [a['name'] for a in self.accounts]
        self.account_dropdown = ctk.CTkOptionMenu(self.acc_row, variable=self.account_var,
                                                  values=acc_names or ["—"], font=FONTS["body"])
        self.account_dropdown.pack(side="left", fill="x", expand=True)

        # Category
        self.cat_row = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        ctk.CTkLabel(self.cat_row, text="Category", width=110, anchor="w", font=FONTS["body"]).pack(side="left")
        self.category_var = ctk.StringVar(value="Loading...")
        self.category_dropdown = ctk.CTkOptionMenu(self.cat_row, variable=self.category_var,
                                                   values=["Loading..."], font=FONTS["body"])
        self.category_dropdown.pack(side="left", fill="x", expand=True)

        # To Account (transfer)
        self.to_acc_row = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        ctk.CTkLabel(self.to_acc_row, text="To Account", width=110, anchor="w", font=FONTS["body"]).pack(side="left")
        self.to_account_var = ctk.StringVar()
        self.to_account_dropdown = ctk.CTkOptionMenu(self.to_acc_row, variable=self.to_account_var,
                                                     values=acc_names or ["—"], font=FONTS["body"])
        self.to_account_dropdown.pack(side="left", fill="x", expand=True)
        self.to_acc_row.pack_forget()

        self.date_entry = self._field("Date", "YYYY-MM-DD")

        # Status row
        self.status_row = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        self.status_row.pack(fill="x", pady=5)
        ctk.CTkLabel(self.status_row, text="Status", width=110, anchor="w",
                     font=FONTS["body"]).pack(side="left")
        self.status_var = ctk.StringVar(value="confirmed")
        self.status_dropdown = ctk.CTkOptionMenu(self.status_row, variable=self.status_var,
                                                 values=["paid", "confirmed", "pending"], font=FONTS["body"])
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
                      font=FONTS["body"], height=38, command=self.destroy).pack(side="left", expand=True, padx=(0, 5))

        self.submit_btn = ctk.CTkButton(footer, text="Save Changes ✓",
                                        fg_color=THEME["green"], hover_color=THEME["green_dark"],
                                        font=FONTS["body"], height=38, command=self._submit)
        self.submit_btn.pack(side="right", expand=True, padx=(5, 0))

    def _prefill(self):
        self._set_type(self.tx['type'])
        
        self.amount_entry.insert(0, str(self.tx['amount']))
        self.desc_entry.insert(0, self.tx['description'])
        
        date_str = self.tx['date'].strftime("%Y-%m-%d") if self.tx['date'] else ""
        self.date_entry.insert(0, date_str)
        if self.tx.get('note'):
            self.note_entry.insert(0, self.tx['note'])
        
        if self.tx.get('edv_amount'):
            self.edv_entry.insert(0, str(self.tx['edv_amount']))
        
        if self.tx.get('edv_account_id'):
            e_acc = next((a for a in self.accounts if a['id'] == self.tx['edv_account_id']), None)
            if e_acc:
                self.edv_account_var.set(e_acc['name'])
        
        if self.tx.get('status'):
            self.status_var.set(self.tx['status'])
        
        if self.tx.get('currency'):
            self.currency_var.set(self.tx['currency'])
            
        # Set Account
        acc = next((a for a in self.accounts if a['id'] == self.tx['account_id']), None)
        if acc: self.account_var.set(acc['name'])
        
        # Set Category / To Account based on type
        if self.tx['type'] == 'transfer':
            to_acc = next((a for a in self.accounts if a['id'] == self.tx['to_account_id']), None)
            if to_acc: self.to_account_var.set(to_acc['name'])
        else:
            self._load_categories()
            # Find the category in the map by id
            display_name = next((name for name, c in self.cat_map.items() if c.id == self.tx['category_id']), None)
            if display_name:
                self.category_var.set(display_name)

    def _field(self, label, placeholder="", value=""):
        row = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        row.pack(fill="x", pady=5)
        ctk.CTkLabel(row, text=label, width=110, anchor="w", font=FONTS["body"]).pack(side="left")
        entry = ctk.CTkEntry(row, placeholder_text=placeholder, font=FONTS["body"])
        if value: entry.insert(0, value)
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
            self.to_acc_row.pack_forget()
            self.edv_row.pack(fill="x", pady=5)
            self.edv_acc_row.pack(fill="x", pady=5)
            self._load_categories()
        elif type_str == "expense":
            self.btn_expense.configure(fg_color=THEME["red"], text_color="white")
            self.submit_btn.configure(fg_color=THEME["red"], hover_color="#a02020")
            self.cat_row.pack(fill="x", pady=5, after=self.acc_row)
            self.to_acc_row.pack_forget()
            self.edv_row.pack(fill="x", pady=5)
            self.edv_acc_row.pack(fill="x", pady=5)
            self._load_categories()
        else:
            self.btn_transfer.configure(fg_color=THEME["blue"], text_color="white")
            self.submit_btn.configure(fg_color=THEME["blue"], hover_color=THEME["blue_light"])
            self.cat_row.pack_forget()
            self.edv_row.pack_forget()
            self.edv_acc_row.pack_forget()
            self.to_acc_row.pack(fill="x", pady=5, after=self.acc_row)

    def _load_categories(self):
        t = self.type_var.get()
        if t == "transfer": return
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
                 display_options.append(display_name)
                 self.cat_map[display_name] = c

        if display_options:
            self.category_dropdown.configure(values=display_options)
            # Only set if not currently matching any
            if self.category_var.get() not in display_options:
                self.category_var.set(display_options[0])
        else:
            self.category_dropdown.configure(values=["— None —"])
            self.category_var.set("— None —")

    def _submit(self):
        try:
            raw = self.amount_entry.get().strip().replace(",", "")
            try: amount = Decimal(raw)
            except InvalidOperation: raise ValueError("Enter a valid numeric amount")
            if amount <= 0: raise ValueError("Amount must be greater than zero")

            desc = self.desc_entry.get().strip()
            if not desc: raise ValueError("Description is required")

            date_str = self.date_entry.get().strip()
            try: dt = datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError: raise ValueError("Date must be YYYY-MM-DD")

            acc_name = self.account_var.get()
            acc = next((a for a in self.accounts if a['name'] == acc_name), None)
            if not acc: raise ValueError("Please select a valid account")

            data = {
                "type": self.type_var.get(),
                "amount": amount,
                "description": desc,
                "date": dt,
                "note": self.note_entry.get().strip(),
                "account_id": acc['id'],
                "category_id": None,
                "to_account_id": None,
                "status": self.status_var.get(),
                "currency": self.currency_var.get(),
                "edv_amount": 0,
                "edv_account_id": None
            }

            if data["type"] != "transfer":
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

            if data["type"] == "transfer":
                to_acc_name = self.to_account_var.get()
                to_acc = next((a for a in self.accounts if a['name'] == to_acc_name), None)
                if not to_acc: raise ValueError("Please select a valid destination account")
                if to_acc['id'] == acc['id']: raise ValueError("Transfer destination must be different from source")
                data["to_account_id"] = to_acc['id']
            else:
                cat_name = self.category_var.get()
                cat = self.cat_map.get(cat_name)
                if cat: data["category_id"] = cat.id

            update_transaction(self.tx_id, data)
            Toast(self.master, "Transaction updated ✓", type="success")
            self.on_success()
            self.destroy()

        except ValueError as e:
            Toast(self, str(e), type="error")
        except Exception as e:
            Toast(self, f"Error: {e}", type="error")
