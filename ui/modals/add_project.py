import customtkinter as ctk
from datetime import datetime
from ui.theme import THEME, FONTS
from ui.components.modal import Modal
from ui.components.toast import Toast
from services.project_service import create_project
from config import CATEGORY_COLORS


class AddProjectModal(Modal):
    def __init__(self, master, company_id, on_success=None, **kwargs):
        super().__init__(master, title="New Project", width=500, height=580, **kwargs)
        self.company_id = company_id
        self.on_success = on_success
        self._selected_color = "#2970ff"
        self._build()

    def _build(self):
        content = self.content_frame

        # Name
        ctk.CTkLabel(content, text="Project Name *", font=FONTS["body"],
                     text_color=THEME["text_secondary"], anchor="w").pack(fill="x", pady=(0, 4))
        self.name_var = ctk.StringVar()
        ctk.CTkEntry(content, textvariable=self.name_var, placeholder_text="e.g. AMOS UBOC 2026",
                     font=FONTS["body"], height=36).pack(fill="x", pady=(0, 12))

        # Description
        ctk.CTkLabel(content, text="Description", font=FONTS["body"],
                     text_color=THEME["text_secondary"], anchor="w").pack(fill="x", pady=(0, 4))
        self.desc_entry = ctk.CTkTextbox(content, font=FONTS["body"], height=60,
                                         fg_color=THEME["bg_tertiary"], border_width=0)
        self.desc_entry.pack(fill="x", pady=(0, 12))

        # Budget (optional)
        ctk.CTkLabel(content, text="Total Budget (optional — leave blank for no cap)",
                     font=FONTS["body"], text_color=THEME["text_secondary"], anchor="w").pack(fill="x", pady=(0, 4))
        self.budget_var = ctk.StringVar()
        ctk.CTkEntry(content, textvariable=self.budget_var, placeholder_text="e.g. 50000",
                     font=FONTS["body"], height=36).pack(fill="x", pady=(0, 12))

        # Dates row
        dates_row = ctk.CTkFrame(content, fg_color="transparent")
        dates_row.pack(fill="x", pady=(0, 12))
        dates_row.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(dates_row, text="Start Date", font=FONTS["body"],
                     text_color=THEME["text_secondary"]).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(dates_row, text="End Date", font=FONTS["body"],
                     text_color=THEME["text_secondary"]).grid(row=0, column=1, sticky="w", padx=(12, 0))

        self.start_var = ctk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        ctk.CTkEntry(dates_row, textvariable=self.start_var, placeholder_text="YYYY-MM-DD",
                     font=FONTS["body"], height=36).grid(row=1, column=0, sticky="ew", pady=(4, 0))
        self.end_var = ctk.StringVar()
        ctk.CTkEntry(dates_row, textvariable=self.end_var, placeholder_text="YYYY-MM-DD (optional)",
                     font=FONTS["body"], height=36).grid(row=1, column=1, sticky="ew", padx=(12, 0), pady=(4, 0))

        # Color Picker
        ctk.CTkLabel(content, text="Color", font=FONTS["body"],
                     text_color=THEME["text_secondary"], anchor="w").pack(fill="x", pady=(0, 6))

        color_frame = ctk.CTkFrame(content, fg_color="transparent")
        color_frame.pack(fill="x", pady=(0, 16))
        self._color_btns = []

        colors = ["#2970ff", "#12b76a", "#f04438", "#f79009", "#8B5CF6",
                  "#EC4899", "#06B6D4", "#F97316", "#1c2434", "#667085"]
        for i, c in enumerate(colors):
            btn = ctk.CTkButton(
                color_frame, text="", width=30, height=30, corner_radius=15,
                fg_color=c, hover_color=c,
                command=lambda col=c: self._pick_color(col)
            )
            btn.grid(row=0, column=i, padx=3)
            self._color_btns.append((btn, c))

        self._color_indicator = ctk.CTkFrame(
            content, width=60, height=10, corner_radius=5,
            fg_color=self._selected_color
        )
        self._color_indicator.pack(anchor="w", pady=(0, 16))

        # Save button
        ctk.CTkButton(
            content, text="Create Project", height=40, font=FONTS["heading"],
            fg_color=THEME["blue"], hover_color=THEME["blue"],
            command=self._save
        ).pack(fill="x", pady=(4, 0))

    def _pick_color(self, color):
        self._selected_color = color
        self._color_indicator.configure(fg_color=color)

    def _save(self):
        name = self.name_var.get().strip()
        if not name:
            Toast(self.winfo_toplevel(), "Project name is required", type="error")
            return

        budget_raw = self.budget_var.get().strip()
        budget = None
        if budget_raw:
            try:
                budget = float(budget_raw.replace(",", ""))
                if budget <= 0:
                    raise ValueError
            except ValueError:
                Toast(self.winfo_toplevel(), "Budget must be a positive number", type="error")
                return

        start_date = None
        if self.start_var.get().strip():
            try:
                start_date = datetime.strptime(self.start_var.get().strip(), "%Y-%m-%d")
            except ValueError:
                Toast(self.winfo_toplevel(), "Start date must be YYYY-MM-DD", type="error")
                return

        end_date = None
        if self.end_var.get().strip():
            try:
                end_date = datetime.strptime(self.end_var.get().strip(), "%Y-%m-%d")
            except ValueError:
                Toast(self.winfo_toplevel(), "End date must be YYYY-MM-DD", type="error")
                return

        desc = self.desc_entry.get("1.0", "end").strip()

        try:
            create_project(
                company_id=self.company_id,
                name=name,
                description=desc,
                color=self._selected_color,
                budget=budget,
                start_date=start_date,
                end_date=end_date,
            )
            Toast(self.winfo_toplevel(), f"Project '{name}' created ✓", type="success")
            self.destroy()
            if self.on_success:
                self.on_success()
        except Exception as e:
            Toast(self.winfo_toplevel(), f"Error: {e}", type="error")
