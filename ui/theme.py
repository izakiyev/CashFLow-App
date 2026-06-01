import re

LIGHT = {
    "green": "#1a9e75", "green_light": "#e1f5ee", "green_dark": "#0f6e56",
    "red": "#c0392b", "red_light": "#fcebeb",
    "blue": "#185fa5", "blue_light": "#e6f1fb",
    "amber": "#ba7517", "amber_light": "#faeeda", "amber_dark": "#8c5811",
    "bg_primary": "#ffffff", "bg_secondary": "#f7f7f5", "bg_tertiary": "#f0efec",
    "text_primary": "#1a1a18", "text_secondary": "#6b6b67", "text_tertiary": "#9b9b97",
    "border": "#e0e0dc", "sidebar_bg": "#f0efec",
}

DARK = {
    "green": "#1a9e75", "green_light": "#0d3d2e", "green_dark": "#5dcaa5",
    "red": "#e05a5a", "red_light": "#3d1a1a",
    "blue": "#4a90d9", "blue_light": "#0d2340",
    "amber": "#d4890a", "amber_light": "#3a2a00", "amber_dark": "#f0a62d",
    "bg_primary": "#1e1e1c", "bg_secondary": "#252523", "bg_tertiary": "#2c2c2a",
    "text_primary": "#f0efec", "text_secondary": "#9b9b97", "text_tertiary": "#6b6b67",
    "border": "#3a3a38", "sidebar_bg": "#161614",
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