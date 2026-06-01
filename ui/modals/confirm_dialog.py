import customtkinter as ctk
from ui.theme import THEME, FONTS
from ui.components.modal import Modal

class ConfirmDialog(Modal):
    def __init__(self, master, title="Confirm Action", message="Are you sure?", on_confirm=None, **kwargs):
        super().__init__(master, title=title, width=350, height=250, **kwargs)
        self.on_confirm = on_confirm
        
        lbl = ctk.CTkLabel(self.content_frame, text=message, font=FONTS["body"], wraplength=300)
        lbl.pack(pady=20)
        
        footer = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        footer.pack(fill="x", side="bottom", pady=10)
        
        btn_cancel = ctk.CTkButton(footer, text="Cancel", fg_color=THEME["bg_secondary"],
                                   command=self.destroy)
        btn_cancel.pack(side="left", expand=True, padx=5)
        
        btn_confirm = ctk.CTkButton(footer, text="Confirm", fg_color=THEME["red"],
                                    command=self._confirm)
        btn_confirm.pack(side="right", expand=True, padx=5)
        
    def _confirm(self):
        cb = self.on_confirm
        self.destroy()
        if cb:
            self.master.after(10, cb)
