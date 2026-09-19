from pathlib import Path

# --- GLOBAL PAGE CONFIGURATION STRINGS ---
PAGE_TITLE = "Wikimedia Campaign Suite"
PAGE_ICON = "🌍"
LAYOUT = "wide"
INITIAL_SIDEBAR_STATE = "expanded"

# --- UNIFIED WIKIPEDIA-INSPIRED DARK THEME ---
WIKI_BLUE = "#3366cc"
WIKI_BLUE_LIGHT = "#7aa7ff"
WIKI_BLUE_DARK = "#14428e"
WIKI_INK = "#202122"
WIKI_GRAY = "#54595d"
CARD_LIGHT = "#f7f9fc"
CARD_DARK = "rgba(255, 255, 255, 0.05)"

BG_DEEP = "#0a1526"
BG_MID = "#13284a"
TEXT_LIGHT = "#eef3fc"
TEXT_MUTED = "#a9b9d8"

KORIKATH_LOGO_URL = "https://commons.wikimedia.org/wiki/Special:FilePath/Project_Korikath_Logo-dark.svg"

def get_custom_css():
    css_path = Path(__file__).with_name("styles.css")
    with css_path.open("r", encoding="utf-8") as css_file:
        custom_css = css_file.read()
    
    custom_css = (
        custom_css.replace("__BG_MID__", BG_MID)
        .replace("__BG_DEEP__", BG_DEEP)
        .replace("__TEXT_LIGHT__", TEXT_LIGHT)
        .replace("__TEXT_MUTED__", TEXT_MUTED)
        .replace("__WIKI_BLUE_DARK__", WIKI_BLUE_DARK)
        .replace("__WIKI_BLUE__", WIKI_BLUE)
        .replace("__WIKI_BLUE_LIGHT__", WIKI_BLUE_LIGHT)
        .replace("__CARD_LIGHT__", CARD_LIGHT)
        .replace("__CARD_DARK__", CARD_DARK)
        .replace("__WIKI_GRAY__", WIKI_GRAY)
        .replace("__WIKI_INK__", WIKI_INK)
    )
    return custom_css

