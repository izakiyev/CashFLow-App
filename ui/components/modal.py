import customtkinter as ctk
from ui.theme import THEME, FONTS

class Modal(ctk.CTkToplevel):
    def __init__(self, master, title="Modal", width=480, height=580, **kwargs):
        super().__init__(master, **kwargs)
        self.title(title)
        self.geometry(f"{width}x{height}")
        self.configure(fg_color=THEME["bg_primary"])
        self.resizable(False, False)

        self.transient(master)
        self.grab_set()

        # Center modal
        self.update_idletasks()
        x = master.winfo_x() + (master.winfo_width() // 2) - (width // 2)
        y = master.winfo_y() + (master.winfo_height() // 2) - (height // 2)
        self.geometry(f"+{x}+{y}")

        self.bind("<Escape>", lambda e: self.destroy())

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=20)

        lbl_title = ctk.CTkLabel(header, text=title, font=FONTS["title"], text_color=THEME["text_primary"])
        lbl_title.pack(side="left")

        btn_close = ctk.CTkButton(header, text="X", width=30, height=30, fg_color="transparent",
                                  hover_color=THEME["bg_secondary"], text_color=THEME["text_secondary"],
                                  command=self.destroy)
        btn_close.pack(side="right")

        # Content frame
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    def focus_set(self):
        try:
            if self.winfo_exists():
                super().focus_set()
        except Exception:
            pass

    def destroy(self):
        """Override destroy to safely return focus and avoid TclErrors."""
        try:
            self.grab_release()
            if self.master and self.master.winfo_exists():
                self.master.focus_set()
            self.update_idletasks()
        except Exception:
            pass
        finally:
            # Delay actual destruction slightly to allow CustomTkinter's after() callbacks to fire
            if self.winfo_exists():
                self.after(10, super().destroy)
