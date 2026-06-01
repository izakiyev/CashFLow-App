import customtkinter as ctk
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from ui.theme import DARK, LIGHT

class ChartFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.canvas = None
        self.figure = Figure(figsize=(5, 4), dpi=100)
        # Apply theme background
        self._update_colors()
        
    def _get_color(self, color):
        """Resolves a theme tuple or string to a single matplotlib-compatible color."""
        if isinstance(color, (list, tuple)) and len(color) == 2:
            mode = ctk.get_appearance_mode().lower()
            return color[0] if mode == "light" else color[1]
        return color

    def _update_colors(self):
        mode = ctk.get_appearance_mode().lower()
        bg_color = LIGHT["bg_secondary"] if mode == "light" else DARK["bg_secondary"]
        self.figure.patch.set_facecolor(bg_color)
        
    def draw_bar_chart(self, x_labels, data_series):
        """
        data_series: dict of name -> list of values
        e.g. {"Income": [10, 20], "Expense": [5, 15]}
        """
        self._update_colors()
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        mode = ctk.get_appearance_mode().lower()
        theme_ref = LIGHT if mode == "light" else DARK
        ax.set_facecolor(theme_ref["bg_secondary"])
        
        x = range(len(x_labels))
        width = 0.35
        
        offset = -width/2
        # Use theme colors for default series if not specified
        colors = {"Income": theme_ref["green"], "Expense": theme_ref["red"]}
        
        for name, values in data_series.items():
            color = self._get_color(colors.get(name, theme_ref["blue"]))
            ax.bar([pos + offset for pos in x], values, width, label=name, color=color)
            offset += width
            
        ax.set_xticks(x)
        ax.set_xticklabels(x_labels, color=theme_ref["text_primary"], fontsize=8)
        ax.tick_params(colors=theme_ref["text_primary"], labelsize=8)
        
        # Spines formatting
        for spine in ['top', 'right']:
            ax.spines[spine].set_visible(False)
        for spine in ['left', 'bottom']:
            ax.spines[spine].set_color(theme_ref["border"])
            
        if data_series:
            ax.legend(facecolor=theme_ref["bg_secondary"], edgecolor=theme_ref["border"], 
                      labelcolor=theme_ref["text_primary"], fontsize='small')
            
        self._render()

    def draw_line_chart(self, days, values, label, color=None):
        """
        days: list of x-axis values (e.g., ["May 07", "May 08"...])
        values: list of cumulative totals
        """
        import matplotlib.ticker as ticker
        self._update_colors()
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        mode = ctk.get_appearance_mode().lower()
        theme_ref = LIGHT if mode == "light" else DARK
        ax.set_facecolor(theme_ref["bg_secondary"])
        
        color = self._get_color(color or theme_ref["blue"])
        ax.plot(days, values, color=color, linewidth=2, marker='o', markersize=3, label=label)
        ax.fill_between(days, values, color=color, alpha=0.1)
        
        # FIX: Avoid overlapping labels by showing only every 10th day
        ax.xaxis.set_major_locator(ticker.MaxNLocator(nbins=10))
        
        ax.tick_params(colors=theme_ref["text_primary"], labelsize=8)
        for spine in ['top', 'right']:
            ax.spines[spine].set_visible(False)
        for spine in ['left', 'bottom']:
            ax.spines[spine].set_color(theme_ref["border"])
            
        if values:
            ax.legend(facecolor=theme_ref["bg_secondary"], edgecolor=theme_ref["border"], 
                      labelcolor=theme_ref["text_primary"], fontsize='small')
            
        self._render()

    def draw_donut_chart(self, data):
        """
        data: list of dicts {"name": "Sales", "amount": 1000, "color": "#hex"}
        """
        self._update_colors()
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        mode = ctk.get_appearance_mode().lower()
        theme_ref = LIGHT if mode == "light" else DARK
        ax.set_facecolor(theme_ref["bg_secondary"])
        
        labels = [d["name"] for d in data]
        sizes = [d["amount"] for d in data]
        colors = [self._get_color(d["color"]) for d in data]
        
        if not sizes or sum(sizes) == 0:
            ax.text(0.5, 0.5, "No Data", ha="center", va="center", color=theme_ref["text_secondary"])
        else:
            wedges, texts = ax.pie(sizes, colors=colors, startangle=90, wedgeprops=dict(width=0.3))
            ax.legend(wedges, labels, loc="center left", bbox_to_anchor=(1, 0, 0.5, 1),
                      facecolor=theme_ref["bg_secondary"], edgecolor=theme_ref["border"], 
                      labelcolor=theme_ref["text_primary"], fontsize='small')
                      
        self._render()

    def _render(self):
        if self.canvas:
            self.canvas.get_tk_widget().destroy()
            
        self.figure.tight_layout()
        self.canvas = FigureCanvasTkAgg(self.figure, self)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def destroy_chart(self):
        if self.canvas:
            self.canvas.get_tk_widget().destroy()
        self.figure.clear()
