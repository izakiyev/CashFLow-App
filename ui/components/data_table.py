import customtkinter as ctk
from ui.theme import THEME, FONTS

class DataTable(ctk.CTkScrollableFrame):
    def __init__(self, master, columns, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.columns = columns
        self.headers = []
        self.rows = []
        self._build_headers()

    def _build_headers(self):
        for col_idx, col_name in enumerate(self.columns):
            lbl = ctk.CTkLabel(self, text=col_name, font=FONTS["heading"], text_color=THEME["text_secondary"])
            lbl.grid(row=0, column=col_idx, sticky="w", padx=10, pady=10)
            self.headers.append(lbl)

        self.header_border = ctk.CTkFrame(self, height=1, fg_color=THEME["border"])
        self.header_border.grid(row=1, column=0, columnspan=len(self.columns), sticky="ew")

    def add_row(self, row_data, on_click=None, color=None):
        row_idx = len(self.rows) + 2
        bg_color = "transparent" if row_idx % 2 == 0 else THEME["bg_secondary"]

        row_widgets = []
        row_frame = ctk.CTkFrame(self, fg_color=bg_color, corner_radius=0)
        row_frame.grid(row=row_idx, column=0, columnspan=len(self.columns), sticky="ew")
        if on_click:
            row_frame.bind("<Button-1>", lambda e: on_click(row_data))

        text_color = color if color else THEME["text_primary"]

        for col_idx, val in enumerate(row_data):
            col_name = self.columns[col_idx].lower()
            if callable(val):
                # It's a lambda/function that takes 'master' and returns a widget
                widget = val(row_frame)
                widget.grid(row=0, column=col_idx, sticky="w", padx=10, pady=8)
                row_widgets.append(widget)
            elif isinstance(val, ctk.CTkBaseClass):
                val.grid(row=0, column=col_idx, sticky="w", padx=10, pady=8)
                row_widgets.append(val)
            else:
                wraplength = 300 if "description" in col_name else 0
                lbl = ctk.CTkLabel(row_frame, text=str(val), font=FONTS["body"], 
                                   text_color=text_color, wraplength=wraplength, justify="left")
                lbl.grid(row=0, column=col_idx, sticky="w", padx=10, pady=8)
                if on_click:
                    lbl.bind("<Button-1>", lambda e: on_click(row_data))
                row_widgets.append(lbl)

        for col_idx in range(len(self.columns)):
            row_frame.grid_columnconfigure(col_idx, weight=1)
            self.grid_columnconfigure(col_idx, weight=1)

        self.rows.append(row_widgets)

    def clear_rows(self):
        for widget in self.winfo_children():
            info = widget.grid_info()
            if int(info['row']) >= 2:
                widget.destroy()
        self.rows = []
