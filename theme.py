"""EquityLens visual design system: colors, typography, and global CSS.

Every view calls apply_theme() once at the top of the page. Centralizing
colors/CSS here is what makes six separate view files read as one product
instead of six independently-styled pages — and it's why this file alone
carries every hex color in the app (grep the repo: no other .py file has a
literal #rrggbb). Retuning the palette or font never means hunting through
views.

Design direction: grey / white / charcoal, with one restrained blue accent —
deliberately NOT a navy-branded product. Dark Charcoal is chrome (sidebar,
primary buttons, strong headings); most of the interface is grey and white
surfaces; Accent Blue is used sparingly for selected states, links, and
informational highlights. Semantic color (teal positive / amber caution /
red negative) means something specific and appears nowhere else.

Typeface: IBM Plex Sans throughout — applied with an aggressive selector
(see GLOBAL_CSS) so it wins over Streamlit's built-in font in every widget,
including BaseWeb components that render in a portal outside .stApp. IBM
Plex Mono is used selectively for tickers/prices/key numbers, where a
monospaced, tabular look reads more like real market data. Weight scale:
400 body text, 500 labels/secondary headings, 600 buttons/important
labels, 700 major headings/key figures — nothing heavier.
"""

import streamlit as st

# ---------------------------------------------------------------------------
# Brand chrome — charcoal/grey, not navy
# ---------------------------------------------------------------------------
PRIMARY_CHARCOAL = "#252A30"   # sidebar, primary buttons, strong headings
CHARCOAL_HOVER = "#3A4149"     # slightly lighter charcoal — hover states
MEDIUM_GREY = "#4C545D"        # secondary chrome, active-adjacent surfaces

# Backwards-compatible alias — the app-wide "primary chrome color" name used
# throughout views/components; holds the charcoal value now, not navy.
INK_PRIMARY = "#20252A"        # primary body text / metric values
INK_SECONDARY = "#6E7781"      # secondary text
INK_MUTED = "#828B94"          # captions, tags, placeholders, metadata
BORDER = "#D9DEE3"             # thin card/table borders (soft grey)
BORDER_STRONG = "#C2CAD1"      # dividers

PAGE_BG = "#EEF1F3"            # app background — soft grey workspace
WHITE = "#FFFFFF"               # literal white — card/panel surfaces
CARD_BG = WHITE

SIDEBAR_BG = PRIMARY_CHARCOAL
SIDEBAR_HOVER = CHARCOAL_HOVER
SIDEBAR_TEXT_MUTED = "#9BA3AB"

RADIUS = "5px"        # panels, containers — flatter, less "SaaS card"
RADIUS_SM = "4px"     # buttons, inputs, badges

# ---------------------------------------------------------------------------
# The one accent — used sparingly for selected states, links, info
# ---------------------------------------------------------------------------
ACCENT_BLUE = "#4D7C9A"

# ---------------------------------------------------------------------------
# Semantic colors — fixed meaning, never restyled to match the brand theme.
# ---------------------------------------------------------------------------
ACCENT_TEAL = "#3E8A78"     # positive/healthy/completed/bullish
AMBER = "#B58A45"           # caution — HOLD, medium conviction, needs attention, developing structure
RED = "#A95454"             # risk/negative — SELL, AVOID, losses, warnings, bearish structure

UP_COLOR = ACCENT_TEAL      # price gains
DOWN_COLOR = RED            # price losses

# Investment stance (Investment Ideas, Watchlist, Dashboard). BUY/HOLD/SELL
# are the user's own manual stance on the Investment Ideas register;
# REDUCE/AVOID belong to idea_engine.py's separate automated Conviction
# Score, used elsewhere (Dashboard, Watchlists) as supporting research,
# never as the user's decision.
STANCE_COLORS = {
    "BUY": ACCENT_TEAL,
    "HOLD": AMBER,
    "SELL": RED,
    "REDUCE": "#A96A3F",   # muted terracotta — between caution and risk
    "AVOID": RED,
}

# Investment Ideas idea status.
STATUS_COLORS = {
    "Watching": ACCENT_BLUE,
    "Active": ACCENT_TEAL,
    "Closed": INK_MUTED,
}

# Financial Health rating — bands match scoring.py's RATING_BANDS exactly
# (Excellent >=80, Good >=60, Average >=40, Weak below), so the color always
# corresponds to the same score the badge/number displays.
RATING_COLORS = {
    "Excellent": ACCENT_TEAL,
    "Good": ACCENT_BLUE,
    "Average": AMBER,
    "Weak": RED,
}

# Technical Rating (Market Research) — same restrained palette, on a
# five-step Strong Sell -> Strong Buy scale rather than Weak -> Excellent.
TECHNICAL_RATING_COLORS = {
    "Strong Buy": ACCENT_TEAL,
    "Buy": "#6BA396",       # lighter teal tint
    "Neutral": INK_SECONDARY,
    "Sell": "#C08484",      # lighter red tint
    "Strong Sell": RED,
}
TECHNICAL_RATING_ORDER = ("Strong Sell", "Sell", "Neutral", "Buy", "Strong Buy")

# Market Structure (structure_engine.py) — bullish/bearish/developing, never
# BUY/SELL. Teal for confirmed bullish structure, red for confirmed bearish,
# amber for anything "in progress" (correction, developing, watching a
# level), steel grey for a flat/no-structure read.
STRUCTURE_COLORS = {
    "bullish": ACCENT_TEAL,
    "bearish": RED,
    "developing": AMBER,
    "neutral": "#77818C",
}

# Economic-calendar event impact (news_calendar.py) — High is the only one
# that should draw the eye; Medium/Low stay muted on purpose.
IMPACT_COLORS = {
    "High": RED,
    "Medium": AMBER,
    "Low": "#77818C",
}

FONT_STACK = "'IBM Plex Sans', 'Source Sans 3', -apple-system, 'Segoe UI', Roboto, sans-serif"
FONT_MONO_STACK = "'IBM Plex Mono', 'SFMono-Regular', Consolas, monospace"

FONT_IMPORT = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
"""

GLOBAL_CSS = f"""
<style>
    html, body, [class*="css"], [class*="st-"], .stApp, .stApp * {{
        font-family: {FONT_STACK} !important;
    }}

    /* BaseWeb dropdowns/menus/tooltips render in a portal attached directly
    to <body>, outside .stApp — this catches those (select options, date
    picker popovers, slider tooltips) so the font stays consistent even
    there. */
    [data-baseweb] {{
        font-family: {FONT_STACK} !important;
    }}

    /* Streamlit's own icon glyphs (sidebar collapse arrow, nav icons,
    expander chevrons, alert/toast icons, ...) are text ligatures rendered
    through a dedicated icon font — the blanket font override above would
    otherwise turn a ligature like "keyboard_double_arrow_left" into
    literal visible text instead of an icon. Restore Streamlit's own icon
    font here, scoped to exactly the elements that need it. */
    [data-testid="stIconMaterial"] {{
        font-family: 'Material Symbols Rounded', 'Material Icons' !important;
    }}

    /* Monospace utility class — components apply this to tickers/prices/
    key numbers (see components.mono_html) for a tabular, market-data feel. */
    .el-mono {{
        font-family: {FONT_MONO_STACK} !important;
        font-variant-numeric: tabular-nums;
    }}

    .stApp {{
        background-color: {PAGE_BG};
    }}

    .block-container {{
        padding-top: 1.5rem;
        padding-bottom: 2.5rem;
        max-width: 1320px;
    }}

    /* Hide dev-facing Streamlit chrome (Deploy button, hamburger menu) —
    cosmetic only, navigation/functionality untouched. */
    .stAppDeployButton {{ display: none !important; }}
    #MainMenu {{ visibility: hidden; }}
    header[data-testid="stHeader"] {{ background: transparent; }}

    /* ===================================================================
    SIDEBAR — charcoal, not navy. Reordered via flexbox so our branding
    (stSidebarUserContent) renders above Streamlit's own nav list
    (stSidebarNav), even though the nav is injected into the DOM first by
    the framework and script order can't otherwise control that. Standard
    CSS, not a DOM hack.
    =================================================================== */
    section[data-testid="stSidebar"] {{
        background-color: {SIDEBAR_BG};
        border-right: 1px solid #1B1F24;
        min-width: 240px !important;
    }}
    section[data-testid="stSidebar"] * {{
        color: {WHITE} !important;
    }}
    div[data-testid="stSidebarContent"] {{
        display: flex;
        flex-direction: column;
    }}
    div[data-testid="stSidebarContent"] > div[data-testid="stSidebarHeader"] {{
        order: 0;
    }}
    div[data-testid="stSidebarContent"] > div[data-testid="stSidebarUserContent"] {{
        order: 1;
        padding-top: 0;
    }}
    div[data-testid="stSidebarContent"] > div[data-testid="stSidebarNav"] {{
        order: 2;
        padding-top: 4px;
    }}
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] ul {{
        padding: 0 8px;
    }}
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a {{
        border-radius: {RADIUS_SM};
        margin: 1px 0;
        padding: 7px 10px;
        font-weight: 500;
        font-size: 0.86rem;
    }}
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a:hover {{
        background-color: {SIDEBAR_HOVER};
    }}
    /* Selected nav item — a subtle tinted background, not a bright box. */
    section[data-testid="stSidebar"] [aria-current="page"] {{
        background-color: rgba(77, 124, 154, 0.22);
        border-left: 2px solid {ACCENT_BLUE};
        font-weight: 600;
    }}
    /* Visual break before the last nav item (Settings) — a subtle divider,
    not a text section label. */
    section[data-testid="stSidebar"] [data-testid="stSidebarNavItems"] li:last-child {{
        margin-top: 10px;
        padding-top: 10px;
        border-top: 1px solid rgba(255,255,255,0.10);
    }}
    section[data-testid="stSidebar"] [data-testid="stIconMaterial"] {{
        font-size: 1rem;
        opacity: 0.75;
    }}

    /* ===================================================================
    TYPOGRAPHY — headings carry the brand charcoal; body text (paragraphs,
    captions, metric values) uses Primary Text instead. Compact scale — no
    48px+ headings anywhere.
    =================================================================== */
    h1, h2 {{
        color: {PRIMARY_CHARCOAL} !important;
        font-weight: 700;
        letter-spacing: -0.01em;
        font-size: 1.5rem;
        margin-top: 0;
        margin-bottom: 0.15rem;
    }}
    h3 {{
        color: {PRIMARY_CHARCOAL} !important;
        font-weight: 700;
        letter-spacing: -0.01em;
        font-size: 1.15rem;
    }}
    h4 {{
        color: {PRIMARY_CHARCOAL} !important;
        font-weight: 600;
        font-size: 0.98rem;
        margin-top: 1.5rem;
        margin-bottom: 0.55rem;
    }}
    h5 {{
        color: {PRIMARY_CHARCOAL} !important;
        font-weight: 600;
        font-size: 0.88rem;
    }}
    h6 {{
        color: {INK_SECONDARY} !important;
        font-weight: 600;
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.07em;
        margin-top: 1.1rem;
        margin-bottom: 0.45rem;
    }}
    [data-testid="stCaptionContainer"] {{
        color: {INK_MUTED};
        font-size: 0.8rem;
    }}

    /* Metrics */
    div[data-testid="stMetric"] {{
        background-color: {CARD_BG};
        border: 1px solid {BORDER};
        border-radius: {RADIUS};
        padding: 12px 14px;
        box-shadow: none;
    }}
    div[data-testid="stMetricLabel"] {{
        font-size: 0.7rem;
        color: {INK_SECONDARY};
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.045em;
    }}
    div[data-testid="stMetricValue"] {{
        color: {INK_PRIMARY};
        font-weight: 700;
        font-size: 1.25rem;
        font-family: {FONT_MONO_STACK} !important;
        font-variant-numeric: tabular-nums;
        overflow: visible;
        text-overflow: clip;
        white-space: nowrap;
    }}

    /* Buttons — flat, minimal radius. Default (Streamlit's "secondary"
    kind) is the low-emphasis look: white surface, grey border, dark text.
    Buttons explicitly marked type="primary" get the solid-charcoal CTA
    look — used only for the main save/confirm action per screen. */
    .stButton > button, .stLinkButton > a, .stDownloadButton > button {{
        background-color: {WHITE};
        color: {PRIMARY_CHARCOAL} !important;
        border-radius: {RADIUS_SM};
        border: 1px solid {BORDER_STRONG};
        font-weight: 600;
        font-size: 0.84rem;
        box-shadow: none;
    }}
    .stButton > button:hover, .stLinkButton > a:hover, .stDownloadButton > button:hover {{
        background-color: {PAGE_BG};
        border-color: {PRIMARY_CHARCOAL};
        color: {PRIMARY_CHARCOAL} !important;
    }}
    .stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {{
        background-color: {PRIMARY_CHARCOAL};
        color: {WHITE} !important;
        border: 1px solid {PRIMARY_CHARCOAL};
    }}
    .stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover {{
        background-color: {CHARCOAL_HOVER};
        border-color: {CHARCOAL_HOVER};
        color: {WHITE} !important;
    }}

    /* Destructive action (Confirm Delete) — scoped via st.container(key=...),
    which Streamlit renders as a stable "st-key-<key>" class on the wrapper. */
    .st-key-confirm-delete-btn .stButton > button {{
        background-color: {WHITE};
        color: {RED} !important;
        border: 1px solid {RED};
    }}
    .st-key-confirm-delete-btn .stButton > button:hover {{
        background-color: {RED};
        color: {WHITE} !important;
        border-color: {RED};
    }}

    /* Inputs — flat, thin borders, blue focus ring, consistent height */
    div[data-testid="stTextInput"] input,
    div[data-testid="stNumberInput"] input,
    div[data-testid="stTextArea"] textarea,
    div[data-baseweb="select"] > div {{
        border-radius: {RADIUS_SM} !important;
        border-color: {BORDER_STRONG} !important;
        background-color: {WHITE};
        font-size: 0.86rem;
    }}
    div[data-testid="stTextInput"] input,
    div[data-testid="stNumberInput"] input {{
        height: 2.3rem;
    }}
    div[data-testid="stTextInput"] input:focus,
    div[data-testid="stNumberInput"] input:focus,
    div[data-testid="stTextArea"] textarea:focus,
    div[data-baseweb="select"] > div:focus-within {{
        border-color: {ACCENT_BLUE} !important;
        box-shadow: 0 0 0 1px {ACCENT_BLUE} !important;
    }}
    label[data-testid="stWidgetLabel"] p {{
        font-size: 0.78rem;
        font-weight: 500;
        color: {INK_SECONDARY};
    }}

    /* Bordered st.container(border=True) — the base "panel" every page is
    built from. Flat white surface, thin border, no shadow — depth through
    hierarchy, not effects. */
    div[data-testid="stVerticalBlockBorderWrapper"] > div {{
        background-color: {CARD_BG};
        border-radius: {RADIUS};
    }}
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        border-radius: {RADIUS} !important;
        border-color: {BORDER} !important;
        box-shadow: none;
    }}

    /* Reusable static-HTML components — see components.py */
    .el-panel {{
        background-color: {CARD_BG};
        border: 1px solid {BORDER};
        border-radius: {RADIUS};
        padding: 14px 16px;
        box-shadow: none;
    }}
    .el-panel-title {{
        font-size: 0.92rem;
        font-weight: 700;
        color: {PRIMARY_CHARCOAL};
        margin-bottom: 2px;
    }}
    .el-panel-subtext {{
        color: {INK_SECONDARY};
        font-size: 0.8rem;
    }}

    .el-page-header {{
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
        border-bottom: 1px solid {BORDER};
        padding-bottom: 12px;
        margin-bottom: 16px;
    }}
    .el-page-title {{
        font-size: 1.5rem;
        font-weight: 700;
        letter-spacing: -0.01em;
        color: {PRIMARY_CHARCOAL};
        line-height: 1.15;
    }}
    .el-page-subtitle {{
        color: {INK_SECONDARY};
        font-size: 0.84rem;
        margin-top: 3px;
    }}
    .el-page-meta {{
        color: {INK_MUTED};
        font-size: 0.76rem;
        text-align: right;
        white-space: nowrap;
    }}

    .el-section-label {{
        font-size: 0.68rem;
        font-weight: 700;
        color: {INK_SECONDARY};
        text-transform: uppercase;
        letter-spacing: 0.07em;
        margin-bottom: 8px;
    }}

    /* Asset header (Market Research / Market Structure) */
    .el-header {{
        font-size: 1.3rem;
        font-weight: 700;
        letter-spacing: -0.01em;
        color: {PRIMARY_CHARCOAL};
        margin-bottom: 0;
    }}
    .el-subtext {{
        color: {INK_SECONDARY};
        font-size: 0.83rem;
        margin-top: 1px;
    }}

    /* Reusable table (components.data_table) — real <table>, styled here
    since st.dataframe's canvas grid can't be. Soft grey header, white
    rows, subtle separators, tabular monospaced numerals, hover state. */
    .el-table-wrap {{
        overflow-x: auto;
    }}
    table.el-table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 0.83rem;
    }}
    table.el-table thead th {{
        background-color: {PAGE_BG};
        color: {INK_SECONDARY};
        font-size: 0.68rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        text-align: left;
        padding: 8px 12px;
        white-space: nowrap;
        border-bottom: 1px solid {BORDER_STRONG};
    }}
    table.el-table tbody td {{
        padding: 8px 12px;
        border-bottom: 1px solid {BORDER};
        color: {INK_PRIMARY};
        font-family: {FONT_MONO_STACK};
        font-variant-numeric: tabular-nums;
        white-space: nowrap;
    }}
    table.el-table tbody td:first-child {{
        font-family: {FONT_STACK};
    }}
    table.el-table tbody tr:last-child td {{ border-bottom: none; }}
    table.el-table tbody tr:hover td {{ background-color: {PAGE_BG}; }}
    table.el-table .el-num {{ text-align: right; }}

    /* Sentiment meter (Market Research Technical View) */
    .el-sentiment-track {{
        display: flex;
        height: 6px;
        border-radius: 3px;
        overflow: hidden;
        background-color: {BORDER};
    }}
    .el-sentiment-track > div {{ flex: 1; }}

    /* Status readout — compact label + accent bar + value, replacing large
    colored pills (components.status_line_html). */
    .el-status {{
        border-left: 3px solid transparent;
        padding-left: 10px;
    }}
    .el-status-label {{
        font-size: 0.68rem;
        font-weight: 700;
        color: {INK_SECONDARY};
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 2px;
    }}
    .el-status-value {{
        font-size: 1rem;
        font-weight: 700;
    }}

    /* Divider */
    hr {{
        border-color: {BORDER} !important;
    }}

    /* Tabs */
    button[data-baseweb="tab"] {{
        font-weight: 600;
        font-size: 0.85rem;
        color: {INK_SECONDARY};
    }}
    button[data-baseweb="tab"][aria-selected="true"] {{
        color: {PRIMARY_CHARCOAL};
    }}
    div[data-baseweb="tab-highlight"] {{
        background-color: {ACCENT_BLUE} !important;
    }}

    /* Expanders — match the panel language */
    div[data-testid="stExpander"] {{
        border: 1px solid {BORDER} !important;
        border-radius: {RADIUS} !important;
        box-shadow: none;
    }}
    div[data-testid="stExpander"] summary {{
        font-weight: 600;
        font-size: 0.86rem;
        color: {PRIMARY_CHARCOAL};
    }}
</style>
"""

SIDEBAR_BRAND = f"""
<div style="padding: 14px 16px 16px 16px;">
    <span style="font-size:1.02rem; font-weight:700; color:{WHITE} !important; letter-spacing:0.02em;">EQUITYLENS</span><br>
    <span style="font-size:0.7rem; color:{SIDEBAR_TEXT_MUTED} !important;">Market Intelligence</span>
</div>
"""


def apply_theme() -> None:
    st.markdown(FONT_IMPORT, unsafe_allow_html=True)
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
    st.sidebar.markdown(SIDEBAR_BRAND, unsafe_allow_html=True)
