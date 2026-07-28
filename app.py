"""EquityLens — entrypoint and navigation router.

Each page's own content lives in views/ (imported by st.Page, not here) —
this file's only job is declaring the fixed page order and titles.
Run with: streamlit run app.py
"""

import streamlit as st

st.set_page_config(page_title="EquityLens", layout="wide")

pg = st.navigation(
    [
        st.Page("views/dashboard.py", title="Dashboard", default=True),
        st.Page("views/market_research.py", title="Market Research"),
        st.Page("views/trade_studio.py", title="Trade Studio"),
        st.Page("views/watchlists.py", title="Watchlists"),
        st.Page("views/settings.py", title="Settings"),
    ]
)
pg.run()
