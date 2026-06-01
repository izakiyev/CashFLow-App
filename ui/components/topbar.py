import customtkinter as ctk
from ui.theme import THEME, FONTS

class Topbar(ctk.CTkFrame):
    def __init__(self, master, title="Dashboard", **kwargs):
        super().__init__(master, height=60, corner_radius=0, fg_color="transparent", **kwargs)
        self.pack_propagate(False)

        self.title_label = ctk.CTkLabel(self, text=title, font=FONTS["title"], text_color=THEME["text_primary"])
        self.title_label.pack(side="left", padx=20)

        # Action Buttons Area (Right Aligned)
        self.actions_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.actions_frame.pack(side="right", padx=20)

    def add_action(self, text, command, primary=False):
        fg_color = THEME["green"] if primary else THEME["bg_secondary"]
        text_color = THEME["text_primary"] if primary else THEME["text_secondary"]
        hover_color = THEME["green_dark"] if primary else THEME["border"]

        btn = ctk.CTkButton(self.actions_frame, text=text, font=FONTS["body"],
                            fg_color=fg_color, text_color=text_color, hover_color=hover_color,
                            height=32, command=command)
        btn.pack(side="left", padx=5)
        return btn

    def set_title(self, title):
        self.title_label.configure(text=title)

    def clear_actions(self):
        for widget in self.actions_frame.winfo_children():
            widget.destroy()
