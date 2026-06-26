import customtkinter as ctk
from ui.theme import THEME, FONTS


class EmptyState(ctk.CTkFrame):
    """
    A centered empty-state placeholder shown when a list has no data.
    Shows a large icon, a title, a subtitle message, and an optional action button.
    """
    def __init__(self, master, icon="📭", title="Nothing here yet",
                 subtitle="There are no items to display.",
                 action_text=None, action_callback=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.place(relx=0.5, rely=0.5, anchor="center")

        # Icon with subtle background circle
        icon_bg = ctk.CTkFrame(inner, width=80, height=80, corner_radius=40,
                                fg_color=THEME["bg_tertiary"])
        icon_bg.pack(pady=(0, 16))
        icon_bg.pack_propagate(False)
        ctk.CTkLabel(icon_bg, text=icon,
                     font=("Segoe UI Emoji", 32),
                     text_color=THEME["text_tertiary"]).place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(inner, text=title,
                     font=("Inter", 16, "bold"),
                     text_color=THEME["text_secondary"]).pack()

        ctk.CTkLabel(inner, text=subtitle,
                     font=FONTS["body"],
                     text_color=THEME["text_tertiary"],
                     wraplength=300, justify="center").pack(pady=(6, 0))

        # Optional action button
        if action_text and action_callback:
            ctk.CTkButton(
                inner, text=action_text, height=32, corner_radius=8,
                font=FONTS["body"],
                fg_color=THEME["blue"], hover_color=THEME["blue_light"],
                text_color="white",
                command=action_callback).pack(pady=(16, 0))
