import customtkinter as ctk
from ui.theme import THEME, FONTS

class SearchBar(ctk.CTkFrame):
    def __init__(self, master, on_search, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.on_search = on_search

        self.entry = ctk.CTkEntry(self, placeholder_text="Search...", width=250,
                                  font=FONTS["body"], fg_color=THEME["bg_secondary"],
                                  border_color=THEME["border"])
        self.entry.pack(side="left", padx=(0, 10))
        self.entry.bind("<Return>", lambda e: self._handle_search())

        self.btn = ctk.CTkButton(self, text="Search", width=80, font=FONTS["body"],
                                 fg_color=THEME["blue"], hover_color=THEME["blue_light"],
                                 command=self._handle_search)
        self.btn.pack(side="left")
        
    def _handle_search(self):
        query = self.entry.get()
        self.on_search(query)
