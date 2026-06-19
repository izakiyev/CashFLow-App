import customtkinter as ctk
from ui.theme import THEME, DARK, FONTS


# Icon map for toast types
_ICONS = {
    "success": "✓",
    "error":   "✕",
    "info":    "ℹ",
    "warning": "⚠",
}

_COLORS = {
    "success": ("#12b76a", "#053321"),   # (icon_bg, body_bg)
    "error":   ("#f04438", "#4a1215"),
    "info":    ("#2970ff", "#0a1f4d"),
    "warning": ("#f79009", "#4a2c04"),
}


class Toast(ctk.CTkToplevel):
    """
    Premium slide-in toast notification.
    Shows icon badge + message, auto-dismisses after `duration` ms.
    """

    def __init__(self, master, message, type="success", duration=3500, **kwargs):
        super().__init__(master, **kwargs)
        self.duration = duration

        icon_color, body_color = _COLORS.get(type, _COLORS["info"])
        icon_char = _ICONS.get(type, "ℹ")

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(fg_color=body_color)

        # ── Layout ────────────────────────────────────────────────────────────
        outer = ctk.CTkFrame(self, fg_color=body_color, corner_radius=10)
        outer.pack(padx=0, pady=0)

        # Colored icon badge
        badge = ctk.CTkFrame(outer, width=36, height=36, corner_radius=18,
                              fg_color=icon_color)
        badge.pack(side="left", padx=(14, 10), pady=14)
        badge.pack_propagate(False)
        ctk.CTkLabel(badge, text=icon_char, font=("Inter", 14, "bold"),
                     text_color="white").place(relx=0.5, rely=0.5, anchor="center")

        # Message
        ctk.CTkLabel(outer, text=message, font=FONTS["body"],
                     text_color="#ffffff", wraplength=280,
                     justify="left").pack(side="left", pady=14, padx=(0, 16))

        # Position: bottom-right corner
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w  = self.winfo_width()
        h  = self.winfo_height()
        self.geometry(f"+{sw - w - 24}+{sh - h - 72}")

        # Fade-out placeholder (just auto-destroy for now)
        self.after(self.duration, self._dismiss)

    def _dismiss(self):
        try:
            if self.winfo_exists():
                self.destroy()
        except Exception:
            pass
