import customtkinter as ctk
from ui.theme import THEME, FONTS


class SearchBar(ctk.CTkFrame):
    """
    Premium live-search bar with:
    - Real-time typing triggers on_search callback (for debounce handling by parent)
    - Clear (✕) button that resets query and fires callback
    - Search icon prefix
    - Rounded, bordered design matching the app theme
    """
    def __init__(self, master, on_search, placeholder="Search transactions...", width=300, **kwargs):
        super().__init__(master, fg_color=THEME["bg_tertiary"], corner_radius=8,
                         border_width=1, border_color=THEME["border"], **kwargs)
        self.on_search = on_search
        self._var = ctk.StringVar()
        self._var.trace_add("write", self._on_change)

        # Search icon label
        icon = ctk.CTkLabel(self, text="🔍", font=FONTS["body"],
                            text_color=THEME["text_tertiary"], width=28)
        icon.pack(side="left", padx=(10, 0))

        # Text entry
        self.entry = ctk.CTkEntry(
            self,
            textvariable=self._var,
            placeholder_text=placeholder,
            width=width,
            font=FONTS["body"],
            fg_color="transparent",
            border_width=0,
            text_color=THEME["text_primary"],
        )
        self.entry.pack(side="left", fill="x", expand=True, pady=4)
        self.entry.bind("<Escape>", lambda e: self.clear())

        # Clear button (hidden by default)
        self.clear_btn = ctk.CTkButton(
            self, text="✕", width=24, height=24,
            fg_color="transparent",
            hover_color=THEME["border"],
            text_color=THEME["text_tertiary"],
            font=FONTS["small"],
            command=self.clear
        )
        # Don't pack yet — shown only when there's text

    def _on_change(self, *args):
        query = self._var.get()
        # Show/hide clear button
        if query:
            self.clear_btn.pack(side="right", padx=(0, 8))
        else:
            self.clear_btn.pack_forget()
        self.on_search(query)

    def clear(self):
        self._var.set("")
        self.entry.focus()

    def get(self):
        return self._var.get()
