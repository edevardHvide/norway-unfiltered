"""Arbeidsledighet per fylke — BearingPoint-branded Streamlit dashboard.

Data: SSB tabell 13563 (prioritert arbeidsstyrkestatus), aggregert per fylke via
codelist agg_KommFylker (sammenslåtte tidsserier). Regenereres via
ssb-report-generator-skillen.
"""

from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

DATA_PATH = Path(__file__).parent.parent.parent / "data" / "13563__e32cdc72.parquet"

BP = {
    "accent_1": "#99171D",
    "accent_2": "#FF787A",
    "accent_3": "#FFB1B5",
    "accent_4": "#806659",
    "accent_5": "#B2A59F",
    "dark_1": "#000000",
    "dark_2": "#421799",
    "light_1": "#FFFFFF",
    "light_2": "#FAF8F7",
    "link": "#A070FF",
}

EXCLUDE_CODES = {"F-21", "F-22", "F-23"}  # Svalbard, Jan Mayen, Kontinentalsokkel — null-serier

st.set_page_config(
    page_title="Arbeidsledighet per fylke",
    page_icon="📊",
    layout="wide",
)

st.markdown(
    f"""
    <style>
      .stApp {{ background: {BP['light_2']}; color: {BP['dark_1']};
              font-family: 'Aptos', Calibri, sans-serif; }}
      h1, h2, h3, h4 {{ font-family: 'Aptos Display', Calibri, sans-serif;
                       color: {BP['dark_1']}; font-weight: 700; letter-spacing: -0.01em; }}
      [data-testid="stMetricValue"] {{ color: {BP['accent_1']};
                                     font-family: 'Aptos Display', Calibri, sans-serif; }}
      [data-testid="stMetricLabel"] {{ color: {BP['accent_4']};
                                      text-transform: uppercase; font-size: 11px;
                                      letter-spacing: 0.08em; }}
      a {{ color: {BP['link']}; text-decoration: none; }}
      a:hover {{ text-decoration: underline; }}
      .footer {{ color: {BP['accent_5']}; font-size: 12px;
                border-top: 1px solid {BP['accent_5']};
                padding-top: 12px; margin-top: 32px; }}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def load_data() -> pd.DataFrame:
    df = pd.read_parquet(DATA_PATH)
    df = df[~df["fylke_kode"].isin(EXCLUDE_CODES)].copy()
    df["fylke"] = df["fylke"].str.split(" - ").str[0]  # "Oslo - Oslove" -> "Oslo"
    df = df.rename(columns={"registrerte_arbeidsledige": "ledige"})
    df["ar"] = df["ar"].astype(int)
    return df


df = load_data()
years = sorted(df["ar"].unique())
fylker = sorted(df["fylke"].unique())

# ── Sidebar ──────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Filtre")
    year = st.slider(
        "Velg år",
        min_value=years[0],
        max_value=years[-1],
        value=years[-1],
        step=1,
    )

    default_top5 = (
        df[df["ar"] == year]
        .nlargest(5, "ledige")["fylke"]
        .tolist()
    )
    trend_fylker = st.multiselect(
        "Fylker i trendgraf",
        options=fylker,
        default=default_top5,
    )

    st.caption(
        f"**Kilde:** SSB tabell 13563 — prioritert arbeidsstyrkestatus. "
        f"Periode {years[0]}–{years[-1]}."
    )

# ── Slice data ───────────────────────────────────────────────────────────
year_df = df[df["ar"] == year].sort_values("ledige", ascending=False)
prev_df = df[df["ar"] == (year - 1)] if (year - 1) in years else pd.DataFrame()
national_ts = df.groupby("ar", as_index=False)["ledige"].sum()

total_now = int(year_df["ledige"].sum())
total_prev = int(prev_df["ledige"].sum()) if not prev_df.empty else None
delta_total = total_now - total_prev if total_prev is not None else None

top_row = year_df.iloc[0]
bottom_row = year_df.iloc[-1]

# ── Header ───────────────────────────────────────────────────────────────
st.title("Arbeidsledighet per fylke")
st.markdown(
    f"Registrerte arbeidsledige 15–74 år, {years[0]}–{years[-1]}. "
    f"Valgt år: **{year}**."
)

# ── KPI row ──────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)

with k1:
    st.metric(
        label="Totalt ledige",
        value=f"{total_now:,}".replace(",", " "),
        delta=f"{delta_total:+,}".replace(",", " ") if delta_total is not None else None,
        border=True,
        chart_data=national_ts["ledige"].tolist(),
        chart_type="line",
    )

with k2:
    st.metric(
        label="Høyest fylke",
        value=top_row["fylke"],
        delta=f"{int(top_row['ledige']):,} ledige".replace(",", " "),
        delta_color="off",
        border=True,
    )

with k3:
    st.metric(
        label="Lavest fylke",
        value=bottom_row["fylke"],
        delta=f"{int(bottom_row['ledige']):,} ledige".replace(",", " "),
        delta_color="off",
        border=True,
    )

with k4:
    pct_of_total = top_row["ledige"] / total_now * 100
    st.metric(
        label=f"{top_row['fylke']}s andel",
        value=f"{pct_of_total:.1f} %",
        border=True,
    )

# ── Charts row ──────────────────────────────────────────────────────────
c1, c2 = st.columns([3, 4])

with c1:
    with st.container(border=True):
        st.subheader(f"Rangering {year}")
        # Highlight top 3 in accent_1, rest in accent_5
        ranked = year_df.reset_index(drop=True).copy()
        ranked["rank_bucket"] = ["Topp 3" if i < 3 else "Øvrige" for i in range(len(ranked))]
        bar = (
            alt.Chart(ranked)
            .mark_bar()
            .encode(
                x=alt.X("ledige:Q", title="Registrerte ledige"),
                y=alt.Y("fylke:N", sort="-x", title=None),
                color=alt.Color(
                    "rank_bucket:N",
                    scale=alt.Scale(
                        domain=["Topp 3", "Øvrige"],
                        range=[BP["accent_1"], BP["accent_5"]],
                    ),
                    legend=None,
                ),
                tooltip=[
                    alt.Tooltip("fylke:N", title="Fylke"),
                    alt.Tooltip("ledige:Q", title="Ledige", format=","),
                ],
            )
            .properties(height=440)
        )
        st.altair_chart(bar, use_container_width=True)

with c2:
    with st.container(border=True):
        st.subheader("Tidsutvikling")
        trend_df = df[df["fylke"].isin(trend_fylker)] if trend_fylker else df.iloc[0:0]
        if trend_df.empty:
            st.info("Velg minst ett fylke i sidepanelet.")
        else:
            palette = [BP["accent_1"], BP["accent_2"], BP["dark_2"],
                       BP["accent_4"], BP["accent_5"], BP["accent_3"]]
            line = (
                alt.Chart(trend_df)
                .mark_line(strokeWidth=2.5, point=alt.OverlayMarkDef(size=40))
                .encode(
                    x=alt.X("ar:O", title="År"),
                    y=alt.Y("ledige:Q", title="Registrerte ledige"),
                    color=alt.Color(
                        "fylke:N",
                        scale=alt.Scale(range=palette),
                        legend=alt.Legend(orient="bottom", title=None),
                    ),
                    tooltip=[
                        alt.Tooltip("fylke:N", title="Fylke"),
                        alt.Tooltip("ar:O", title="År"),
                        alt.Tooltip("ledige:Q", title="Ledige", format=","),
                    ],
                )
                .properties(height=440)
            )
            rule = alt.Chart(pd.DataFrame({"ar": [year]})).mark_rule(
                color=BP["dark_1"], strokeDash=[4, 4], opacity=0.5
            ).encode(x="ar:O")
            st.altair_chart(line + rule, use_container_width=True)

# ── Data table ──────────────────────────────────────────────────────────
with st.container(border=True):
    st.subheader(f"Fylkestabell — {year}")
    table = year_df[["fylke", "ledige"]].reset_index(drop=True).copy()
    if not prev_df.empty:
        prev_lookup = prev_df.set_index("fylke")["ledige"]
        table["endring_yoy"] = table["fylke"].map(prev_lookup).rsub(table["ledige"])
        table["endring_pct"] = (table["endring_yoy"] / table["fylke"].map(prev_lookup)) * 100
    table.index = table.index + 1
    table.index.name = "Rang"
    st.dataframe(
        table,
        use_container_width=True,
        column_config={
            "fylke": st.column_config.TextColumn("Fylke"),
            "ledige": st.column_config.NumberColumn("Ledige", format="%d"),
            "endring_yoy": st.column_config.NumberColumn(
                f"Endring vs {year - 1}", format="%+d"
            ) if not prev_df.empty else None,
            "endring_pct": st.column_config.NumberColumn(
                "Endring (%)", format="%+.1f %%"
            ) if not prev_df.empty else None,
        },
    )

st.markdown(
    '<div class="footer">'
    'Kilde: Statistisk sentralbyrå, tabell 13563 — prioritert arbeidsstyrkestatus, '
    'aggregert via codelist <code>agg_KommFylker</code>. '
    'Registrerte arbeidsledige 15–74 år, I alt (begge kjønn, alle innvandringskategorier). '
    'Svalbard, Jan Mayen og Kontinentalsokkelen er utelatt (null-serier). '
    'Visuell identitet: BearingPoint.'
    '</div>',
    unsafe_allow_html=True,
)
