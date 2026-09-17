"""
app.py
-------
Streamlit dashboard for the Sustainable Tourism Pressure & Risk Monitoring System.

Overview page improvements:
- "Last updated" + data source info moved to the sidebar (shown once, not
  repeated on every page)
- Fixed a real bug: markdown **bold** syntax doesn't render inside a raw
  HTML block - the destination name in the executive summary was literally
  showing as **Mount Kinabalu** instead of bold text. Now uses real <b> tags.
- Removed the duplicate full-text alert banner from the page - elevated
  status lives only in the sidebar now, as an expandable list
- "Recommended Actions" is now a collapsible expander, not always-visible
- Key Metrics and Highlights now sit SIDE BY SIDE (metrics left, highlights
  right), each as a compact 2-per-row grid of square cards
- Card borders/shadows polished for a nicer, more framed look

Sidebar navigation:
- Scope selector (Land/Marine/All pill buttons) + page navigator
- Clicking any map marker instantly navigates to a dedicated Location
  Detail page with trend charts and (for marine) a verified-accurate
  component breakdown + what-if simulator

All other underlying logic (scores, colors, confidence, leading-factor
detection, what-if simulator) is unchanged.
"""

import json
import os
from datetime import datetime

import altair as alt
import pandas as pd
import pydeck as pdk
import streamlit as st

st.set_page_config(page_title="Tourism Pressure & Risk Monitor", layout="wide")

# ============================== CUSTOM STYLING ==============================
st.markdown("""
<style>
.block-container, div[data-testid="stMainBlockContainer"] {
    padding-top: 1.5rem !important;
    padding-bottom: 1rem !important;
}
.st-key-header_row {
    background-color: #CFE4F5;
    border: 1px solid #A9CDE3;
    padding: 10px 16px 2px 16px;
    border-radius: 10px;
    margin-bottom: 8px;
    box-shadow: 0 3px 10px rgba(27,58,75,0.08);
}
.st-key-header_row div[data-testid="stHorizontalBlock"] {
    align-items: center;
}
.st-key-header_row div[data-testid="stButton"] button {
    all: unset;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
}
.st-key-header_row div[data-testid="stButton"] button p {
    font-size: 1.8rem !important;
    line-height: 1 !important;
    margin: 0 !important;
}
.st-key-header_row div[data-testid="stButton"] button:hover,
.st-key-header_row div[data-testid="stButton"] button:focus,
.st-key-header_row div[data-testid="stButton"] button:active {
    color: #ef4444;
    outline: none;
}
.st-key-elevated_panel {
    background-color: transparent;
    padding: 4px 0;
}
hr {
    margin: 0.5rem 0 !important;
    border-color: #A9CDE3 !important;
}
h1 {
    font-size: 1.7rem !important;
    margin-bottom: 0.2rem !important;
    color: #1B3A4B !important;
}
h2 {
    color: #1B3A4B !important;
}
h3 {
    margin-top: 0.3rem !important;
    margin-bottom: 0.2rem !important;
    border-bottom: 2px solid #1C7293;
    padding-bottom: 3px;
    color: #1B3A4B !important;
}
div[data-testid="stMetric"] {
    background: linear-gradient(135deg, #FFFFFF, #EDF6FC);
    border: 2px solid #A9CDE3;
    border-radius: 12px;
    padding: 10px 14px;
    box-shadow: 0 3px 10px rgba(27,58,75,0.10);
    height: 96px;
    display: flex;
    flex-direction: column;
    justify-content: center;
}
div[data-testid="stMetric"] label {
    color: #4A6572 !important;
}
div[data-testid="stMetricValue"] {
    color: #0E3A5C !important;
    font-size: 1.6rem !important;
}
.highlight-card {
    background: linear-gradient(135deg, #FFFFFF, #EDF6FC);
    border: 2px solid #A9CDE3;
    border-radius: 12px;
    padding: 10px 12px;
    box-shadow: 0 3px 10px rgba(27,58,75,0.10);
    min-height: 96px;
    margin-bottom: 16px;
    display: flex;
    flex-direction: column;
    justify-content: center;
}
.highlight-title {
    font-size: 0.85rem;
    font-weight: 700;
    margin-bottom: 3px;
    color: #1B3A4B;
}
.highlight-value {
    font-size: 0.98rem;
    font-weight: 700;
    color: #0E3A5C;
}
.highlight-sub {
    font-size: 0.78rem;
    color: #4A6572;
}
.card-heading {
    text-align: center;
    font-weight: 700;
    font-size: 1rem;
    color: #1B3A4B;
    margin: -4px 0 12px 0;
    padding-bottom: 8px;
    border-bottom: 1px solid #B9CCD6;
}
.st-key-kpi_box, .st-key-highlight_box, .st-key-risktier_box, .st-key-rank_box,
.st-key-map_land_box, .st-key-map_marine_box, .st-key-map_all_box,
.st-key-detail_land_chart_box, .st-key-detail_land_complaint_box,
.st-key-detail_marine_chart_box, .st-key-detail_marine_driving_box,
.st-key-dataconf_box, .st-key-drilldown_box,
.st-key-trend_compare_box, .st-key-tier_donut_box,
.st-key-risk_heatmap_box, .st-key-complaint_trend_box {
    background: linear-gradient(135deg, #FFFFFF 0%, #EDF6FC 100%) !important;
    border: 2px solid #A9CDE3 !important;
    border-radius: 14px !important;
    box-shadow: 0 4px 14px rgba(27,58,75,0.10) !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: linear-gradient(135deg, #FFFFFF 0%, #EDF6FC 100%) !important;
    border: 2px solid #A9CDE3 !important;
    border-radius: 14px !important;
    box-shadow: 0 4px 14px rgba(27,58,75,0.10) !important;
}
div[data-testid="stDataFrame"] {
    border: 2px solid #23516B;
    border-radius: 10px;
    overflow: hidden;
}
.accent-bar {
    height: 5px;
    border-radius: 8px 8px 0 0;
    margin-bottom: -1px;
}
.exec-summary {
    background: linear-gradient(135deg, #FFFFFF, #EDF6FC);
    border: 2px solid #A9CDE3;
    border-radius: 10px;
    padding: 8px 14px;
    font-size: 0.88rem;
    color: #1B3A4B;
    margin-top: 0px;
    margin-bottom: 18px;
}
.action-card {
    background-color: #F7CACA;
    border: 2px solid #E39B9B;
    border-radius: 10px;
    padding: 8px 12px;
    margin-bottom: 5px;
    font-size: 0.85rem;
    color: #1B3A4B;
    min-height: 90px;
    display: flex;
    flex-direction: column;
    justify-content: center;
}
.action-card.high {
    background-color: #F0A8A8;
    border-color: #D97B7B;
}
.confidence-badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 0.78rem;
    font-weight: 700;
}
.confidence-high { background-color: #d1fae5; color: #065f46; }
.confidence-medium { background-color: #fef3c7; color: #92400e; }
.confidence-low { background-color: #fee2e2; color: #991b1b; }

.selected-card {
    background: linear-gradient(135deg, #FFFFFF, #EDF6FC);
    border: 2px solid #A9CDE3;
    border-radius: 10px;
    padding: 10px 12px;
    box-shadow: 0 3px 10px rgba(27,58,75,0.10);
    margin-top: 6px;
}
.selected-card-title {
    font-size: 0.82rem;
    font-weight: 700;
    color: #1C7293;
    margin-bottom: 5px;
}
.selected-card-name {
    font-size: 0.95rem;
    font-weight: 700;
    color: #1B3A4B;
    margin-bottom: 4px;
}
.selected-row {
    display: flex;
    justify-content: space-between;
    padding: 3px 0;
    border-bottom: 1px solid #B9CCD6;
    font-size: 0.78rem;
}
.selected-row-label {
    color: #4A6572;
}
.selected-row-value {
    color: #1B3A4B;
    font-weight: 600;
}
div[data-testid="stRadio"] {
    background: #FFFFFF;
    border: 1px solid #A9CDE3;
    border-radius: 10px;
    padding: 8px 10px;
}
</style>
""", unsafe_allow_html=True)

LAND_PATH = "sample_data/land_pressure_scores.csv"
MARINE_PATH = "sample_data/marine_risk_tiers.csv"
METADATA_PATH = "sample_data/destination_metadata.csv"
BOUNDARY_PATH = "sample_data/malaysia_states.json"
LAND_REVIEWS_PATH = "sample_data/scored_reviews_land.csv"
MARINE_REVIEWS_PATH = "sample_data/scored_reviews_marine.csv"

CONFIDENCE_HIGH = 200
CONFIDENCE_MEDIUM = 100


def accent_bar(color: str):
    st.markdown(f'<div class="accent-bar" style="background:{color};"></div>', unsafe_allow_html=True)


def confidence_label(total_reviews: int) -> str:
    if total_reviews >= CONFIDENCE_HIGH:
        return "High"
    elif total_reviews >= CONFIDENCE_MEDIUM:
        return "Medium"
    return "Low"

def confidence_box_html(total_reviews: int) -> str:
    """A colored confidence card - green/amber/red by tier, tuned to a
    mid-brightness range (~190-210) so it's neither washed-out pale nor
    heavy/dark, matching st.metric's card height for row alignment."""
    label = confidence_label(total_reviews)
    box_colors = {
        "High": ("#86efac", "#065f46"),
        "Medium": ("#fcd34d", "#78350f"),
        "Low": ("#fca5a5", "#991b1b"),
    }
    bg, fg = box_colors[label]
    return (
        f'<div style="background:{bg}; color:{fg}; border-radius:12px; padding:10px 14px; '
        f'text-align:center; font-weight:700; height:96px; box-sizing:border-box; '
        f'display:flex; flex-direction:column; justify-content:center;">'
        f'<div style="font-size:0.85rem; margin-bottom:2px;">Confidence</div>'
        f'<div style="font-size:1.1rem;">{label}</div>'
        f'<div style="font-size:0.75rem; font-weight:500;">({int(total_reviews)} reviews)</div>'
        f'</div>'
    )


def confidence_badge_html(total_reviews: int) -> str:
    label = confidence_label(total_reviews)
    css_class = {"High": "confidence-high", "Medium": "confidence-medium", "Low": "confidence-low"}[label]
    return f'<span class="confidence-badge {css_class}">{label} confidence ({int(total_reviews)} reviews)</span>'


@st.cache_data
def load_data():
    land = pd.read_csv(LAND_PATH)
    marine = pd.read_csv(MARINE_PATH)
    meta = pd.read_csv(METADATA_PATH)

    boundary = None
    if os.path.exists(BOUNDARY_PATH):
        with open(BOUNDARY_PATH) as f:
            boundary = json.load(f)

    land_reviews = pd.read_csv(LAND_REVIEWS_PATH) if os.path.exists(LAND_REVIEWS_PATH) else None
    marine_reviews = pd.read_csv(MARINE_REVIEWS_PATH) if os.path.exists(MARINE_REVIEWS_PATH) else None

    if "is_forecast" not in marine.columns:
        marine = marine.copy()
        marine["is_forecast"] = False

    return land, marine, meta, boundary, land_reviews, marine_reviews


def risk_color_from_tier(tier: str):
    return {"Low": [16, 185, 129], "Medium": [245, 158, 11], "High": [239, 68, 68]}.get(tier, [148, 163, 184])


def risk_color_from_score(score: float):
    score = max(0, min(100, score))
    if score < 50:
        t = score / 50
        r = int(16 + (245 - 16) * t)
        g = int(185 + (158 - 185) * t)
        b = int(129 + (11 - 129) * t)
    else:
        t = (score - 50) / 50
        r = int(245 + (239 - 245) * t)
        g = int(158 + (68 - 158) * t)
        b = int(11 + (68 - 11) * t)
    return [r, g, b]


def radius_from_score(score: float, min_r=6000, max_r=16000):
    """Marker radius in METERS, tied to real geography, so circles shrink
    naturally as you zoom out. Combined with radius_min_pixels/
    radius_max_pixels on the layer itself, this keeps markers clearly
    visible at every zoom level without ever ballooning when zoomed in."""
    score = max(0, min(100, score))
    return min_r + (max_r - min_r) * (score / 100)


def simulate_visitor_cap(marine_df: pd.DataFrame, marine_park: str, reduction_pct: float) -> pd.DataFrame:
    visitor_min, visitor_max = marine_df["visitors"].min(), marine_df["visitors"].max()

    subset = marine_df[marine_df["marine_park"] == marine_park].copy()
    subset["visitors"] = subset["visitors"] * (1 - reduction_pct / 100)

    if visitor_max == visitor_min:
        subset["visitor_norm"] = 0.0
    else:
        subset["visitor_norm"] = ((subset["visitors"] - visitor_min) / (visitor_max - visitor_min)).clip(0, 1)

    subset["risk_score"] = (
        0.35 * subset["visitor_norm"]
        + 0.35 * subset["sst_anomaly_norm"]
        + 0.15 * subset["turbidity_norm"]
        + 0.15 * subset["neg_review_norm"]
    ) * 100
    subset["risk_score"] = subset["risk_score"].clip(0, 100)
    subset["risk_tier"] = subset["risk_score"].apply(
        lambda s: "High" if s >= 66 else "Medium" if s >= 33 else "Low"
    )
    return subset


def score_to_tier(score: float) -> str:
    if score >= 66:
        return "High"
    elif score >= 33:
        return "Medium"
    return "Low"


def latest_actual(df: pd.DataFrame, group_col: str) -> pd.DataFrame:
    actual = df[df["is_forecast"] == False]
    return actual.sort_values("month").groupby(group_col).tail(1)


def biggest_delta(df: pd.DataFrame, group_col: str, score_col: str, ascending: bool):
    """ascending=True -> most improved (biggest decrease); False -> fastest rising."""
    actual = df[df["is_forecast"] == False].sort_values([group_col, "month"]).copy()
    actual["delta"] = actual.groupby(group_col)[score_col].diff()
    latest = actual.groupby(group_col).tail(1).dropna(subset=["delta"])
    if latest.empty:
        return None, None
    row = latest.sort_values("delta", ascending=ascending).iloc[0]
    return row[group_col], row["delta"]


def negative_mentions_by_aspect(reviews_df: pd.DataFrame) -> pd.DataFrame:
    neg = reviews_df[reviews_df["sentiment_score"] < -0.05]
    neg = neg[neg["aspect"] != "general"]
    return (
        neg.groupby("aspect").size().reset_index(name="negative_mentions")
        .sort_values("negative_mentions", ascending=False)
    )


def render_kpi_grid(items):
    """items: list of (label, value, help_text) tuples. Renders 2 per row
    as square-ish cards, so groups of 3 or 4 metrics form a compact grid
    instead of one long horizontal row."""
    for i in range(0, len(items), 2):
        row = items[i:i + 2]
        cols = st.columns(2)
        for col, (label, value, help_text) in zip(cols, row):
            with col:
                st.metric(label, value, help=help_text)


def render_highlight_grid(items):
    """items: list of (emoji, title, name, value_text, border_color) tuples.
    Renders 2 per row, matching render_kpi_grid's layout on the other side
    of the page."""
    for i in range(0, len(items), 2):
        row = items[i:i + 2]
        cols = st.columns(2)
        for col, (emoji, title, name, value_text, color) in zip(cols, row):
            highlight_card(col, emoji, title, name, value_text, color)


def highlight_card(col, emoji, title, name, value_text, border_color=None):
    with col:
        if name:
            body = f'<div class="highlight-value">{name}</div><div class="highlight-sub">{value_text}</div>'
        else:
            body = '<div class="highlight-sub">Not enough history yet</div>'
        st.markdown(
            f'<div class="highlight-card">'
            f'<div class="highlight-title">{emoji} {title}</div>{body}</div>',
            unsafe_allow_html=True,
        )


def style_score_table(df: pd.DataFrame, score_col: str, tier_col: str = None):
    """Colors the score (and optional tier) column's background by risk
    tier, formats all numeric values to exactly 3 decimal places, and
    drops the pandas row index (which otherwise leaks through as a
    meaningless extra number column in st.dataframe)."""
    df = df.reset_index(drop=True)
    tier_colors = {
        "Low": ("#d1fae5", "#065f46"),
        "Medium": ("#fef3c7", "#92400e"),
        "High": ("#fee2e2", "#991b1b"),
    }

    def color_by_score(v):
        bg, fg = tier_colors[score_to_tier(v)]
        return f"background-color:{bg}; color:{fg}; font-weight:600;"

    def color_by_tier_label(v):
        bg, fg = tier_colors.get(v, ("", ""))
        return f"background-color:{bg}; color:{fg}; font-weight:600;" if bg else ""

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    styler = df.style.map(color_by_score, subset=[score_col])
    if tier_col:
        styler = styler.map(color_by_tier_label, subset=[tier_col])
    if numeric_cols:
        styler = styler.format({col: "{:.3f}" for col in numeric_cols})
    return styler

def style_confidence_table(df: pd.DataFrame, confidence_col: str = "Confidence"):
    """Colors the Confidence column to match the confidence-badge CSS
    (High/Medium/Low), and drops the pandas row index."""
    df = df.reset_index(drop=True)
    conf_colors = {
        "High": ("#d1fae5", "#065f46"),
        "Medium": ("#fef3c7", "#92400e"),
        "Low": ("#fee2e2", "#991b1b"),
    }

def confidence_table_html(df: pd.DataFrame, first_col_left: bool = True, max_height: int = 320) -> str:
    """Renders the Data Confidence table as a real HTML table (so headers
    can be centered, unlike st.dataframe's canvas-rendered grid). Wrapped
    in a fixed-height scrollable div so a long table scrolls WITHIN its
    own box instead of pushing the whole page down. Every cell explicitly
    resets border:none before setting only border-bottom, so no stray
    default browser vertical lines appear - only our own intentional
    horizontal dividers show, all matching in thickness and colour."""
    tier_colors = {
        "High": ("#d1fae5", "#065f46"),
        "Medium": ("#fef3c7", "#92400e"),
        "Low": ("#fee2e2", "#991b1b"),
    }
    header_cells = "".join(
        f'<th style="text-align:center; padding:8px 12px; border:none; border-bottom:4px solid #4A6572; '
        f'color:#1B3A4B; position:sticky; top:0; background:#FFFFFF;">{col}</th>'
        for col in df.columns
    )
    rows_html = ""
    for _, row in df.iterrows():
        cells = ""
        for i, col in enumerate(df.columns):
            align = "left" if (i == 0 and first_col_left) else "center"
            val = row[col]
            if col == "Confidence":
                bg, fg = tier_colors.get(val, ("", "#1B3A4B"))
                cell_content = f'<span style="background:{bg}; color:{fg}; padding:2px 10px; border-radius:12px; font-weight:700; font-size:0.82rem;">{val}</span>'
            else:
                cell_content = val
            cells += f'<td style="text-align:{align}; padding:6px 12px; border:none; border-bottom:3px solid #4A6572; color:#1B3A4B;">{cell_content}</td>'
        rows_html += f"<tr>{cells}</tr>"
    table = f'<table style="width:100%; border-collapse:collapse; box-sizing:border-box;"><thead><tr>{header_cells}</tr></thead><tbody>{rows_html}</tbody></table>'
    return f'<div style="max-height:{max_height}px; overflow-y:auto; box-sizing:border-box; padding-right:6px;">{table}</div>'

def score_table_html(df: pd.DataFrame, score_col: str, tier_col: str = None, first_col_left: bool = True, max_height: int = None) -> str:
    """Same visual treatment as confidence_table_html (centered headers,
    thick dark horizontal-only borders, no stray vertical lines) but for
    score-based tables: colors the score column (and optional tier
    column) by risk tier, and every numeric value shows exactly 3
    decimal places. Used on the Map page to match the Deep Dive table format."""
    tier_colors = {
        "Low": ("#d1fae5", "#065f46"),
        "Medium": ("#fef3c7", "#92400e"),
        "High": ("#fee2e2", "#991b1b"),
    }
    header_cells = "".join(
        f'<th style="text-align:center; padding:8px 12px; border:none; border-bottom:4px solid #4A6572; '
        f'color:#1B3A4B; position:sticky; top:0; background:#FFFFFF;">{col}</th>'
        for col in df.columns
    )
    rows_html = ""
    for _, row in df.iterrows():
        cells = ""
        for i, col in enumerate(df.columns):
            align = "left" if (i == 0 and first_col_left) else "center"
            val = row[col]
            if col == score_col:
                bg, fg = tier_colors[score_to_tier(val)]
                display_val = f"{val:.3f}" if isinstance(val, float) else val
                cell_content = f'<span style="background:{bg}; color:{fg}; padding:2px 10px; border-radius:12px; font-weight:700; font-size:0.82rem;">{display_val}</span>'
            elif tier_col and col == tier_col:
                bg, fg = tier_colors.get(val, ("", "#1B3A4B"))
                cell_content = f'<span style="background:{bg}; color:{fg}; padding:2px 10px; border-radius:12px; font-weight:700; font-size:0.82rem;">{val}</span>'
            else:
                cell_content = val
            cells += f'<td style="text-align:{align}; padding:6px 12px; border:none; border-bottom:3px solid #4A6572; color:#1B3A4B;">{cell_content}</td>'
        rows_html += f"<tr>{cells}</tr>"
    table = f'<table style="width:100%; border-collapse:collapse; box-sizing:border-box;"><thead><tr>{header_cells}</tr></thead><tbody>{rows_html}</tbody></table>'
    if max_height:
        return f'<div style="max-height:{max_height}px; overflow-y:auto; box-sizing:border-box; padding-right:6px;">{table}</div>'
    return table

    def color_by_confidence(v):
        bg, fg = conf_colors.get(v, ("", ""))
        return f"background-color:{bg}; color:{fg}; font-weight:600;" if bg else ""

    return df.style.map(color_by_confidence, subset=[confidence_col])

def render_click_hint():
    st.caption("💡 Click a marker on the map to open its full detail page.")


def legend_html(items):
    """items: list of (label, color) tuples. Renders a compact colour-key legend."""
    rows = "".join(
        f'<div style="display:flex;align-items:center;gap:6px;margin-bottom:3px;">'
        f'<span style="width:10px;height:10px;border-radius:50%;background:{color};display:inline-block;"></span>'
        f'<span style="font-size:0.82rem;color:#5A6B72;">{label}</span></div>'
        for label, color in items
    )
    return f'<div style="margin-top:8px;padding-top:8px;border-top:1px solid #E5E9EC;">{rows}</div>'


def land_leading_factor(row) -> str:
    if row["negative_share_norm"] > row["visitor_growth_norm"]:
        return "rising negative sentiment in reviews"
    return "rapid visitor growth"


def marine_leading_factor(row) -> str:
    components = {
        "high visitor volume": row["visitor_norm"],
        "elevated sea temperature (bleaching risk)": row["sst_anomaly_norm"],
        "high water turbidity": row["turbidity_norm"],
        "negative environmental reviews": row["neg_review_norm"],
    }
    return max(components, key=components.get)


def land_recommended_action(row) -> str:
    factor = land_leading_factor(row)
    if "sentiment" in factor:
        return "Investigate recurring complaint themes (see the complaint breakdown in Trends & Analysis) and address the specific issue driving negative reviews."
    return "Consider promoting off-peak visiting periods or timed-entry ticketing to spread out visitor load."


def marine_recommended_action(row) -> str:
    factor = marine_leading_factor(row)
    if "visitor volume" in factor:
        return "Consider a temporary visitor cap reduction - use the What-If Simulator in Deep Dive to estimate the impact."
    if "sea temperature" in factor:
        return "Environmental stress detected. Increase monitoring frequency and consider a temporary access restriction during peak heat periods."
    if "turbidity" in factor:
        return "Water clarity is degraded. Investigate nearby runoff or boat traffic as a possible cause."
    return "Investigate recurring environmental complaints (trash, coral damage) in recent reviews."


# ============================== LOAD DATA ==============================

land_df, marine_df, meta_df, boundary_geojson, land_reviews_df, marine_reviews_df = load_data()

land_latest_all = latest_actual(land_df, "destination").copy()
land_latest_all["risk_tier"] = land_latest_all["pressure_score"].apply(score_to_tier)

marine_latest_all = latest_actual(marine_df, "marine_park").copy()

land_total_reviews = land_df[land_df["is_forecast"] == False].groupby("destination")["n_reviews"].sum()
marine_total_reviews = marine_df.groupby("marine_park")["visitors"].sum()

combined_latest = pd.concat([
    land_latest_all.rename(columns={"destination": "name", "pressure_score": "score"})[["name", "score", "risk_tier", "month"]].assign(type="Land"),
    marine_latest_all.rename(columns={"marine_park": "name", "risk_score": "score"})[["name", "score", "risk_tier", "month"]].assign(type="Marine"),
], ignore_index=True)
combined_latest = combined_latest.merge(
    meta_df[["destination", "lat", "lon"]].rename(columns={"destination": "name"}), on="name", how="left"
)

elevated_land = land_latest_all[land_latest_all["risk_tier"] != "Low"]
elevated_marine = marine_latest_all[marine_latest_all["risk_tier"] != "Low"]
elevated_count = len(elevated_land) + len(elevated_marine)

# ============================== SIDEBAR: NAVIGATION ==============================

MAIN_PAGES = ["Overview", "Map", "Trends & Analysis", "Deep Dive"]

if "active_page" not in st.session_state:
    st.session_state.active_page = "Overview"
if "selected_detail" not in st.session_state:
    st.session_state.selected_detail = None


def navigate_to_detail(event, layer_id, name_field, kind):
    """Checks a map's click event; if a NEW marker was clicked (different
    from whatever is already stored), stores its full data and jumps
    straight to the Location Detail page via a rerun."""
    if event is None:
        return
    objects = event.selection.objects.get(layer_id, [])
    if not objects:
        return
    obj = dict(objects[0])
    obj["_kind"] = kind
    obj["_name_field"] = name_field
    already_showing = (
        st.session_state.selected_detail is not None
        and st.session_state.selected_detail.get(name_field) == obj.get(name_field)
        and st.session_state.active_page == "Location Detail"
    )
    if not already_showing:
        st.session_state.selected_detail = obj
        st.session_state.active_page = "Location Detail"
        st.rerun()


with st.sidebar:
    st.markdown(
        '<div style="line-height:1.3;">'
        '<span style="font-size:1.3rem; font-weight:700; color:#1B3A4B;">🏝️ Tourism Monitor</span><br>'
        '<span style="font-size:0.82rem; color:#4A6572;">DOSM Datathon 2026</span>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.divider()

    layer_choice = st.selectbox(
        "Scope", ["Land Pressure", "Marine Risk", "All"]
    )
    st.caption("Filters every page by Land, Marine, or both.")

    st.divider()

    default_radio_page = st.session_state.active_page if st.session_state.active_page in MAIN_PAGES else "Map"
    nav_choice = st.radio(
        "Go to",
        MAIN_PAGES,
        index=MAIN_PAGES.index(default_radio_page),
        format_func=lambda p: {
            "Overview": "📋 Overview",
            "Map": "🗺️ Map",
            "Trends & Analysis": "📈 Trends & Analysis",
            "Deep Dive": "🔍 Deep Dive",
        }[p],
        label_visibility="collapsed",
        key="nav_radio_widget",
    )
    if nav_choice != default_radio_page:
        st.session_state.active_page = nav_choice
        st.session_state.selected_detail = None

    st.divider()
    if elevated_count == 0:
        st.success("✅ All Low")

    st.divider()
    with st.expander("ℹ️ About this dashboard"):
        st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        st.caption(
            "Data sources: real Google Reviews (translated), NOAA Coral Reef "
            "Watch SST via Google Earth Engine, official DOSM boundary data."
        )

page = st.session_state.active_page

if "show_warning_panel" not in st.session_state:
    st.session_state.show_warning_panel = False

# ============================== MAIN AREA ==============================

# Scope-aware: the warning icon only shows when the CURRENTLY SELECTED
# scope actually has elevated destinations - e.g. viewing "Marine Risk"
# when only a land destination is elevated shows no icon at all.
if layer_choice == "Land Pressure":
    scope_elevated_count = len(elevated_land)
elif layer_choice == "Marine Risk":
    scope_elevated_count = len(elevated_marine)
else:
    scope_elevated_count = elevated_count

with st.container(key="header_row"):
    title_col, warn_col = st.columns([11, 1])
    with title_col:
        st.title("Sustainable Tourism Pressure & Risk Monitoring System")
    with warn_col:
        if scope_elevated_count > 0:
            if st.button("⚠️", key="warn_btn", help=f"{scope_elevated_count} destination(s) elevated - click for details"):
                st.session_state.show_warning_panel = not st.session_state.show_warning_panel
        else:
            st.session_state.show_warning_panel = False

if page == "Overview":

    if layer_choice == "Land Pressure":
        top = land_latest_all.sort_values("pressure_score", ascending=False).iloc[0]
        kpi_items = [
            ("Land Destinations Monitored", len(land_latest_all), None),
            ("Highest Pressure", f"{top['pressure_score']:.1f} / 100",
             f"{top['destination']} - score is 0-100, combining review sentiment + visitor growth"),
            ("At Medium/High Risk", len(elevated_land),
             "Count of land destinations currently above the Low risk threshold (score >= 33)"),
        ]
    elif layer_choice == "Marine Risk":
        top = marine_latest_all.sort_values("risk_score", ascending=False).iloc[0]
        kpi_items = [
            ("Marine Parks Monitored", len(marine_latest_all), None),
            ("Highest Risk", f"{top['risk_score']:.1f} / 100",
             f"{top['marine_park']} - score is 0-100, combining visitors + sea temperature + turbidity + reviews"),
            ("At Medium/High Risk", len(elevated_marine),
             "Count of marine parks currently above the Low risk threshold (score >= 33)"),
        ]
    else:  # All
        top_land = land_latest_all.sort_values("pressure_score", ascending=False).iloc[0]
        top_marine = marine_latest_all.sort_values("risk_score", ascending=False).iloc[0]
        kpi_items = [
            ("Destinations Monitored", len(combined_latest), None),
            ("Highest Land Pressure", f"{top_land['pressure_score']:.1f} / 100", top_land["destination"]),
            ("Highest Marine Risk", f"{top_marine['risk_score']:.1f} / 100", top_marine["marine_park"]),
            ("At Medium/High Risk", elevated_count,
             "Combined count across land and marine, currently above the Low threshold (score >= 33)"),
        ]

    # Build the Highlights list for the current scope
    if layer_choice == "Land Pressure":
        name1, delta1 = biggest_delta(land_df, "destination", "pressure_score", ascending=False)
        name2, delta2 = biggest_delta(land_df, "destination", "pressure_score", ascending=True)
        top_reviewed = land_df.sort_values("n_reviews", ascending=False).iloc[0] if "n_reviews" in land_df.columns else None
        hl_items = [
            ("📈", "Fastest Rising", name1, f"+{delta1:.1f} pts vs. previous month" if name1 else "", None),
            ("📉", "Most Improved", name2, f"{delta2:.1f} pts vs. previous month" if name2 else "", None),
            ("🔍", "Most Reviewed",
             top_reviewed["destination"] if top_reviewed is not None else None,
             f'{int(top_reviewed["n_reviews"])} reviews in {top_reviewed["month"]}' if top_reviewed is not None else "",
             None),
        ]
    elif layer_choice == "Marine Risk":
        name1, delta1 = biggest_delta(marine_df, "marine_park", "risk_score", ascending=False)
        name2, delta2 = biggest_delta(marine_df, "marine_park", "risk_score", ascending=True)
        top_reviewed = marine_df.sort_values("visitors", ascending=False).iloc[0]
        hl_items = [
            ("📈", "Fastest Rising", name1, f"+{delta1:.1f} pts vs. previous month" if name1 else "", None),
            ("📉", "Most Improved", name2, f"{delta2:.1f} pts vs. previous month" if name2 else "", None),
            ("🔍", "Most Reviewed", top_reviewed["marine_park"],
             f'{int(top_reviewed["visitors"])} reviews in {top_reviewed["month"]}', None),
        ]
    else:  # All
        name1, delta1 = biggest_delta(land_df, "destination", "pressure_score", ascending=False)
        name2, delta2 = biggest_delta(land_df, "destination", "pressure_score", ascending=True)
        name3, delta3 = biggest_delta(marine_df, "marine_park", "risk_score", ascending=False)
        top_reviewed = land_df.sort_values("n_reviews", ascending=False).iloc[0] if "n_reviews" in land_df.columns else None
        hl_items = [
            ("📈", "Fastest Rising (Land)", name1, f"+{delta1:.1f} pts vs. previous month" if name1 else "", None),
            ("📉", "Most Improved (Land)", name2, f"{delta2:.1f} pts vs. previous month" if name2 else "", None),
            ("📈", "Fastest Rising (Marine)", name3, f"+{delta3:.1f} pts vs. previous month" if name3 else "", None),
            ("🔍", "Most Reviewed (Land)",
             top_reviewed["destination"] if top_reviewed is not None else None,
             f'{int(top_reviewed["n_reviews"])} reviews in {top_reviewed["month"]}' if top_reviewed is not None else "",
             None),
        ]

    # Data for the Graph (Risk Tier Distribution donut) and Chart (all
    # destinations ranked), both scoped to the current selector.
    if layer_choice == "Land Pressure":
        tier_source = land_latest_all[["risk_tier"]]
        rank_source = land_latest_all[["destination", "pressure_score"]].rename(
            columns={"destination": "name", "pressure_score": "score"}
        )
    elif layer_choice == "Marine Risk":
        tier_source = marine_latest_all[["risk_tier"]]
        rank_source = marine_latest_all[["marine_park", "risk_score"]].rename(
            columns={"marine_park": "name", "risk_score": "score"}
        )
    else:
        tier_source = combined_latest[["risk_tier"]]
        rank_source = combined_latest[["name", "score"]]
    rank_source = rank_source.sort_values("score", ascending=False)

    def render_main_overview_content():
        # Executive summary only makes sense when viewing everything at
        # once (it compares land vs. marine) - so it only shows for "All".
        if layer_choice == "All":
            summary_parts = []
            if len(elevated_land) > 0:
                top_land_elevated = elevated_land.sort_values("pressure_score", ascending=False).iloc[0]
                factor = land_leading_factor(top_land_elevated)
                summary_parts.append(
                    f"On land, <b>{top_land_elevated['destination']}</b> is the primary concern "
                    f"({top_land_elevated['risk_tier']}, score {top_land_elevated['pressure_score']:.1f}), driven mainly by {factor}."
                )
            if len(elevated_marine) > 0:
                top_marine_elevated = elevated_marine.sort_values("risk_score", ascending=False).iloc[0]
                factor = marine_leading_factor(top_marine_elevated)
                summary_parts.append(
                    f"At sea, <b>{top_marine_elevated['marine_park']}</b> is the primary concern "
                    f"({top_marine_elevated['risk_tier']}, score {top_marine_elevated['risk_score']:.1f}), driven mainly by {factor}."
                )
            if not summary_parts:
                summary_parts.append("No destinations are currently elevated - all monitored sites are within the Low risk/pressure range.")
            st.markdown(f'<div class="exec-summary">📋 <b>Summary:</b> {" ".join(summary_parts)}</div>', unsafe_allow_html=True)

            # Row 1: Key Metrics (left) + Highlights (right), same fixed height

            # Row 1: Key Metrics (left) + Highlights (right), same fixed height
        col_kpi, col_hl = st.columns(2)
        with col_kpi:
            with st.container(border=True, key="kpi_box"):
                st.markdown('<div class="card-heading">Key Metrics</div>', unsafe_allow_html=True)
                render_kpi_grid(kpi_items)
        with col_hl:
            with st.container(border=True, key="highlight_box"):
                st.markdown('<div class="card-heading">Highlights</div>', unsafe_allow_html=True)
                render_highlight_grid(hl_items)

        # Row 2: risk tier donut (left) + all-destinations ranking bar (right)
        col_graph, col_chart = st.columns(2)
        with col_graph:
            with st.container(border=True, key="risktier_box"):
                st.markdown('<div class="card-heading">Risk Tier Distribution</div>', unsafe_allow_html=True)
                tier_counts = tier_source["risk_tier"].value_counts().reset_index()
                tier_counts.columns = ["tier", "count"]
                donut = (
                    alt.Chart(tier_counts)
                    .mark_arc(innerRadius=45)
                    .encode(
                        theta="count:Q",
                        color=alt.Color("tier:N", scale=alt.Scale(
                            domain=["Low", "Medium", "High"], range=["#10b981", "#f59e0b", "#ef4444"]
                        )),
                        tooltip=["tier", "count"],
                    )
                    .properties(height=170)
                )
                st.altair_chart(donut, use_container_width=True)
        with col_chart:
            with st.container(border=True, key="rank_box"):
                st.markdown('<div class="card-heading">All Destinations Ranked</div>', unsafe_allow_html=True)
                bar = (
                    alt.Chart(rank_source)
                    .mark_bar(color="#2FA8C4")
                    .encode(
                        x=alt.X("score:Q", title="Score"),
                        y=alt.Y("name:N", sort="-x", title=None),
                        tooltip=["name", "score"],
                    )
                    .properties(height=170)
                )
                st.altair_chart(bar, use_container_width=True)

    if st.session_state.show_warning_panel and scope_elevated_count > 0:
        st.markdown("**⚠️ Elevated Destinations**")
        with st.container(border=False, key="elevated_panel"):
            if layer_choice in ("Land Pressure", "All") and len(elevated_land) > 0:
                for _, row in elevated_land.sort_values("pressure_score", ascending=False).iterrows():
                    action = land_recommended_action(row)
                    st.markdown(
                        f'<div class="action-card"><b>{row["destination"]}</b> ({row["risk_tier"]}, {row["pressure_score"]:.1f})<br>{action}</div>',
                        unsafe_allow_html=True,
                    )
            if layer_choice in ("Marine Risk", "All") and len(elevated_marine) > 0:
                for _, row in elevated_marine.sort_values("risk_score", ascending=False).iterrows():
                    action = marine_recommended_action(row)
                    st.markdown(
                        f'<div class="action-card"><b>{row["marine_park"]}</b> ({row["risk_tier"]}, {row["risk_score"]:.1f})<br>{action}</div>',
                        unsafe_allow_html=True,
                    )

    render_main_overview_content()

# ---------- PAGE: MAP ----------
elif page == "Map":

    base_layers = []
    if boundary_geojson is not None:
        base_layers.append(pdk.Layer(
            "GeoJsonLayer",
            data=boundary_geojson,
            stroked=True,
            filled=True,
            get_fill_color=[28, 114, 147, 45],
            get_line_color=[6, 90, 130, 220],
            line_width_min_pixels=1.5,
        ))

    MY_VIEW = pdk.ViewState(latitude=4.0, longitude=109.2, zoom=4.6)

    if layer_choice == "Land Pressure":
        latest = land_latest_all.merge(meta_df[["destination", "lat", "lon"]], on="destination", how="left")
        missing_coords = latest[latest["lat"].isna()]
        if len(missing_coords) > 0:
            st.warning(f"No coordinates found for: {missing_coords['destination'].tolist()}")
        latest = latest.dropna(subset=["lat", "lon"])
        latest["lat"] = latest["lat"].round(3)
        latest["lon"] = latest["lon"].round(3)
        latest["pressure_score"] = latest["pressure_score"].round(3)
        latest["color"] = latest["pressure_score"].apply(risk_color_from_score)
        latest["radius"] = latest["pressure_score"].apply(radius_from_score)

        with st.container(border=True, key="map_land_box"):
            st.markdown(f'<div class="card-heading">Map — {layer_choice}</div>', unsafe_allow_html=True)
            col_map, col_detail = st.columns([2, 1])
            with col_map:
                marker_layer = pdk.Layer(
                    "ScatterplotLayer", data=latest, get_position="[lon, lat]",
                    id="land-markers",
                    get_fill_color="color", get_radius="radius",
                    radius_units='"meters"', radius_min_pixels=8, radius_max_pixels=22,
                    get_line_color=[255, 255, 255], line_width_min_pixels=2, stroked=True,
                    pickable=True,
                )
                event = st.pydeck_chart(
                    pdk.Deck(
                        map_style="light", initial_view_state=MY_VIEW,
                        layers=base_layers + [marker_layer],
                        tooltip={"text": "{destination}\nPressure Score: {pressure_score}"},
                    ),
                    on_select="rerun", selection_mode="single-object", key="land_map", height=340,
                )
            with col_detail:
                st.markdown('<div class="card-heading">Top Highest Pressure</div>', unsafe_allow_html=True)
                top5 = latest.sort_values("pressure_score", ascending=False).head(5)
                top5_display = top5[["destination", "pressure_score"]].round(3).rename(
                    columns={"destination": "Destination", "pressure_score": "Pressure Score"}
                )
                st.markdown(score_table_html(top5_display, "Pressure Score"), unsafe_allow_html=True)
                st.markdown(
                    legend_html([("Low (0-32)", "#10b981"), ("Medium (33-65)", "#f59e0b"), ("High (66-100)", "#ef4444")]),
                    unsafe_allow_html=True,
                )
                render_click_hint()
        navigate_to_detail(event, "land-markers", "destination", "Land")

    elif layer_choice == "Marine Risk":
        latest = marine_latest_all.merge(
            meta_df[["destination", "lat", "lon"]].rename(columns={"destination": "marine_park"}),
            on="marine_park", how="left"
        )
        missing_coords = latest[latest["lat"].isna()]
        if len(missing_coords) > 0:
            st.warning(f"No coordinates found for: {missing_coords['marine_park'].tolist()}")
        latest = latest.dropna(subset=["lat", "lon"])
        latest["lat"] = latest["lat"].round(3)
        latest["lon"] = latest["lon"].round(3)
        latest["risk_score"] = latest["risk_score"].round(3)
        latest["color"] = latest["risk_tier"].apply(risk_color_from_tier)
        latest["radius"] = latest["risk_score"].apply(radius_from_score)

        with st.container(border=True, key="map_marine_box"):
            st.markdown(f'<div class="card-heading">Map — {layer_choice}</div>', unsafe_allow_html=True)
            col_map, col_detail = st.columns([2, 1])
            with col_map:
                marker_layer = pdk.Layer(
                    "ScatterplotLayer", data=latest, get_position="[lon, lat]",
                    id="marine-markers",
                    get_fill_color="color", get_radius="radius",
                    radius_units='"meters"', radius_min_pixels=8, radius_max_pixels=22,
                    get_line_color=[255, 255, 255], line_width_min_pixels=2, stroked=True,
                    pickable=True,
                )
                event = st.pydeck_chart(
                    pdk.Deck(
                        map_style="light", initial_view_state=MY_VIEW,
                        layers=base_layers + [marker_layer],
                        tooltip={"text": "{marine_park}\nRisk: {risk_tier} ({risk_score})"},
                    ),
                    on_select="rerun", selection_mode="single-object", key="marine_map", height=340,
                )
            with col_detail:
                st.markdown('<div class="card-heading">Risk Ranking</div>', unsafe_allow_html=True)
                ranking_display = (
                    latest[["marine_park", "risk_score", "risk_tier"]]
                    .sort_values("risk_score", ascending=False)
                    .round(3)
                    .rename(columns={"marine_park": "Marine Park", "risk_score": "Risk Score", "risk_tier": "Risk Tier"})
                )
                st.markdown(score_table_html(ranking_display, "Risk Score", "Risk Tier"), unsafe_allow_html=True)
                st.markdown(
                    legend_html([("Low", "#10b981"), ("Medium", "#f59e0b"), ("High", "#ef4444")]),
                    unsafe_allow_html=True,
                )
                render_click_hint()
        navigate_to_detail(event, "marine-markers", "marine_park", "Marine")

    else:  # All
        combined_map = combined_latest.dropna(subset=["lat", "lon"]).copy()
        combined_map["lat"] = combined_map["lat"].round(3)
        combined_map["lon"] = combined_map["lon"].round(3)
        combined_map["score"] = combined_map["score"].round(3)
        combined_map["color"] = combined_map["score"].apply(risk_color_from_score)
        combined_map["radius"] = combined_map["score"].apply(radius_from_score)
        combined_map["line_width"] = combined_map["type"].apply(lambda t: 6 if t == "Marine" else 2)

        with st.container(border=True, key="map_all_box"):
            st.markdown(f'<div class="card-heading">Map — {layer_choice}</div>', unsafe_allow_html=True)
            col_map, col_detail = st.columns([2, 1])
            with col_map:
                marker_layer = pdk.Layer(
                    "ScatterplotLayer", data=combined_map, get_position="[lon, lat]",
                    id="combined-markers",
                    get_fill_color="color", get_radius="radius",
                    radius_units='"meters"', radius_min_pixels=8, radius_max_pixels=22,
                    get_line_color=[255, 255, 255], get_line_width="line_width",
                    line_width_units='"pixels"', line_width_min_pixels=2,
                    stroked=True,
                    pickable=True,
                )
                event = st.pydeck_chart(
                    pdk.Deck(
                        map_style="light", initial_view_state=MY_VIEW,
                        layers=base_layers + [marker_layer],
                        tooltip={"text": "{name} ({type})\nScore: {score}"},
                    ),
                    on_select="rerun", selection_mode="single-object", key="combined_map", height=340,
                )
                st.caption("Marine markers have a thicker white outline to distinguish them from land markers.")
            with col_detail:
                st.markdown('<div class="card-heading">Top Highest (All)</div>', unsafe_allow_html=True)
                top5 = combined_map.sort_values("score", ascending=False).head(5)
                top5_display = top5[["name", "type", "score"]].round(3).rename(
                    columns={"name": "Destination", "type": "Type", "score": "Score"}
                )
                st.markdown(score_table_html(top5_display, "Score"), unsafe_allow_html=True)
                st.markdown(
                    legend_html([("Low (0-32)", "#10b981"), ("Medium (33-65)", "#f59e0b"), ("High (66-100)", "#ef4444")]),
                    unsafe_allow_html=True,
                )
                render_click_hint()
        if event is not None:
            _objs = event.selection.objects.get("combined-markers", [])
            _kind = _objs[0].get("type", "Land") if _objs else "Land"
            navigate_to_detail(event, "combined-markers", "name", _kind)

elif page == "Trends & Analysis":

    col_trend, col_complaint = st.columns([2, 1])
    with col_trend:
        with st.container(border=True, key="trend_compare_box", height=280):
            st.markdown('<div class="card-heading">Trend Comparison</div>', unsafe_allow_html=True)
            if layer_choice == "Land Pressure":
                all_names = sorted(land_df["destination"].unique())
                picked = st.multiselect("Compare destinations", all_names, default=all_names[:2])
                trend_df = land_df[land_df["destination"].isin(picked)].copy()
                score_field, group_field = "pressure_score", "destination"

            elif layer_choice == "Marine Risk":
                all_names = sorted(marine_df["marine_park"].unique())
                picked = st.multiselect("Compare marine parks", all_names, default=all_names[:2])
                trend_df = marine_df[marine_df["marine_park"].isin(picked)].copy()
                score_field, group_field = "risk_score", "marine_park"

            else:  # All
                land_for_trend = land_df.rename(columns={"destination": "name", "pressure_score": "score"})[["name", "month", "score", "is_forecast"]]
                marine_for_trend = marine_df.rename(columns={"marine_park": "name", "risk_score": "score"})[["name", "month", "score", "is_forecast"]]
                combined_trend_source = pd.concat([land_for_trend, marine_for_trend], ignore_index=True)
                all_names = sorted(combined_trend_source["name"].unique())
                picked = st.multiselect("Compare destinations (land + marine)", all_names, default=all_names[:2])
                trend_df = combined_trend_source[combined_trend_source["name"].isin(picked)].copy()
                score_field, group_field = "score", "name"

            if len(trend_df) > 0:
                chart = (
                    alt.Chart(trend_df)
                    .mark_line(point=True)
                    .encode(
                        x=alt.X("month:N", title="Month"),
                        y=alt.Y(f"{score_field}:Q", title="Score (0-100)"),
                        color=alt.Color(f"{group_field}:N", title="Destination"),
                        strokeDash=alt.StrokeDash("is_forecast:N", legend=None) if "is_forecast" in trend_df.columns else alt.value([1, 0]),
                        tooltip=[group_field, "month", score_field],
                    )
                    .properties(height=200)
                )
                st.altair_chart(chart, use_container_width=True)
                st.caption("Dashed segments are forecasted values, not observed data.")
            else:
                st.info("Select at least one destination to see its trend.")

    with col_complaint:
        if layer_choice == "Land Pressure":
            aspect_sources = [land_reviews_df] if land_reviews_df is not None else []
        elif layer_choice == "Marine Risk":
            aspect_sources = [marine_reviews_df] if marine_reviews_df is not None else []
        else:
            aspect_sources = [df for df in [land_reviews_df, marine_reviews_df] if df is not None]

        with st.container(border=True, key="complaint_trend_box", height=280):
            st.markdown('<div class="card-heading">What Are People Complaining About?</div>', unsafe_allow_html=True)
            if aspect_sources:
                combined_reviews = pd.concat(aspect_sources, ignore_index=True)
                aspect_counts = negative_mentions_by_aspect(combined_reviews)
                if len(aspect_counts) > 0:
                    bar = (
                        alt.Chart(aspect_counts)
                        .mark_bar(color="#1C7293")
                        .encode(
                            x=alt.X("negative_mentions:Q", title="Negative mentions"),
                            y=alt.Y("aspect:N", sort="-x", title=None),
                            tooltip=["aspect", "negative_mentions"],
                        )
                        .properties(height=200)
                    )
                    st.altair_chart(bar, use_container_width=True)
                else:
                    st.info("No negative aspect-tagged mentions found in the current data.")
            else:
                st.info("Review-level data not available.")

    col_donut, col_heat = st.columns(2)

    with col_donut:
        with st.container(border=True, key="tier_donut_box"):
            st.markdown('<div class="card-heading">Risk Tier Mix Over Time</div>', unsafe_allow_html=True)
            if layer_choice == "Land Pressure":
                tier_trend_source = land_df[land_df["is_forecast"] == False][["month", "pressure_score"]].rename(columns={"pressure_score": "score"})
            elif layer_choice == "Marine Risk":
                tier_trend_source = marine_df[["month", "risk_score"]].rename(columns={"risk_score": "score"})
            else:
                land_t = land_df[land_df["is_forecast"] == False][["month", "pressure_score"]].rename(columns={"pressure_score": "score"})
                marine_t = marine_df[["month", "risk_score"]].rename(columns={"risk_score": "score"})
                tier_trend_source = pd.concat([land_t, marine_t], ignore_index=True)

            tier_trend_source = tier_trend_source.copy()
            tier_trend_source["tier"] = tier_trend_source["score"].apply(score_to_tier)
            tier_month_counts = tier_trend_source.groupby(["month", "tier"]).size().reset_index(name="count")

            tier_area = (
                alt.Chart(tier_month_counts)
                .mark_bar()
                .encode(
                    x=alt.X("month:N", title="Month"),
                    y=alt.Y("count:Q", title="Destinations", stack="zero"),
                    color=alt.Color("tier:N", title="Tier", scale=alt.Scale(
                        domain=["Low", "Medium", "High"], range=["#10b981", "#f59e0b", "#ef4444"]
                    )),
                    tooltip=["month", "tier", "count"],
                )
                .properties(height=190)
            )
            st.altair_chart(tier_area, use_container_width=True)

    with col_heat:
        with st.container(border=True, key="risk_heatmap_box"):
            st.markdown('<div class="card-heading">Pressure/Risk Heatmap</div>', unsafe_allow_html=True)
            if layer_choice == "Land Pressure":
                heat_source = land_df[land_df["is_forecast"] == False]
                heat_score, heat_group = "pressure_score", "destination"
            elif layer_choice == "Marine Risk":
                heat_source = marine_df
                heat_score, heat_group = "risk_score", "marine_park"
            else:
                heat_source = pd.concat([
                    land_df[land_df["is_forecast"] == False].rename(columns={"destination": "name", "pressure_score": "score"})[["name", "month", "score"]],
                    marine_df.rename(columns={"marine_park": "name", "risk_score": "score"})[["name", "month", "score"]],
                ], ignore_index=True)
                heat_score, heat_group = "score", "name"

            heatmap = (
                alt.Chart(heat_source)
                .mark_rect()
                .encode(
                    x=alt.X("month:N", title="Month"),
                    y=alt.Y(f"{heat_group}:N", title=None),
                    color=alt.Color(f"{heat_score}:Q", scale=alt.Scale(scheme="yelloworangered"), title="Score"),
                    tooltip=[heat_group, "month", heat_score],
                )
                .properties(height=190)
            )
            st.altair_chart(heatmap, use_container_width=True)

elif page == "Location Detail":
    detail = st.session_state.selected_detail

    if detail is None:
        st.info("No location selected. Go to the Map page and click a marker.")
    else:
        kind = detail.get("_kind", "Land")
        name_field = detail.get("_name_field", "destination")
        loc_name = detail.get(name_field, "Unknown")

        title_col, back_col = st.columns([5, 1])
        with title_col:
            score_field = "pressure_score" if kind == "Land" else "risk_score"
            score_val = detail.get(score_field, detail.get("score"))
            tier_val = detail.get("risk_tier", score_to_tier(score_val) if score_val is not None else "Low")
            tier_color = {"Low": "#10b981", "Medium": "#f59e0b", "High": "#ef4444"}[tier_val]
            st.markdown(
                f'<h2 style="margin:0;">{loc_name} '
                f'<span style="font-size:0.9rem; background:{tier_color}; color:white; '
                f'padding:2px 10px; border-radius:10px; vertical-align:middle;">{tier_val}</span></h2>',
                unsafe_allow_html=True,
            )
            st.caption(f"{kind} destination — {detail.get('lat', 0):.3f}, {detail.get('lon', 0):.3f}")
        with back_col:
            st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
            if st.button("← Back to Map"):
                st.session_state.active_page = "Map"
                st.session_state.selected_detail = None
                st.rerun()

        if kind == "Land":
            trend = land_df[land_df["destination"] == loc_name].sort_values("month")
            latest_row = trend[trend["is_forecast"] == False].iloc[-1] if len(trend[trend["is_forecast"] == False]) else None
            total_reviews = land_total_reviews.get(loc_name, 0)
            factor = land_leading_factor(latest_row) if latest_row is not None else "insufficient data"

            k1, k2, k3 = st.columns(3)
            with k1:
                st.metric("Pressure Score", f"{latest_row['pressure_score']:.2f}" if latest_row is not None else "N/A")
            with k2:
                st.metric("This Month's Reviews", int(latest_row["n_reviews"]) if latest_row is not None else 0)
            with k3:
                st.markdown(confidence_box_html(total_reviews), unsafe_allow_html=True)

            st.markdown(f'<div class="exec-summary">💡 Pressure here is currently driven mainly by <b>{factor}</b>.</div>', unsafe_allow_html=True)

            col_chart, col_complaint = st.columns(2)
            with col_chart:
                with st.container(border=True, key="detail_land_chart_box"):
                    st.markdown('<div class="card-heading">Pressure Score Over Time</div>', unsafe_allow_html=True)
                    chart = (
                        alt.Chart(trend)
                        .mark_line(point=True)
                        .encode(
                            x=alt.X("month:N", title="Month"),
                            y=alt.Y("pressure_score:Q", title="Score", scale=alt.Scale(domain=[0, 100])),
                            strokeDash=alt.StrokeDash("is_forecast:N", legend=None),
                            tooltip=["month", "pressure_score"],
                        )
                        .properties(height=220)
                    )
                    st.altair_chart(chart, use_container_width=True)

            with col_complaint:
                with st.container(border=True, key="detail_land_complaint_box"):
                    st.markdown('<div class="card-heading">Complaint Breakdown (this destination)</div>', unsafe_allow_html=True)
                    if land_reviews_df is not None:
                        dest_reviews = land_reviews_df[land_reviews_df["destination"] == loc_name]
                        aspect_counts = negative_mentions_by_aspect(dest_reviews)
                        if len(aspect_counts) > 0:
                            bar = (
                                alt.Chart(aspect_counts)
                                .mark_bar(color="#1C7293")
                                .encode(
                                    x=alt.X("negative_mentions:Q", title="Negative mentions"),
                                    y=alt.Y("aspect:N", sort="-x", title=None),
                                    tooltip=["aspect", "negative_mentions"],
                                )
                                .properties(height=220)
                            )
                            st.altair_chart(bar, use_container_width=True)
                        else:
                            st.info("No specific complaint themes found for this destination.")
                    else:
                        st.info("Review-level data not available.")

        else:  # Marine
            trend = marine_df[marine_df["marine_park"] == loc_name].sort_values("month")
            latest_row = trend.iloc[-1] if len(trend) else None
            total_reviews = marine_total_reviews.get(loc_name, 0)
            factor = marine_leading_factor(latest_row) if latest_row is not None else "insufficient data"

            k1, k2, k3 = st.columns(3)
            with k1:
                st.metric("Risk Score", f"{latest_row['risk_score']:.2f}" if latest_row is not None else "N/A")
            with k2:
                st.metric("Sea Temp (°C)", f"{latest_row['sst_celsius']:.2f}" if latest_row is not None else "N/A")
            with k3:
                st.markdown(confidence_box_html(total_reviews), unsafe_allow_html=True)

            st.markdown(f'<div class="exec-summary">💡 Risk here is currently driven mainly by <b>{factor}</b>.</div>', unsafe_allow_html=True)

            col_chart, col_driving = st.columns(2)
            with col_chart:
                with st.container(border=True, key="detail_marine_chart_box"):
                    st.markdown('<div class="card-heading">Risk Score Over Time</div>', unsafe_allow_html=True)
                    chart = (
                        alt.Chart(trend)
                        .mark_line(point=True)
                        .encode(
                            x=alt.X("month:N", title="Month"),
                            y=alt.Y("risk_score:Q", title="Score", scale=alt.Scale(domain=[0, 100])),
                            tooltip=["month", "risk_score"],
                        )
                        .properties(height=220)
                    )
                    st.altair_chart(chart, use_container_width=True)

            with col_driving:
                with st.container(border=True, key="detail_marine_driving_box"):
                    st.markdown("<div class=\"card-heading\">What's Driving This Score</div>", unsafe_allow_html=True)
                    if latest_row is not None:
                        components_df = pd.DataFrame({
                            "component": ["Visitor Volume", "Sea Temp Anomaly", "Turbidity", "Negative Reviews"],
                            "contribution": [
                                latest_row["visitor_norm"] * 35,
                                latest_row["sst_anomaly_norm"] * 35,
                                latest_row["turbidity_norm"] * 15,
                                latest_row["neg_review_norm"] * 15,
                            ],
                        })
                        bar = (
                            alt.Chart(components_df)
                            .mark_bar(color="#1C7293")
                            .encode(
                                x=alt.X("contribution:Q", title="Points contributed (of 100)"),
                                y=alt.Y("component:N", sort="-x", title=None),
                                tooltip=["component", "contribution"],
                            )
                            .properties(height=190)
                        )
                        st.altair_chart(bar, use_container_width=True)
                    st.caption("Weights: 35% visitors, 35% sea temp anomaly, 15% turbidity, 15% negative reviews.")

            if latest_row is not None:
                reduction = st.slider("What-if: reduce visitors by (%)", 0, 80, 0, step=10, key="detail_page_slider")
                if reduction > 0:
                    simulated = simulate_visitor_cap(marine_df, loc_name, reduction)
                    new_score = simulated.sort_values("month")["risk_score"].iloc[-1]
                    new_tier = simulated.sort_values("month")["risk_tier"].iloc[-1]
                    st.metric(f"Projected risk with {reduction}% fewer visitors", f"{new_tier} ({new_score:.2f})")



elif page == "Deep Dive":

    with st.expander("ℹ️ How are these scores calculated?"):
        st.markdown("""
**Land Pressure Score (0-100)** combines two factors, each scaled 0-1 before weighting:
- 50% - share of recent reviews with negative sentiment
- 50% - month-over-month visitor volume growth (proxied by review posting volume)

**Marine Risk Score (0-100)** combines four factors, each scaled 0-1 before weighting:
- 35% - visitor volume
- 35% - sea surface temperature anomaly (deviation from that park's own average - a known coral bleaching indicator)
- 15% - water turbidity
- 15% - negative sentiment in environment-related reviews

Both scores are bucketed into tiers: **Low** (0-32), **Medium** (33-65), **High** (66-100).

Visitor volume for both modules is proxied using real review-posting counts, since no public
real-time visitor dataset exists for these specific destinations - see the confidence badges
below for how much review data backs each score.
    """)


    col_conf, col_drill = st.columns(2)

    with col_conf:
        with st.container(border=True, key="dataconf_box"):
            st.markdown('<div class="card-heading">Data Confidence</div>', unsafe_allow_html=True)
            st.caption("Based on total reviews collected across all months for each destination.")
            if layer_choice == "Land Pressure":
                conf_df = pd.DataFrame({
                    "Destination": land_total_reviews.index,
                    "Reviews": land_total_reviews.values.astype(int),
                }).sort_values("Destination")
                conf_df["Confidence"] = conf_df["Reviews"].apply(confidence_label)
                st.markdown(confidence_table_html(conf_df), unsafe_allow_html=True)
            elif layer_choice == "Marine Risk":
                conf_df = pd.DataFrame({
                    "Marine Park": marine_total_reviews.index,
                    "Reviews": marine_total_reviews.values.astype(int),
                }).sort_values("Marine Park")
                conf_df["Confidence"] = conf_df["Reviews"].apply(confidence_label)
                st.markdown(confidence_table_html(conf_df), unsafe_allow_html=True)
            else:  # All
                land_conf_df = pd.DataFrame({
                    "Destination": land_total_reviews.index,
                    "Type": "Land",
                    "Reviews": land_total_reviews.values.astype(int),
                })
                marine_conf_df = pd.DataFrame({
                    "Destination": marine_total_reviews.index,
                    "Type": "Marine",
                    "Reviews": marine_total_reviews.values.astype(int),
                })
                conf_df = pd.concat([land_conf_df, marine_conf_df], ignore_index=True).sort_values("Destination")
                conf_df["Confidence"] = conf_df["Reviews"].apply(confidence_label)
                st.markdown(confidence_table_html(conf_df), unsafe_allow_html=True)

    with col_drill:
        with st.container(border=True, key="drilldown_box"):
            st.markdown(
                f'<div class="card-heading">Drill Down{" + What-If Simulator" if layer_choice == "Marine Risk" else ""}</div>',
                unsafe_allow_html=True,
            )
            if layer_choice == "Land Pressure":
                dest = st.selectbox("Choose a destination", sorted(land_df["destination"].unique()))
                trend = land_df[land_df["destination"] == dest].sort_values("month")
                st.line_chart(trend.set_index("month")["pressure_score"], height=200)

            elif layer_choice == "Marine Risk":
                park = st.selectbox("Choose a marine park", sorted(marine_df["marine_park"].unique()))
                trend = marine_df[marine_df["marine_park"] == park].sort_values("month")
                st.line_chart(trend.set_index("month")["risk_score"], height=200)

                reduction = st.slider("Simulate visitor cap reduction (%)", 0, 80, 0, step=10)
                if reduction > 0:
                    simulated = simulate_visitor_cap(marine_df, park, reduction)
                    new_score = simulated.sort_values("month")["risk_score"].iloc[-1]
                    new_tier = simulated.sort_values("month")["risk_tier"].iloc[-1]
                    st.metric(f"Projected risk with {reduction}% fewer visitors", f"{new_tier} ({new_score:.1f})")

            else:  # All
                options = sorted(combined_latest["name"].unique())
                chosen = st.selectbox("Choose any destination (land or marine)", options)
                chosen_type = combined_latest[combined_latest["name"] == chosen]["type"].iloc[0]

                if chosen_type == "Land":
                    trend = land_df[land_df["destination"] == chosen].sort_values("month")
                    st.line_chart(trend.set_index("month")["pressure_score"], height=200)
                else:
                    trend = marine_df[marine_df["marine_park"] == chosen].sort_values("month")
                    st.line_chart(trend.set_index("month")["risk_score"], height=200)
                    reduction = st.slider("Simulate visitor cap reduction (%)", 0, 80, 0, step=10, key="all_view_slider")
                    if reduction > 0:
                        simulated = simulate_visitor_cap(marine_df, chosen, reduction)
                        new_score = simulated.sort_values("month")["risk_score"].iloc[-1]
                        new_tier = simulated.sort_values("month")["risk_tier"].iloc[-1]
                        st.metric(f"Projected risk with {reduction}% fewer visitors", f"{new_tier} ({new_score:.1f})")

                        
            if layer_choice == "Land Pressure":
                export_df, export_name = land_df, "land_pressure"
            elif layer_choice == "Marine Risk":
                export_df, export_name = marine_df, "marine_risk"
            else:
                export_df, export_name = combined_latest, "combined_overview"

            st.download_button(
                "Download current view as CSV",
                data=export_df.to_csv(index=False).encode("utf-8"),
                file_name=f"{export_name}_export.csv",
                mime="text/csv",
            )
    