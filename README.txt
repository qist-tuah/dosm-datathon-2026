=============================================================
Sustainable Tourism Pressure & Risk Monitoring System
DOSM Datathon 2026 — Team Bits & Bytes
=============================================================

SOFTWARE NAME AND VERSION
--------------------------
Python: 3.14.3
Streamlit: 1.63.0
pandas: 3.0.2
pydeck: 0.9.3
altair: 6.3.0

Full dependency list is included in requirements.txt in this
submission package.


DEPLOYED DASHBOARD LINK
-------------------------
[https://dosm-datathon-2026-aaxzgbcesq8rv7lsdc9xqb.streamlit.app/]

The dashboard will remain accessible and operational throughout
the judging period, through the completion of the Live Pitching
session.


HOW TO RUN LOCALLY (OPTIONAL — DASHBOARD IS ALSO LIVE AT THE
LINK ABOVE)
--------------------------------------------------------------
1. Ensure Python 3.10+ is installed.
2. Open a terminal in this folder and create a virtual
   environment:
       python -m venv venv
       venv\Scripts\activate          (Windows)
       source venv/bin/activate       (Mac/Linux)
3. Install dependencies:
       pip install -r requirements.txt
4. Run the dashboard:
       streamlit run dashboard.py
5. The dashboard opens automatically in your default browser at
   http://localhost:8501


STEP-BY-STEP: NAVIGATING THE DASHBOARD
----------------------------------------
1. SCOPE SELECTOR (top of sidebar)
   Choose "Land Pressure", "Marine Risk", or "All" from the
   dropdown. This filters every page's content — metrics,
   charts, and map markers — to the selected category.

2. PAGE NAVIGATION (sidebar, below Scope)
   - Overview: summary KPIs, highlights, risk tier breakdown,
     seasonal pattern, and (when applicable) a warning icon
     next to the dashboard title showing elevated destinations
     and recommended actions.
   - Map: interactive map of Malaysia with colour-coded markers
     (green = Low, amber = Medium, red = High). Click any
     marker to open that destination's full detail page,
     including its score trend, complaint breakdown (land) or
     risk-driver breakdown and what-if visitor-cap simulator
     (marine).
   - Trends & Analysis: month-by-month trend comparison across
     selected destinations, risk tier mix over time, seasonal
     pattern, and top complaint themes.
   - Deep Dive: methodology explanation, data confidence table
     per destination, and a drill-down chart with CSV export.

3. RETURNING FROM A DESTINATION DETAIL PAGE
   Use the "← Back to Map" button at the top of that page.

4. DOWNLOADING DATA
   On the Deep Dive page, use "Download current view as CSV" to
   export the currently filtered dataset.


ADDITIONAL REQUIREMENTS / PLUGINS
-----------------------------------
None beyond the Python packages listed in requirements.txt.
No browser plugins, API keys, or external accounts are needed
to view or interact with the deployed dashboard. (Note: the
data collection/preparation pipeline — Google Earth Engine
satellite data and review scraping — required separate API
credentials during development, but these are not needed to
run or view the dashboard itself, only its pre-computed output
data in sample_data/.)


LIMITATIONS, ASSUMPTIONS & SPECIAL CONSIDERATIONS
----------------------------------------------------
- Visitor volume (both land and marine) is PROXIED using
  review-posting volume, since no public real-time
  ticketing/visitor-count API exists for these destinations.
  Scores should be read as "visible tourism activity and
  sentiment trend," not literal footfall counts.
- Non-English Google Reviews were machine-translated to
  English before sentiment/aspect scoring; translation quality
  may introduce minor noise in a small subset of reviews.
- Pulau Payar has no on-island accommodation; its review data
  is sourced from nearby dive operators and day-trip services
  rather than resort reviews, as used for the other 4 marine
  parks.
- DOSM's official visitor arrivals data (state-of-entry border
  crossings) measures national/state-level entry, not
  per-destination visits, so it is used for contextual
  narrative in the written report only — it does not feed the
  dashboard's live Pressure/Risk scores.
- The dashboard monitors 8 land destinations and 5 marine
  parks (13 total) across the dataset's available date range;
  it is a proof-of-concept monitoring system, not an
  exhaustive national survey.
- Forecasted score segments (shown as dashed lines on trend
  charts) are model projections, not observed data.
- The deployed dashboard runs on Streamlit Community Cloud's
  free tier, which may briefly "sleep" after a period of
  inactivity — if so, it will automatically restart within
  under a minute on the next visit.