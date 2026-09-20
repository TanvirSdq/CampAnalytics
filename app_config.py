from pathlib import Path

# --- GLOBAL PAGE CONFIGURATION STRINGS ---
PAGE_TITLE = "CampAnalytics - Event Evaluation"
PAGE_ICON = "📊"
LAYOUT = "wide"
INITIAL_SIDEBAR_STATE = "expanded"

# --- DISTINCTIVE REFINED TOOL PALETTE ---
NAV_TEAL = "#183f54"
NAV_ACCENT = "#72ded6"
BG_CANVAS = "#ffffff"
BG_SUBTLE = "#fbfcfd"
TEXT_INK = "#202122"
TEXT_MUTED = "#54595d"
BORDER_COLOR = "#e0e0e0"
WIKI_BLUE = "#3366cc"
WIKI_BLUE_HOVER = "#14428e"

CARD_LIGHT = "#ffffff"
CARD_SUBTLE = "#f8f9fa"
CARD_DARK = "#ffffff"

# Compatibility aliases
WIKI_BLUE_LIGHT = "#7ce0d3"
WIKI_BLUE_DARK = "#14428e"
WIKI_INK = "#202122"
WIKI_GRAY = "#54595d"
BG_DEEP = "#ffffff"
BG_MID = "#fbfcfd"
TEXT_LIGHT = "#202122"

KORIKATH_LOGO_URL = "https://commons.wikimedia.org/wiki/Special:FilePath/Project_Korikath_Logo-dark.svg"

def get_custom_css():
    """Returns CSS for Flask application."""
    css_path = Path(__file__).with_name("styles.css")
    if not css_path.exists():
        return ""
    with css_path.open("r", encoding="utf-8") as css_file:
        return css_file.read()

def get_streamlit_css():
    """Returns CSS for Streamlit application."""
    css_path = Path(__file__).with_name("streamlit_styles.css")
    if not css_path.exists():
        return ""
    with css_path.open("r", encoding="utf-8") as css_file:
        custom_css = css_file.read()
    
    custom_css = (
        custom_css.replace("__NAV_TEAL__", NAV_TEAL)
        .replace("__NAV_ACCENT__", NAV_ACCENT)
        .replace("__BG_CANVAS__", BG_CANVAS)
        .replace("__BG_SUBTLE__", BG_SUBTLE)
        .replace("__TEXT_INK__", TEXT_INK)
        .replace("__TEXT_MUTED__", TEXT_MUTED)
        .replace("__BORDER_COLOR__", BORDER_COLOR)
        .replace("__WIKI_BLUE__", WIKI_BLUE)
        .replace("__WIKI_BLUE_HOVER__", WIKI_BLUE_HOVER)
        .replace("__CARD_LIGHT__", CARD_LIGHT)
        .replace("__CARD_SUBTLE__", CARD_SUBTLE)
        .replace("__BG_MID__", BG_SUBTLE)
        .replace("__BG_DEEP__", BG_CANVAS)
        .replace("__TEXT_LIGHT__", TEXT_INK)
        .replace("__WIKI_BLUE_DARK__", WIKI_BLUE_HOVER)
        .replace("__WIKI_BLUE_LIGHT__", NAV_ACCENT)
        .replace("__CARD_DARK__", CARD_LIGHT)
        .replace("__WIKI_GRAY__", TEXT_MUTED)
    )
    return custom_css
