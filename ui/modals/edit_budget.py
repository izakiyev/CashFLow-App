import customtkinter as ctk
from ui.theme import THEME, FONTS
from ui.components.modal import Modal
from services.budget_service import set_budget
from ui.components.toast import Toast

class EditBudgetModal(Modal):
    def __init__(self, master, company_id, category_id, category_name, current_amount, current_period_type, current_month, current_year, on_success=None, **kwargs):
        super().__init__(master, title=f"Set Budget: {category_name}", width=400, height=350, **kwargs)
        
        self.company_id = company_id
        self.category_id = category_id
        self.current_month = current_month
        self.current_year = current_year
        self.on_success = on_success

        # Period Type (Monthly/Yearly)
        ctk.CTkLabel(self.content_frame, text="Budget Period", font=FONTS["small"]).pack(anchor="w", pady=(0, 5))
        self.period_var = ctk.StringVar(value=current_period_type.capitalize())
        self.period_seg = ctk.CTkSegmentedButton(self.content_frame, values=["Monthly", "Yearly"], variable=self.period_var)
        self.period_seg.pack(fill="x", pady=(0, 20))

        # Amount
        ctk.CTkLabel(self.content_frame, text="Amount", font=FONTS["small"]).pack(anchor="w", pady=(0, 5))
        self.amount_var = ctk.StringVar(value=str(current_amount) if current_amount > 0 else "")
        self.amount_entry = ctk.CTkEntry(self.content_frame, textvariable=self.amount_var, font=FONTS["body"])
        self.amount_entry.pack(fill="x", pady=(0, 20))
        self.amount_entry.focus()

        # Context Info
        period_str = f"for {current_year}" if current_period_type == "yearly" else f"for month {current_month}/{current_year}"
        ctk.CTkLabel(self.content_frame, 
                     text=f"Setting budget {period_str}", 
                     font=FONTS["small"], text_color=THEME["text_tertiary"]).pack(anchor="w", pady=(0, 20))

        # Footer
        footer = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        footer.pack(fill="x", side="bottom", pady=10)
        
        btn_cancel = ctk.CTkButton(footer, text="Cancel", fg_color=THEME["bg_secondary"],
                                   command=self.destroy)
        btn_cancel.pack(side="left", expand=True, padx=5)
        
        btn_save = ctk.CTkButton(footer, text="Save Budget", fg_color=THEME["green"],
                                 command=self._save)
        btn_save.pack(side="right", expand=True, padx=5)

    def _save(self):
        amount_str = self.amount_var.get().replace(",", "").strip()
        if not amount_str:
            Toast(self, "Please enter an amount", type="error")
            return
            
        try:
            amount = float(amount_str)
            if amount < 0: raise ValueError
        except ValueError:
            Toast(self, "Invalid amount", type="error")
            return
            
        period_type = self.period_var.get().lower()
        
        try:
            set_budget(
                self.company_id, 
                self.category_id, 
                amount, 
                self.current_month, 
                self.current_year, 
                period_type
            )
            if self.on_success:
                self.on_success()
            self.destroy()
        except Exception as e:
            Toast(self, f"Error saving budget: {e}", type="error")
