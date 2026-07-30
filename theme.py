"""EquityLens visual design system: colors, typography, and global CSS.

Every view calls apply_theme() once at the top of the page. Centralizing
colors/CSS here is what makes five separate view files read as one product
instead of five independently-styled pages.

Design direction: minimal black / white / light-grey, institutional rather
than "dashboard." Deliberately no separate accent hue — near-black
(INK_PRIMARY) does double duty as both text ink and the interactive/accent
color (buttons, active nav, focus states). That is a considered choice, not
an oversight: introducing a second hue just for "accent" would work against
the brief's "minimal palette" instruction. Color is reserved entirely for
semantic meaning — gains, losses, and the four Financial Health rating
tiers — never for decoration or brand chrome.
"""

import streamlit as st

# ---------------------------------------------------------------------------
# Brand chrome — grayscale only
# ---------------------------------------------------------------------------
INK_PRIMARY = "#18181B"     # near-black — text, primary buttons, active states
INK_SECONDARY = "#52525B"   # secondary text
INK_MUTED = "#A1A1AA"       # captions, tags, placeholders
BORDER = "#E4E4E7"          # thin card/table borders
BORDER_STRONG = "#D4D4D8"   # dividers
WHITE = "#FFFFFF"           # page background
CARD_BG = "#FAFAFA"         # subtle light-grey card surface, distinct from the white page

SIDEBAR_BG = "#18181B"
SIDEBAR_HOVER = "#27272A"
SIDEBAR_TEXT_MUTED = "#A1A1AA"

RADIUS = "8px"       # cards, containers
RADIUS_SM = "6px"    # buttons, inputs, badges — "square," not pill-shaped

# ---------------------------------------------------------------------------
# Semantic colors — fixed meaning, never restyled to match the brand theme.
# Color appears in exactly two places in this app: price direction and the
# Financial Health rating. Nowhere else.
# ---------------------------------------------------------------------------
UP_COLOR = "#1D7A4C"        # muted institutional green — gains
DOWN_COLOR = "#B3261E"      # muted institutional red — losses

RATING_COLORS = {
    "Excellent": "#1D7A4C",
    "Good": "#5B8A6E",
    "Average": "#A1662F",
    "Weak": "#B3261E",
}

# Technical Rating (Market Research) — same muted institutional palette,
# on a five-step Strong Sell -> Strong Buy scale rather than Weak -> Excellent.
TECHNICAL_RATING_COLORS = {
    "Strong Buy": "#1D7A4C",
    "Buy": "#5B8A6E",
    "Neutral": "#52525B",
    "Sell": "#C17A6B",
    "Strong Sell": "#B3261E",
}

FONT_IMPORT = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
"""

GLOBAL_CSS = f"""
<style>
    html, body, [class*="css"] {{
        font-family: 'Inter', -apple-system, 'Segoe UI', sans-serif;
    }}

    .stApp {{
        background-color: {WHITE};
    }}

    .block-container {{
        padding-top: 2.5rem;
        padding-bottom: 4rem;
        max-width: 1200px;
    }}

    /* Sidebar */
    section[data-testid="stSidebar"] {{
        background-color: {SIDEBAR_BG};
        border-right: 1px solid #000000;
    }}
    section[data-testid="stSidebar"] * {{
        color: {WHITE} !important;
    }}
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a {{
        border-radius: {RADIUS_SM};
        margin: 1px 8px;
        font-weight: 500;
    }}
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a:hover {{
        background-color: {SIDEBAR_HOVER};
    }}
    section[data-testid="stSidebar"] [aria-current="page"] {{
        background-color: {SIDEBAR_HOVER};
        border-left: 2px solid {WHITE};
        font-weight: 600;
    }}

    /* Typography hierarchy */
    h1, h2 {{
        color: {INK_PRIMARY}   !important;
        font-weight: 800;
        letter-spacing: -0.02em;
        font-size: 2rem;
        margin-top: 0;
        margin-bottom: 0.2rem;
    }}
    h3 {{
        color: {INK_PRIMARY} !important;
        font-weight: 700;
        letter-spacing: -0.01em;
        font-size: 1.4rem;
    }}
    h4 {{
        color: {INK_PRIMARY} !important;
        font-weight: 700;
        font-size: 1.1rem;
        margin-top: 2.25rem;
        margin-bottom: 0.75rem;
    }}
    h5 {{
        color: {INK_PRIMARY} !important;
        font-weight: 700;
        font-size: 0.95rem;
    }}
    h6 {{
        color: {INK_SECONDARY} !important;
        font-weight: 700;
        font-size: 0.76rem;
        text-transform: uppercase;
        letter-spacing: 0.07em;
        margin-top: 1.5rem;
        margin-bottom: 0.6rem;
    }}
    [data-testid="stCaptionContainer"] {{
        color: {INK_MUTED};
    }}

    /* Metrics */
    div[data-testid="stMetric"] {{
        background-color: {CARD_BG};
        border: 1px solid {BORDER};
        border-radius: {RADIUS};
        padding: 18px 20px;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
    }}
    div[data-testid="stMetricLabel"] {{
        font-size: 0.78rem;
        color: {INK_SECONDARY};
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }}
    div[data-testid="stMetricValue"] {{
        color: {INK_PRIMARY};
        font-weight: 700;
        font-size: 1.45rem;
        font-variant-numeric: tabular-nums;
        overflow: visible;
        text-overflow: clip;
        white-space: nowrap;
    }}

    /* Buttons — square, not pill-shaped */
    .stButton > button, .stLinkButton > a, .stDownloadButton > button {{
        background-color: {INK_PRIMARY};
        color: {WHITE} !important;
        border-radius: {RADIUS_SM};
        border: 1px solid {INK_PRIMARY};
        font-weight: 600;
        box-shadow: none;
    }}
    .stButton > button:hover, .stLinkButton > a:hover {{
        background-color: {INK_SECONDARY};
        border-color: {INK_SECONDARY};
        color: {WHITE} !important;
    }}

    /* Inputs — square, thin borders */
    div[data-testid="stTextInput"] input,
    div[data-testid="stNumberInput"] input,
    div[data-testid="stTextArea"] textarea,
    div[data-baseweb="select"] > div {{
        border-radius: {RADIUS_SM} !important;
        border-color: {BORDER} !important;
    }}

    /* Bordered st.container(border=True) — used for cards holding real widgets */
    div[data-testid="stVerticalBlockBorderWrapper"] > div {{
        background-color: {CARD_BG};
        border-radius: {RADIUS};
    }}
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        border-radius: {RADIUS} !important;
        border-color: {BORDER} !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
    }}

    /* Generic card (static HTML content only) */
    .el-card {{
        background-color: {CARD_BG};
        border: 1px solid {BORDER};
        border-radius: {RADIUS};
        padding: 22px 24px;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
        margin-bottom: 16px;
    }}
    .el-card-title {{
        font-size: 1.02rem;
        font-weight: 700;
        color: {INK_PRIMARY};
        margin-bottom: 4px;
    }}
    .el-card-subtext {{
        color: {INK_SECONDARY};
        font-size: 0.85rem;
    }}

    /* Company / asset header */
    .el-header {{
        font-size: 1.7rem;
        font-weight: 800;
        letter-spacing: -0.01em;
        color: {INK_PRIMARY};
        margin-bottom: 0;
    }}
    .el-subtext {{
        color: {INK_SECONDARY};
        font-size: 0.92rem;
        margin-top: 2px;
    }}

    /* Divider */
    hr {{
        border-color: {BORDER} !important;
    }}

    /* Tabs */
    button[data-baseweb="tab"] {{
        font-weight: 600;
        color: {INK_SECONDARY};
    }}
    button[data-baseweb="tab"][aria-selected="true"] {{
        color: {INK_PRIMARY};
    }}
    div[data-baseweb="tab-highlight"] {{
        background-color: {INK_PRIMARY} !important;
    }}
</style>
"""

SIDEBAR_BRAND = f"""
<div style="padding: 4px 8px 20px 8px;">
    <span style="font-size:1.15rem; font-weight:800; color:{WHITE}; letter-spacing:0.03em;">EQUITYLENS</span><br>
    <span style="font-size:0.72rem; color:{SIDEBAR_TEXT_MUTED};">Equity Research &amp; Risk Intelligence</span>
</div>
"""


def apply_theme() -> None:
    st.markdown(FONT_IMPORT, unsafe_allow_html=True)
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
    st.sidebar.markdown(SIDEBAR_BRAND, unsafe_allow_html=True)
