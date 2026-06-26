import customtkinter as ctk
from decimal import Decimal, InvalidOperation
from ui.theme import THEME, FONTS, CATEGORY_COLORS, validate_hex_color
from ui.components.modal import Modal
from services.account_service import update_account
from ui.components.toast import Toast
import tkinter.colorchooser as colorchooser

class EditAccountModal(Modal):
    def __init__(self, master, account, on_success, **kwargs):
        super().__init__(master, title="Edit Account", width=450, height=550, **kwargs)
        self.account = account
        self.on_success = on_success
        self.selected_color = validate_hex_color(account.get("color", CATEGORY_COLORS[0]))
        self._build_ui()

    def _build_ui(self):
        self.form_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.form_frame.pack(fill="both", expand=True)

        self.name_entry  = self._field("Name", "e.g. Main Checking", value=self.account["name"])
        bal_str = f"{self.account['balance']:.2f}"
        self.bal_entry   = self._field("Balance", "0.00", value=bal_str)

        row2 = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        row2.pack(fill="x", pady=8)
        
        ctk.CTkLabel(row2, text="Type", width=60, anchor="w", font=FONTS["body"]).pack(side="left")
        self.type_var = ctk.StringVar(value=self.account.get("type", "Bank"))
        ctk.CTkOptionMenu(row2, variable=self.type_var, font=FONTS["body"], width=120,
                          values=["Bank", "Cash", "E-wallet", "Crypto", "Credit Card"]
                          ).pack(side="left", padx=(0, 10))

        ctk.CTkLabel(row2, text="Currency", width=70, anchor="w", font=FONTS["body"]).pack(side="left")
        self.curr_var = ctk.StringVar(value=self.account.get("currency", "AZN"))
        ctk.CTkOptionMenu(row2, variable=self.curr_var, font=FONTS["body"], width=100,
                          values=["USD", "EUR", "GBP", "AZN", "RUB", "TRY"]
                          ).pack(side="left")

        # Color Section
        ctk.CTkLabel(self.form_frame, text="Select Color", font=FONTS["heading"]).pack(anchor="w", pady=(15, 5))
        
        color_container = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        color_container.pack(fill="x", pady=5)
        
        grid_frame = ctk.CTkFrame(color_container, fg_color="transparent")
        grid_frame.pack(side="left", fill="both", expand=True)
        self.color_buttons = {}
        for i, color in enumerate(CATEGORY_COLORS):
            btn = ctk.CTkButton(grid_frame, text="", width=24, height=24, corner_radius=12,
                                fg_color=color, hover_color=color,
                                command=lambda c=color: self._select_color(c))
            btn.grid(row=i//5, column=i%5, padx=3, pady=3)
            self.color_buttons[color] = btn
            
        preview_frame = ctk.CTkFrame(color_container, fg_color=THEME["bg_secondary"], corner_radius=10, width=110)
        preview_frame.pack(side="right", fill="both", padx=(10, 0))
        preview_frame.pack_propagate(False)
        self.preview_dot = ctk.CTkFrame(preview_frame, width=30, height=30, corner_radius=15, fg_color=self.selected_color)
        self.preview_dot.pack(pady=10)
        ctk.CTkButton(preview_frame, text="Custom", height=24, font=FONTS["small"],
                      command=self._pick_custom_color).pack(pady=5, padx=10)
        
        self._select_color(self.selected_color)

        # Footer
        footer = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        footer.pack(fill="x", pady=(20, 0))

        ctk.CTkButton(footer, text="Cancel", fg_color=THEME["bg_secondary"],
                      hover_color=THEME["border"], text_color=THEME["text_primary"],
                      command=self.destroy).pack(side="left", expand=True, padx=(0, 5))

        ctk.CTkButton(footer, text="Save Changes \u2713", fg_color=THEME["green"],
                      hover_color=THEME["green_dark"],
                      command=self._submit).pack(side="right", expand=True, padx=(5, 0))

    def _field(self, label, placeholder="", value=""):
        row = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        row.pack(fill="x", pady=8)
        ctk.CTkLabel(row, text=label, width=110, anchor="w", font=FONTS["body"]).pack(side="left")
        entry = ctk.CTkEntry(row, placeholder_text=placeholder, font=FONTS["body"])
        if value: entry.insert(0, value)
        entry.pack(side="left", fill="x", expand=True)
        return entry

    def _select_color(self, color):
        for c, btn in self.color_buttons.items(): btn.configure(border_width=0)
        self.selected_color = validate_hex_color(color)
        if self.selected_color in self.color_buttons:
            self.color_buttons[self.selected_color].configure(border_width=2, border_color=THEME["text_primary"])
        self.preview_dot.configure(fg_color=self.selected_color)

    def _pick_custom_color(self):
        color = colorchooser.askcolor(title="Choose Account Color", initialcolor=self.selected_color)[1]
        if color: self._select_color(color)

    def _submit(self):
        try:
            name = self.name_entry.get().strip()
            if not name: raise ValueError("Account name is required")
            
            raw_bal = self.bal_entry.get().strip().replace(",", "")
            try: balance = Decimal(raw_bal)
            except InvalidOperation: raise ValueError("Balance must be a valid number")
            
            data = {
                "name": name,
                "type": self.type_var.get(),
                "currency": self.curr_var.get(),
                "balance": balance,
                "color": self.selected_color,
            }
            update_account(self.account["id"], data)
            Toast(self.master, "Account updated", type="success")
            self.on_success(); self.destroy()
        except Exception as e:
            Toast(self, str(e), type="error")
