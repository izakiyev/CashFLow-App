import customtkinter as ctk
from ui.theme import THEME, DARK, FONTS

class Toast(ctk.CTkToplevel):
    def __init__(self, master, message, type="success", duration=3000, **kwargs):
        super().__init__(master, **kwargs)
        self.message = message
        self.duration = duration

        if type == "success":
            bg = DARK["green"]   # Toast uses fixed vivid colors — these work on both themes
        elif type == "error":
            bg = DARK["red"]
        else:
            bg = DARK["blue"]

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(fg_color=bg)

        lbl = ctk.CTkLabel(self, text=message, font=FONTS["body"], text_color="#ffffff")
        lbl.pack(padx=20, pady=10)

        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = screen_width - width - 20
        y = screen_height - height - 60
        self.geometry(f"+{x}+{y}")

        self.after(self.duration, self.destroy)
