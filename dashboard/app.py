"""
dashboard/app.py

Interactive Streamlit dashboard presenting Bob's Part 2-4 analyses, reading
directly from the SQLite database built by load_data.py.

Run with:
    streamlit run dashboard/app.py
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from analysis.queries import (  # noqa: E402
    DEFAULT_DB,
    avg_b_cells_melanoma_male_responders_t0,
    baseline_subset_breakdown,
    cell_frequencies,
    get_connection,
    responder_frequencies,
    responder_statistics,
)

st.set_page_config(page_title="Loblaw Bio | Miraclib Immune Cell Analysis", layout="wide")

if not Path(DEFAULT_DB).exists():
    # Hosted deployments don't have the gitignored .db; build it from the CSV.
    import subprocess

    subprocess.run([sys.executable, str(ROOT / "load_data.py")], check=True, cwd=ROOT)

conn = get_connection()

st.title("Loblaw Bio — Miraclib Immune Cell Population Analysis")
st.caption(
    "Cell population frequencies and treatment-response analysis for Bob Loblaw's "
    "clinical trial, built on cell-count.csv."
)

tab2, tab3, tab4 = st.tabs(
    ["Part 2 — Frequency Overview", "Part 3 — Responders vs Non-Responders", "Part 4 — Baseline Subset"]
)

# ---------------------------------------------------------------------------
# Part 2
# ---------------------------------------------------------------------------
with tab2:
    st.subheader("Relative frequency of each cell population, per sample")
    freq = cell_frequencies(conn)

    samples = sorted(freq["sample"].unique())
    selected = st.multiselect(
        "Filter to specific samples (leave empty to show all)", samples, default=[]
    )
    view = freq[freq["sample"].isin(selected)] if selected else freq

    st.dataframe(view, use_container_width=True, height=400)
    st.download_button(
        "Download full frequency table as CSV",
        freq.to_csv(index=False).encode(),
        file_name="cell_frequencies.csv",
        mime="text/csv",
    )

    st.markdown("**Average population composition across all samples**")
    avg_comp = freq.groupby("population")["percentage"].mean().reset_index()
    fig_avg = px.pie(avg_comp, names="population", values="percentage", hole=0.4)
    st.plotly_chart(fig_avg, use_container_width=True)

# ---------------------------------------------------------------------------
# Part 3
# ---------------------------------------------------------------------------
with tab3:
    st.subheader("Melanoma patients on miraclib (PBMC samples): responders vs non-responders")

    resp_df = responder_frequencies(conn)
    stats_df = responder_statistics(conn)

    st.markdown("**Boxplots of relative frequency (%) by population and response**")
    fig = px.box(
        resp_df,
        x="population",
        y="percentage",
        color="response",
        points="all",
        category_orders={"response": ["yes", "no"]},
        labels={"percentage": "Relative frequency (%)", "population": "Cell population", "response": "Response"},
        color_discrete_map={"yes": "#2ca02c", "no": "#d62728"},
    )
    fig.update_layout(legend_title_text="Responder?")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("**Statistical comparison (Mann-Whitney U test, two-sided)**")
    st.dataframe(stats_df, use_container_width=True)

    sig = stats_df[stats_df["significant_p<0.05"]]
    if len(sig):
        pops = ", ".join(sig["population"].tolist())
        st.success(
            f"In plain English: responders and non-responders differ significantly "
            f"(p < 0.05, uncorrected) in: **{pops}**."
        )
    else:
        st.info("No population reached statistical significance at p < 0.05.")

    with st.expander("Methodology notes"):
        st.markdown(
            "- Restricted to **melanoma** patients treated with **miraclib**, **PBMC** samples only.\n"
            "- Relative frequency (%) = population count / total cell count for that sample, "
            "from the Part 2 summary table.\n"
            "- Mann-Whitney U (rank-sum) test used rather than a t-test since percentages are "
            "bounded and not guaranteed to be normally distributed; it compares distributions "
            "without assuming normality.\n"
            "- Significance threshold: p < 0.05, uncorrected for multiple comparisons "
            "(5 populations tested)."
        )

# ---------------------------------------------------------------------------
# Part 4
# ---------------------------------------------------------------------------
with tab4:
    st.subheader("Baseline (t=0) melanoma PBMC samples, miraclib-treated")

    breakdown = baseline_subset_breakdown(conn)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**Samples per project**")
        st.dataframe(breakdown["samples_per_project"], use_container_width=True, hide_index=True)
    with c2:
        st.markdown("**Responders vs non-responders**")
        st.dataframe(breakdown["responders_vs_non"], use_container_width=True, hide_index=True)
    with c3:
        st.markdown("**Sex breakdown**")
        st.dataframe(breakdown["sex_breakdown"], use_container_width=True, hide_index=True)

    st.markdown("---")
    avg_b = avg_b_cells_melanoma_male_responders_t0(conn)
    st.metric(
        "Avg. B cells — melanoma males, responders, t=0 (all sample/treatment types)",
        f"{avg_b:.2f}",
    )
    st.caption(
        "This figure considers melanoma male subjects across all sample types and treatments "
        "(not limited to miraclib/PBMC), filtered to responders at time_from_treatment_start = 0."
    )

conn.close()
