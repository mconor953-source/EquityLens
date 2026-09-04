"""EquityLens — Investment Ideas: the user's personal investment thesis register.

This is a manual idea tracker, not an automated signal generator: the
stance, conviction, thesis, risks, target, and invalidation level are all
typed in by the user and stored as-is in ideas_store.py (data/investment_ideas.json).
Nothing here decides BUY/HOLD/SELL for the user.

EquityLens's automated research — the Conviction Score / Financial Health /
Technical Rating built by idea_engine.py and scoring.py — still exists and
is shown here as a clearly separate "Automated Research (reference only)"
panel when data for the ticker is available, so it can inform the user's
decision without ever becoming it. That same automated engine continues to
power the Dashboard's Research Highlights and Market Research elsewhere in
the app.
"""

from datetime import date, datetime

import pandas as pd
import streamlit as st

from theme import apply_theme, INK_PRIMARY, INK_SECONDARY, INK_MUTED, STANCE_COLORS, STATUS_COLORS, RATING_COLORS, ACCENT_TEAL, ACCENT_BLUE, AMBER, RED
from components import render_html, price_change_html, page_header
from data_fetcher import (
    get_current_price_and_change,
    get_price_history,
    get_ticker_info,
    is_valid_ticker,
    format_market_price,
)
from idea_engine import build_investment_idea
from ideas_store import load_ideas, add_idea, update_idea, delete_idea, get_idea

st.set_page_config(page_title="EquityLens — Investment Ideas", layout="wide")
apply_theme()

page_header(
    "Investment Ideas",
    subtitle="Track your own views and theses — you decide the stance, conviction, and horizon.",
)

ASSET_CLASS_OPTIONS = ["Stock", "ETF", "Index", "Forex", "Commodity", "Crypto", "Other"]
STANCE_OPTIONS = ["BUY", "HOLD", "SELL"]
HORIZON_OPTIONS = ["Days", "Weeks", "Months", "1+ Year"]
STATUS_OPTIONS = ["Watching", "Active", "Closed"]

SORT_OPTIONS = {
    "Last Updated (newest)": ("updated_at", True),
    "Last Updated (oldest)": ("updated_at", False),
    "Conviction (highest)": ("conviction", True),
    "Conviction (lowest)": ("conviction", False),
    "Entry Date (newest)": ("entry_date", True),
    "Entry Date (oldest)": ("entry_date", False),
    "Asset (A-Z)": ("ticker", False),
}


def _parse_price(text: str, warn_label: str = None):
    text = (text or "").strip()
    if not text:
        return None
    try:
        return float(text.replace(",", "").replace("$", ""))
    except ValueError:
        if warn_label:
            st.warning(f"Couldn't read '{text}' as a number for {warn_label} — left blank.")
        return None


def _price_field(label: str, default, key: str, help_text: str = None) -> str:
    default_text = "" if default is None else f"{default:g}"
    return st.text_input(label, value=default_text, key=key, placeholder="Optional", help=help_text)


def _render_multiline(text: str) -> None:
    if not text or not text.strip():
        st.markdown("_Not filled in._")
        return
    st.markdown(text.replace("\n", "  \n"))


def _score_color(score: int) -> str:
    """Same 80/60/40 bands as scoring.py's Financial Health rating, applied
    to any 0-100 score (e.g. the user's own Conviction) for a consistent
    color language across the app — purely a display choice, not a new
    scoring rule."""
    if score >= 80:
        return ACCENT_TEAL
    if score >= 60:
        return ACCENT_BLUE
    if score >= 40:
        return AMBER
    return RED


def _status_badge_html(status: str) -> str:
    color = STATUS_COLORS.get(status, INK_SECONDARY)
    return (
        f'<span style="display:inline-flex; align-items:center; gap:6px; '
        f'font-weight:700; font-size:0.85rem; color:{color}; text-transform:uppercase; letter-spacing:0.03em;">'
        f'<span style="width:7px; height:7px; border-radius:50%; background-color:{color}; '
        f'display:inline-block; flex-shrink:0;"></span>{status}</span>'
    )


def _fetch_current_price(ticker: str):
    if not ticker:
        return None, None
    try:
        return get_current_price_and_change(ticker)
    except Exception:
        return None, None


def _fetch_automated_research(ticker: str, asset_class: str):
    """Best-effort automated read (idea_engine's Conviction Score) for the
    ticker on a manual idea — reference only. Returns None rather than
    fabricating anything if the ticker can't be resolved."""
    if not ticker:
        return None
    try:
        history = get_price_history(ticker, period="1y")
    except Exception:
        return None
    if history is None or history.empty or "Close" not in history.columns:
        return None

    info = None
    if asset_class == "Stock":
        raw_info = get_ticker_info(ticker)
        if is_valid_ticker(raw_info) and raw_info.get("quoteType") == "EQUITY":
            info = raw_info

    price = history["Close"].iloc[-1]
    return build_investment_idea(ticker, ticker, asset_class, price, history, info)


def _return_pct(entry_price, exit_price):
    if entry_price is None or exit_price is None or entry_price == 0:
        return None
    return (exit_price - entry_price) / entry_price * 100


# ---------- Prefill from Watchlists "Create Idea" ----------
prefill = st.session_state.pop("idea_prefill", None) or {}

# =====================================================================
# ADD INVESTMENT IDEA — collapsed behind a "New Idea" action by default
# (auto-opens if arriving via a Watchlist "Create Idea" handoff), rather
# than a permanently-open form dominating the page.
# =====================================================================
if "show_add_idea_form" not in st.session_state:
    st.session_state["show_add_idea_form"] = bool(prefill)

header_col, action_col = st.columns([5, 1])
with header_col:
    st.markdown("#### Your Ideas")
with action_col:
    toggle_label = "Close" if st.session_state["show_add_idea_form"] else "+ New Idea"
    if st.button(toggle_label, key="toggle_add_idea_form", use_container_width=True, type="primary"):
        st.session_state["show_add_idea_form"] = not st.session_state["show_add_idea_form"]
        st.rerun()

if st.session_state["show_add_idea_form"]:
    with st.container(border=True):
        st.markdown("###### Add Investment Idea")
        with st.form("add_idea_form", clear_on_submit=True):
            row1 = st.columns([1.1, 1.3, 2])
            with row1[0]:
                asset_class_default = prefill.get("asset_class", "Stock")
                asset_class_index = ASSET_CLASS_OPTIONS.index(asset_class_default) if asset_class_default in ASSET_CLASS_OPTIONS else 0
                f_asset_class = st.selectbox("Asset Class", ASSET_CLASS_OPTIONS, index=asset_class_index)
            with row1[1]:
                f_ticker = st.text_input("Ticker / Asset", value=prefill.get("ticker", ""), placeholder="e.g. AAPL")
            with row1[2]:
                f_title = st.text_input("Idea Title", placeholder="Optional — e.g. Apple long-term compounder")

            row2 = st.columns(4)
            with row2[0]:
                f_stance = st.selectbox("Direction / Stance", STANCE_OPTIONS)
            with row2[1]:
                f_horizon = st.selectbox("Time Horizon", HORIZON_OPTIONS, index=3)
            with row2[2]:
                f_conviction = st.slider("Conviction", min_value=1, max_value=100, value=50)
            with row2[3]:
                f_status = st.selectbox("Status", STATUS_OPTIONS, index=0)

            row3 = st.columns(4)
            with row3[0]:
                f_entry_date = st.date_input("Entry Date", value=date.today())
            with row3[1]:
                f_entry_price = _price_field("Entry Price", None, "add_entry_price")
            with row3[2]:
                f_target_price = _price_field("Target Price", None, "add_target_price")
            with row3[3]:
                f_invalidation_price = _price_field("Invalidation / Stop Level", None, "add_invalidation_price")

            f_thesis = st.text_area("Investment Thesis", height=90, placeholder="Why does this idea exist?")
            f_drivers = st.text_area("Why I Like It / Key Drivers", height=90)
            f_risks = st.text_area("Key Risks", height=90)
            f_strengthen = st.text_area("What Would Strengthen the Idea", height=70)
            f_weaken = st.text_area("What Would Weaken / Invalidate the Idea", height=70)
            f_notes = st.text_area("Notes", height=70, placeholder="Optional")

            submitted = st.form_submit_button("SAVE INVESTMENT IDEA", use_container_width=True, type="primary")

            if submitted:
                ticker_clean = f_ticker.strip().upper()
                if not ticker_clean:
                    st.error("Ticker / Asset is required.")
                else:
                    entry_price = _parse_price(f_entry_price, "Entry Price")
                    target_price = _parse_price(f_target_price, "Target Price")
                    invalidation_price = _parse_price(f_invalidation_price, "Invalidation / Stop Level")
                    add_idea({
                        "asset_class": f_asset_class,
                        "ticker": ticker_clean,
                        "title": f_title.strip(),
                        "stance": f_stance,
                        "horizon": f_horizon,
                        "conviction": f_conviction,
                        "status": f_status,
                        "entry_date": f_entry_date.isoformat(),
                        "entry_price": entry_price,
                        "target_price": target_price,
                        "invalidation_price": invalidation_price,
                        "thesis": f_thesis.strip(),
                        "drivers": f_drivers.strip(),
                        "risks": f_risks.strip(),
                        "strengthen": f_strengthen.strip(),
                        "weaken": f_weaken.strip(),
                        "notes": f_notes.strip(),
                        "exit_date": None,
                        "exit_price": None,
                        "closing_notes": None,
                    })
                    st.toast(f"Saved investment idea for {ticker_clean}.")
                    st.session_state["show_add_idea_form"] = False
                    st.rerun()

st.write("")

# =====================================================================
# SAVED INVESTMENT IDEAS
# =====================================================================
st.markdown("#### Saved Investment Ideas")

all_ideas = load_ideas()

if not all_ideas:
    st.info("No investment ideas saved yet — add your first one above.")
    st.stop()

with st.container(border=True):
    filt_cols = st.columns([1.2, 1, 1, 1, 1.4])
    with filt_cols[0]:
        f_class_filter = st.multiselect("Asset Class", ASSET_CLASS_OPTIONS, placeholder="All")
    with filt_cols[1]:
        f_stance_filter = st.multiselect("Stance", STANCE_OPTIONS, placeholder="All")
    with filt_cols[2]:
        f_horizon_filter = st.multiselect("Time Horizon", HORIZON_OPTIONS, placeholder="All")
    with filt_cols[3]:
        f_status_filter = st.multiselect("Status", STATUS_OPTIONS, placeholder="All")
    with filt_cols[4]:
        sort_choice = st.selectbox("Sort by", list(SORT_OPTIONS.keys()))

filtered = [
    idea for idea in all_ideas
    if (not f_class_filter or idea["asset_class"] in f_class_filter)
    and (not f_stance_filter or idea["stance"] in f_stance_filter)
    and (not f_horizon_filter or idea["horizon"] in f_horizon_filter)
    and (not f_status_filter or idea["status"] in f_status_filter)
]

sort_key, sort_reverse = SORT_OPTIONS[sort_choice]
filtered.sort(key=lambda i: (i.get(sort_key) is None, i.get(sort_key) or ""), reverse=sort_reverse)

st.write("")

if not filtered:
    st.info("No investment ideas match these filters.")
    st.stop()

table_rows = []
for idea in filtered:
    updated = idea.get("updated_at")
    updated_label = datetime.fromisoformat(updated).strftime("%Y-%m-%d %H:%M") if updated else "—"
    asset_label = idea["ticker"] + (f" · {idea['title']}" if idea.get("title") else "")
    table_rows.append({
        "Asset": asset_label,
        "Class": idea["asset_class"],
        "Stance": idea["stance"],
        "Horizon": idea["horizon"],
        "Conviction": idea["conviction"],
        "Status": idea["status"],
        "Entry Price": format_market_price(idea["entry_price"]) if idea.get("entry_price") is not None else "—",
        "Target Price": format_market_price(idea["target_price"]) if idea.get("target_price") is not None else "—",
        "Entry Date": idea.get("entry_date") or "—",
        "Last Updated": updated_label,
    })

table_df = pd.DataFrame(table_rows)

selection = st.dataframe(
    table_df,
    hide_index=True,
    use_container_width=True,
    on_select="rerun",
    selection_mode="single-row",
    key="ideas_table",
)

selected_rows = selection.selection.rows if selection and selection.selection else []
if selected_rows:
    st.session_state["selected_idea_id"] = filtered[selected_rows[0]]["id"]

st.caption(f"{len(filtered)} of {len(all_ideas)} ideas shown. Click a row to open its detail view below.")

st.write("")

# =====================================================================
# IDEA DETAIL VIEW
# =====================================================================
selected_id = st.session_state.get("selected_idea_id")
idea = get_idea(selected_id) if selected_id else None

if idea is None:
    st.stop()

mode_key = f"idea_mode_{idea['id']}"
mode = st.session_state.get(mode_key, "view")

st.markdown("#### Idea Detail")

with st.container(border=True):
    header_title = idea.get("title") or idea["ticker"]
    render_html(f'<p class="el-header">{header_title}</p>')
    render_html(f'<p class="el-subtext">{idea["ticker"]} &middot; {idea["asset_class"]}</p>')
    st.write("")

    view_cols = st.columns(4)
    with view_cols[0]:
        render_html(
            f'<div style="text-align:center;"><div style="font-size:1.5rem; font-weight:700; '
            f'color:{STANCE_COLORS.get(idea["stance"], INK_SECONDARY)};">{idea["stance"]}</div>'
            f'<div style="font-size:0.72rem; color:{INK_MUTED}; text-transform:uppercase; letter-spacing:0.05em;">Stance</div></div>'
        )
    with view_cols[1]:
        render_html(
            f'<div style="text-align:center;"><div style="font-size:1.5rem; font-weight:700; color:{_score_color(idea["conviction"])};">'
            f'{idea["conviction"]}<span style="font-size:0.9rem; color:{INK_MUTED};"> /100</span></div>'
            f'<div style="font-size:0.72rem; color:{INK_MUTED}; text-transform:uppercase; letter-spacing:0.05em;">Conviction</div></div>'
        )
    with view_cols[2]:
        render_html(
            f'<div style="text-align:center;"><div style="font-size:1.5rem; font-weight:700; color:{INK_PRIMARY};">'
            f'{idea["horizon"]}</div>'
            f'<div style="font-size:0.72rem; color:{INK_MUTED}; text-transform:uppercase; letter-spacing:0.05em;">Time Horizon</div></div>'
        )
    with view_cols[3]:
        render_html(
            f'<div style="text-align:center;">{_status_badge_html(idea["status"])}'
            f'<div style="font-size:0.72rem; color:{INK_MUTED}; text-transform:uppercase; letter-spacing:0.05em; margin-top:6px;">Status</div></div>'
        )

st.write("")

# ---------- Entry Information ----------
st.markdown("###### Entry Information")
current_price, current_change = _fetch_current_price(idea["ticker"])
entry_cols = st.columns(5)
entry_cols[0].metric("Entry Date", idea.get("entry_date") or "N/A")
entry_cols[1].metric("Entry Price", format_market_price(idea["entry_price"]) if idea.get("entry_price") is not None else "N/A")
entry_cols[2].metric("Current Price", format_market_price(current_price) if current_price is not None else "N/A")
entry_cols[3].metric("Target Price", format_market_price(idea["target_price"]) if idea.get("target_price") is not None else "N/A")
entry_cols[4].metric("Invalidation Level", format_market_price(idea["invalidation_price"]) if idea.get("invalidation_price") is not None else "N/A")

if idea["status"] == "Closed" and (idea.get("exit_date") or idea.get("exit_price") is not None):
    ret = _return_pct(idea.get("entry_price"), idea.get("exit_price"))
    exit_cols = st.columns(3)
    exit_cols[0].metric("Exit Date", idea.get("exit_date") or "N/A")
    exit_cols[1].metric("Exit Price", format_market_price(idea["exit_price"]) if idea.get("exit_price") is not None else "N/A")
    with exit_cols[2]:
        st.markdown(
            '<div style="font-size:0.78rem; color:%s; font-weight:600; text-transform:uppercase; '
            'letter-spacing:0.04em; margin-bottom:2px;">Return</div>' % INK_SECONDARY,
            unsafe_allow_html=True,
        )
        if ret is not None:
            render_html(f'<div style="font-size:1.45rem;">{price_change_html(ret)}</div>')
        else:
            render_html(f'<div style="font-size:1.45rem; color:{INK_MUTED};">N/A</div>')
    if idea.get("closing_notes"):
        st.caption(f"Closing notes: {idea['closing_notes']}")

st.write("")

# ---------- Automated Research (reference only) ----------
with st.expander("Automated Research (reference only) — not your decision", expanded=False):
    research = _fetch_automated_research(idea["ticker"], idea["asset_class"])
    if research is None:
        st.caption("Automated research unavailable for this ticker — check the symbol, or it may not be a supported market data ticker.")
    else:
        st.caption(
            "EquityLens's automated Conviction Score for this ticker, for reference only — "
            "your manual Stance/Conviction above is the one that counts."
        )
        r1, r2, r3 = st.columns(3)
        r1.metric("Conviction Score", f"{research['conviction']}/100")
        r2.metric("Suggested Stance", research["stance"])
        r3.metric("Long-Term Trend", research["trend_label"])
        if research["financial_health"]:
            fh = research["financial_health"]
            fh_color = RATING_COLORS.get(fh["rating"], INK_PRIMARY)
            render_html(
                f'<div style="font-size:0.78rem; color:{INK_SECONDARY}; font-weight:500; text-transform:uppercase; '
                f'letter-spacing:0.04em; margin-top:10px; margin-bottom:2px;">Financial Health Score</div>'
                f'<div style="font-size:1.45rem; font-weight:700; color:{fh_color};">{fh["total_score"]}/100 '
                f'<span style="font-size:0.95rem; font-weight:500;">&middot; {fh["rating"]}</span></div>'
            )
        else:
            st.caption("Fundamental data unavailable for this asset class.")

st.write("")

# ---------- Thesis / Drivers / Risks ----------
tcol1, tcol2 = st.columns(2)
with tcol1:
    st.markdown("###### Investment Thesis")
    _render_multiline(idea.get("thesis"))
    st.write("")
    st.markdown("###### Key Drivers")
    _render_multiline(idea.get("drivers"))
with tcol2:
    st.markdown("###### Risks")
    _render_multiline(idea.get("risks"))
    st.write("")
    st.markdown("###### Notes")
    _render_multiline(idea.get("notes"))

st.write("")

wcol1, wcol2 = st.columns(2)
with wcol1:
    st.markdown("###### What Would Strengthen the Idea")
    _render_multiline(idea.get("strengthen"))
with wcol2:
    st.markdown("###### What Would Weaken / Invalidate the Idea")
    _render_multiline(idea.get("weaken"))

st.write("")

# ---------- Actions ----------
action_cols = st.columns(4)
if action_cols[0].button("Edit Idea", use_container_width=True, key=f"btn_edit_{idea['id']}"):
    st.session_state[mode_key] = "edit" if mode != "edit" else "view"
    st.rerun()
if action_cols[1].button("Close Idea", use_container_width=True, key=f"btn_close_{idea['id']}"):
    st.session_state[mode_key] = "close" if mode != "close" else "view"
    st.rerun()
if action_cols[2].button("Delete Idea", use_container_width=True, key=f"btn_delete_{idea['id']}"):
    st.session_state[mode_key] = "delete" if mode != "delete" else "view"
    st.rerun()
if action_cols[3].button("Dismiss", use_container_width=True, key=f"btn_dismiss_{idea['id']}", help="Close this detail view"):
    st.session_state["selected_idea_id"] = None
    st.session_state[mode_key] = "view"
    st.rerun()

mode = st.session_state.get(mode_key, "view")

# ---------- Edit form ----------
if mode == "edit":
    st.write("")
    st.markdown("##### Edit Idea")
    with st.container(border=True):
        with st.form(f"edit_idea_form_{idea['id']}"):
            e1 = st.columns(4)
            with e1[0]:
                stance_idx = STANCE_OPTIONS.index(idea["stance"]) if idea["stance"] in STANCE_OPTIONS else 0
                e_stance = st.selectbox("Direction / Stance", STANCE_OPTIONS, index=stance_idx)
            with e1[1]:
                horizon_idx = HORIZON_OPTIONS.index(idea["horizon"]) if idea["horizon"] in HORIZON_OPTIONS else 0
                e_horizon = st.selectbox("Time Horizon", HORIZON_OPTIONS, index=horizon_idx)
            with e1[2]:
                e_conviction = st.slider("Conviction", min_value=1, max_value=100, value=int(idea["conviction"]))
            with e1[3]:
                status_idx = STATUS_OPTIONS.index(idea["status"]) if idea["status"] in STATUS_OPTIONS else 0
                e_status = st.selectbox("Status", STATUS_OPTIONS, index=status_idx)

            e2 = st.columns(3)
            with e2[0]:
                e_target_price = _price_field("Target Price", idea.get("target_price"), f"edit_target_{idea['id']}")
            with e2[1]:
                e_invalidation_price = _price_field("Invalidation / Stop Level", idea.get("invalidation_price"), f"edit_invalidation_{idea['id']}")
            with e2[2]:
                e_entry_price = _price_field("Entry Price", idea.get("entry_price"), f"edit_entry_{idea['id']}")

            e_thesis = st.text_area("Investment Thesis", value=idea.get("thesis") or "", height=90)
            e_drivers = st.text_area("Why I Like It / Key Drivers", value=idea.get("drivers") or "", height=90)
            e_risks = st.text_area("Key Risks", value=idea.get("risks") or "", height=90)
            e_strengthen = st.text_area("What Would Strengthen the Idea", value=idea.get("strengthen") or "", height=70)
            e_weaken = st.text_area("What Would Weaken / Invalidate the Idea", value=idea.get("weaken") or "", height=70)
            e_notes = st.text_area("Notes", value=idea.get("notes") or "", height=70)

            save_col, cancel_col = st.columns(2)
            save_clicked = save_col.form_submit_button("Save Changes", use_container_width=True, type="primary")
            cancel_clicked = cancel_col.form_submit_button("Cancel", use_container_width=True)

            if save_clicked:
                update_idea(idea["id"], {
                    "stance": e_stance,
                    "horizon": e_horizon,
                    "conviction": e_conviction,
                    "status": e_status,
                    "entry_price": _parse_price(e_entry_price, "Entry Price"),
                    "target_price": _parse_price(e_target_price, "Target Price"),
                    "invalidation_price": _parse_price(e_invalidation_price, "Invalidation / Stop Level"),
                    "thesis": e_thesis.strip(),
                    "drivers": e_drivers.strip(),
                    "risks": e_risks.strip(),
                    "strengthen": e_strengthen.strip(),
                    "weaken": e_weaken.strip(),
                    "notes": e_notes.strip(),
                })
                st.session_state[mode_key] = "view"
                st.toast("Idea updated.")
                st.rerun()
            elif cancel_clicked:
                st.session_state[mode_key] = "view"
                st.rerun()

# ---------- Close form ----------
elif mode == "close":
    st.write("")
    st.markdown("##### Close Idea")
    with st.container(border=True):
        with st.form(f"close_idea_form_{idea['id']}"):
            c1 = st.columns(2)
            with c1[0]:
                c_exit_date = st.date_input("Exit Date", value=date.today())
            with c1[1]:
                c_exit_price = _price_field("Exit Price", idea.get("exit_price"), f"close_exit_price_{idea['id']}")
            c_closing_notes = st.text_area("Closing Notes", value=idea.get("closing_notes") or "", height=80, placeholder="Optional")

            confirm_col, cancel_col = st.columns(2)
            confirm_clicked = confirm_col.form_submit_button("Confirm Close", use_container_width=True, type="primary")
            cancel_clicked = cancel_col.form_submit_button("Cancel", use_container_width=True)

            if confirm_clicked:
                update_idea(idea["id"], {
                    "status": "Closed",
                    "exit_date": c_exit_date.isoformat(),
                    "exit_price": _parse_price(c_exit_price, "Exit Price"),
                    "closing_notes": c_closing_notes.strip(),
                })
                st.session_state[mode_key] = "view"
                st.toast("Idea closed.")
                st.rerun()
            elif cancel_clicked:
                st.session_state[mode_key] = "view"
                st.rerun()

# ---------- Delete confirm ----------
elif mode == "delete":
    st.write("")
    with st.container(border=True):
        st.warning(f"Delete the investment idea for **{idea['ticker']}**? This cannot be undone.")
        confirm_col, cancel_col = st.columns(2)
        with confirm_col:
            confirm_delete_clicked = st.container(key="confirm-delete-btn").button(
                "Confirm Delete", use_container_width=True, key=f"confirm_delete_{idea['id']}"
            )
        if confirm_delete_clicked:
            delete_idea(idea["id"])
            st.session_state["selected_idea_id"] = None
            st.session_state[mode_key] = "view"
            st.toast("Idea deleted.")
            st.rerun()
        if cancel_col.button("Cancel", use_container_width=True, key=f"cancel_delete_{idea['id']}"):
            st.session_state[mode_key] = "view"
            st.rerun()

st.write("")
st.caption(
    "Investment Ideas is your personal register — stance, conviction, and thesis are entered by you and never "
    "generated automatically. Automated research above is reference only. Not investment advice."
)
