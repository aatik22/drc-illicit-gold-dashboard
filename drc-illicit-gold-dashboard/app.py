app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from pathlib import Path

# ==========================================================
# PAGE CONFIG
# ==========================================================

st.set_page_config(
    page_title="DRC Illicit Gold Trade Risk Dashboard",
    layout="wide"
)

st.title("DRC Illicit Gold Trade & Conflict Financing Dashboard")

st.markdown(
    """
    **Ahsen Neva Atik**  
    Koç University  
    DS4SDGs - SDG Target 16.4

    Interactive evidence base for reducing illicit financial and mineral flows in the Democratic Republic of Congo.
    """
)

# ==========================================================
# PATHS
# ==========================================================

BASE_DIR = Path(__file__).parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"

# ==========================================================
# LOAD DATA
# ==========================================================

@st.cache_data
def load_data():
    mines = pd.read_csv(PROCESSED_DIR / "ipis_clustered.csv")
    mirror_gap = pd.read_csv(PROCESSED_DIR / "comtrade_mirror_gap.csv")
    anomalies = pd.read_csv(PROCESSED_DIR / "comtrade_anomalies.csv")
    corridors = pd.read_csv(PROCESSED_DIR / "partner_corridors.csv")
    province_summary = pd.read_csv(PROCESSED_DIR / "province_summary.csv")
    simulations = pd.read_csv(PROCESSED_DIR / "counterfactual_results.csv")
    return mines, mirror_gap, anomalies, corridors, province_summary, simulations


try:
    mines, mirror_gap, anomalies, corridors, province_summary, simulations = load_data()
except Exception as e:
    st.error(f"Data loading failed: {e}")
    st.stop()

# ==========================================================
# COLUMN NORMALIZATION
# ==========================================================

if "reporterDesc" in anomalies.columns and "country" not in anomalies.columns:
    anomalies = anomalies.rename(columns={"reporterDesc": "country"})

if "reporterDesc" in corridors.columns and "country" not in corridors.columns:
    corridors = corridors.rename(columns={"reporterDesc": "country"})

if "Unnamed: 0" in province_summary.columns:
    province_summary = province_summary.rename(columns={"Unnamed: 0": "province"})

# ==========================================================
# DASHBOARD FILTERS
# ==========================================================

st.subheader("Dashboard Filters")

province_options = sorted(mines["province"].dropna().unique())
tier_options = ["Low", "Moderate", "High", "Critical"]
cluster_options = sorted(mines["cluster_label"].dropna().unique())

c1, c2, c3 = st.columns(3)

with c1:
    selected_provinces = st.multiselect(
        "Province",
        province_options,
        default=province_options
    )

with c2:
    selected_tiers = st.multiselect(
        "Risk Tier",
        tier_options,
        default=tier_options
    )

with c3:
    selected_clusters = st.multiselect(
        "Institutional Typology",
        cluster_options,
        default=cluster_options
    )

show_contamination_only = st.checkbox(
    "Show contamination-flagged mines only",
    value=False
)

filtered = mines[
    mines["province"].isin(selected_provinces)
    &
    mines["itri_tier"].isin(selected_tiers)
    &
    mines["cluster_label"].isin(selected_clusters)
].copy()

if show_contamination_only:
    filtered = filtered[filtered["contamination_flag"] == 1]

if filtered.empty:
    st.warning("No mines match the selected filters.")
    st.stop()

# ==========================================================
# TABS
# ==========================================================

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Executive Overview",
    "GIS Risk Map",
    "Institutional Typologies",
    "Trade Discrepancy & Anomalies",
    "Policy Simulation"
])

# ==========================================================
# TAB 1 — EXECUTIVE OVERVIEW
# ==========================================================

with tab1:
    st.subheader("Policy Snapshot")

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric("Gold Mines", f"{len(filtered):,}")
    c2.metric("Mean ITRI", f"{filtered['itri'].mean():.3f}")
    c3.metric("Critical Mines", f"{(filtered['itri_tier'] == 'Critical').sum():,}")
    c4.metric("Contamination Flags", f"{filtered['contamination_flag'].sum():,}")

    top_province = (
        filtered.groupby("province")["itri"]
        .mean()
        .sort_values(ascending=False)
        .index[0]
    )

    c5.metric("Highest-Risk Province", top_province)

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### ITRI Distribution")
        fig = px.histogram(
            filtered,
            x="itri",
            nbins=35,
            color="itri_tier",
            title="Distribution of Illicit Trade Risk Index"
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("### Province Risk Summary")

        prov_chart = (
            filtered.groupby("province")
            .agg(
                Mean_ITRI=("itri", "mean"),
                Critical_Mines=("itri_tier", lambda x: (x == "Critical").sum())
            )
            .reset_index()
            .sort_values("Mean_ITRI", ascending=False)
        )

        fig = px.bar(
            prov_chart,
            x="province",
            y="Mean_ITRI",
            title="Mean ITRI by Province"
        )
        st.plotly_chart(fig, use_container_width=True)

    st.info(
        "The dashboard identifies mine-level illicit trade risk, institutional failure typologies, "
        "trade discrepancy signals, and intervention scenarios. It is designed as a policy prioritization tool, "
        "not as a direct causal estimate of smuggling."
    )

# ==========================================================
# TAB 2 — GIS MAP
# ==========================================================

with tab2:
    st.subheader("Interactive Mine-Level Risk Map")

    map_df = filtered.dropna(subset=["latitude", "longitude"]).copy()

    risk_colors = {
    "Low": "#2E8B57",
    "Moderate": "#F4D03F",
    "High": "#E67E22",
    "Critical": "#C0392B"
}
fig = px.scatter_mapbox(
    map_df,
    lat="latitude",
    lon="longitude",
    color="itri_tier",
    color_discrete_map=risk_colors,
    category_orders={
        "itri_tier": [
            "Low",
            "Moderate",
            "High",
            "Critical"
        ]
    },
    size="itri",
    hover_name="name",
    hover_data={
        "province": True,
        "territoire": True,
        "itri": ":.3f",
        "itri_tier": True,
        "cluster_label": True,
        "contamination_flag": True,
        "latitude": False,
        "longitude": False
    },
    zoom=5,
    height=650,
    title="Mine-Level Illicit Trade Risk Map")
        zoom=5,
        height=650,
        title="Mine-Level Illicit Trade Risk Map")

    fig.update_layout(
        mapbox_style="carto-positron",
        margin={"r": 0, "t": 40, "l": 0, "b": 0})

    st.plotly_chart(fig, use_container_width=True)
    st.caption("Map uses quartile-based ITRI risk tiers.")

# ==========================================================
# TAB 3 — TYPOLOGIES
# ==========================================================

with tab3:
    st.subheader("K-Means Institutional Failure Typologies")

    cluster_summary = (
        mines.groupby("cluster_label")
        .agg(
            Mines=("cluster_label", "size"),
            Mean_ITRI=("itri", "mean"),
            Mean_Conflict=("conflict_financing_score", "mean"),
            Mean_Production=("production_opportunity_score", "mean"),
            Mean_Governance=("governance_weakness_score", "mean"),
            Mean_State_Services=("num_state_services", "mean")
        )
        .round(3)
        .reset_index()
        .sort_values("Mean_ITRI", ascending=False)
    )

    st.dataframe(cluster_summary, use_container_width=True, hide_index=True)

    col1, col2 = st.columns(2)

    with col1:
        fig = px.bar(
            cluster_summary,
            x="cluster_label",
            y="Mines",
            title="Number of Mines by Typology"
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.bar(
            cluster_summary,
            x="cluster_label",
            y="Mean_ITRI",
            title="Mean ITRI by Typology"
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Typology Interpretation")
    st.markdown("""
    - **Captured Governance Hotspots:** many state services but high governance weakness and conflict risk.
    - **Remote Conflict-Financed Mines:** high conflict risk with almost no formal oversight.
    - **Monitored Extraction Zones:** moderate risk with comparatively stronger monitoring.
    - **Peripheral Low-Governance Mines:** low conflict and limited formal state presence.
    """)

# ==========================================================
# TAB 4 — TRADE DISCREPANCY
# ==========================================================

with tab4:
    st.subheader("UN Comtrade Mirror Analysis")

    col1, col2 = st.columns(2)

    plot_gap = mirror_gap[
        mirror_gap["is_2023_shock"] == 0
    ]

    with col1:
        fig = px.line(
            plot_gap,
            x="period",
            y="mirror_trade_gap",
            markers=True,
            title="Mirror Trade Gap: Partner Imports − DRC Exports (2023 excluded)"
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.line(
            plot_gap,
            x="period",
            y="gap_ratio",
            markers=True,
            title="Mirror Gap Ratio (2023 excluded)"
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Mirror Gap Table")

    mirror_display = (
        mirror_gap.rename(
            columns={
                "period": "Year",
                "partner_reported_imports": "Partner Imports (USD)",
                "reporting_partners": "Reporting Partners",
                "drc_reported_exports": "DRC Exports (USD)",
                "mirror_trade_gap": "Mirror Gap (USD)",
                "gap_ratio": "Gap Ratio",
                "is_2023_shock": "2023 Structural Outlier"
            }
        )
    )

    money_cols = [
        "Partner Imports (USD)",
        "DRC Exports (USD)",
        "Mirror Gap (USD)"
    ]

    for col in money_cols:
        mirror_display[col] = (
            mirror_display[col]
            .map(lambda x: f"${x:,.0f}")
        )

    mirror_display["Gap Ratio"] = (
        mirror_display["Gap Ratio"]
        .map(lambda x: f"{x:.1%}")
    )

    st.dataframe(
        mirror_display,
        use_container_width=True,
        hide_index=True
    )

    st.markdown("### Top Partner Corridors")

    if "country" in corridors.columns:
        top_corridors = (
            corridors.groupby("country")
            .agg(
                Total_Import_Value=("partner_import_value", "sum"),
                Years_Reported=("period", "nunique")
            )
            .reset_index()
            .sort_values("Total_Import_Value", ascending=False)
        )

        fig = px.bar(
            top_corridors.head(12),
            x="country",
            y="Total_Import_Value",
            title="Top Reported Import Corridors"
        )
        st.plotly_chart(fig, use_container_width=True)

        corridor_display = (
            top_corridors.rename(
                columns={
                    "country": "Partner Country",
                    "Total_Import_Value": "Total Import Value (USD)",
                    "Years_Reported": "Years Reported"
                }
            )
        )

        corridor_display["Total Import Value (USD)"] = (
            corridor_display["Total Import Value (USD)"]
            .map(lambda x: f"${x:,.0f}")
        )

        st.dataframe(
            corridor_display,
            use_container_width=True,
            hide_index=True
        )

        st.info(
            "The United Arab Emirates, China, Uganda, and Belgium account for the majority of declared partner imports of Congolese gold and constitute the principal trade corridors requiring enhanced due diligence and traceability measures."
        )

    else:
        st.warning("Country column not found in partner corridors file.")

    st.markdown("### Isolation Forest Trade Anomalies")

    display_df = (
        anomalies[
            [
                "period",
                "country",
                "partner_import_value",
                "anomaly_score"
            ]
        ]
        .rename(
            columns={
                "period": "Year",
                "country": "Partner Country",
                "partner_import_value": "Declared Import Value (USD)",
                "anomaly_score": "Anomaly Score"
            }
        )
    )

    display_df["Declared Import Value (USD)"] = (
        display_df["Declared Import Value (USD)"]
        .map(lambda x: f"${x:,.0f}")
    )

    display_df["Anomaly Score"] = (
        display_df["Anomaly Score"]
        .round(4)
    )

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )

    st.info(
        "The Isolation Forest flags statistically unusual partner-year import values. "
        "Quantity information (altQty) exhibited no variation in the available UN Comtrade records, "
        "so anomaly detection was implemented as a univariate model on declared import values only. "
        "These anomalies should be interpreted as signals requiring further scrutiny rather than direct proof of illicit trade."
    )

# ==========================================================
# TAB 5 — POLICY SIMULATION
# ==========================================================

with tab5:
    st.subheader("Counterfactual Policy Simulation")

    st.markdown(
        "Scenario simulations estimate how expanding responsible sourcing and traceability coverage "
        "could reduce the national Illicit Trade Risk Index."
    )

    st.dataframe(simulations, use_container_width=True, hide_index=True)

    col1, col2 = st.columns(2)

    with col1:
        fig = px.bar(
            simulations,
            x="Scenario",
            y="Mean_ITRI",
            title="Simulated Mean ITRI by Scenario"
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.bar(
            simulations,
            x="Scenario",
            y="Critical_Mines_Reduction",
            title="Reduction in Critical Mines"
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Priority Intervention Mines")

    priority_cols = [
        "name",
        "province",
        "territoire",
        "itri",
        "itri_tier",
        "cluster_label",
        "workers_numb",
        "contamination_flag"
    ]

    priority = (
        mines[
            (mines["traceability"].isna())
            &
            (mines["itri_tier"].isin(["High", "Critical"]))
        ]
        .sort_values("itri", ascending=False)
        [priority_cols]
        .head(25)
    )

    st.dataframe(priority, use_container_width=True, hide_index=True)

    st.success(
        "Policy implication: targeting high-risk and critical untraceable mines produces the largest reduction "
        "in critical risk exposure, while accessible mine expansion offers a practical lower-cost intervention path."
    )

st.markdown("---")
st.caption(
    "Developed by Ahsen Neva Atik • Koç University • DS4SDGs")# LOAD DATA
# ==========================================================

@st.cache_data
def load_data():
    mines = pd.read_csv(PROCESSED_DIR / "ipis_clustered.csv")
    mirror_gap = pd.read_csv(PROCESSED_DIR / "comtrade_mirror_gap.csv")
    anomalies = pd.read_csv(PROCESSED_DIR / "comtrade_anomalies.csv")
    corridors = pd.read_csv(PROCESSED_DIR / "partner_corridors.csv")
    province_summary = pd.read_csv(PROCESSED_DIR / "province_summary.csv")
    simulations = pd.read_csv(PROCESSED_DIR / "counterfactual_results.csv")
    return mines, mirror_gap, anomalies, corridors, province_summary, simulations


try:
    mines, mirror_gap, anomalies, corridors, province_summary, simulations = load_data()
except Exception as e:
    st.error(f"Data loading failed: {e}")
    st.stop()

# ==========================================================
# COLUMN NORMALIZATION
# ==========================================================

if "reporterDesc" in anomalies.columns and "country" not in anomalies.columns:
    anomalies = anomalies.rename(columns={"reporterDesc": "country"})

if "reporterDesc" in corridors.columns and "country" not in corridors.columns:
    corridors = corridors.rename(columns={"reporterDesc": "country"})

if "Unnamed: 0" in province_summary.columns:
    province_summary = province_summary.rename(columns={"Unnamed: 0": "province"})

# ==========================================================
# DASHBOARD FILTERS
# ==========================================================

st.subheader("Dashboard Filters")

province_options = sorted(mines["province"].dropna().unique())
tier_options = ["Low", "Moderate", "High", "Critical"]
cluster_options = sorted(mines["cluster_label"].dropna().unique())

c1, c2, c3 = st.columns(3)

with c1:
    selected_provinces = st.multiselect(
        "Province",
        province_options,
        default=province_options
    )

with c2:
    selected_tiers = st.multiselect(
        "Risk Tier",
        tier_options,
        default=tier_options
    )

with c3:
    selected_clusters = st.multiselect(
        "Institutional Typology",
        cluster_options,
        default=cluster_options
    )

show_contamination_only = st.checkbox(
    "Show contamination-flagged mines only",
    value=False
)

filtered = mines[
    mines["province"].isin(selected_provinces)
    &
    mines["itri_tier"].isin(selected_tiers)
    &
    mines["cluster_label"].isin(selected_clusters)
].copy()

if show_contamination_only:
    filtered = filtered[filtered["contamination_flag"] == 1]

if filtered.empty:
    st.warning("No mines match the selected filters.")
    st.stop()

# ==========================================================
# TABS
# ==========================================================

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Executive Overview",
    "GIS Risk Map",
    "Institutional Typologies",
    "Trade Discrepancy & Anomalies",
    "Policy Simulation"
])

# ==========================================================
# TAB 1 — EXECUTIVE OVERVIEW
# ==========================================================

with tab1:
    st.subheader("Policy Snapshot")

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric("Gold Mines", f"{len(filtered):,}")
    c2.metric("Mean ITRI", f"{filtered['itri'].mean():.3f}")
    c3.metric("Critical Mines", f"{(filtered['itri_tier'] == 'Critical').sum():,}")
    c4.metric("Contamination Flags", f"{filtered['contamination_flag'].sum():,}")

    top_province = (
        filtered.groupby("province")["itri"]
        .mean()
        .sort_values(ascending=False)
        .index[0]
    )

    c5.metric("Highest-Risk Province", top_province)

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### ITRI Distribution")
        fig = px.histogram(
            filtered,
            x="itri",
            nbins=35,
            color="itri_tier",
            title="Distribution of Illicit Trade Risk Index"
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("### Province Risk Summary")

        prov_chart = (
            filtered.groupby("province")
            .agg(
                Mean_ITRI=("itri", "mean"),
                Critical_Mines=("itri_tier", lambda x: (x == "Critical").sum())
            )
            .reset_index()
            .sort_values("Mean_ITRI", ascending=False)
        )

        fig = px.bar(
            prov_chart,
            x="province",
            y="Mean_ITRI",
            title="Mean ITRI by Province"
        )
        st.plotly_chart(fig, use_container_width=True)

    st.info(
        "The dashboard identifies mine-level illicit trade risk, institutional failure typologies, "
        "trade discrepancy signals, and intervention scenarios. It is designed as a policy prioritization tool, "
        "not as a direct causal estimate of smuggling."
    )

# ==========================================================
# TAB 2 — GIS MAP
# ==========================================================

with tab2:
    st.subheader("Interactive Mine-Level Risk Map")

    map_df = filtered.dropna(subset=["latitude", "longitude"]).copy()

    fig = px.scatter_mapbox(
        map_df,
        lat="latitude",
        lon="longitude",
        color="itri_tier",
        size="itri",
        hover_name="name",
        hover_data={
            "province": True,
            "territoire": True,
            "itri": ":.3f",
            "itri_tier": True,
            "cluster_label": True,
            "contamination_flag": True,
            "latitude": False,
            "longitude": False
        },
        zoom=5,
        height=650,
        title="Mine-Level Illicit Trade Risk Map"
    )

    fig.update_layout(
        mapbox_style="carto-positron",
        margin={"r": 0, "t": 40, "l": 0, "b": 0}
    )

    st.plotly_chart(fig, use_container_width=True)
    st.caption("Map uses quartile-based ITRI risk tiers.")

# ==========================================================
# TAB 3 — TYPOLOGIES
# ==========================================================

with tab3:
    st.subheader("K-Means Institutional Failure Typologies")

    cluster_summary = (
        mines.groupby("cluster_label")
        .agg(
            Mines=("cluster_label", "size"),
            Mean_ITRI=("itri", "mean"),
            Mean_Conflict=("conflict_financing_score", "mean"),
            Mean_Production=("production_opportunity_score", "mean"),
            Mean_Governance=("governance_weakness_score", "mean"),
            Mean_State_Services=("num_state_services", "mean")
        )
        .round(3)
        .reset_index()
        .sort_values("Mean_ITRI", ascending=False)
    )

    st.dataframe(cluster_summary, use_container_width=True, hide_index=True)

    col1, col2 = st.columns(2)

    with col1:
        fig = px.bar(
            cluster_summary,
            x="cluster_label",
            y="Mines",
            title="Number of Mines by Typology"
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.bar(
            cluster_summary,
            x="cluster_label",
            y="Mean_ITRI",
            title="Mean ITRI by Typology"
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Typology Interpretation")
    st.markdown("""
    - **Captured Governance Hotspots:** many state services but high governance weakness and conflict risk.
    - **Remote Conflict-Financed Mines:** high conflict risk with almost no formal oversight.
    - **Monitored Extraction Zones:** moderate risk with comparatively stronger monitoring.
    - **Peripheral Low-Governance Mines:** low conflict and limited formal state presence.
    """)

# ==========================================================
# TAB 4 — TRADE DISCREPANCY
# ==========================================================

with tab4:
    st.subheader("UN Comtrade Mirror Analysis")

    col1, col2 = st.columns(2)

    plot_gap = mirror_gap[
        mirror_gap["is_2023_shock"] == 0
    ]

    with col1:
        fig = px.line(
            plot_gap,
            x="period",
            y="mirror_trade_gap",
            markers=True,
            title="Mirror Trade Gap: Partner Imports − DRC Exports (2023 excluded)"
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.line(
            plot_gap,
            x="period",
            y="gap_ratio",
            markers=True,
            title="Mirror Gap Ratio (2023 excluded)"
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Mirror Gap Table")

    mirror_display = (
        mirror_gap.rename(
            columns={
                "period": "Year",
                "partner_reported_imports": "Partner Imports (USD)",
                "reporting_partners": "Reporting Partners",
                "drc_reported_exports": "DRC Exports (USD)",
                "mirror_trade_gap": "Mirror Gap (USD)",
                "gap_ratio": "Gap Ratio",
                "is_2023_shock": "2023 Structural Outlier"
            }
        )
    )

    money_cols = [
        "Partner Imports (USD)",
        "DRC Exports (USD)",
        "Mirror Gap (USD)"
    ]

    for col in money_cols:
        mirror_display[col] = (
            mirror_display[col]
            .map(lambda x: f"${x:,.0f}")
        )

    mirror_display["Gap Ratio"] = (
        mirror_display["Gap Ratio"]
        .map(lambda x: f"{x:.1%}")
    )

    st.dataframe(
        mirror_display,
        use_container_width=True,
        hide_index=True
    )

    st.markdown("### Top Partner Corridors")

    if "country" in corridors.columns:
        top_corridors = (
            corridors.groupby("country")
            .agg(
                Total_Import_Value=("partner_import_value", "sum"),
                Years_Reported=("period", "nunique")
            )
            .reset_index()
            .sort_values("Total_Import_Value", ascending=False)
        )

        fig = px.bar(
            top_corridors.head(12),
            x="country",
            y="Total_Import_Value",
            title="Top Reported Import Corridors"
        )
        st.plotly_chart(fig, use_container_width=True)

        corridor_display = (
            top_corridors.rename(
                columns={
                    "country": "Partner Country",
                    "Total_Import_Value": "Total Import Value (USD)",
                    "Years_Reported": "Years Reported"
                }
            )
        )

        corridor_display["Total Import Value (USD)"] = (
            corridor_display["Total Import Value (USD)"]
            .map(lambda x: f"${x:,.0f}")
        )

        st.dataframe(
            corridor_display,
            use_container_width=True,
            hide_index=True
        )

        st.info(
            "The United Arab Emirates, China, Uganda, and Belgium account for the majority of declared partner imports of Congolese gold and constitute the principal trade corridors requiring enhanced due diligence and traceability measures."
        )

    else:
        st.warning("Country column not found in partner corridors file.")

    st.markdown("### Isolation Forest Trade Anomalies")

    display_df = (
        anomalies[
            [
                "period",
                "country",
                "partner_import_value",
                "anomaly_score"
            ]
        ]
        .rename(
            columns={
                "period": "Year",
                "country": "Partner Country",
                "partner_import_value": "Declared Import Value (USD)",
                "anomaly_score": "Anomaly Score"
            }
        )
    )

    display_df["Declared Import Value (USD)"] = (
        display_df["Declared Import Value (USD)"]
        .map(lambda x: f"${x:,.0f}")
    )

    display_df["Anomaly Score"] = (
        display_df["Anomaly Score"]
        .round(4)
    )

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )

    st.info(
        "The Isolation Forest flags statistically unusual partner-year import values. "
        "Quantity information (altQty) exhibited no variation in the available UN Comtrade records, "
        "so anomaly detection was implemented as a univariate model on declared import values only. "
        "These anomalies should be interpreted as signals requiring further scrutiny rather than direct proof of illicit trade."
    )

# ==========================================================
# TAB 5 — POLICY SIMULATION
# ==========================================================

with tab5:
    st.subheader("Counterfactual Policy Simulation")

    st.markdown(
        "Scenario simulations estimate how expanding responsible sourcing and traceability coverage "
        "could reduce the national Illicit Trade Risk Index."
    )

    st.dataframe(simulations, use_container_width=True, hide_index=True)

    col1, col2 = st.columns(2)

    with col1:
        fig = px.bar(
            simulations,
            x="Scenario",
            y="Mean_ITRI",
            title="Simulated Mean ITRI by Scenario"
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.bar(
            simulations,
            x="Scenario",
            y="Critical_Mines_Reduction",
            title="Reduction in Critical Mines"
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Priority Intervention Mines")

    priority_cols = [
        "name",
        "province",
        "territoire",
        "itri",
        "itri_tier",
        "cluster_label",
        "workers_numb",
        "contamination_flag"
    ]

    priority = (
        mines[
            (mines["traceability"].isna())
            &
            (mines["itri_tier"].isin(["High", "Critical"]))
        ]
        .sort_values("itri", ascending=False)
        [priority_cols]
        .head(25)
    )

    st.dataframe(priority, use_container_width=True, hide_index=True)

    st.success(
        "Policy implication: targeting high-risk and critical untraceable mines produces the largest reduction "
        "in critical risk exposure, while accessible mine expansion offers a practical lower-cost intervention path."
    )

st.markdown("---")
st.caption(
    "Developed by Ahsen Neva Atik • Koç University • DS4SDGs")
