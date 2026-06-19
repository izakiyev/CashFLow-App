import customtkinter as ctk
from ui.theme import THEME, FONTS


class Topbar(ctk.CTkFrame):
    """
    Premium top navigation bar shown on every page.
    Features:
      - Bold page title with optional subtitle / breadcrumb
      - Subtle bottom border separator
      - Right-aligned action buttons (primary + secondary)
      - Keyboard shortcut badge support
    """

    def __init__(self, master, title="Dashboard", subtitle=None, **kwargs):
        super().__init__(
            master, height=64, corner_radius=0,
            fg_color=THEME["bg_secondary"],
            border_width=0,
            **kwargs
        )
        self.pack_propagate(False)

        # Subtle bottom border via a 1-px frame at the bottom
        self._border = ctk.CTkFrame(self, height=1, fg_color=THEME["border"],
                                     corner_radius=0)
        self._border.pack(side="bottom", fill="x")

        # ── Left: title + optional subtitle ──────────────────────────────────
        left = ctk.CTkFrame(self, fg_color="transparent")
        left.pack(side="left", padx=(24, 0), fill="y")

        self.title_label = ctk.CTkLabel(
            left, text=title,
            font=("Inter", 18, "bold"),
            text_color=THEME["text_primary"])
        self.title_label.pack(side="left", pady=(0, 0))

        if subtitle:
            ctk.CTkLabel(
                left, text=f"  /  {subtitle}",
                font=FONTS["body"],
                text_color=THEME["text_tertiary"]).pack(side="left", pady=(2, 0))

        # ── Right: actions ────────────────────────────────────────────────────
        self.actions_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.actions_frame.pack(side="right", padx=(0, 24), fill="y")

    # ── Public API ────────────────────────────────────────────────────────────

    def add_action(self, text, command, primary=False, shortcut=None):
        """Add a button to the right side of the topbar.

        Args:
            text:      Button label.
            command:   Callback.
            primary:   If True, renders as a green filled button.
            shortcut:  Optional keyboard shortcut string shown as a muted badge
                       (e.g. "Ctrl+N").
        """
        if primary:
            fg    = THEME["green"]
            hover = THEME["green_dark"]
            tc    = "white"
            bw    = 0
            bc    = THEME["green"]   # hidden when border_width=0
        else:
            fg    = "transparent"
            hover = THEME["bg_tertiary"]
            tc    = THEME["text_secondary"]
            bw    = 1
            bc    = THEME["border"]

        wrapper = ctk.CTkFrame(self.actions_frame, fg_color="transparent")
        wrapper.pack(side="left", padx=(6, 0), fill="y", pady=14)

        btn = ctk.CTkButton(
            wrapper, text=text,
            font=("Inter", 13, "bold") if primary else FONTS["body"],
            fg_color=fg, hover_color=hover,
            text_color=tc, border_width=bw, border_color=bc,
            height=36, corner_radius=8,
            command=command)
        btn.pack(side="left")

        if shortcut:
            ctk.CTkLabel(
                wrapper, text=shortcut,
                font=("Inter", 10, "normal"),
                text_color=THEME["text_tertiary"],
                fg_color=THEME["bg_tertiary"],
                corner_radius=4, padx=5, pady=2
            ).pack(side="left", padx=(4, 0))

        return btn

    def set_title(self, title):
        self.title_label.configure(text=title)

    def clear_actions(self):
        for widget in self.actions_frame.winfo_children():
            widget.destroy()
