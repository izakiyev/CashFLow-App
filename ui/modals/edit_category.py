import customtkinter as ctk
from ui.theme import THEME, FONTS, CATEGORY_COLORS
from ui.components.modal import Modal
from services.category_service import update_category, get_categories
from ui.components.toast import Toast

class EditCategoryModal(Modal):
    def __init__(self, master, category, on_success, **kwargs):
        super().__init__(master, title=f"Edit Category: {category.name}", width=400, height=600, **kwargs)
        self.category = category
        self.on_success = on_success
        self.selected_color = category.color
        
        # Load potential parents (excluding self)
        all_cats = get_categories(category.company_id, type_filter=category.type)
        self.potential_parents = [c for c in all_cats if c.parent_id is None and c.id != category.id]
        
        self._build_ui()

    def _build_ui(self):
        # Name
        ctk.CTkLabel(self.content_frame, text="Category Name", font=FONTS["body"]).pack(anchor="w", pady=(0, 5))
        self.name_entry = ctk.CTkEntry(self.content_frame, font=FONTS["heading"], height=40)
        self.name_entry.insert(0, self.category.name)
        self.name_entry.pack(fill="x", pady=(0, 20))

        # Parent Category
        ctk.CTkLabel(self.content_frame, text="Parent Category (Optional)", font=FONTS["body"]).pack(anchor="w", pady=(0, 5))
        
        parent_options = ["— None (Top Level) —"] + [c.name for c in self.potential_parents]
        self.parent_var = ctk.StringVar()
        
        # Determine current parent name
        current_parent_name = "— None (Top Level) —"
        if self.category.parent_id:
            parent = next((c for c in self.potential_parents if c.id == self.category.parent_id), None)
            if parent: current_parent_name = parent.name
            
        self.parent_var.set(current_parent_name)
        
        self.parent_dropdown = ctk.CTkOptionMenu(self.content_frame, variable=self.parent_var, values=parent_options, height=36)
        self.parent_dropdown.pack(fill="x", pady=(0, 20))
        
        # Only show parent selection if this category isn't a parent itself (to keep it 1-level)
        # Actually, let's keep it simple: any top-level category can become a sub, 
        # but if it has children, moving it might be complex. 
        # For now, let's just allow it.

        # Color Grid
        ctk.CTkLabel(self.content_frame, text="Category Color", font=FONTS["body"]).pack(anchor="w", pady=(0, 10))
        color_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        color_frame.pack(fill="x")
        
        self.color_buttons = {}
        for i, color in enumerate(CATEGORY_COLORS):
            btn = ctk.CTkButton(color_frame, text="", width=32, height=32, corner_radius=16,
                                fg_color=color, hover_color=color, 
                                command=lambda c=color: self._select_color(c))
            btn.grid(row=i // 8, column=i % 8, padx=4, pady=4)
            self.color_buttons[color] = btn
        
        self._select_color(self.selected_color)

        # Icon (Simple Text Entry for now)
        ctk.CTkLabel(self.content_frame, text="Icon (Emoji)", font=FONTS["body"]).pack(anchor="w", pady=(20, 5))
        self.icon_entry = ctk.CTkEntry(self.content_frame, placeholder_text="e.g. 🏢")
        if self.category.icon: self.icon_entry.insert(0, self.category.icon)
        self.icon_entry.pack(fill="x", pady=(0, 30))

        # Actions
        btn_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        btn_frame.pack(fill="x", side="bottom", pady=(10, 10))
        
        ctk.CTkButton(btn_frame, text="Cancel", fg_color=THEME["bg_secondary"], 
                      hover_color=THEME["border"], text_color=THEME["text_primary"],
                      command=self.destroy).pack(side="left", expand=True, padx=(0, 5))
                      
        ctk.CTkButton(btn_frame, text="Save Changes ✓", fg_color=THEME["green"],
                      hover_color=THEME["green_dark"], command=self._submit).pack(side="right", expand=True, padx=(5, 0))

    def _select_color(self, color):
        self.selected_color = color
        for c, btn in self.color_buttons.items():
            btn.configure(border_width=3 if c == color else 0, border_color="white")

    def _submit(self):
        name = self.name_entry.get().strip()
        if not name:
            Toast(self, "Name is required", type="error")
            return
            
        parent_name = self.parent_var.get()
        parent_id = None
        if parent_name != "— None (Top Level) —":
            parent = next((c for c in self.potential_parents if c.name == parent_name), None)
            if parent: parent_id = parent.id

        data = {
            "name": name,
            "color": self.selected_color,
            "icon": self.icon_entry.get().strip() or None,
            "parent_id": parent_id
        }
        
        if update_category(self.category.id, data):
            Toast(self.master, "Category updated", type="success")
            self.on_success()
            self.destroy()
        else:
            Toast(self, "Failed to update category", type="error")
