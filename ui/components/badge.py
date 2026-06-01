import customtkinter as ctk
from ui.theme import THEME, FONTS

class Badge(ctk.CTkFrame):
    def __init__(self, master, text, color=None, text_color=None, **kwargs):
        c = color if color is not None else THEME["green"]
        tc = text_color if text_color is not None else THEME["text_primary"]
        super().__init__(master, corner_radius=10, fg_color=c, **kwargs)
        self.lbl = ctk.CTkLabel(self, text=text, font=FONTS["small"], text_color=tc)
        self.lbl.pack(padx=8, pady=2)
