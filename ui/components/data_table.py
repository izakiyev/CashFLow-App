import customtkinter as ctk
from ui.theme import THEME, FONTS
from ui.components.empty_state import EmptyState


class DataTable(ctk.CTkScrollableFrame):
    """
    Premium data table with:
      - Bold UPPERCASE column headers with bottom border
      - Alternating subtle row shading
      - Per-row hover highlight
      - Click-to-edit support
      - Empty state message
    """

    def __init__(self, master, columns, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.columns = columns
        self.rows    = []
        self._build_headers()
        # Configure column weights once
        for i in range(len(columns)):
            self.grid_columnconfigure(i, weight=1)

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_headers(self):
        for col_idx, col_name in enumerate(self.columns):
            ctk.CTkLabel(
                self, text=col_name.upper(),
                font=("Inter", 10, "bold"),
                text_color=THEME["text_tertiary"]
            ).grid(row=0, column=col_idx, sticky="w", padx=(12, 8), pady=(10, 8))

        # Full-width divider
        sep = ctk.CTkFrame(self, height=1, fg_color=THEME["border"])
        sep.grid(row=1, column=0, columnspan=len(self.columns), sticky="ew", pady=0)

    # ── Rows ──────────────────────────────────────────────────────────────────

    def add_row(self, row_data, on_click=None, color=None):
        row_idx   = len(self.rows) + 2
        # Very subtle zebra shading
        alt_bg    = THEME["bg_secondary"] if row_idx % 2 == 0 else "transparent"
        text_color = color if color else THEME["text_primary"]

        row_frame = ctk.CTkFrame(self, fg_color=alt_bg, corner_radius=6)
        row_frame.grid(row=row_idx, column=0, columnspan=len(self.columns),
                       sticky="ew", padx=2, pady=1)

        for col_idx, val in enumerate(row_data):
            row_frame.grid_columnconfigure(col_idx, weight=1)
            if callable(val):
                widget = val(row_frame)
                widget.grid(row=0, column=col_idx, sticky="w", padx=(12, 8), pady=8)
            elif isinstance(val, ctk.CTkBaseClass):
                val.grid(row=0, column=col_idx, sticky="w", padx=(12, 8), pady=8)
            else:
                col_name   = self.columns[col_idx].lower()
                wraplength = 280 if "description" in col_name or "name" in col_name else 0
                lbl = ctk.CTkLabel(
                    row_frame, text=str(val),
                    font=FONTS["body"], text_color=text_color,
                    wraplength=wraplength, justify="left")
                lbl.grid(row=0, column=col_idx, sticky="w", padx=(12, 8), pady=8)
                if on_click:
                    lbl.bind("<Button-1>", lambda e, d=row_data: on_click(d))

        # Hover effect
        def _enter(e, f=row_frame):
            f.configure(fg_color=THEME["bg_tertiary"])
        def _leave(e, f=row_frame, bg=alt_bg):
            f.configure(fg_color=bg)

        row_frame.bind("<Enter>", _enter)
        row_frame.bind("<Leave>", _leave)
        if on_click:
            row_frame.bind("<Button-1>", lambda e: on_click(row_data))
            row_frame.configure(cursor="hand2")

        self.rows.append(row_frame)

    # ── Utilities ─────────────────────────────────────────────────────────────

    def clear_rows(self):
        for widget in self.winfo_children():
            info = widget.grid_info()
            if int(info.get("row", 0)) >= 2:
                widget.destroy()
        self.rows = []

    def show_empty(self, icon="📭", title="No data to display", subtitle="There are no items matching your criteria."):
        """Show a centered empty message spanning all columns."""
        self.clear_rows()
        empty = EmptyState(self, icon=icon, title=title, subtitle=subtitle)
        empty.grid(row=2, column=0, columnspan=len(self.columns), pady=40)
