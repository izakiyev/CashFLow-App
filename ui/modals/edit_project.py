import customtkinter as ctk
from datetime import datetime
from ui.theme import THEME, FONTS
from ui.components.modal import Modal
from ui.components.toast import Toast
from services.project_service import update_project


class EditProjectModal(Modal):
    def __init__(self, master, project_data, on_success=None, **kwargs):
        super().__init__(master, title="Edit Project", width=500, height=610, **kwargs)
        self.project = project_data
        self.on_success = on_success
        self._selected_color = project_data.get("color", "#2970ff")
        self._build()

    def _build(self):
        # Allow extra room, but make it scrollable if it doesn't fit
        scroll = ctk.CTkScrollableFrame(self.content_frame, fg_color="transparent")
        scroll.pack(fill="both", expand=True)
        content = scroll

        # Name
        ctk.CTkLabel(content, text="Project Name *", font=FONTS["body"],
                     text_color=THEME["text_secondary"], anchor="w").pack(fill="x", pady=(0, 4))
        self.name_var = ctk.StringVar(value=self.project.get("name", ""))
        ctk.CTkEntry(content, textvariable=self.name_var, font=FONTS["body"], height=36).pack(fill="x", pady=(0, 12))

        # Description
        ctk.CTkLabel(content, text="Description", font=FONTS["body"],
                     text_color=THEME["text_secondary"], anchor="w").pack(fill="x", pady=(0, 4))
        self.desc_entry = ctk.CTkTextbox(content, font=FONTS["body"], height=60,
                                         fg_color=THEME["bg_tertiary"], border_width=0)
        self.desc_entry.pack(fill="x", pady=(0, 12))
        self.desc_entry.insert("1.0", self.project.get("description", ""))

        # Budget
        ctk.CTkLabel(content, text="Total Budget (leave blank for no cap)",
                     font=FONTS["body"], text_color=THEME["text_secondary"], anchor="w").pack(fill="x", pady=(0, 4))
        current_budget = str(self.project["budget"]) if self.project.get("budget") else ""
        self.budget_var = ctk.StringVar(value=current_budget)
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

        sd = self.project.get("start_date")
        ed = self.project.get("end_date")
        self.start_var = ctk.StringVar(value=sd.strftime("%Y-%m-%d") if sd else "")
        self.end_var = ctk.StringVar(value=ed.strftime("%Y-%m-%d") if ed else "")

        ctk.CTkEntry(dates_row, textvariable=self.start_var, placeholder_text="YYYY-MM-DD",
                     font=FONTS["body"], height=36).grid(row=1, column=0, sticky="ew", pady=(4, 0))
        ctk.CTkEntry(dates_row, textvariable=self.end_var, placeholder_text="YYYY-MM-DD",
                     font=FONTS["body"], height=36).grid(row=1, column=1, sticky="ew", padx=(12, 0), pady=(4, 0))

        # Status
        ctk.CTkLabel(content, text="Status", font=FONTS["body"],
                     text_color=THEME["text_secondary"], anchor="w").pack(fill="x", pady=(0, 4))
        self.status_var = ctk.StringVar(value=self.project.get("status", "active").capitalize())
        ctk.CTkSegmentedButton(content, values=["Active", "Completed", "Archived"],
                               variable=self.status_var, font=FONTS["body"]).pack(fill="x", pady=(0, 12))

        # Color Picker
        ctk.CTkLabel(content, text="Color", font=FONTS["body"],
                     text_color=THEME["text_secondary"], anchor="w").pack(fill="x", pady=(0, 6))
        color_frame = ctk.CTkFrame(content, fg_color="transparent")
        color_frame.pack(fill="x", pady=(0, 8))

        colors = ["#2970ff", "#12b76a", "#f04438", "#f79009", "#8B5CF6",
                  "#EC4899", "#06B6D4", "#F97316", "#1c2434", "#667085"]
        for i, c in enumerate(colors):
            ctk.CTkButton(color_frame, text="", width=30, height=30, corner_radius=15,
                          fg_color=c, hover_color=c,
                          command=lambda col=c: self._pick_color(col)).grid(row=0, column=i, padx=3)

        self._color_indicator = ctk.CTkFrame(content, width=60, height=10, corner_radius=5,
                                              fg_color=self._selected_color)
        self._color_indicator.pack(anchor="w", pady=(0, 16))

        # Save button
        ctk.CTkButton(content, text="Save Changes", height=40, font=FONTS["heading"],
                      fg_color=THEME["blue"], hover_color=THEME["blue"],
                      command=self._save).pack(fill="x", pady=(4, 0))

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
            except ValueError:
                Toast(self.winfo_toplevel(), "Budget must be a number", type="error")
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
        status = self.status_var.get().lower()

        try:
            update_project(
                self.project["id"],
                name=name, description=desc, color=self._selected_color,
                budget=budget, start_date=start_date, end_date=end_date, status=status
            )
            Toast(self.winfo_toplevel(), "Project updated ✓", type="success")
            self.destroy()
            if self.on_success:
                self.on_success()
        except Exception as e:
            Toast(self.winfo_toplevel(), f"Error: {e}", type="error")
