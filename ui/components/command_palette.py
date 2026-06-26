import customtkinter as ctk
from ui.theme import THEME, FONTS


# ── Command definitions ───────────────────────────────────────────────────────
COMMANDS = [
    {"label": "Dashboard",           "page": "dashboard",    "icon": "📊", "shortcut": "Ctrl+D"},
    {"label": "Cash Flow",           "page": "cashflow",     "icon": "🌊", "shortcut": ""},
    {"label": "Transactions",        "page": "transactions", "icon": "💳", "shortcut": "Ctrl+T"},
    {"label": "Accounts",            "page": "accounts",     "icon": "🏦", "shortcut": ""},
    {"label": "Projects",            "page": "projects",     "icon": "📁", "shortcut": ""},
    {"label": "Budgets",             "page": "budgets",      "icon": "📊", "shortcut": ""},
    {"label": "Reports",             "page": "reports",      "icon": "📈", "shortcut": "Ctrl+R"},
    {"label": "Categories",          "page": "categories",   "icon": "🏷️", "shortcut": ""},
    {"label": "Settings",            "page": "settings",     "icon": "⚙️", "shortcut": ""},
    {"label": "AI Assistant",        "page": "ai",           "icon": "🤖", "shortcut": ""},
    {"label": "New Transaction",     "action": "new_tx",     "icon": "➕", "shortcut": "Ctrl+N"},
    {"label": "Planned Payments",    "page": "planned",      "icon": "📅", "shortcut": ""},
]


class CommandPaletteItem(ctk.CTkFrame):
    """A single item row in the command palette results."""

    def __init__(self, master, cmd, on_select, is_selected=False, **kwargs):
        super().__init__(master, fg_color=THEME["blue"] if is_selected else "transparent",
                         corner_radius=8, height=40, **kwargs)
        self.pack_propagate(False)
        self.cmd = cmd
        self._on_select = on_select
        self._is_selected = is_selected

        # Icon
        ctk.CTkLabel(self, text=cmd["icon"], font=("Segoe UI Emoji", 14),
                     text_color="white" if is_selected else THEME["text_secondary"],
                     width=30).pack(side="left", padx=(12, 4))

        # Label
        ctk.CTkLabel(self, text=cmd["label"], font=FONTS["body"],
                     text_color="white" if is_selected else THEME["text_primary"],
                     anchor="w").pack(side="left", fill="x", expand=True)

        # Shortcut badge
        if cmd.get("shortcut"):
            ctk.CTkLabel(self, text=cmd["shortcut"], font=("Inter", 9),
                         text_color=THEME["text_tertiary"],
                         fg_color=THEME["bg_tertiary"], corner_radius=4,
                         padx=6, pady=2).pack(side="right", padx=(0, 12))

        # Category badge
        if cmd.get("page"):
            ctk.CTkLabel(self, text="Navigate", font=("Inter", 9),
                         text_color=THEME["text_tertiary"]).pack(side="right", padx=(0, 8))
        elif cmd.get("action"):
            ctk.CTkLabel(self, text="Action", font=("Inter", 9),
                         text_color=THEME["green"]).pack(side="right", padx=(0, 8))

        # Click binding
        for w in self.winfo_children():
            w.bind("<Button-1>", lambda e: self._on_select(self.cmd))
        self.bind("<Button-1>", lambda e: self._on_select(self.cmd))

        # Hover
        if not is_selected:
            for w in [self] + list(self.winfo_children()):
                w.bind("<Enter>", lambda e: self.configure(fg_color=THEME["bg_tertiary"]))
                w.bind("<Leave>", lambda e: self.configure(fg_color="transparent"))
                w.configure(cursor="hand2")


class CommandPalette(ctk.CTkToplevel):
    """
    VS Code-style command palette (Ctrl+K).
    Provides quick navigation and actions via fuzzy search.
    """

    def __init__(self, master, nav_callback, action_callback=None, **kwargs):
        super().__init__(master, **kwargs)
        self.nav_callback = nav_callback
        self.action_callback = action_callback
        self._selected_index = 0
        self._filtered_commands = list(COMMANDS)

        # Window setup
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(fg_color=THEME["bg_primary"])

        width = 520
        height = 420

        # Center on screen
        self.update_idletasks()
        x = master.winfo_x() + (master.winfo_width() // 2) - (width // 2)
        y = master.winfo_y() + max(80, master.winfo_height() // 5)
        self.geometry(f"{width}x{height}+{x}+{y}")

        # ── Outer frame with border ──────────────────────────────────────────
        outer = ctk.CTkFrame(self, fg_color=THEME["bg_secondary"], corner_radius=12,
                              border_width=1, border_color=THEME["border"])
        outer.pack(fill="both", expand=True, padx=2, pady=2)

        # ── Search input ─────────────────────────────────────────────────────
        search_frame = ctk.CTkFrame(outer, fg_color="transparent")
        search_frame.pack(fill="x", padx=16, pady=(16, 0))

        ctk.CTkLabel(search_frame, text="🔍", font=("Segoe UI Emoji", 16),
                     text_color=THEME["text_tertiary"], width=28).pack(side="left")

        self._search_entry = ctk.CTkEntry(
            search_frame, placeholder_text="Type a command or search...",
            font=("Inter", 14), height=40, border_width=0,
            fg_color="transparent", text_color=THEME["text_primary"])
        self._search_entry.pack(side="left", fill="x", expand=True, padx=(4, 0))

        # ESC badge
        ctk.CTkLabel(search_frame, text="ESC", font=("Inter", 9, "bold"),
                     text_color=THEME["text_tertiary"],
                     fg_color=THEME["bg_tertiary"], corner_radius=4,
                     padx=6, pady=2).pack(side="right")

        # Divider
        ctk.CTkFrame(outer, height=1, fg_color=THEME["border"]).pack(fill="x", padx=12, pady=(8, 0))

        # ── Results area ─────────────────────────────────────────────────────
        self._results_frame = ctk.CTkScrollableFrame(
            outer, fg_color="transparent", corner_radius=0,
            scrollbar_button_color=THEME["bg_tertiary"],
            scrollbar_button_hover_color=THEME["border"])
        self._results_frame.pack(fill="both", expand=True, padx=8, pady=8)

        # ── Footer hint ──────────────────────────────────────────────────────
        footer = ctk.CTkFrame(outer, fg_color=THEME["bg_tertiary"], corner_radius=0, height=30)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)

        ctk.CTkLabel(footer, text="↑↓ Navigate    ↵ Select    Esc Close",
                     font=("Inter", 10), text_color=THEME["text_tertiary"]).pack(
            side="left", padx=16)

        # ── Bindings ─────────────────────────────────────────────────────────
        self._search_entry.bind("<KeyRelease>", self._on_search)
        self._search_entry.bind("<Up>", self._on_key_up)
        self._search_entry.bind("<Down>", self._on_key_down)
        self._search_entry.bind("<Return>", self._on_enter)
        self.bind("<Escape>", lambda e: self._close())
        self.bind("<FocusOut>", self._on_focus_out)

        # Initial render
        self._render_results()

        # Focus the search entry
        self.after(50, self._search_entry.focus_set)

    def _on_focus_out(self, event):
        """Close palette when clicking outside."""
        try:
            # Check if the focus went to a child widget
            focus_widget = self.focus_get()
            if focus_widget and str(focus_widget).startswith(str(self)):
                return
        except Exception:
            pass
        self.after(100, self._check_focus)

    def _check_focus(self):
        try:
            if not self.winfo_exists():
                return
            focus = self.focus_get()
            if focus is None or not str(focus).startswith(str(self)):
                self._close()
        except Exception:
            pass

    def _on_search(self, event=None):
        if event and event.keysym in ("Up", "Down", "Return", "Escape"):
            return

        query = self._search_entry.get().strip().lower()
        if not query:
            self._filtered_commands = list(COMMANDS)
        else:
            self._filtered_commands = [
                cmd for cmd in COMMANDS
                if query in cmd["label"].lower()
            ]
        self._selected_index = 0
        self._render_results()

    def _on_key_up(self, event):
        if self._selected_index > 0:
            self._selected_index -= 1
            self._render_results()
        return "break"

    def _on_key_down(self, event):
        if self._selected_index < len(self._filtered_commands) - 1:
            self._selected_index += 1
            self._render_results()
        return "break"

    def _on_enter(self, event):
        if self._filtered_commands:
            self._select_command(self._filtered_commands[self._selected_index])
        return "break"

    def _render_results(self):
        for w in self._results_frame.winfo_children():
            w.destroy()

        if not self._filtered_commands:
            ctk.CTkLabel(self._results_frame, text="No matching commands",
                         font=FONTS["body"], text_color=THEME["text_tertiary"]).pack(
                pady=20)
            return

        for i, cmd in enumerate(self._filtered_commands):
            item = CommandPaletteItem(
                self._results_frame, cmd,
                on_select=self._select_command,
                is_selected=(i == self._selected_index))
            item.pack(fill="x", pady=1)

    def _select_command(self, cmd):
        self._close()
        if cmd.get("page"):
            self.nav_callback(cmd["page"])
        elif cmd.get("action") and self.action_callback:
            self.action_callback(cmd["action"])

    def _close(self):
        try:
            if self.winfo_exists():
                self.destroy()
        except Exception:
            pass
