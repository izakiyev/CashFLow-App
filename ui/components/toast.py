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
    Premium slide-in toast notification with stacking support.
    Shows icon badge + message, auto-dismisses after `duration` ms.
    Supports optional action button (e.g. "Undo").
    """

    # Class-level tracking for stacking
    _active_toasts: list = []
    _TOAST_HEIGHT = 64
    _TOAST_GAP = 8
    _SLIDE_DURATION_MS = 200
    _SLIDE_STEPS = 12

    def __init__(self, master, message, type="success", duration=3500,
                 action_text=None, action_callback=None, **kwargs):
        super().__init__(master, **kwargs)
        self.duration = duration
        self._action_callback = action_callback

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
                     text_color="#ffffff", wraplength=260,
                     justify="left").pack(side="left", pady=14, padx=(0, 10))

        # Optional action button (e.g., "Undo")
        if action_text and action_callback:
            action_btn = ctk.CTkButton(
                outer, text=action_text, width=60, height=28,
                font=("Inter", 11, "bold"), corner_radius=6,
                fg_color="rgba(255,255,255,0.15)",
                hover_color="rgba(255,255,255,0.25)",
                text_color="white",
                command=self._on_action)
            action_btn.pack(side="right", padx=(0, 14), pady=14)

        # Close button
        close_btn = ctk.CTkButton(
            outer, text="✕", width=24, height=24, corner_radius=12,
            fg_color="transparent", hover_color="rgba(255,255,255,0.1)",
            text_color="#ffffff80", font=("Inter", 10, "bold"),
            command=self._dismiss)
        close_btn.pack(side="right", padx=(0, 8), pady=14)

        # Register in the stack
        Toast._active_toasts.append(self)

        # Position: slide in from right edge
        self.update_idletasks()
        self._sw = self.winfo_screenwidth()
        self._sh = self.winfo_screenheight()
        self._w = self.winfo_width()
        self._h = self.winfo_height()

        # Calculate stacked Y position
        stack_index = len(Toast._active_toasts) - 1
        self._target_y = self._sh - self._h - 24 - (stack_index * (self._TOAST_HEIGHT + self._TOAST_GAP))
        self._target_x = self._sw - self._w - 24

        # Start off-screen to the right
        self._current_x = self._sw + 10
        self.geometry(f"+{self._current_x}+{self._target_y}")

        # Animate slide-in
        self._slide_step = 0
        self._slide_in()

        # Auto-dismiss timer
        self._dismiss_timer = self.after(self.duration, self._dismiss)

    def _slide_in(self):
        if self._slide_step >= self._SLIDE_STEPS:
            return
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return

        self._slide_step += 1
        progress = self._slide_step / self._SLIDE_STEPS
        # Ease-out cubic
        eased = 1 - (1 - progress) ** 3
        current_x = int(self._sw + 10 - (self._sw + 10 - self._target_x) * eased)
        self.geometry(f"+{current_x}+{self._target_y}")
        self.after(self._SLIDE_DURATION_MS // self._SLIDE_STEPS, self._slide_in)

    def _on_action(self):
        if self._action_callback:
            self._action_callback()
        self._dismiss()

    def _dismiss(self):
        try:
            if hasattr(self, '_dismiss_timer'):
                self.after_cancel(self._dismiss_timer)
        except Exception:
            pass

        # Remove from stack
        if self in Toast._active_toasts:
            Toast._active_toasts.remove(self)

        # Reposition remaining toasts
        for i, toast in enumerate(Toast._active_toasts):
            try:
                if toast.winfo_exists():
                    new_y = toast._sh - toast._h - 24 - (i * (self._TOAST_HEIGHT + self._TOAST_GAP))
                    toast.geometry(f"+{toast._target_x}+{new_y}")
                    toast._target_y = new_y
            except Exception:
                pass

        try:
            if self.winfo_exists():
                self.destroy()
        except Exception:
            pass
