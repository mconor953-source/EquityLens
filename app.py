"""EquityLens — entrypoint and navigation router.

Each page's own content lives in views/ (imported by st.Page, not here) —
this file's only job is declaring the fixed page order and titles.
Run with: streamlit run app.py
"""

import streamlit as st

st.set_page_config(page_title="EquityLens", layout="wide")

pg = st.navigation(
    [
        st.Page("views/dashboard.py", title="Dashboard", default=True, icon=":material/space_dashboard:"),
        st.Page("views/market_research.py", title="Market Research", icon=":material/query_stats:"),
        st.Page("views/market_structure.py", title="Market Structure", icon=":material/candlestick_chart:"),
        st.Page("views/investment_ideas.py", title="Investment Ideas", icon=":material/lightbulb:"),
        st.Page("views/watchlists.py", title="Watchlists", icon=":material/visibility:"),
        st.Page("views/settings.py", title="Settings", icon=":material/settings:"),
    ]
)
pg.run()
