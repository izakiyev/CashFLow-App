import customtkinter as ctk
from ui.theme import THEME, FONTS

# Status → (label, fg_color, bg_color)
STATUS_STYLES = {
    "paid":           ("✓  Paid",           THEME["green"],  THEME["green_light"]),
    "confirmed":      ("●  Confirmed",       THEME["blue"],   THEME["blue_light"]),
    "pending":        ("⏳  Pending",         THEME["amber"],  THEME["amber_light"]),
    "qaime gözleyir": ("📄  Awaiting Invoice", "#9b59b6",      "#e8d5f5"),
    "cancelled":      ("✕  Cancelled",        THEME["red"],    THEME["red_light"]),
}

TYPE_STYLES = {
    "income":   ("↑  Income",   THEME["green"], THEME["green_light"]),
    "expense":  ("↓  Expense",  THEME["red"],   THEME["red_light"]),
    "transfer": ("⇄  Transfer", THEME["blue"],  THEME["blue_light"]),
}


class Badge(ctk.CTkLabel):
    """
    A pill-shaped label badge.
    Automatically looks up styling for known status/type values.
    Falls back to provided color args.
    """
    def __init__(self, master, text, color=None, bg_color=None, **kwargs):
        # Normalize lookup key
        key = str(text).lower().strip()

        if key in STATUS_STYLES:
            label, fg, bg = STATUS_STYLES[key]
        elif key in TYPE_STYLES:
            label, fg, bg = TYPE_STYLES[key]
        else:
            label = text
            fg    = color  or THEME["text_secondary"]
            bg    = bg_color or THEME["bg_tertiary"]

        super().__init__(
            master,
            text=label,
            font=("Inter", 10, "bold"),
            text_color=fg,
            fg_color=bg,
            corner_radius=6,
            **kwargs
        )
        # Internal pack padding via configure
        self.configure(padx=8, pady=3)
