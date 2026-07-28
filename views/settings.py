"""EquityLens — Settings.

Every control on this page is a placeholder: laid out and styled like real
settings so the page doesn't feel empty, but none of it is wired to actual
app behavior yet. Each control says so explicitly rather than pretending.
"""

import streamlit as st

from theme import apply_theme
from components import compact_placeholder
from assets import PREDEFINED_ASSETS

st.set_page_config(page_title="EquityLens — Settings", layout="wide")
apply_theme()

st.markdown("## Settings")
st.caption("Preferences for how EquityLens looks and behaves.")

NOT_WIRED = "Not yet functional — saved for a future update."

st.write("")
col1, col2 = st.columns(2)

with col1:
    st.markdown("#### Theme")
    st.radio("Theme", ["Light", "Dark", "Match System"], horizontal=True,
             label_visibility="collapsed", disabled=True)
    st.caption(NOT_WIRED)

    st.write("")
    st.markdown("#### Default Asset")
    default_class = st.selectbox("Default asset class", list(PREDEFINED_ASSETS.keys()), disabled=True)
    st.selectbox("Default asset", list(PREDEFINED_ASSETS[default_class].keys()), disabled=True)
    st.caption(NOT_WIRED)

with col2:
    st.markdown("#### Notifications")
    st.checkbox("Price alerts", disabled=True)
    st.checkbox("News alerts", disabled=True)
    st.checkbox("Weekly portfolio summary", disabled=True)
    st.caption(NOT_WIRED)

    st.write("")
    st.markdown("#### Default Timeframe")
    st.radio("Default timeframe", ["1M", "3M", "6M", "1Y", "5Y"], index=3, horizontal=True,
              label_visibility="collapsed", disabled=True)
    st.caption(NOT_WIRED)

st.write("")
st.markdown("#### Future AI Preferences")
compact_placeholder("AI tone, depth, and per-page preferences")
