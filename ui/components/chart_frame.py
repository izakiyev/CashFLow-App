import customtkinter as ctk
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from ui.theme import DARK, LIGHT
import warnings
warnings.filterwarnings("ignore", message="constrained_layout not applied.*")

class ChartFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.canvas = None
        self.figure = Figure(figsize=(5, 4), dpi=100, constrained_layout=True)
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
        
    def draw_bar_chart(self, x_labels, data_series, series_colors=None, is_expanded=False):
        """
        data_series: dict of name -> list of values
        series_colors: optional dict of name -> color hex string
        e.g. {"Income": [10, 20], "Expense": [5, 15]}
        """
        self._update_colors()
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        mode = ctk.get_appearance_mode().lower()
        theme_ref = LIGHT if mode == "light" else DARK
        ax.set_facecolor(theme_ref["bg_secondary"])
        
        x = list(range(len(x_labels)))
        n = len(data_series)
        width = 0.7 / max(n, 1)
        
        # Default color mapping, plus caller-supplied overrides
        default_colors = {
            "Income": theme_ref["green"],
            "Expense": theme_ref["red"],
        }
        if series_colors:
            default_colors.update(series_colors)

        offsets = [i * width - (n * width / 2) + width / 2 for i in range(n)]

        max_val = max([max(v) if v else 0 for v in data_series.values()]) if data_series else 0
        pad = max_val * 0.015

        for (name, values), offset in zip(data_series.items(), offsets):
            color = self._get_color(default_colors.get(name, theme_ref["blue"]))
            
            # Premium bar styling: touch edges but separated by background-colored stroke
            lw = 1.5 if is_expanded else 1.0
            bars = ax.bar([pos + offset for pos in x], values, width,
                          label=name, color=color, edgecolor=theme_ref["bg_secondary"], 
                          linewidth=lw, alpha=0.95, zorder=3)
                          
            # Value labels on top of bars
            for bar in bars:
                h = bar.get_height()
                if h > 0:
                    label_text = self._currency_formatter(h, None)
                    label_font = 10 if is_expanded else 7
                    ax.text(bar.get_x() + bar.get_width() / 2, h + pad,
                            label_text, ha='center', va='bottom',
                            fontsize=label_font, fontweight='medium', 
                            color=theme_ref["text_secondary"], zorder=4)
            
        ax.set_xticks(x)
        ax.set_xticklabels(x_labels, color=theme_ref["text_primary"], 
                           fontsize=(11 if is_expanded else 9), fontweight='semibold')
        ax.tick_params(colors=theme_ref["text_tertiary"], labelsize=(9 if is_expanded else 8))
        
        import matplotlib.ticker as ticker
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(self._currency_formatter))
        
        # Increase Y-axis limit slightly so top labels don't clip
        if max_val > 0:
            ax.set_ylim(0, max_val * 1.1)
        
        for spine in ['top', 'right', 'left']:
            ax.spines[spine].set_visible(False)
        ax.spines['bottom'].set_color(theme_ref["border"])
            
        ax.grid(axis='y', color=theme_ref["border"], linestyle='--', alpha=0.3, zorder=0)
            
        if data_series:
            leg_font = 12 if is_expanded else 'small'
            ax.legend(loc='upper right', bbox_to_anchor=(1, 1.15), ncol=len(data_series),
                      frameon=False, labelcolor=theme_ref["text_secondary"], fontsize=leg_font,
                      handletextpad=0.4, handlelength=1.2)
            
        self._render()

    def draw_horizontal_bar_chart(self, labels, values, colors=None, title=None, is_expanded=False):
        """
        Draws a horizontal bar chart.
        labels: list of category names
        values: list of numeric values
        colors: list of hex color strings (optional)
        """
        import matplotlib.ticker as ticker
        self._update_colors()
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        mode = ctk.get_appearance_mode().lower()
        theme_ref = LIGHT if mode == "light" else DARK
        ax.set_facecolor(theme_ref["bg_secondary"])

        n = len(labels)
        y_pos = list(range(n))

        bar_colors = [self._get_color(c) for c in colors] if colors else [self._get_color(theme_ref["blue"])] * n

        bars = ax.barh(y_pos, values, color=bar_colors, alpha=0.85, zorder=3, height=0.6)

        # Value labels at end of each bar
        for bar, val in zip(bars, values):
            ax.text(bar.get_width() + max(values) * 0.01, bar.get_y() + bar.get_height() / 2,
                    self._currency_formatter(val, None),
                    va='center', ha='left', fontsize=8,
                    color=theme_ref["text_primary"])

        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels, color=theme_ref["text_primary"], fontsize=9)
        ax.tick_params(colors=theme_ref["text_primary"], labelsize=8)
        ax.xaxis.set_major_formatter(ticker.FuncFormatter(self._currency_formatter))
        ax.invert_yaxis()  # Largest at top

        for spine in ['top', 'right', 'bottom']:
            ax.spines[spine].set_visible(False)
        ax.spines['left'].set_color(theme_ref["border"])

        ax.grid(axis='x', color=theme_ref["border"], linestyle='--', alpha=0.4, zorder=0)
        ax.set_xlim(0, max(values) * 1.18 if values else 1)

        if title:
            ax.set_title(title, color=theme_ref["text_primary"], fontsize=10, pad=8)

        self._render()


    def draw_line_chart(self, days, values, label, color=None, is_expanded=False):
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

    def draw_multi_line_chart(self, x_labels, data_series, colors=None, is_expanded=False):
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
            if isinstance(series_info, dict):
                values = series_info.get("values", [])
                color = self._get_color(series_info.get("color", colors[i % len(colors)]))
            else:
                values = series_info
                color = self._get_color(colors[i % len(colors)])

            # Enhanced line and marker styling for a premium look
            lw = 3.5 if is_expanded else 2.5
            ms = 7 if is_expanded else 5
            mew = 2 if is_expanded else 1.5
            
            ax.plot(x, values, color=color, linewidth=lw, marker='o', markersize=ms, 
                    markeredgecolor=theme_ref["bg_secondary"], markeredgewidth=mew, label=name, zorder=4)
            
            # Subtle area fill
            ax.fill_between(x, values, color=color, alpha=0.12, zorder=3)
            self.line_data.append({"name": name, "x": x, "y": values})

        # Fix: Show labels correctly without MaxNLocator overriding string labels
        max_ticks = 12 if is_expanded else 8
        if len(x) > max_ticks:
            step = max(1, len(x) // max_ticks)
            tick_positions = x[::step]
            tick_labels = [x_labels[i] for i in tick_positions]
        else:
            tick_positions = x
            tick_labels = x_labels
            
        ax.set_xticks(tick_positions)
        ax.set_xticklabels(tick_labels, color=theme_ref["text_tertiary"], fontsize=(10 if is_expanded else 8), fontweight='medium')
        
        ax.tick_params(colors=theme_ref["text_tertiary"], labelsize=(9 if is_expanded else 8))
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(self._currency_formatter))

        for spine in ['top', 'right', 'left']:
            ax.spines[spine].set_visible(False)
        for spine in ['bottom']:
            ax.spines[spine].set_color(theme_ref["border"])

        ax.grid(axis='y', color=theme_ref["border"], linestyle='--', alpha=0.3, zorder=0)

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

    def draw_donut_chart(self, data, on_click=None, is_expanded=False):
        """
        data: list of dicts {"id": 1, "name": "Sales", "amount": 1000, "color": "#hex"}
        on_click: optional callback(category_dict) triggered when a wedge is clicked.
        """
        self._donut_on_click = on_click
        # Sort data descending by amount to keep largest slices at the top
        self.donut_data = sorted(data, key=lambda x: x.get("amount", 0), reverse=True)
        
        mode = ctk.get_appearance_mode().lower()
        theme_ref = LIGHT if mode == "light" else DARK
        
        self._update_colors()
        self.figure.clear()
        
        # We add the subplot normally
        ax = self.figure.add_subplot(111)
        ax.set_facecolor(theme_ref["bg_secondary"])
        
        labels = [d["name"] for d in self.donut_data]
        sizes = [d["amount"] for d in self.donut_data]
        colors = [self._get_color(d["color"]) for d in self.donut_data]
        
        if not sizes or sum(sizes) == 0:
            ax.text(0.5, 0.5, "No Data", ha="center", va="center", color=theme_ref["text_secondary"])
            self.wedges = []
        else:
            self.wedges, texts = ax.pie(sizes, colors=colors, startangle=90, 
                                        wedgeprops=dict(width=0.35, edgecolor=theme_ref["bg_secondary"], linewidth=2))
            
            num_items = len(labels)
            
            # Smart UI/UX scaling for legend to ensure pie chart remains large and all items are visible
            if num_items <= 8:
                ncol = 1
                f_size = 12 if is_expanded else 'small'
                max_len = 35 if is_expanded else 22
            elif num_items <= 16:
                ncol = 2
                f_size = 12 if is_expanded else 'small'
                max_len = 25 if is_expanded else 12
            elif num_items <= 24:
                ncol = 2
                f_size = 11 if is_expanded else 'x-small'
                max_len = 20 if is_expanded else 14
            elif num_items <= 36:
                ncol = 3
                f_size = 10 if is_expanded else 7
                max_len = 16 if is_expanded else 9
            else:
                ncol = 3
                f_size = 9 if is_expanded else 6
                max_len = 14 if is_expanded else 8
                
            # Truncate labels based on columns so legend doesn't expand infinitely
            legend_labels = [lbl[:max_len] + ".." if len(lbl) > max_len+1 else lbl for lbl in labels]

            ax.legend(self.wedges, legend_labels, loc="center left", bbox_to_anchor=(1, 0.5),
                      frameon=False, labelcolor=theme_ref["text_primary"], 
                      fontsize=f_size, ncol=ncol, borderaxespad=0.1, 
                      columnspacing=0.8, handletextpad=0.4, handlelength=1.2)
                      
            self.donut_labels = labels
            self.donut_sizes = sizes
            self.annot = ax.annotate("", xy=(0,0), xytext=(15, 15), textcoords="offset points",
                                     bbox=dict(boxstyle="round4,pad=0.6", fc=theme_ref["bg_secondary"], 
                                               ec=theme_ref["border"], lw=1, alpha=0.95),
                                     arrowprops=dict(arrowstyle="-|>", connectionstyle="arc3,rad=0", 
                                                     color=theme_ref["text_secondary"]),
                                     color=theme_ref["text_primary"], fontsize=(14 if is_expanded else 9), zorder=100)
            self.annot.set_visible(False)
            
            # Show cursor pointer hint if clickable
            if on_click:
                ax.set_title("Click a slice to drill down", fontsize=(12 if is_expanded else 7), 
                             color=theme_ref["text_tertiary"], pad=(10 if is_expanded else 4))
                      
        self._render()

    def _render(self):
        if self.canvas:
            self.canvas.get_tk_widget().destroy()
            
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
