import customtkinter as ctk
import tkinter as tk
from ui.theme import THEME, FONTS


class KPICard(ctk.CTkFrame):
    """
    Premium KPI card with:
      - Colored top accent bar
      - Label + large value
      - Optional delta badge (↑ green / ↓ red)
      - Smooth hover lift effect
      - Skeleton loading state
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
        self._is_loading = False
        self._pulse_step = 0
        self._accent_color = accent_color or THEME["blue"]

        # Colored top accent line
        ctk.CTkFrame(self, height=3, corner_radius=0,
                     fg_color=self._accent_color).pack(fill="x", side="top")

        self._body = ctk.CTkFrame(self, fg_color="transparent")
        self._body.pack(fill="both", expand=True, padx=16, pady=(10, 12))

        # Title row
        self.lbl_title = ctk.CTkLabel(
            self._body, text=label.upper(),
            font=("Inter", 10, "bold"),
            text_color=THEME["text_tertiary"])
        self.lbl_title.pack(anchor="w")

        # Value
        val_color = value_color or THEME["text_primary"]
        self.lbl_value = ctk.CTkLabel(
            self._body, text=value,
            font=("Inter", 20, "bold"),
            text_color=val_color)
        self.lbl_value.pack(anchor="w", pady=(4, 0))

        # Skeleton placeholder (hidden by default)
        self._skeleton = ctk.CTkFrame(
            self._body, height=22, corner_radius=6,
            fg_color=THEME["bg_tertiary"])

        # Delta badge
        if delta_text:
            delta_color = THEME["green"] if delta_positive else THEME["red"]
            delta_bg    = THEME["green_light"] if delta_positive else THEME["red_light"]
            arrow       = "▲" if delta_positive else "▼"
            self.lbl_delta = ctk.CTkLabel(
                self._body, text=f"{arrow} {delta_text}",
                font=("Inter", 10, "normal"),
                text_color=delta_color,
                fg_color=delta_bg,
                corner_radius=4, padx=5, pady=2)
            self.lbl_delta.pack(anchor="w", pady=(5, 0))

        # Hover micro-animation (subtle border highlight)
        self.bind("<Enter>", lambda e: self.configure(border_color=THEME["blue"]))
        self.bind("<Leave>", lambda e: self.configure(border_color=THEME["border"]))
        
        # Also bind children to pass hover events
        for w in [self._body, self.lbl_title, self.lbl_value]:
            w.bind("<Enter>", lambda e: self.configure(border_color=THEME["blue"]))
            w.bind("<Leave>", lambda e: self.configure(border_color=THEME["border"]))

    # ── Public API ────────────────────────────────────────────────────────────

    def set_loading(self):
        """Show skeleton loading state."""
        self._is_loading = True
        self.lbl_value.pack_forget()
        if hasattr(self, 'lbl_delta'):
            self.lbl_delta.pack_forget()
        self._skeleton.pack(anchor="w", fill="x", pady=(6, 0))
        self._pulse_step = 0
        self._pulse()

    def set_loaded(self):
        """Return to normal value display."""
        self._is_loading = False
        self._skeleton.pack_forget()
        self.lbl_value.pack(anchor="w", pady=(4, 0))
        if hasattr(self, 'lbl_delta'):
            self.lbl_delta.pack(anchor="w", pady=(5, 0))

    def _pulse(self):
        """Animate skeleton with a subtle pulse effect."""
        if not self._is_loading:
            return
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return

        self._pulse_step = (self._pulse_step + 1) % 20
        if self._pulse_step < 10:
            self._skeleton.configure(fg_color=THEME["bg_tertiary"])
        else:
            self._skeleton.configure(fg_color=THEME["border"])
        self.after(60, self._pulse)

    def update_data(self, value, delta_text=None,
                    delta_positive=True, value_color=None):
        if self._is_loading:
            self.set_loaded()
            
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