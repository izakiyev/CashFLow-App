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
        
    @staticmethod
    def _currency_formatter(x, pos):
        if x >= 1e6: return f'{x*1e-6:.1f}M'
        if x >= 1e3: return f'{x*1e-3:.1f}K'
        if x <= -1e6: return f'{x*1e-6:.1f}M'
        if x <= -1e3: return f'{x*1e-3:.1f}K'
        return f'{int(x)}'
        
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
        
        import matplotlib.ticker as ticker
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(self._currency_formatter))
        
        # Spines formatting
        for spine in ['top', 'right', 'left']:
            ax.spines[spine].set_visible(False)
        for spine in ['bottom']:
            ax.spines[spine].set_color(theme_ref["border"])
            
        ax.grid(axis='y', color=theme_ref["border"], linestyle='--', alpha=0.5)
            
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
        x = list(range(len(days)))
        ax.plot(x, values, color=color, linewidth=2.5, marker='o', markersize=5, 
                markeredgecolor=theme_ref["bg_secondary"], markeredgewidth=1.5, label=label)
        ax.fill_between(x, values, color=color, alpha=0.15)
        
        ax.set_xticks(x)
        ax.set_xticklabels(days, color=theme_ref["text_primary"], fontsize=8)
        
        # FIX: Avoid overlapping labels by showing only every 10th day
        ax.xaxis.set_major_locator(ticker.MaxNLocator(nbins=10))
        
        ax.tick_params(colors=theme_ref["text_primary"], labelsize=8)
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(self._currency_formatter))
        
        for spine in ['top', 'right', 'left']:
            ax.spines[spine].set_visible(False)
        for spine in ['bottom']:
            ax.spines[spine].set_color(theme_ref["border"])
            
        ax.grid(axis='y', color=theme_ref["border"], linestyle='--', alpha=0.5)
            
        if values:
            ax.legend(facecolor=theme_ref["bg_secondary"], edgecolor=theme_ref["border"], 
                      labelcolor=theme_ref["text_primary"], fontsize='small')
                      
        self.line_data = [{"name": label, "x": x, "y": values}]
        self.x_labels = days
        self.wedges = []
        self.annot = ax.annotate("", xy=(0,0), xytext=(15, 15), textcoords="offset points",
                                 bbox=dict(boxstyle="round4,pad=0.6", fc=theme_ref["bg_secondary"], 
                                           ec=theme_ref["border"], lw=1, alpha=0.95),
                                 arrowprops=dict(arrowstyle="-|>", connectionstyle="arc3,rad=0", 
                                                 color=theme_ref["text_secondary"]),
                                 color=theme_ref["text_primary"], fontsize=9, zorder=100)
        self.annot.set_visible(False)
            
        self._render()

    def draw_multi_line_chart(self, x_labels, data_series, colors=None):
        """
        Flexible multi-line area chart. Accepts two formats:
        Format A (dict-of-dicts): {"Income": {"values": [10, 20], "color": "#hex"}, ...}
        Format B (dict-of-lists): {"Income": [10, 20], ...} with optional `colors` list
        """
        import matplotlib.ticker as ticker
        self._update_colors()
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        mode = ctk.get_appearance_mode().lower()
        theme_ref = LIGHT if mode == "light" else DARK
        ax.set_facecolor(theme_ref["bg_secondary"])

        # Resolve default fallback colors
        default_colors = [theme_ref["green"], theme_ref["blue"], theme_ref["red"], theme_ref["amber"]]
        if colors is None:
            colors = default_colors

        x = list(range(len(x_labels)))
        self.line_data = []

        for i, (name, series_info) in enumerate(data_series.items()):
            # Handle both Format A and Format B
            if isinstance(series_info, dict):
                values = series_info.get("values", [])
                color = self._get_color(series_info.get("color", colors[i % len(colors)]))
            else:
                values = series_info  # plain list
                color = self._get_color(colors[i % len(colors)])

            ax.plot(x, values, color=color, linewidth=2.5, marker='o', markersize=4, 
                    markeredgecolor=theme_ref["bg_secondary"], markeredgewidth=1, label=name)
            ax.fill_between(x, values, color=color, alpha=0.15)
            self.line_data.append({"name": name, "x": x, "y": values})

        ax.set_xticks(x)
        ax.set_xticklabels(x_labels, color=theme_ref["text_tertiary"], fontsize=8)
        ax.xaxis.set_major_locator(ticker.MaxNLocator(nbins=10))
        ax.tick_params(colors=theme_ref["text_tertiary"], labelsize=8)
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(self._currency_formatter))

        for spine in ['top', 'right', 'left']:
            ax.spines[spine].set_visible(False)
        for spine in ['bottom']:
            ax.spines[spine].set_color(theme_ref["border"])

        ax.grid(axis='y', color=theme_ref["border"], linestyle='--', alpha=0.5)

        if data_series:
            ax.legend(loc='upper right', bbox_to_anchor=(1, 1.15), ncol=len(data_series),
                      frameon=False, labelcolor=theme_ref["text_secondary"], fontsize='small',
                      handletextpad=0.4, handlelength=1.0)
                      
        self.x_labels = x_labels
        self.wedges = []
        self.annot = ax.annotate("", xy=(0,0), xytext=(15, 15), textcoords="offset points",
                                 bbox=dict(boxstyle="round4,pad=0.6", fc=theme_ref["bg_secondary"], 
                                           ec=theme_ref["border"], lw=1, alpha=0.95),
                                 arrowprops=dict(arrowstyle="-|>", connectionstyle="arc3,rad=0", 
                                                 color=theme_ref["text_secondary"]),
                                 color=theme_ref["text_primary"], fontsize=9, zorder=100)
        self.annot.set_visible(False)

        self._render()

    def draw_donut_chart(self, data, on_click=None):
        """
        data: list of dicts {"id": 1, "name": "Sales", "amount": 1000, "color": "#hex"}
        on_click: optional callback(category_dict) triggered when a wedge is clicked.
        """
        self._donut_on_click = on_click
        self.donut_data = data
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
            self.wedges = []
        else:
            self.wedges, texts = ax.pie(sizes, colors=colors, startangle=90, 
                                        wedgeprops=dict(width=0.35, edgecolor=theme_ref["bg_secondary"], linewidth=2))
            ax.legend(self.wedges, labels, loc="center left", bbox_to_anchor=(1, 0, 0.5, 1),
                      frameon=False, labelcolor=theme_ref["text_primary"], fontsize='small')
                      
            self.donut_labels = labels
            self.donut_sizes = sizes
            self.annot = ax.annotate("", xy=(0,0), xytext=(15, 15), textcoords="offset points",
                                     bbox=dict(boxstyle="round4,pad=0.6", fc=theme_ref["bg_secondary"], 
                                               ec=theme_ref["border"], lw=1, alpha=0.95),
                                     arrowprops=dict(arrowstyle="-|>", connectionstyle="arc3,rad=0", 
                                                     color=theme_ref["text_secondary"]),
                                     color=theme_ref["text_primary"], fontsize=9, zorder=100)
            self.annot.set_visible(False)
            
            # Show cursor pointer hint if clickable
            if on_click:
                ax.set_title("Click a slice to drill down", fontsize=7, 
                             color=theme_ref["text_tertiary"], pad=4)
                      
        self._render()

    def _render(self):
        if self.canvas:
            self.canvas.get_tk_widget().destroy()
            
        self.figure.tight_layout()
        self.canvas = FigureCanvasTkAgg(self.figure, self)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        self.canvas.mpl_connect("motion_notify_event", self._on_hover)
        self.canvas.mpl_connect("button_press_event", self._on_click_handler)

    def _on_click_handler(self, event):
        """Fires on_click callback if a donut wedge is clicked."""
        if not event.inaxes or not hasattr(self, '_donut_on_click') or not self._donut_on_click:
            return
        if not hasattr(self, 'wedges') or not self.wedges:
            return
        for i, wedge in enumerate(self.wedges):
            cont, _ = wedge.contains(event)
            if cont:
                if self.donut_data and i < len(self.donut_data):
                    self._donut_on_click(self.donut_data[i])
                return

    def _on_hover(self, event):
        if not hasattr(self, 'annot') or not event.inaxes: 
            return
            
        # Check Donut Chart wedges
        if hasattr(self, 'wedges') and self.wedges:
            for i, wedge in enumerate(self.wedges):
                cont, _ = wedge.contains(event)
                if cont:
                    self.annot.xy = (event.xdata, event.ydata)
                    total = sum(self.donut_sizes)
                    pct = (self.donut_sizes[i] / total * 100) if total > 0 else 0
                    
                    amt = self.donut_sizes[i]
                    formatted_amt = f"AZN {amt:,.2f}" if amt % 1 != 0 else f"AZN {int(amt):,}"
                    
                    text = f"{self.donut_labels[i]}\nAmount: {formatted_amt}\nShare: {pct:.1f}%"
                    self.annot.set_text(text)
                    self.annot.set_visible(True)
                    self.canvas.draw_idle()
                    return
                    
        # Check Line Charts
        if hasattr(self, 'line_data') and self.line_data:
            import math
            min_dist = float('inf')
            closest_pt = None
            
            for series in self.line_data:
                for i in range(len(series["x"])):
                    x_val = series["x"][i]
                    y_val = series["y"][i]
                    
                    # Convert data coords to display coords to calculate pixel distance
                    pt_disp = event.inaxes.transData.transform((x_val, y_val))
                    mouse_disp = (event.x, event.y)
                    
                    dist = math.hypot(pt_disp[0] - mouse_disp[0], pt_disp[1] - mouse_disp[1])
                    
                    # Hover radius of 15 pixels
                    if dist < 15 and dist < min_dist:
                        min_dist = dist
                        closest_pt = (x_val, y_val, series, i)
                        
            if closest_pt:
                x_val, y_val, series, i = closest_pt
                self.annot.xy = (x_val, y_val)
                label = self.x_labels[i] if hasattr(self, 'x_labels') and i < len(self.x_labels) else ""
                
                formatted_amt = f"AZN {y_val:,.2f}" if y_val % 1 != 0 else f"AZN {int(y_val):,}"
                
                text = f"{label}\n{series['name']}: {formatted_amt}"
                self.annot.set_text(text)
                self.annot.set_visible(True)
                self.canvas.draw_idle()
                return
                    
        # Hide if not over anything
        if getattr(self, 'annot', None) and self.annot.get_visible():
            self.annot.set_visible(False)
            self.canvas.draw_idle()

    def destroy_chart(self):
        if self.canvas:
            self.canvas.get_tk_widget().destroy()
        self.figure.clear()
