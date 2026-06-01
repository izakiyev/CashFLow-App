import customtkinter as ctk
from ui.theme import THEME, FONTS

class KPICard(ctk.CTkFrame):
    def __init__(self, master, label, value, delta_text=None, delta_positive=True, **kwargs):
        super().__init__(master, height=100, corner_radius=8,
                         fg_color=THEME["bg_secondary"], border_width=1,
                         border_color=THEME["border"], **kwargs)
        self.pack_propagate(False)

        self.lbl_title = ctk.CTkLabel(self, text=label, font=FONTS["subheading"], text_color=THEME["text_secondary"])
        self.lbl_title.pack(anchor="w", padx=15, pady=(15, 0))

        self.lbl_value = ctk.CTkLabel(self, text=value, font=FONTS["title"], text_color=THEME["text_primary"])
        self.lbl_value.pack(anchor="w", padx=15, pady=5)

        if delta_text:
            delta_color = THEME["green"] if delta_positive else THEME["red"]
            self.lbl_delta = ctk.CTkLabel(self, text=delta_text, font=FONTS["small"], text_color=delta_color)
            self.lbl_delta.pack(anchor="w", padx=15, pady=(0, 10))

    def update_data(self, value, delta_text=None, delta_positive=True):
        self.lbl_value.configure(text=value)
        if hasattr(self, 'lbl_delta') and delta_text:
            delta_color = THEME["green"] if delta_positive else THEME["red"]
            self.lbl_delta.configure(text=delta_text, text_color=delta_color)