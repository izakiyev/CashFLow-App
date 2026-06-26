import customtkinter as ctk
from ui.theme import THEME, FONTS, CATEGORY_COLORS, validate_hex_color
from ui.components.modal import Modal
from services.category_service import create_category
from ui.components.toast import Toast
import tkinter.colorchooser as colorchooser
import re

class AddCategoryModal(Modal):
    def __init__(self, master, company_id, type_filter, on_success, **kwargs):
        super().__init__(master, title=f"New {type_filter.capitalize()} Client / Category", width=450, height=620, **kwargs)
        self.company_id = company_id
        self.type_filter = type_filter
        self.on_success = on_success
        # Load existing categories for parent selection
        from services.category_service import get_categories
        all_cats = get_categories(self.company_id, type_filter=self.type_filter)
        
        # Auto-select a unique color
        used_colors = {c.color.lower() for c in all_cats if c.color}
        available_colors = [color for color in CATEGORY_COLORS if color.lower() not in used_colors]
        
        if available_colors:
            self.selected_color = available_colors[0]
        else:
            self.selected_color = CATEGORY_COLORS[len(all_cats) % len(CATEGORY_COLORS)]
            
        # Only top-level categories can be parents
        self.parents = [c for c in all_cats if c.parent_id is None]
        self.parent_id_map = {c.name: c.id for c in self.parents}
        self.parent_var = ctk.StringVar(value="— None —")
        
        self._build_ui()
        
    def _build_ui(self):
        self.form_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.form_frame.pack(fill="both", expand=True, padx=10)
        
        # Name
        self.name_entry = self._add_field("Name", placeholder="e.g. Subscriptions")
        
        # Icon
        self.icon_entry = self._add_field("Icon", placeholder="Optional icon name")
        
        # Parent Client
        row = self._create_row("Client")
        parent_names = ["— None —"] + [c.name for c in self.parents]
        self.parent_dropdown = ctk.CTkOptionMenu(row, variable=self.parent_var, values=parent_names, font=FONTS["body"])
        self.parent_dropdown.pack(side="left", fill="x", expand=True)
        
        # Color Section
        color_label = ctk.CTkLabel(self.form_frame, text="Select Color", font=FONTS["heading"], text_color=THEME["text_primary"])
        color_label.pack(anchor="w", pady=(10, 5))
        
        color_container = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        color_container.pack(fill="x", pady=5)
        
        # Left side: Color Grid
        grid_frame = ctk.CTkFrame(color_container, fg_color="transparent")
        grid_frame.pack(side="left", fill="both", expand=True)
        
        self.color_buttons = {}
        cols = 5
        for i, color in enumerate(CATEGORY_COLORS):
            btn = ctk.CTkButton(grid_frame, text="", width=28, height=28, corner_radius=14,
                                fg_color=color, hover_color=color,
                                command=lambda c=color: self._select_color(c))
            btn.grid(row=i//cols, column=i%cols, padx=4, pady=4)
            self.color_buttons[color] = btn
        
        # Right side: Preview & Custom
        preview_frame = ctk.CTkFrame(color_container, fg_color=THEME["bg_secondary"], corner_radius=10, width=120)
        preview_frame.pack(side="right", fill="both", padx=(10, 0))
        preview_frame.pack_propagate(False)
        
        self.preview_dot = ctk.CTkFrame(preview_frame, width=40, height=40, corner_radius=20, fg_color=self.selected_color)
        self.preview_dot.pack(pady=(15, 5))
        
        self.hex_label = ctk.CTkLabel(preview_frame, text=self.selected_color, font=FONTS["small"])
        self.hex_label.pack()
        
        custom_btn = ctk.CTkButton(preview_frame, text="Custom...", height=24, font=FONTS["small"],
                                   fg_color="transparent", border_width=1, border_color=THEME["border"],
                                   text_color=THEME["text_secondary"], command=self._pick_custom_color)
        custom_btn.pack(pady=10, padx=10)
        
        self._select_color(self.selected_color) # Initial highlight
        
        # Footer
        footer = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        footer.pack(fill="x", pady=(10, 0))
        
        btn_cancel = ctk.CTkButton(footer, text="Cancel", fg_color=THEME["bg_secondary"],
                                   hover_color=THEME["border"], text_color=THEME["text_primary"],
                                   command=self.destroy)
        btn_cancel.pack(side="left", expand=True, padx=5)
        
        btn_submit = ctk.CTkButton(footer, text="Create \u2713", fg_color=THEME["green"],
                                   hover_color=THEME["green_dark"], command=self._submit)
        btn_submit.pack(side="right", expand=True, padx=5)

    def _create_row(self, label_text):
        row = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        row.pack(fill="x", pady=5)
        lbl = ctk.CTkLabel(row, text=label_text, width=80, anchor="w", font=FONTS["body"])
        lbl.pack(side="left")
        return row

    def _add_field(self, label_text, placeholder="", value=""):
        row = self._create_row(label_text)
        entry = ctk.CTkEntry(row, placeholder_text=placeholder, font=FONTS["body"])
        if value: entry.insert(0, value)
        entry.pack(side="left", fill="x", expand=True)
        return entry

    def _select_color(self, color):
        # Reset borders
        for c, btn in self.color_buttons.items():
            btn.configure(border_width=0)
            
        self.selected_color = validate_hex_color(color)
        if self.selected_color in self.color_buttons:
            self.color_buttons[self.selected_color].configure(border_width=2, border_color=THEME["text_primary"])
            
        self.preview_dot.configure(fg_color=self.selected_color)
        self.hex_label.configure(text=self.selected_color.upper())

    def _pick_custom_color(self):
        color = colorchooser.askcolor(title="Choose Color", initialcolor=self.selected_color)[1]
        if color:
            self._select_color(color)

    def _submit(self):
        try:
            name = self.name_entry.get().strip()
            if not name: raise ValueError("Name is required")
                
            color = self.selected_color
            if color == "#999999": # Fallback value from validator if input was somehow bad
                 raise ValueError("Please select a valid color")
                
            data = {
                "company_id": self.company_id,
                "name": name,
                "type": self.type_filter,
                "color": color,
                "icon": self.icon_entry.get().strip() or None,
                "parent_id": self.parent_id_map.get(self.parent_var.get())
            }
            
            create_category(data)
            Toast(self.master, "Created successfully", type="success")
            self.on_success()
            self.destroy()
        except Exception as e:
            Toast(self, str(e), type="error")
