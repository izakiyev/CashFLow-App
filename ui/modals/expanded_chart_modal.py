import customtkinter as ctk
from ui.theme import THEME, FONTS
from ui.components.chart_frame import ChartFrame

class ExpandedChartModal(ctk.CTkToplevel):
    def __init__(self, master, title, chart_type, draw_kwargs):
        """
        chart_type: str, one of "donut", "line", "multi_line", "bar"
        draw_kwargs: dict of arguments to pass to the respective draw_* method
        """
        super().__init__(master)
        
        # Modal setup
        self.title(title)
        self.geometry("900x700")
        self.minsize(800, 600)
        self.configure(fg_color=THEME["bg_primary"])
        
        # Maximize window (Full Screen)
        self.after(10, lambda: self.state("zoomed"))
        
        self.transient(master)
        self.grab_set()
        
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent", height=60)
        header.pack(fill="x", padx=24, pady=(20, 10))
        
        ctk.CTkLabel(header, text=title, font=FONTS["heading"], text_color=THEME["text_primary"]).pack(side="left")
        
        close_btn = ctk.CTkButton(header, text="Close", width=80, height=32, corner_radius=8,
                                  fg_color=THEME["bg_tertiary"], hover_color=THEME["border"],
                                  text_color=THEME["text_primary"], command=self.destroy)
        close_btn.pack(side="right")
        
        # Chart Container
        container = ctk.CTkFrame(self, fg_color=THEME["bg_secondary"], corner_radius=12,
                                 border_width=1, border_color=THEME["border"])
        container.pack(fill="both", expand=True, padx=24, pady=(0, 24))
        
        # Draw Chart
        self.chart = ChartFrame(container)
        self.chart.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Inject is_expanded flag to ensure font sizes scale up
        draw_kwargs["is_expanded"] = True
        
        if chart_type == "donut":
            self.chart.draw_donut_chart(**draw_kwargs)
        elif chart_type == "line":
            self.chart.draw_line_chart(**draw_kwargs)
        elif chart_type == "multi_line":
            self.chart.draw_multi_line_chart(**draw_kwargs)
        elif chart_type == "bar":
            self.chart.draw_bar_chart(**draw_kwargs)
