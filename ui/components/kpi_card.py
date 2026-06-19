import customtkinter as ctk
from ui.theme import THEME, FONTS


class KPICard(ctk.CTkFrame):
    """
    Premium KPI card with:
      - Colored top accent bar
      - Label + large value
      - Optional delta badge (↑ green / ↓ red)
      - Smooth hover lift effect
    """

    def __init__(self, master, label, value,
                 delta_text=None, delta_positive=True,
                 value_color=None, accent_color=None, **kwargs):

        super().__init__(
            master, height=108, corner_radius=10,
            fg_color=THEME["bg_secondary"],
            border_width=1, border_color=THEME["border"],
            **kwargs)
        self.pack_propagate(False)

        # Colored top accent line
        accent = accent_color or THEME["blue"]
        ctk.CTkFrame(self, height=3, corner_radius=0,
                     fg_color=accent).pack(fill="x", side="top")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=(10, 12))

        # Title row
        self.lbl_title = ctk.CTkLabel(
            body, text=label.upper(),
            font=("Inter", 10, "bold"),
            text_color=THEME["text_tertiary"])
        self.lbl_title.pack(anchor="w")

        # Value
        val_color = value_color or THEME["text_primary"]
        self.lbl_value = ctk.CTkLabel(
            body, text=value,
            font=("Inter", 20, "bold"),
            text_color=val_color)
        self.lbl_value.pack(anchor="w", pady=(4, 0))

        # Delta badge
        if delta_text:
            delta_color = THEME["green"] if delta_positive else THEME["red"]
            delta_bg    = THEME["green_light"] if delta_positive else THEME["red_light"]
            arrow       = "▲" if delta_positive else "▼"
            self.lbl_delta = ctk.CTkLabel(
                body, text=f"{arrow} {delta_text}",
                font=("Inter", 10, "normal"),
                text_color=delta_color,
                fg_color=delta_bg,
                corner_radius=4, padx=5, pady=2)
            self.lbl_delta.pack(anchor="w", pady=(5, 0))

        # Hover micro-animation (subtle border highlight)
        self.bind("<Enter>", lambda e: self.configure(border_color=THEME["blue"]))
        self.bind("<Leave>", lambda e: self.configure(border_color=THEME["border"]))

    # ── Public API ────────────────────────────────────────────────────────────

    def update_data(self, value, delta_text=None,
                    delta_positive=True, value_color=None):
        self.lbl_value.configure(text=value)
        if value_color:
            self.lbl_value.configure(text_color=value_color)
        if hasattr(self, "lbl_delta") and delta_text:
            delta_color = THEME["green"] if delta_positive else THEME["red"]
            delta_bg    = THEME["green_light"] if delta_positive else THEME["red_light"]
            arrow       = "▲" if delta_positive else "▼"
            self.lbl_delta.configure(
                text=f"{arrow} {delta_text}",
                text_color=delta_color,
                fg_color=delta_bg)