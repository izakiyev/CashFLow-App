import customtkinter as ctk
from ui.theme import THEME, FONTS
from ui.components.modal import Modal
from services.currency_service import load_rates, save_rates
from ui.components.toast import Toast

class ManageCurrenciesModal(Modal):
    def __init__(self, master, company_id, on_success, **kwargs):
        super().__init__(master, title="Manage Exchange Rates", width=500, height=600, **kwargs)
        self.company_id = company_id
        self.on_success = on_success
        
        from services.company_service import get_company
        company = get_company(company_id)
        self.base_currency = company['currency'] if company else "AZN"
        
        self.rates = load_rates()
        self.entries = {}
        self._build_ui()

    def _build_ui(self):
        # Description
        desc_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        desc_frame.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(desc_frame, text=f"Set exchange rates relative to your main currency ({self.base_currency} = 1.0).\nThese are used for accurate multi-currency Dashboards.",
                     font=FONTS["small"], text_color=THEME["text_secondary"], justify="left").pack(anchor="w")

        # Scrollable list
        self.list_frame = ctk.CTkScrollableFrame(self.content_frame, fg_color="transparent")
        self.list_frame.pack(fill="both", expand=True, pady=10)

        # Header
        header = ctk.CTkFrame(self.list_frame, fg_color="transparent")
        header.pack(fill="x", pady=(0, 5))
        ctk.CTkLabel(header, text="Currency Code", font=FONTS["body"], width=120, anchor="w").pack(side="left")
        ctk.CTkLabel(header, text="Exchange Rate", font=FONTS["body"], anchor="w").pack(side="left", padx=10, expand=True)

        self._render_rows()

        # Add Row Button
        add_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        add_frame.pack(fill="x", pady=10)
        
        self.new_curr_entry = ctk.CTkEntry(add_frame, placeholder_text="e.g. JPY", width=120, font=FONTS["body"])
        self.new_curr_entry.pack(side="left")
        
        self.new_rate_entry = ctk.CTkEntry(add_frame, placeholder_text="e.g. 150.5", font=FONTS["body"])
        self.new_rate_entry.pack(side="left", fill="x", expand=True, padx=10)
        
        ctk.CTkButton(add_frame, text="Add", width=60, fg_color=THEME["blue"], font=FONTS["body"],
                      command=self._add_currency).pack(side="right")

        # Footer
        footer = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        footer.pack(fill="x", pady=(16, 0))

        ctk.CTkButton(footer, text="Cancel", fg_color=THEME["bg_secondary"],
                      hover_color=THEME["border"], text_color=THEME["text_primary"],
                      font=FONTS["body"], height=38,
                      command=self.destroy).pack(side="left", expand=True, padx=(0, 5))

        ctk.CTkButton(footer, text="Save Rates ✓", fg_color=THEME["green"],
                      hover_color=THEME["green_dark"], font=FONTS["body"], height=38,
                      command=self._save).pack(side="right", expand=True, padx=(5, 0))

    def _render_rows(self):
        for w in self.list_frame.winfo_children():
            # Skip the header (we could identify it, but we recreate everything for simplicity)
            w.destroy()

        header = ctk.CTkFrame(self.list_frame, fg_color="transparent")
        header.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(header, text="Currency Code", font=FONTS["body"], width=120, anchor="w", text_color=THEME["text_secondary"]).pack(side="left")
        ctk.CTkLabel(header, text="Exchange Rate", font=FONTS["body"], anchor="w", text_color=THEME["text_secondary"]).pack(side="left", padx=10, expand=True)

        self.entries.clear()
        
        # Calculate the pivot rate (base_currency relative to USD)
        pivot = self.rates.get(self.base_currency, 1.0)
        
        for curr, rate in self.rates.items():
            row = ctk.CTkFrame(self.list_frame, fg_color=THEME["bg_tertiary"], corner_radius=6)
            row.pack(fill="x", pady=4)
            
            lbl = ctk.CTkLabel(row, text=curr, font=FONTS["heading"], width=100, anchor="w")
            lbl.pack(side="left", padx=(10, 0), pady=6)
            
            entry = ctk.CTkEntry(row, font=FONTS["body"])
            
            # Display rate relative to our Base Currency
            display_rate = rate / pivot
            entry.insert(0, f"{display_rate:g}")
            entry.pack(side="left", fill="x", expand=True, padx=10, pady=6)
            
            if curr != self.base_currency:  # Prevent deleting base currency
                btn = ctk.CTkButton(row, text="X", width=30, fg_color="transparent", text_color=THEME["red"], 
                                    hover_color=THEME["bg_secondary"],
                                    command=lambda c=curr: self._remove_currency(c))
                btn.pack(side="right", padx=6)
                
            self.entries[curr] = entry

    def _add_currency(self):
        curr = self.new_curr_entry.get().strip().upper()
        rate_str = self.new_rate_entry.get().strip()
        
        if not curr or len(curr) > 5:
            Toast(self, "Invalid currency code", type="error")
            return
            
        try:
            rate = float(rate_str)
            if rate <= 0: raise ValueError
        except ValueError:
            Toast(self, "Invalid rate value", type="error")
            return
            
        self.rates[curr] = rate
        self.new_curr_entry.delete(0, 'end')
        self.new_rate_entry.delete(0, 'end')
        self._render_rows()

    def _remove_currency(self, curr):
        if curr in self.rates:
            del self.rates[curr]
            self._render_rows()

    def _save(self):
        # Update rates from entries
        new_rates = {}
        for curr, entry in self.entries.items():
            val = entry.get().strip()
            try:
                rate = float(val)
                if rate <= 0: raise ValueError
                new_rates[curr] = rate
            except ValueError:
                Toast(self, f"Invalid rate for {curr}", type="error")
                return
                
        # Must have our base currency as 1.0 internally for this save operation
        # But wait, if we want to keep USD as the pivot internally, we'd multiply back.
        # Let's just save exactly what the user entered. The logic to_rate/from_rate works 
        # as long as they are all relative to the SAME currency (which they now are).
        if self.base_currency not in new_rates:
            new_rates[self.base_currency] = 1.0
            
        save_rates(new_rates)
        Toast(self.master, "Exchange rates saved ✓", type="success")
        self.on_success()
        self.destroy()
