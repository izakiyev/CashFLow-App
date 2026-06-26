import customtkinter as ctk
from datetime import datetime
from ui.theme import THEME, FONTS
from services.currency_service import format_currency


class AccountMiniRow(ctk.CTkFrame):
    def __init__(self, master, acc, max_balance, currency="AZN", **kwargs):
        super().__init__(master, fg_color=THEME["bg_tertiary"], corner_radius=8, **kwargs)
        self.pack_propagate(False)

        # Dot
        dot = ctk.CTkFrame(self, width=12, height=12, corner_radius=6, fg_color=acc.get('color', THEME["blue"]))
        dot.pack(side="left", padx=(12, 10), pady=14)

        # Info
        info = ctk.CTkFrame(self, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True, pady=10)
        ctk.CTkLabel(info, text=acc['name'], font=FONTS["body"], text_color=THEME["text_primary"],
                     anchor="w").pack(fill="x")
        ctk.CTkLabel(info, text=acc['type'], font=FONTS["small"], text_color=THEME["text_tertiary"],
                     anchor="w").pack(fill="x", pady=(2, 0))

        # Balance
        bal_color = THEME["green"] if acc['balance'] >= 0 else THEME["red"]
        bal = ctk.CTkFrame(self, fg_color="transparent")
        bal.pack(side="right", padx=(10, 16), pady=10)
        ctk.CTkLabel(bal, text=format_currency(acc['balance'], currency),
                     font=FONTS["body"], text_color=bal_color, anchor="e").pack(fill="x")
        
        # Micro progress bar based on max balance across all accounts
        ratio = (acc['balance'] / max_balance) if max_balance > 0 and acc['balance'] > 0 else 0
        pb_bg = ctk.CTkFrame(bal, height=4, fg_color=THEME["border"], corner_radius=2)
        pb_bg.pack(fill="x", pady=(4, 0))
        if ratio > 0:
            pb_fill = ctk.CTkFrame(pb_bg, height=4, width=max(4, int(100 * ratio)), 
                                   fg_color=acc.get('color', THEME["blue"]), corner_radius=2)
            pb_fill.pack(side="left", fill="y")


class TxMiniRow(ctk.CTkFrame):
    def __init__(self, master, tx, on_click=None, **kwargs):
        super().__init__(master, fg_color=THEME["bg_tertiary"], corner_radius=8, **kwargs)
        self.pack_propagate(False)
        
        date_str = tx['date'].strftime("%b %d") if tx['date'] else "—"
        type_color = THEME["green"] if tx['type'] == 'income' else (THEME["blue"] if tx['type'] == 'transfer' else THEME["red"])
        
        # Indicator strip
        strip = ctk.CTkFrame(self, width=4, fg_color=type_color, corner_radius=2)
        strip.pack(side="left", fill="y", padx=(8, 12), pady=8)

        # Main Info
        info = ctk.CTkFrame(self, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True, pady=10)
        ctk.CTkLabel(info, text=tx['description'] or "—", font=FONTS["body"], text_color=THEME["text_primary"],
                     anchor="w").pack(fill="x")
        is_overdue = tx.get('status') != 'paid' and tx['date'] and tx['date'].date() < datetime.now().date()
        date_color = THEME["red"] if is_overdue else THEME["text_tertiary"]
        date_display = f"⚠ {date_str} (Gecikib)" if is_overdue else date_str

        ctk.CTkLabel(info, text=date_display, font=FONTS["small"], text_color=date_color,
                     anchor="w").pack(fill="x")

        # Amount
        sign = "+" if tx['type'] == 'income' else ("-" if tx['type'] == 'expense' else "")
        ctk.CTkLabel(self, text=format_currency(tx['amount'], tx.get('currency', 'AZN'), sign),
                     font=FONTS["body"], text_color=type_color, anchor="e").pack(side="right", padx=(10, 16))

        # Make clickable if callback provided
        if on_click:
            for widget in [self, info, strip]:
                widget.bind("<Button-1>", lambda e: on_click(tx))
                widget.configure(cursor="hand2")
            self.bind("<Enter>", lambda e: self.configure(fg_color=THEME["border"]))
            self.bind("<Leave>", lambda e: self.configure(fg_color=THEME["bg_tertiary"]))


class PlannedMiniRow(ctk.CTkFrame):
    def __init__(self, master, p, on_pay, **kwargs):
        super().__init__(master, fg_color=THEME["bg_tertiary"], corner_radius=8, **kwargs)
        self.pack_propagate(False)
        
        date_str = p.due_date.strftime("%b %d") if p.due_date else "—"
        is_overdue = p.due_date and p.due_date < datetime.now() and p.status != "paid"
        
        status_color = THEME["red"] if is_overdue else THEME["blue"]
        status_text = "⚠ Overdue" if is_overdue else "Upcoming"

        info = ctk.CTkFrame(self, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True, padx=16, pady=10)
        ctk.CTkLabel(info, text=p.description or "—", font=FONTS["body"], text_color=THEME["text_primary"],
                     anchor="w").pack(fill="x")
        
        cat_name = getattr(p, 'category_name', None) or "Uncategorized"
        ctk.CTkLabel(info, text=f"Due: {date_str}  •  {cat_name}", font=FONTS["small"], text_color=status_color,
                     anchor="w").pack(fill="x")

        amt = float(p.amount)
        if hasattr(p, 'edv_amount') and p.edv_amount:
            amt += float(p.edv_amount)

        amt_f = ctk.CTkFrame(self, fg_color="transparent")
        amt_f.pack(side="right", padx=(10, 8))

        ctk.CTkLabel(amt_f, text=format_currency(amt, p.currency), font=FONTS["body"],
                     text_color=THEME["text_primary"], anchor="e").pack(fill="x")
        
        if hasattr(p, 'edv_amount') and p.edv_amount:
             ctk.CTkLabel(amt_f, text="+ VAT included", font=FONTS["small"],
                          text_color=THEME["text_tertiary"], anchor="e").pack(fill="x")
        
        if p.status != "paid":
            btn = ctk.CTkButton(self, text="Pay", width=50, height=28, corner_radius=6,
                                fg_color=THEME["green"], hover_color=THEME["green_dark"],
                                text_color="white", font=FONTS["small"], command=lambda: on_pay(p.id))
            btn.pack(side="right", padx=(0, 16))
