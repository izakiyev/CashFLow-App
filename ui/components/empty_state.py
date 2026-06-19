import customtkinter as ctk
from ui.theme import THEME, FONTS


class EmptyState(ctk.CTkFrame):
    """
    A centered empty-state placeholder shown when a list has no data.
    Shows a large icon, a title, and a subtitle message.
    """
    def __init__(self, master, icon="📭", title="Nothing here yet",
                 subtitle="There are no items to display.", **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(inner, text=icon,
                     font=("Segoe UI Emoji", 48),
                     text_color=THEME["text_tertiary"]).pack(pady=(0, 12))

        ctk.CTkLabel(inner, text=title,
                     font=("Inter", 16, "bold"),
                     text_color=THEME["text_secondary"]).pack()

        ctk.CTkLabel(inner, text=subtitle,
                     font=FONTS["body"],
                     text_color=THEME["text_tertiary"],
                     wraplength=300, justify="center").pack(pady=(6, 0))
