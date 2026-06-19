import customtkinter as ctk
from datetime import datetime, timedelta
from ui.theme import THEME, FONTS
from ui.components.modal import Modal
from ui.components.toast import Toast


QUICK_RANGES = [
    ("Today",      lambda: _range(0, 0)),
    ("Yesterday",  lambda: _range(1, 1)),
    ("Last 7 Days",lambda: _range(6, 0)),
    ("Last 30 Days",lambda: _range(29, 0)),
    ("This Week",  lambda: _this_week()),
    ("This Month", lambda: _this_month()),
]


def _range(days_back_from, days_back_to):
    now = datetime.now()
    d_from = (now - timedelta(days=days_back_from)).replace(
        hour=0, minute=0, second=0, microsecond=0)
    d_to = (now - timedelta(days=days_back_to)).replace(
        hour=23, minute=59, second=59, microsecond=999999)
    return d_from, d_to


def _this_week():
    now = datetime.now()
    start = now - timedelta(days=now.weekday())
    return start.replace(hour=0, minute=0, second=0, microsecond=0), \
           now.replace(hour=23, minute=59, second=59, microsecond=999999)


def _this_month():
    now = datetime.now()
    return datetime(now.year, now.month, 1), \
           now.replace(hour=23, minute=59, second=59, microsecond=999999)


class CustomDateModal(Modal):
    def __init__(self, master, on_success, **kwargs):
        super().__init__(master, title="Custom Date Range", width=440, height=420, **kwargs)
        self.on_success = on_success
        self._build_ui()

    def _build_ui(self):
        # ── Quick picks ───────────────────────────────────────────────────────
        quick_header = ctk.CTkLabel(
            self.content_frame, text="Quick Select",
            font=("Inter", 11, "bold"), text_color=THEME["text_tertiary"])
        quick_header.pack(anchor="w", pady=(0, 8))

        chip_row1 = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        chip_row1.pack(fill="x", pady=(0, 4))
        chip_row2 = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        chip_row2.pack(fill="x", pady=(0, 16))

        for i, (label, fn) in enumerate(QUICK_RANGES):
            row = chip_row1 if i < 3 else chip_row2
            chip = ctk.CTkButton(
                row, text=label, height=30, font=FONTS["small"],
                corner_radius=15,
                fg_color=THEME["bg_tertiary"],
                hover_color=THEME["border"],
                text_color=THEME["text_secondary"],
                command=lambda f=fn: self._apply_quick(f))
            chip.pack(side="left", padx=(0, 6))

        # ── Divider ───────────────────────────────────────────────────────────
        ctk.CTkFrame(self.content_frame, height=1,
                     fg_color=THEME["border"]).pack(fill="x", pady=(0, 16))

        # ── Manual input ──────────────────────────────────────────────────────
        ctk.CTkLabel(
            self.content_frame, text="Or enter a custom range",
            font=("Inter", 11, "bold"), text_color=THEME["text_tertiary"]).pack(anchor="w", pady=(0, 12))

        grid = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        grid.pack(fill="x")
        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)

        # From field
        from_f = ctk.CTkFrame(grid, fg_color=THEME["bg_secondary"],
                               corner_radius=8, border_width=1,
                               border_color=THEME["border"])
        from_f.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkLabel(from_f, text="FROM", font=("Inter", 9, "bold"),
                     text_color=THEME["text_tertiary"]).pack(anchor="w", padx=12, pady=(8, 0))
        self.entry_from = ctk.CTkEntry(
            from_f, placeholder_text="YYYY-MM-DD", font=FONTS["body"],
            border_width=0, fg_color="transparent")
        self.entry_from.pack(fill="x", padx=8, pady=(2, 10))

        # To field
        to_f = ctk.CTkFrame(grid, fg_color=THEME["bg_secondary"],
                             corner_radius=8, border_width=1,
                             border_color=THEME["border"])
        to_f.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        ctk.CTkLabel(to_f, text="TO", font=("Inter", 9, "bold"),
                     text_color=THEME["text_tertiary"]).pack(anchor="w", padx=12, pady=(8, 0))
        self.entry_to = ctk.CTkEntry(
            to_f, placeholder_text="YYYY-MM-DD", font=FONTS["body"],
            border_width=0, fg_color="transparent")
        self.entry_to.pack(fill="x", padx=8, pady=(2, 10))

        # Pre-fill today
        today_str = datetime.now().strftime("%Y-%m-%d")
        self.entry_from.insert(0, today_str)
        self.entry_to.insert(0, today_str)

        # ── Footer ────────────────────────────────────────────────────────────
        footer = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        footer.pack(fill="x", pady=(20, 0))

        ctk.CTkButton(
            footer, text="Cancel", height=40, corner_radius=8,
            fg_color=THEME["bg_secondary"], hover_color=THEME["border"],
            text_color=THEME["text_primary"], font=FONTS["body"],
            border_width=1, border_color=THEME["border"],
            command=self.destroy).pack(side="left", expand=True, fill="x", padx=(0, 6))

        self.submit_btn = ctk.CTkButton(
            footer, text="Apply Range  →", height=40, corner_radius=8,
            fg_color=THEME["blue"], hover_color="#1a5ce0",
            text_color="white", font=("Inter", 13, "bold"),
            command=self._submit)
        self.submit_btn.pack(side="right", expand=True, fill="x", padx=(6, 0))

        # Focus on from entry
        self.after(100, self.entry_from.focus_set)

    def _apply_quick(self, fn):
        d_from, d_to = fn()
        self.entry_from.delete(0, "end")
        self.entry_to.delete(0, "end")
        self.entry_from.insert(0, d_from.strftime("%Y-%m-%d"))
        self.entry_to.insert(0, d_to.strftime("%Y-%m-%d"))
        # Auto-submit
        self._submit()

    def _submit(self):
        date_from_str = self.entry_from.get().strip()
        date_to_str   = self.entry_to.get().strip()
        try:
            date_from = datetime.strptime(date_from_str, "%Y-%m-%d")
            date_to_base = datetime.strptime(date_to_str, "%Y-%m-%d")
            date_to = date_to_base.replace(
                hour=23, minute=59, second=59, microsecond=999999)
            if date_from > date_to:
                raise ValueError("'From Date' cannot be after 'To Date'")
            self.on_success(date_from, date_to)
            self.destroy()
        except ValueError as e:
            if "does not match format" in str(e):
                Toast(self, "Invalid date format. Please use YYYY-MM-DD.", type="error")
            else:
                Toast(self, str(e), type="error")
