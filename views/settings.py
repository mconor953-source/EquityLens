"""EquityLens — Settings.

Every control on this page is real and wired to actual app behavior —
saved to disk via settings_store.py, not just session state. There is no
disabled/"not yet functional" control here on purpose: Theme, Notifications,
and AI preferences were cut rather than shipped as decoration, since none
of them can be honestly implemented without infrastructure this app doesn't
have (no server process for scheduled alerts, no AI backend, and a
light/dark toggle would mean maintaining a second palette across every page
— out of scope for the minimal black/white design this app is built on).
"""

import streamlit as st

from theme import apply_theme
from assets import PREDEFINED_ASSETS
from settings_store import load_settings, save_settings

st.set_page_config(page_title="EquityLens — Settings", layout="wide")
apply_theme()

st.markdown("## Settings")
st.caption("Preferences for how EquityLens opens — saved to disk, so they persist across restarts.")

settings = load_settings()

st.write("")
col1, col2 = st.columns(2)

with col1:
    st.markdown("#### Default Asset")
    st.caption("Market Research and Trade Studio open to this asset.")

    classes = list(PREDEFINED_ASSETS.keys())
    saved_class = settings.get("default_asset_class", "Stocks")
    class_index = classes.index(saved_class) if saved_class in classes else 0
    default_class = st.selectbox("Default asset class", classes, index=class_index, key="settings_default_class")

    asset_options = list(PREDEFINED_ASSETS[default_class].keys())
    saved_asset = settings.get("default_asset")
    asset_index = asset_options.index(saved_asset) if saved_asset in asset_options else 0
    default_asset = st.selectbox("Default asset", asset_options, index=asset_index, key="settings_default_asset")

with col2:
    st.markdown("#### Default Chart Period")
    st.caption("The time range Market Research's price chart loads with.")

    period_options = ["1M", "3M", "6M", "1Y", "5Y"]
    saved_period = settings.get("default_period_label", "1Y")
    period_index = period_options.index(saved_period) if saved_period in period_options else 3
    default_period = st.radio(
        "Default chart period", period_options, index=period_index,
        horizontal=True, label_visibility="collapsed", key="settings_default_period",
    )

st.write("")
if st.button("Save Preferences"):
    save_settings({
        "default_asset_class": default_class,
        "default_asset": default_asset,
        "default_period_label": default_period,
    })
    st.success("Saved. Takes effect the next time you open Market Research or Trade Studio.")
