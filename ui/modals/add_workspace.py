import customtkinter as ctk
import tkinter as tk
from ui.theme import THEME, FONTS
from services.company_service import create_company
from services.auth_service import get_current_user_id

class AddWorkspaceModal(ctk.CTkToplevel):
    def __init__(self, master, on_success=None):
        super().__init__(master)
        
        self.on_success = on_success
        self.title("Create Workspace")
        self.geometry("400x350")
        self.resizable(False, False)
        
        # Make it modal
        self.transient(master)
        self.grab_set()
        
        # Center it
        self.update_idletasks()
        x = master.winfo_x() + (master.winfo_width() // 2) - (400 // 2)
        y = master.winfo_y() + (master.winfo_height() // 2) - (350 // 2)
        self.geometry(f"+{x}+{y}")
        
        self.configure(fg_color=THEME["bg_primary"])
        
        # UI Elements
        ctk.CTkLabel(self, text="Create Workspace", font=FONTS["title"], text_color=THEME["text_primary"]).pack(pady=(20, 20))
        
        form_frame = ctk.CTkFrame(self, fg_color="transparent")
        form_frame.pack(fill="x", padx=30)
        
        ctk.CTkLabel(form_frame, text="Workspace Name", font=FONTS["small"], text_color=THEME["text_secondary"]).pack(anchor="w")
        self.name_entry = ctk.CTkEntry(form_frame, font=FONTS["body"], fg_color=THEME["bg_secondary"],
                                       border_color=THEME["border"], text_color=THEME["text_primary"])
        self.name_entry.pack(fill="x", pady=(5, 15))
        
        ctk.CTkLabel(form_frame, text="Base Currency", font=FONTS["small"], text_color=THEME["text_secondary"]).pack(anchor="w")
        self.currency_var = ctk.StringVar(value="AZN")
        self.currency_dropdown = ctk.CTkOptionMenu(form_frame, variable=self.currency_var,
                                                   values=["AZN", "USD", "EUR", "GBP"],
                                                   font=FONTS["body"], fg_color=THEME["bg_secondary"],
                                                   button_color=THEME["bg_tertiary"], button_hover_color=THEME["border"],
                                                   text_color=THEME["text_primary"])
        self.currency_dropdown.pack(fill="x", pady=(5, 20))
        
        self.error_label = ctk.CTkLabel(self, text="", text_color=THEME["red"], font=FONTS["small"])
        self.error_label.pack()
        
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(side="bottom", fill="x", pady=20, padx=30)
        
        ctk.CTkButton(btn_frame, text="Cancel", font=FONTS["body"], fg_color="transparent",
                      border_width=1, border_color=THEME["border"], text_color=THEME["text_primary"],
                      hover_color=THEME["bg_secondary"], command=self.destroy).pack(side="left", expand=True, padx=(0, 10))
                      
        ctk.CTkButton(btn_frame, text="Create", font=FONTS["body"], fg_color=THEME["green"],
                      text_color=THEME["text_primary"], hover_color=THEME["green_dark"],
                      command=self._save).pack(side="right", expand=True, padx=(10, 0))

    def _save(self):
        name = self.name_entry.get().strip()
        currency = self.currency_var.get()
        
        if not name:
            self.error_label.configure(text="Name is required.")
            return
            
        user_id = get_current_user_id()
        if not user_id:
            self.error_label.configure(text="Authentication error.")
            return
            
        try:
            new_company_id = create_company(name, currency, user_id)
            if self.on_success:
                self.on_success(new_company_id)
            self.destroy()
        except Exception as e:
            self.error_label.configure(text=f"Error: {e}")
