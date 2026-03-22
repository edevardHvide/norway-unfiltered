import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os

st.set_page_config(
    page_title="Norway Unfiltered",
    page_icon="\U0001F1F3\U0001F1F4",
    layout="wide",
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def load_json(name):
    with open(os.path.join(DATA_DIR, name)) as f:
        return json.load(f)


# ── Custom CSS ───────────────────────────────────────────────────────────────

st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');

    .stApp { background: #08090c; }
    .block-container { padding-top: 2rem; max-width: 1200px; }

    .main-header {
        font-family: 'DM Sans', sans-serif;
        font-size: 32px;
        font-weight: 700;
        color: #e8e8ed;
        letter-spacing: -0.5px;
        margin-bottom: 0;
    }
    .sub-header {
        font-size: 13px;
        color: #52536a;
        margin-bottom: 28px;
    }

    div[data-testid="stMetric"] {
        background: #0f1117;
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 16px;
        padding: 20px;
    }
    div[data-testid="stMetric"] label { color: #8b8d98 !important; font-size: 12px !important; }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] { font-size: 36px !important; font-weight: 700 !important; }

    .chart-container {
        background: #0f1117;
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 16px;
        padding: 20px;
    }

    div[data-testid="stTabs"] button {
        color: #8b8d98 !important;
        font-weight: 500 !important;
    }
    div[data-testid="stTabs"] button[aria-selected="true"] {
        color: #e8e8ed !important;
        border-bottom-color: #60a5fa !important;
    }

    .fun-stat {
        background: #0f1117;
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 16px;
        padding: 24px;
        text-align: center;
    }
    .fun-stat .number {
        font-family: 'DM Sans', sans-serif;
        font-size: 48px;
        font-weight: 700;
        color: #60a5fa;
    }
    .fun-stat .label {
        font-size: 13px;
        color: #8b8d98;
        margin-top: 4px;
    }
</style>
""",
    unsafe_allow_html=True,
)

# ── Header ───────────────────────────────────────────────────────────────────

st.markdown('<div class="main-header">Norway Unfiltered \U0001F1F3\U0001F1F4</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Humorous statistics from SSB (Statistics Norway) &middot; Because data doesn\'t have to be boring</div>',
    unsafe_allow_html=True,
)

# ── Tabs ─────────────────────────────────────────────────────────────────────

PLOT_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#e8e8ed", family="DM Sans"),
    xaxis=dict(gridcolor="rgba(255,255,255,0.06)", zerolinecolor="rgba(255,255,255,0.06)"),
    yaxis=dict(gridcolor="rgba(255,255,255,0.06)", zerolinecolor="rgba(255,255,255,0.06)"),
    legend=dict(font=dict(color="#e8e8ed", size=11)),
)

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "\U0001F37A 175 Years of Drinking",
    "\U0001F4F1 The Loneliness Graph",
    "\U0001F98C Moose vs Machine",
    "\U0001F9C0 Cheese > Fish",
    "\U0001F494 Marriage Survival",
    "\U0001F6B2 Bike Theft Map",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1: 175 Years of Drinking
# ══════════════════════════════════════════════════════════════════════════════

with tab1:
    st.markdown("### From Spirits Nation to Wine Snobs")
    st.markdown("*How Norway's drinking habits evolved over 175 years*")

    alcohol_data = load_json("alcohol.json")
    df_alc = pd.DataFrame(alcohol_data)

    # Fun stats row
    k1, k2, k3 = st.columns(3)

    peak_year = df_alc.loc[df_alc["total"].idxmax()]
    latest = df_alc.iloc[-1]

    spirits_1980 = df_alc.loc[df_alc["year"] == 1980, "spirits"].values
    spirits_latest = latest.get("spirits", 0)

    k1.metric("Peak Drinking Year", f"{int(peak_year['year'])}", f"{peak_year['total']:.1f}L pure alcohol/capita")
    k2.metric("Current (Latest)", f"{latest['total']:.1f}L", f"per capita per year")
    k3.metric("Spirits Collapse", f"{spirits_latest:.1f}L",
              f"down from {spirits_1980[0]:.1f}L in 1980" if len(spirits_1980) > 0 else "")

    st.markdown("")

    # Stacked area chart
    beverage_cols = [c for c in ["spirits", "wine", "beer", "alcopops"] if c in df_alc.columns]
    colors = {"spirits": "#a78bfa", "wine": "#f472b6", "beer": "#fb923c", "alcopops": "#34d399"}

    fig = go.Figure()
    for bev in beverage_cols:
        fig.add_trace(go.Scatter(
            x=df_alc["year"], y=df_alc[bev],
            name=bev.capitalize(),
            mode="lines",
            stackgroup="one",
            line=dict(width=0.5, color=colors.get(bev, "#60a5fa")),
            fillcolor=colors.get(bev, "#60a5fa"),
        ))

    # Annotations for key events
    fig.add_annotation(x=1919, y=0.5, text="Prohibition<br>1916-1927",
                       showarrow=True, arrowhead=2, arrowcolor="#e8e8ed",
                       font=dict(size=10, color="#e8e8ed"), ay=-60)

    covid_row = df_alc.loc[df_alc["year"] == 2020]
    if not covid_row.empty:
        fig.add_annotation(x=2020, y=float(covid_row["total"].values[0]),
                           text="COVID lockdown<br>peak drinking!",
                           showarrow=True, arrowhead=2, arrowcolor="#f472b6",
                           font=dict(size=10, color="#f472b6"), ay=-40)

    fig.update_layout(
        **PLOT_LAYOUT,
        height=500,
        margin=dict(t=20, b=40, l=60, r=20),
        yaxis_title="Litres pure alcohol per capita",
        xaxis_title="Year",
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown(
        "> **Fun fact:** In 2020, locked-down Norwegians drank more than any year since the 1980s. "
        "The wine revolution is real &mdash; spirits went from king to afterthought in just 40 years."
    )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2: The Loneliness Graph
# ══════════════════════════════════════════════════════════════════════════════

with tab2:
    st.markdown("### Young Norwegians Stopped Talking to Each Other")
    st.markdown("*Time spent socializing collapsed. Gaming and social media took over.*")

    time_data = load_json("time_use.json")
    df_time = pd.DataFrame(time_data)

    # Summary metrics
    k1, k2, k3 = st.columns(3)
    k1.markdown(
        '<div class="fun-stat"><div class="number">-64%</div>'
        '<div class="label">Socializing time for young men<br>(1980 vs 2022)</div></div>',
        unsafe_allow_html=True,
    )
    k2.markdown(
        '<div class="fun-stat"><div class="number">1h 45m</div>'
        '<div class="label">Daily gaming for young men in 2022<br>(was 0 in 1980)</div></div>',
        unsafe_allow_html=True,
    )
    k3.markdown(
        '<div class="fun-stat"><div class="number">+43 min</div>'
        '<div class="label">Extra sleep for young women<br>(2022 vs 1980)</div></div>',
        unsafe_allow_html=True,
    )

    st.markdown("")

    # Let user pick what to compare
    col_filter, col_chart = st.columns([1, 3])

    available_activities = sorted(df_time["activity"].unique()) if len(df_time) > 0 else []

    with col_filter:
        selected_sex = st.radio("Gender", ["Males", "Females", "Both sexes"], index=0, key="time_sex")
        default_activities = [a for a in ["Socializing", "Gaming", "Social media", "Reading books, newspapers, magazines"]
                              if a in available_activities]
        if not default_activities:
            default_activities = available_activities[:4]
        selected_activities = st.multiselect(
            "Activities", available_activities,
            default=default_activities,
            key="time_act",
        )

    with col_chart:
        mask = df_time["activity"].isin(selected_activities)
        if selected_sex != "Both sexes":
            mask &= df_time["sex"] == selected_sex

        filtered = df_time[mask]

        if len(filtered) > 0:
            fig = px.line(
                filtered,
                x="year", y="hours",
                color="activity",
                line_dash="sex" if selected_sex == "Both sexes" else None,
                markers=True,
                color_discrete_sequence=["#60a5fa", "#f472b6", "#34d399", "#fb923c", "#a78bfa", "#fbbf24"],
            )
            fig.update_layout(
                **PLOT_LAYOUT,
                height=450,
                margin=dict(t=20, b=40, l=60, r=20),
                yaxis_title="Hours per day",
                xaxis_title="Year",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                            font=dict(color="#e8e8ed", size=10)),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Select activities to compare")

    st.markdown(
        "> **The trade:** Young men swapped 1.5 hours of face-to-face socializing for 1.75 hours of gaming. "
        "Meanwhile, everyone is sleeping more. Norway: the introvert's paradise."
    )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3: Moose vs Machine
# ══════════════════════════════════════════════════════════════════════════════

with tab3:
    st.markdown("### The Silent War on Norway's Roads")
    st.markdown("*Thousands of animals meet their end on Norwegian roads and railways every year*")

    roadkill_raw = load_json("roadkill.json")
    df_rk = pd.DataFrame(roadkill_raw.get("records", roadkill_raw) if isinstance(roadkill_raw, dict) else roadkill_raw)

    # Counter
    roe_deer_per_year = 6800
    minutes_between = (365.25 * 24 * 60) / roe_deer_per_year

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Roe Deer vs Cars", f"~{roe_deer_per_year:,}/yr", "19 per day")
    k2.metric("Moose vs Cars", "~1,000/yr", "3 per day")
    k3.metric("Moose vs Trains", "~400/yr", "1 per day")
    k4.markdown(
        f'<div class="fun-stat"><div class="number">~{minutes_between:.0f} min</div>'
        '<div class="label">Average time between<br>roe deer roadkills</div></div>',
        unsafe_allow_html=True,
    )

    st.markdown("")

    # Map of roadkill by county
    COUNTY_COORDS = {
        "Oslo - Oslove": {"lat": 59.91, "lon": 10.75},
        "Rogaland": {"lat": 58.97, "lon": 5.73},
        "Møre og Romsdal": {"lat": 62.47, "lon": 6.15},
        "Nordland - Nordlánnda": {"lat": 67.28, "lon": 14.40},
        "Innlandet": {"lat": 61.50, "lon": 10.47},
        "Agder": {"lat": 58.15, "lon": 7.99},
        "Vestland": {"lat": 60.39, "lon": 5.32},
        "Trøndelag - Trööndelage": {"lat": 63.43, "lon": 10.40},
        "Troms - Romsa - Tromssa": {"lat": 69.65, "lon": 18.96},
        "Finnmark - Finnmárku - Finmarkku": {"lat": 70.07, "lon": 25.07},
        "Akershus": {"lat": 59.87, "lon": 11.17},
        "Buskerud": {"lat": 60.24, "lon": 9.60},
        "Østfold": {"lat": 59.44, "lon": 11.18},
        "Telemark": {"lat": 59.27, "lon": 9.10},
        "Vestfold": {"lat": 59.27, "lon": 10.25},
    }

    # Aggregate by county for map
    if "county" in df_rk.columns and len(df_rk) > 0:
        county_totals = df_rk.groupby("county")["count"].sum().reset_index()
        county_totals = county_totals[county_totals["count"] > 0]

        map_rows = []
        for _, row in county_totals.iterrows():
            county = row["county"]
            coords = COUNTY_COORDS.get(county)
            if coords:
                map_rows.append({
                    "county": county,
                    "total_killed": int(row["count"]),
                    "lat": coords["lat"],
                    "lon": coords["lon"],
                })

        if map_rows:
            map_df = pd.DataFrame(map_rows)

            fig_map = px.scatter_mapbox(
                map_df,
                lat="lat", lon="lon",
                size="total_killed",
                size_max=40,
                color="total_killed",
                color_continuous_scale=["#34d399", "#fbbf24", "#ef4444"],
                hover_name="county",
                hover_data={"total_killed": True, "lat": False, "lon": False},
                zoom=4,
                center={"lat": 64.0, "lon": 12.0},
            )
            fig_map.update_layout(
                mapbox_style="carto-darkmatter",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(t=0, b=0, l=0, r=0),
                height=500,
                coloraxis_colorbar=dict(title="Animals killed", tickfont=dict(color="#8b8d98"),
                                        titlefont=dict(color="#8b8d98")),
            )
            st.plotly_chart(fig_map, use_container_width=True)

    # Bar chart by animal type
    if "animal" in df_rk.columns and "cause" in df_rk.columns:
        animal_summary = df_rk.groupby(["animal", "cause"])["count"].sum().reset_index()
        if len(animal_summary) > 0:
            fig_bar = px.bar(
                animal_summary, x="animal", y="count", color="cause",
                barmode="group",
                color_discrete_map={"car": "#ef4444", "train": "#60a5fa", "other": "#8b8d98"},
            )
            fig_bar.update_layout(
                **PLOT_LAYOUT,
                height=350,
                margin=dict(t=20, b=40, l=60, r=20),
                yaxis_title="Animals killed",
                xaxis_title="",
            )
            st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown(
        "> **Sobering fact:** Norway's roads claim more roe deer lives than all hunting seasons combined. "
        "The real apex predator? The Volvo."
    )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4: Cheese > Fish
# ══════════════════════════════════════════════════════════════════════════════

with tab4:
    st.markdown("### A Coastal Nation That Prefers Cheese")
    st.markdown("*Norwegian households spend more on cheese than seafood. Let that sink in.*")

    food_data = load_json("food_spending.json")
    df_food = pd.DataFrame(food_data)

    if len(df_food) > 0:
        df_food = df_food.sort_values("nok_per_year", ascending=True)

        colors = []
        for _, row in df_food.iterrows():
            cat = row["category"].lower()
            if "cheese" in cat:
                colors.append("#fbbf24")
            elif "fish" in cat or "seafood" in cat:
                colors.append("#60a5fa")
            else:
                colors.append("#8b8d98")

        fig = go.Figure(go.Bar(
            y=df_food["category"],
            x=df_food["nok_per_year"],
            orientation="h",
            marker_color=colors,
            text=[f"{v:,.0f} kr" for v in df_food["nok_per_year"]],
            textposition="outside",
            textfont=dict(color="#e8e8ed", size=11),
        ))

        # Highlight cheese vs fish
        cheese_val = df_food.loc[df_food["category"].str.lower().str.contains("cheese"), "nok_per_year"]
        fish_val = df_food.loc[df_food["category"].str.lower().str.contains("fish|seafood"), "nok_per_year"]

        if len(cheese_val) > 0 and len(fish_val) > 0:
            diff = float(cheese_val.values[0]) - float(fish_val.values[0])
            if diff > 0:
                st.markdown(
                    f'<div class="fun-stat"><div class="number">{diff:,.0f} kr</div>'
                    '<div class="label">More spent on cheese than fish per household per year</div></div>',
                    unsafe_allow_html=True,
                )
                st.markdown("")

        fig.update_layout(
            **PLOT_LAYOUT,
            height=max(400, len(df_food) * 40),
            margin=dict(t=20, b=40, l=180, r=80),
            xaxis_title="NOK per household per year",
            yaxis_title="",
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown(
        "> **National scandal:** Vikings conquered the seas for fish. Their descendants go to the store for Norvegia. "
        "The fishing industry is in shambles (not really, they export it all)."
    )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5: Marriage Survival
# ══════════════════════════════════════════════════════════════════════════════

with tab5:
    st.markdown("### Your Marriage: A Statistical Survival Guide")
    st.markdown("*Norwegian divorce data, presented with uncomfortable honesty*")

    divorce_data = load_json("divorces.json")
    df_div = pd.DataFrame(divorce_data)

    if len(df_div) > 0:
        # Get available years for the slider
        available_years = sorted(df_div["year"].unique())

        if len(available_years) > 1:
            selected_year = st.select_slider(
                "Select year",
                options=available_years,
                value=available_years[-1],
                key="div_year",
            )
        else:
            selected_year = available_years[0]

        year_data = df_div[df_div["year"] == selected_year].sort_values("count", ascending=False)

        if len(year_data) > 0:
            total_divorces = year_data["count"].sum()
            peak_duration = year_data.iloc[0]["duration"]

            k1, k2 = st.columns(2)
            k1.metric("Total Divorces", f"{total_divorces:,}", f"in {selected_year}")
            k2.metric("Most Dangerous Period", peak_duration, "highest divorce count")

            fig = px.bar(
                year_data, x="duration", y="count",
                color_discrete_sequence=["#f472b6"],
            )
            fig.update_layout(
                **PLOT_LAYOUT,
                height=400,
                margin=dict(t=20, b=40, l=60, r=20),
                yaxis_title="Number of divorces",
                xaxis_title="Duration of marriage",
            )
            st.plotly_chart(fig, use_container_width=True)

    # Regional divorce map
    try:
        regional_data = load_json("divorces_regional.json")
        df_reg = pd.DataFrame(regional_data)

        df_reg = df_reg[df_reg["region"] != "The whole country"]
        if len(df_reg) > 0 and "region" in df_reg.columns:
            st.markdown("##### Divorce Rate by Region")

            REGION_COORDS = {
                "Oslo": {"lat": 59.91, "lon": 10.75},
                "Rogaland": {"lat": 58.97, "lon": 5.73},
                "Nordland": {"lat": 67.28, "lon": 14.40},
                "Viken": {"lat": 59.87, "lon": 11.17},
                "Innlandet": {"lat": 61.50, "lon": 10.47},
                "Vestfold og Telemark": {"lat": 59.27, "lon": 9.60},
                "Agder": {"lat": 58.15, "lon": 7.99},
                "Vestland": {"lat": 60.39, "lon": 5.32},
                "More og Romsdal": {"lat": 62.47, "lon": 6.15},
                "Trondelag": {"lat": 63.43, "lon": 10.40},
                "Troms og Finnmark": {"lat": 69.65, "lon": 18.96},
                "Troms": {"lat": 69.65, "lon": 18.96},
                "Finnmark": {"lat": 70.07, "lon": 25.07},
                "Akershus": {"lat": 59.87, "lon": 11.17},
                "Buskerud": {"lat": 60.24, "lon": 9.60},
                "Ostfold": {"lat": 59.44, "lon": 11.18},
                "Telemark": {"lat": 59.27, "lon": 9.10},
                "Vestfold": {"lat": 59.27, "lon": 10.25},
            }

            latest_year = df_reg["year"].max()
            latest_reg = df_reg[df_reg["year"] == latest_year]

            map_rows = []
            for _, row in latest_reg.iterrows():
                region = row["region"]
                coords = REGION_COORDS.get(region)
                if coords:
                    map_rows.append({
                        "region": region,
                        "divorces": int(row["divorces"]),
                        "lat": coords["lat"],
                        "lon": coords["lon"],
                    })

            if map_rows:
                map_df = pd.DataFrame(map_rows)
                fig_map = px.scatter_mapbox(
                    map_df, lat="lat", lon="lon",
                    size="divorces", size_max=35,
                    color="divorces",
                    color_continuous_scale=["#34d399", "#fbbf24", "#ef4444"],
                    hover_name="region",
                    hover_data={"divorces": True, "lat": False, "lon": False},
                    zoom=4, center={"lat": 64.0, "lon": 12.0},
                )
                fig_map.update_layout(
                    mapbox_style="carto-darkmatter",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    margin=dict(t=0, b=0, l=0, r=0),
                    height=450,
                    coloraxis_colorbar=dict(title="Divorces", tickfont=dict(color="#8b8d98"),
                                            titlefont=dict(color="#8b8d98")),
                )
                st.plotly_chart(fig_map, use_container_width=True)
    except FileNotFoundError:
        pass

    st.markdown(
        "> **Pro tip:** If you've made it past 15 years, statistically you're in the clear. "
        "The 5-9 year mark is where dreams go to die."
    )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 6: Bike Theft Map
# ══════════════════════════════════════════════════════════════════════════════

with tab6:
    st.markdown("### Where NOT to Park Your Bike")
    st.markdown("*Crime rates per 1,000 population by county &mdash; Oslo stands alone*")

    crime_data = load_json("crime.json")
    df_crime = pd.DataFrame(crime_data)
    df_crime = df_crime.drop_duplicates()
    df_crime = df_crime[df_crime["offence"] != "All groups of offences"]

    if len(df_crime) > 0:
        CRIME_COUNTY_COORDS = {
            "Oslo": {"lat": 59.91, "lon": 10.75},
            "Rogaland": {"lat": 58.97, "lon": 5.73},
            "Nordland": {"lat": 67.28, "lon": 14.40},
            "Viken": {"lat": 59.87, "lon": 11.17},
            "Innlandet": {"lat": 61.50, "lon": 10.47},
            "Vestfold og Telemark": {"lat": 59.27, "lon": 9.60},
            "Agder": {"lat": 58.15, "lon": 7.99},
            "Vestland": {"lat": 60.39, "lon": 5.32},
            "More og Romsdal": {"lat": 62.47, "lon": 6.15},
            "Trondelag": {"lat": 63.43, "lon": 10.40},
            "Troms og Finnmark": {"lat": 69.65, "lon": 18.96},
            "Troms": {"lat": 69.65, "lon": 18.96},
            "Finnmark": {"lat": 70.07, "lon": 25.07},
            "Akershus": {"lat": 59.87, "lon": 11.17},
            "Buskerud": {"lat": 60.24, "lon": 9.60},
            "Ostfold": {"lat": 59.44, "lon": 11.18},
            "Telemark": {"lat": 59.27, "lon": 9.10},
            "Vestfold": {"lat": 59.27, "lon": 10.25},
        }

        # Get latest year
        latest_year = df_crime["year"].max()
        latest_crime = df_crime[df_crime["year"] == latest_year]

        # Offence type selector
        offence_types = sorted(latest_crime["offence"].unique())
        default_offence = next((o for o in offence_types if "theft" in o.lower() or "property" in o.lower()), offence_types[0] if offence_types else "")

        selected_offence = st.selectbox("Offence type", offence_types,
                                         index=offence_types.index(default_offence) if default_offence in offence_types else 0,
                                         key="crime_off")

        offence_data = latest_crime[latest_crime["offence"] == selected_offence]

        if len(offence_data) > 0:
            # Oslo comparison
            oslo_row = offence_data[offence_data["county"].str.contains("Oslo", case=False, na=False)]
            non_oslo = offence_data[~offence_data["county"].str.contains("Oslo", case=False, na=False)]

            if len(oslo_row) > 0 and len(non_oslo) > 0:
                oslo_rate = float(oslo_row["rate_per_1000"].values[0])
                avg_rate = non_oslo["rate_per_1000"].mean()
                ratio = oslo_rate / avg_rate if avg_rate > 0 else 0

                k1, k2, k3 = st.columns(3)
                k1.metric("Oslo", f"{oslo_rate:.1f}", "per 1,000 people")
                k2.metric("Rest of Norway (avg)", f"{avg_rate:.1f}", "per 1,000 people")
                k3.markdown(
                    f'<div class="fun-stat"><div class="number">{ratio:.1f}x</div>'
                    '<div class="label">Oslo vs rest of Norway</div></div>',
                    unsafe_allow_html=True,
                )

            st.markdown("")

            # Map
            map_rows = []
            for _, row in offence_data.iterrows():
                county = row["county"]
                coords = CRIME_COUNTY_COORDS.get(county)
                if coords:
                    map_rows.append({
                        "county": county,
                        "rate": float(row["rate_per_1000"]),
                        "lat": coords["lat"],
                        "lon": coords["lon"],
                    })

            if map_rows:
                map_df = pd.DataFrame(map_rows)
                fig_map = px.scatter_mapbox(
                    map_df, lat="lat", lon="lon",
                    size="rate", size_max=40,
                    color="rate",
                    color_continuous_scale=["#34d399", "#fbbf24", "#ef4444"],
                    hover_name="county",
                    hover_data={"rate": ":.1f", "lat": False, "lon": False},
                    zoom=4, center={"lat": 64.0, "lon": 12.0},
                )
                fig_map.update_layout(
                    mapbox_style="carto-darkmatter",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    margin=dict(t=0, b=0, l=0, r=0),
                    height=500,
                    coloraxis_colorbar=dict(title="Per 1,000", tickfont=dict(color="#8b8d98"),
                                            titlefont=dict(color="#8b8d98")),
                )
                st.plotly_chart(fig_map, use_container_width=True)

            # Bar chart
            offence_sorted = offence_data.sort_values("rate_per_1000", ascending=True)
            fig_bar = px.bar(
                offence_sorted, y="county", x="rate_per_1000",
                orientation="h",
                color_discrete_sequence=["#60a5fa"],
                text=[f"{v:.1f}" for v in offence_sorted["rate_per_1000"]],
            )
            fig_bar.update_traces(textposition="outside", textfont=dict(color="#e8e8ed", size=11))
            fig_bar.update_layout(
                **PLOT_LAYOUT,
                height=max(350, len(offence_sorted) * 35),
                margin=dict(t=20, b=40, l=200, r=60),
                xaxis_title="Offences per 1,000 people",
                yaxis_title="",
            )
            st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown(
        "> **Advice:** If you love your bicycle, move to Finnmark. "
        "Sure, it's dark 6 months a year, but at least your bike will still be there in the morning."
    )

# ── Footer ───────────────────────────────────────────────────────────────────

st.markdown(
    "<div style='text-align:center;color:#3f3f46;font-size:11px;margin-top:48px;padding-bottom:24px;'>"
    "Data from SSB (Statistics Norway) &middot; Built with Streamlit &middot; "
    "No Norwegians were harmed in the making of this dashboard (but several roe deer were)"
    "</div>",
    unsafe_allow_html=True,
)
