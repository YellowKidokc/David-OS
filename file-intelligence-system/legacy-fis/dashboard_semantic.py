"""Semantic Address Dashboard — Tier 1 (Read-Only)
FIS Knowledge Coordinate System Viewer

Scans a folder, scores every file, displays the vector space.
Zero renames. Zero file changes. Pure visibility.

Deploy: Copy to NAS, run with streamlit run dashboard_semantic.py
Requires: streamlit, plotly, pandas, psycopg2
Also needs FIS repo accessible (for scorer imports)
"""
import sys
from pathlib import Path

# Add FIS repo to path for imports
FIS_REPO = r"D:\GitHub\file-intelligence-system"
sys.path.insert(0, FIS_REPO)

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from collections import Counter

from fis.nlp.semantic_scorer import SemanticScorer, VAR_NAMES, project_name
from fis.nlp.extractor import extract_text

# --- Page Config ---
st.set_page_config(
    page_title="FIS Semantic Dashboard",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🧭 Knowledge Coordinate System")
st.caption("Tier 1 — Read Only. Your files are not modified.")


@st.cache_resource
def get_scorer():
    return SemanticScorer()


@st.cache_data(ttl=300)
def scan_folder(folder_path: str, max_files: int = 500):
    """Scan a folder and score every file. Returns DataFrame."""
    scorer = get_scorer()
    root = Path(folder_path)

    if not root.exists():
        return pd.DataFrame()

    files = []
    for f in root.rglob("*"):
        if f.is_file() and not f.name.startswith(".") and f.name != "desktop.ini":
            files.append(f)
        if len(files) >= max_files:
            break

    results = []
    progress = st.progress(0, text="Scanning files...")

    for i, f in enumerate(files):
        progress.progress((i + 1) / len(files), text=f"Scoring {f.name[:40]}...")
        try:
            addr = scorer.score_file(str(f))
            results.append({
                "file": f.name,
                "path": str(f),
                "ext": f.suffix.lower(),
                "size_kb": f.stat().st_size / 1024,
                "hash": addr.coord_hash,
                "magnitude": addr.magnitude,
                "state": addr.state,
                "dominant": ", ".join(addr.dominant),
                **{v: addr.vector[i] for i, v in enumerate(VAR_NAMES)},
            })
        except Exception as e:
            results.append({
                "file": f.name,
                "path": str(f),
                "ext": f.suffix.lower(),
                "size_kb": 0,
                "hash": "ERR",
                "magnitude": 0,
                "state": "X",
                "dominant": "E",
                **{v: 0.0 for v in VAR_NAMES},
            })

    progress.empty()
    return pd.DataFrame(results)


# --- Sidebar ---
with st.sidebar:
    st.header("Scan Settings")
    folder = st.text_input(
        "Folder to scan",
        value=r"B:\transfer\Desktop STAY",
        help="Full path to folder"
    )
    max_files = st.slider("Max files", 50, 2000, 500)
    scan_btn = st.button("🔍 Scan", type="primary", use_container_width=True)

    st.divider()
    st.header("Tier Level")
    tier = st.radio(
        "Trust Level",
        ["👁️ Tier 1 — View Only", "✏️ Tier 2 — Suggest", "⚡ Tier 3 — Auto"],
        index=0,
        help="Tier 1: No file changes. Tier 2: Propose renames. Tier 3: Auto-rename."
    )
    if "Tier 2" in tier or "Tier 3" in tier:
        st.warning("Tiers 2-3 coming soon. Dashboard is read-only.")

    st.divider()
    st.caption("10 Variables: G M E S T K R Q F C")
    st.caption("G=Authority M=Mechanism E=Entropy")
    st.caption("S=Identity T=Time K=Knowledge")
    st.caption("R=Relation Q=Experience F=Faith C=Coherence")

# --- Main Area ---
if scan_btn or "df" in st.session_state:
    if scan_btn:
        df = scan_folder(folder, max_files)
        st.session_state.df = df
    else:
        df = st.session_state.df

    if df.empty:
        st.error(f"No files found in {folder}")
        st.stop()

    # --- Summary Row ---
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Files", len(df))
    col2.metric("Unique Hashes", df["hash"].nunique())
    col3.metric("E-Dominant (noise)", len(df[df["E"] >= 2.0]))
    col4.metric("K-Dominant (knowledge)", len(df[df["K"] >= 2.0]))
    col5.metric("M-Dominant (mechanism)", len(df[df["M"] >= 2.0]))

    # --- Tabs ---
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Vector Space", "📋 File Table", "🎯 Clusters",
        "🔴 Entropy Report", "🏷️ Hash Distribution"
    ])

    # --- Tab 1: Vector Space Visualization ---
    with tab1:
        st.subheader("10-Variable Heatmap")
        # Heatmap of all files x variables
        heat_data = df[VAR_NAMES].copy()
        heat_data.index = df["file"].str[:35]

        fig_heat = px.imshow(
            heat_data.values,
            x=VAR_NAMES,
            y=heat_data.index.tolist(),
            color_continuous_scale="YlOrRd",
            aspect="auto",
            title="File × Variable Scores"
        )
        fig_heat.update_layout(height=max(400, len(df) * 18))
        st.plotly_chart(fig_heat, use_container_width=True)

        # Radar chart for selected file
        st.subheader("File Detail — Radar")
        selected = st.selectbox("Select file", df["file"].tolist())
        if selected:
            row = df[df["file"] == selected].iloc[0]
            fig_radar = go.Figure(data=go.Scatterpolar(
                r=[row[v] for v in VAR_NAMES],
                theta=VAR_NAMES,
                fill="toself",
                name=selected[:30]
            ))
            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 3])),
                title=f"{selected} — Hash: {row['hash']}"
            )
            col_r1, col_r2 = st.columns([2, 1])
            with col_r1:
                st.plotly_chart(fig_radar, use_container_width=True)
            with col_r2:
                st.markdown(f"**Hash:** `{row['hash']}`")
                st.markdown(f"**Dominant:** {row['dominant']}")
                st.markdown(f"**Magnitude:** {row['magnitude']}")
                st.markdown(f"**State:** {row['state']}")
                st.markdown(f"**Extension:** {row['ext']}")
                st.markdown(f"**Size:** {row['size_kb']:.1f} KB")
                st.markdown("**Scores:**")
                for v in VAR_NAMES:
                    bar = "█" * int(row[v] * 3)
                    st.text(f"  {v}: {row[v]:.1f} {bar}")

    # --- Tab 2: File Table ---
    with tab2:
        st.subheader("All Scored Files")

        # Filter controls
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            filter_hash = st.text_input("Filter by hash prefix", "")
        with fc2:
            filter_ext = st.multiselect(
                "Filter by extension",
                options=sorted(df["ext"].unique()),
                default=[]
            )
        with fc3:
            filter_state = st.multiselect(
                "Filter by state",
                options=["D", "W", "F", "X"],
                default=[]
            )

        display_df = df.copy()
        if filter_hash:
            display_df = display_df[display_df["hash"].str.startswith(filter_hash.upper())]
        if filter_ext:
            display_df = display_df[display_df["ext"].isin(filter_ext)]
        if filter_state:
            display_df = display_df[display_df["state"].isin(filter_state)]

        # Show table
        show_cols = ["file", "hash", "dominant", "magnitude", "state",
                     "ext", "size_kb"] + VAR_NAMES
        st.dataframe(
            display_df[show_cols].round(1),
            use_container_width=True,
            height=600
        )
        st.caption(f"Showing {len(display_df)} of {len(df)} files")

    # --- Tab 3: Clusters ---
    with tab3:
        st.subheader("Vector Space Clusters")
        st.caption("Files plotted by their top two variable scores")

        # Pick two axes to visualize
        ac1, ac2 = st.columns(2)
        with ac1:
            x_var = st.selectbox("X axis", VAR_NAMES, index=VAR_NAMES.index("K"))
        with ac2:
            y_var = st.selectbox("Y axis", VAR_NAMES, index=VAR_NAMES.index("M"))

        fig_scatter = px.scatter(
            df,
            x=x_var,
            y=y_var,
            color="dominant",
            hover_name="file",
            hover_data=["hash", "magnitude", "state", "ext"],
            size="size_kb",
            size_max=20,
            title=f"Files in {x_var} × {y_var} space",
            opacity=0.7,
        )
        fig_scatter.update_layout(height=600)
        st.plotly_chart(fig_scatter, use_container_width=True)

        # 3D view
        if st.checkbox("Show 3D view"):
            z_var = st.selectbox("Z axis", VAR_NAMES, index=VAR_NAMES.index("C"))
            fig_3d = px.scatter_3d(
                df,
                x=x_var, y=y_var, z=z_var,
                color="dominant",
                hover_name="file",
                hover_data=["hash"],
                title=f"3D: {x_var} × {y_var} × {z_var}",
                opacity=0.7,
            )
            fig_3d.update_layout(height=700)
            st.plotly_chart(fig_3d, use_container_width=True)

    # --- Tab 4: Entropy Report ---
    with tab4:
        st.subheader("🔴 Entropy Report — Files That Need Attention")
        st.caption("High E-score = noise, fragments, unresolved files")

        entropy_df = df[df["E"] >= 1.5].sort_values("E", ascending=False)

        if len(entropy_df) == 0:
            st.success("No high-entropy files detected!")
        else:
            st.warning(f"{len(entropy_df)} files with E ≥ 1.5")

            for _, row in entropy_df.iterrows():
                with st.expander(f"E={row['E']:.1f} | {row['file'][:60]}"):
                    st.text(f"Hash: {row['hash']}")
                    st.text(f"Path: {row['path']}")
                    st.text(f"Size: {row['size_kb']:.1f} KB")
                    st.text(f"Dominant: {row['dominant']}")

                    # Suggest action
                    if row["E"] >= 2.5 and row["size_kb"] < 1:
                        st.error("Candidate for deletion — near-empty, high noise")
                    elif row["E"] >= 2.0:
                        st.warning("Review needed — ambiguous or fragmented")
                    else:
                        st.info("Minor entropy — check naming or content")

    # --- Tab 5: Hash Distribution ---
    with tab5:
        st.subheader("Hash Distribution")

        # Count files per hash prefix (first 2-3 chars)
        df["hash_prefix"] = df["hash"].str[:2]
        hash_counts = df["hash_prefix"].value_counts().reset_index()
        hash_counts.columns = ["prefix", "count"]

        fig_bar = px.bar(
            hash_counts.head(20),
            x="prefix", y="count",
            title="Top 20 Hash Prefixes (regions of meaning-space)",
            color="count",
            color_continuous_scale="Viridis"
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        # Variable dominance pie
        all_dominant = []
        for d in df["dominant"]:
            all_dominant.extend([v.strip() for v in d.split(",")])
        dom_counts = Counter(all_dominant)
        dom_df = pd.DataFrame(dom_counts.items(), columns=["variable", "count"])

        fig_pie = px.pie(
            dom_df,
            names="variable",
            values="count",
            title="Variable Dominance Across All Files",
            hole=0.3
        )
        st.plotly_chart(fig_pie, use_container_width=True)

        # State distribution
        state_map = {"D": "Draft", "W": "Working", "F": "Final", "X": "Fragment"}
        df["state_label"] = df["state"].map(state_map)
        fig_state = px.pie(
            df,
            names="state_label",
            title="Document State Distribution",
            hole=0.3
        )
        st.plotly_chart(fig_state, use_container_width=True)

else:
    st.info("👈 Enter a folder path and click **Scan** to begin.")
    st.markdown("""
    ### What this does

    The Semantic Address Dashboard scans your files and assigns each one a position
    in a 10-dimensional knowledge space. No files are renamed or moved.

    **The 10 Variables:**
    - **G** Authority — **M** Mechanism — **E** Entropy
    - **S** Identity — **T** Time — **K** Knowledge
    - **R** Relation — **Q** Experience — **F** Faith — **C** Coherence

    **The Hash** is your file's semantic address — a compressed coordinate
    that tells you WHERE it lives in meaning-space.

    Click Scan to see your files in a new way.
    """)
