import customtkinter as ctk
from ui.theme import THEME, FONTS


class LoadingState(ctk.CTkFrame):
    """
    A centered loading-state placeholder shown when fetching data.
    """
    def __init__(self, master, text="Loading data...", **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(inner, text="⏳",
                     font=("Segoe UI Emoji", 32),
                     text_color=THEME["text_tertiary"]).pack(pady=(0, 8))

        ctk.CTkLabel(inner, text=text,
                     font=FONTS["body"],
                     text_color=THEME["text_secondary"]).pack()
