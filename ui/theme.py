import re

LIGHT = {
    "green": "#12b76a", "green_light": "#d1fadf", "green_dark": "#039855",
    "red": "#f04438", "red_light": "#fee4e2",
    "blue": "#2970ff", "blue_light": "#eff4ff",
    "amber": "#f79009", "amber_light": "#fef0c7", "amber_dark": "#dc6803",
    "bg_primary": "#ebeef2", "bg_secondary": "#ffffff", "bg_tertiary": "#dce0e5",
    "text_primary": "#101828", "text_secondary": "#475467", "text_tertiary": "#98a2b3",
    "border": "#cfd4dc", 
    "sidebar_bg": "#1c2434", "sidebar_text": "#94a3b8", "sidebar_text_active": "#ffffff", "sidebar_hover": "#2c3545",
}

DARK = {
    "green": "#12b76a", "green_light": "#053321", "green_dark": "#15cc76",
    "red": "#f04438", "red_light": "#4a1215",
    "blue": "#2970ff", "blue_light": "#0a1f4d",
    "amber": "#f79009", "amber_light": "#4a2c04", "amber_dark": "#f9a02e",
    "bg_primary": "#101828", "bg_secondary": "#1d2939", "bg_tertiary": "#344054",
    "text_primary": "#f2f4f7", "text_secondary": "#98a2b3", "text_tertiary": "#667085",
    "border": "#344054", 
    "sidebar_bg": "#0b111d", "sidebar_text": "#94a3b8", "sidebar_text_active": "#ffffff", "sidebar_hover": "#1d2939",
}

FONTS = {
    "title": ("Inter", 22, "bold"),
    "heading": ("Inter", 16, "bold"),
    "subheading": ("Inter", 14, "normal"),
    "body": ("Inter", 13, "normal"),
    "small": ("Inter", 11, "normal"),
    "mono": ("Courier New", 12, "normal"),
}

THEME = {}
for key in LIGHT:
    if key in DARK:
        THEME[key] = (LIGHT[key], DARK[key])
    else:
        THEME[key] = LIGHT[key]

CATEGORY_COLORS = [
    "#1abc9c", "#2ecc71", "#3498db", "#9b59b6", "#34495e",
    "#16a085", "#27ae60", "#2980b9", "#8e44ad", "#2c3e50",
    "#f1c40f", "#e67e22", "#e74c3c", "#ecf0f1", "#95a5a6",
    "#f39c12", "#d35400", "#c0392b", "#bdc3c7", "#7f8c8d"
]

def validate_hex_color(color, fallback="#999999"):
    """Ensures a color string is a valid 7-character hex code."""
    if not color or not isinstance(color, str):
        return fallback
    if re.match(r'^#[0-9A-Fa-f]{6}$', color):
        return color
    return fallback