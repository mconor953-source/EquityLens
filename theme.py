"""EquityLens visual design system: colors, typography, and global CSS.

Every view calls apply_theme() once at the top of the page. Centralizing
colors/CSS here is what makes five separate view files read as one product
instead of five independently-styled pages.

Color choices are documented, not eyeballed:
- Brand chrome (navy/white/light-blue) is checked against WCAG contrast
  (computed with the standard relative-luminance formula) rather than picked
  by eye.
- Semantic colors (price up/down, Financial Health rating tiers) reuse hex
  values already validated for contrast and colorblind-safety in the
  project's dataviz reference palette, rather than inventing new ones.
  Status colors are deliberately NOT restyled to match the brand — that is
  what keeps "Weak" reading as bad and "Excellent" reading as good
  regardless of the navy/blue theme.
"""

import streamlit as st

# ---------------------------------------------------------------------------
# Brand chrome
# ---------------------------------------------------------------------------
NAVY_900 = "#0A1F44"       # sidebar background
NAVY_700 = "#12305C"       # hover / secondary navy surfaces
ACCENT_BLUE = "#2A78D6"    # buttons, links, active nav, "up" price/chart
WHITE = "#FFFFFF"
PAGE_BG = "#F4F7FB"        # subtle blue-tinted page background
INK_PRIMARY = "#0B1F33"
INK_SECONDARY = "#5B6B82"
BORDER = "#E2E8F0"

# ---------------------------------------------------------------------------
# Semantic colors — fixed meaning, never restyled to match the brand theme
# ---------------------------------------------------------------------------
UP_COLOR = ACCENT_BLUE      # price increase — deliberately not green
DOWN_COLOR = "#E34948"      # price decrease

RATING_COLORS = {
    "Excellent": "#0CA30C",
    "Good": "#FAB219",
    "Average": "#EC835A",
    "Weak": "#D03B3B",
}

FONT_IMPORT = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
"""

GLOBAL_CSS = f"""
<style>
    html, body, [class*="css"] {{
        font-family: 'Inter', -apple-system, 'Segoe UI', sans-serif;
    }}

    .stApp {{
        background-color: {PAGE_BG};
    }}

    .block-container {{
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1200px;
    }}

    /* Sidebar */
    section[data-testid="stSidebar"] {{
        background-color: {NAVY_900};
    }}
    section[data-testid="stSidebar"] * {{
        color: {WHITE} !important;
    }}
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a {{
        border-radius: 8px;
        margin: 2px 8px;
    }}
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a:hover {{
        background-color: {NAVY_700};
    }}
    section[data-testid="stSidebar"] [aria-current="page"] {{
        background-color: {NAVY_700};
        border-left: 3px solid {ACCENT_BLUE};
    }}

    /* Metrics */
    div[data-testid="stMetric"] {{
        background-color: {WHITE};
        border: 1px solid {BORDER};
        border-radius: 14px;
        padding: 18px 20px;
        box-shadow: 0 1px 3px rgba(10, 31, 68, 0.06);
    }}
    div[data-testid="stMetricLabel"] {{
        font-size: 0.82rem;
        color: {INK_SECONDARY};
        font-weight: 500;
    }}
    div[data-testid="stMetricValue"] {{
        color: {INK_PRIMARY};
        font-weight: 700;
        font-size: 1.5rem;
        overflow: visible;
        text-overflow: clip;
        white-space: nowrap;
    }}

    /* Buttons */
    .stButton > button, .stLinkButton > a, .stDownloadButton > button {{
        background-color: {ACCENT_BLUE};
        color: {WHITE} !important;
        border-radius: 10px;
        border: none;
        font-weight: 600;
    }}
    .stButton > button:hover, .stLinkButton > a:hover {{
        background-color: {NAVY_700};
        color: {WHITE} !important;
    }}

    /* Headings */
    h1, h2, h3, h4 {{
        color: {INK_PRIMARY};
        font-weight: 700;
    }}

    /* Bordered st.container(border=True) — used for cards holding real widgets */
    div[data-testid="stVerticalBlockBorderWrapper"] > div {{
        background-color: {WHITE};
        border-radius: 14px;
    }}
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        border-radius: 14px !important;
        border-color: {BORDER} !important;
        box-shadow: 0 1px 3px rgba(10, 31, 68, 0.06);
    }}

    /* Generic card (static HTML content only) */
    .el-card {{
        background-color: {WHITE};
        border: 1px solid {BORDER};
        border-radius: 14px;
        padding: 22px 24px;
        box-shadow: 0 1px 3px rgba(10, 31, 68, 0.06);
        margin-bottom: 16px;
    }}
    .el-card-title {{
        font-size: 1.05rem;
        font-weight: 700;
        color: {INK_PRIMARY};
        margin-bottom: 4px;
    }}
    .el-card-subtext {{
        color: {INK_SECONDARY};
        font-size: 0.9rem;
    }}

    /* Rating / status badges */
    .el-badge {{
        display: inline-block;
        padding: 4px 14px;
        border-radius: 999px;
        font-weight: 700;
        font-size: 0.85rem;
    }}

    /* Company / asset header */
    .el-header {{
        font-size: 1.6rem;
        font-weight: 700;
        color: {INK_PRIMARY};
        margin-bottom: 0;
    }}
    .el-subtext {{
        color: {INK_SECONDARY};
        font-size: 0.95rem;
        margin-top: 2px;
    }}
</style>
"""

SIDEBAR_BRAND = f"""
<div style="padding: 4px 8px 18px 8px;">
    <span style="font-size:1.25rem; font-weight:700; color:{WHITE}; letter-spacing:0.02em;">EQUITYLENS</span><br>
    <span style="font-size:0.75rem; color:#9FB3CC;">Equity Research &amp; Risk Intelligence</span>
</div>
"""


def apply_theme() -> None:
    st.markdown(FONT_IMPORT, unsafe_allow_html=True)
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
    st.sidebar.markdown(SIDEBAR_BRAND, unsafe_allow_html=True)
