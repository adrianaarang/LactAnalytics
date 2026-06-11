"""
mapa_ccaa.py
============
Cuarta sección del dashboard LactAnalytics.
Visualización geográfica de la lactancia materna por CCAA.
Incluye mapa coroplético, ranking y análisis territorial.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import json
import urllib.request
from src.config import COLORES, CCAA_GEOJSON_URL


# ---------------------------------------------------------------------------
# Mapa de equivalencias: nombres del dataset → nombres del GeoJSON
# El GeoJSON no tiene tildes en algunos nombres, hay que normalizarlos.
# ---------------------------------------------------------------------------
CCAA_NORM = {
    "Andalucía":          "Andalucia",
    "Aragón":             "Aragon",
    "Asturias":           "Asturias",
    "Baleares":           "Baleares",
    "Canarias":           "Canarias",
    "Cantabria":          "Cantabria",
    "Castilla-La Mancha": "Castilla-La Mancha",
    "Castilla y León":    "Castilla-Leon",
    "Cataluña":           "Cataluña",
    "C. Valenciana":      "Valencia",
    "Extremadura":        "Extremadura",
    "Galicia":            "Galicia",
    "Madrid":             "Madrid",
    "Murcia":             "Murcia",
    "Navarra":            "Navarra",
    "País Vasco":         "Pais Vasco",
    "La Rioja":           "La Rioja",
    "Ceuta":              "Ceuta",
    "Melilla":            "Melilla",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _titulo_seccion(titulo: str, subtitulo: str = ""):
    st.html(f"""
    <div style="margin-bottom:1rem;">
        <div style="font-family:'DM Serif Display',serif;font-size:1.4rem;
                    color:#1A2E35;line-height:1.2;">{titulo}</div>
        <div style="font-size:0.78rem;color:#648A96;margin-top:0.2rem;">
            {subtitulo}
        </div>
    </div>
    """)


@st.cache_data
def _cargar_geojson() -> dict:
    """Carga el GeoJSON de CCAA españolas. Cacheado para evitar requests repetidas."""
    with urllib.request.urlopen(CCAA_GEOJSON_URL) as r:
        return json.load(r)


# ---------------------------------------------------------------------------
# Gráfico 1 — Mapa coroplético LME ≥ 6 meses
# ---------------------------------------------------------------------------

def _chart_mapa_lme(df: pd.DataFrame, geojson: dict) -> go.Figure:
    """
    Mapa de España coloreado por % de LME ≥ 6 meses por CCAA.
    Los nombres se normalizan para que coincidan con el GeoJSON.
    """
    sub = df[df["lme_6meses"].notna()]
    tasa = (
        sub.groupby("ccaa")["lme_6meses"]
        .agg(n="count", n_lme6=lambda x: x.sum())
        .reset_index()
    )
    tasa["pct"] = (tasa["n_lme6"] / tasa["n"] * 100).round(1)

    # Normalizar nombres para el GeoJSON
    tasa["ccaa_geo"] = tasa["ccaa"].map(CCAA_NORM).fillna(tasa["ccaa"])

    fig = px.choropleth(
        tasa,
        geojson=geojson,
        locations="ccaa_geo",
        featureidkey="properties.name",
        color="pct",
        color_continuous_scale=[
            [0.0, "#F6F0E6"],
            [0.3, "#E8B8B8"],
            [0.6, "#648A96"],
            [1.0, "#1A2E35"],
        ],
        range_color=(0, 45),
        labels={"pct": "% LME ≥ 6m", "ccaa_geo": "CCAA"},
        custom_data=["ccaa", "pct", "n"]
    )

    fig.update_traces(
        hovertemplate="<b>%{customdata[0]}</b><br>"
                      "LME ≥ 6 meses: %{customdata[1]:.1f}%<br>"
                      "n = %{customdata[2]}<extra></extra>"
    )

    fig.update_geos(
        fitbounds="locations",
        visible=False,
        bgcolor="white"
    )

    fig.update_layout(
        height=650,
        margin=dict(t=0, b=0, l=0, r=0),
        paper_bgcolor="white",
        coloraxis_colorbar=dict(
            title="% LME<br>≥ 6 meses",
            ticksuffix="%",
            len=0.6,
            thickness=12,
        ),
        hoverlabel=dict(bgcolor="white", font_size=13),
    )
    return fig


# ---------------------------------------------------------------------------
# Gráfico 2 — Ranking CCAA
# ---------------------------------------------------------------------------

def _chart_ranking(df: pd.DataFrame) -> go.Figure:
    """
    Ranking horizontal de todas las CCAA por % LME ≥ 6 meses.
    Azul = por encima de la media. Rosa = por debajo.
    """
    sub = df[df["lme_6meses"].notna()]
    tasa = (
        sub.groupby("ccaa")["lme_6meses"]
        .agg(n="count", n_lme6=lambda x: x.sum())
        .reset_index()
    )
    tasa["pct"] = (tasa["n_lme6"] / tasa["n"] * 100).round(1)
    tasa = tasa.sort_values("pct", ascending=True)
    media = tasa["pct"].mean()

    colores = [
        "#648A96" if v >= media else "#E8B8B8"
        for v in tasa["pct"]
    ]

    fig = go.Figure(go.Bar(
        x=tasa["pct"],
        y=tasa["ccaa"],
        orientation="h",
        marker_color=colores,
        text=tasa["pct"].apply(lambda x: f"{x:.1f}%"),
        textposition="outside",
        customdata=tasa["n"],
        hovertemplate="<b>%{y}</b><br>LME ≥ 6m: %{x:.1f}%<br>n = %{customdata}<extra></extra>",
    ))

    fig.add_vline(
        x=media,
        line_dash="dash",
        line_color="#1A2E35",
        line_width=1.5,
        annotation_text=f"Media: {media:.1f}%",
        annotation_position="top right",
        annotation_font=dict(size=11, color="#1A2E35")
    )

    fig.update_layout(
        height=580,
        plot_bgcolor="white",
        paper_bgcolor="white",
        font_family="Inter, sans-serif",
        margin=dict(t=20, b=40, l=10, r=60),
        xaxis=dict(
            title="% con LME ≥ 6 meses",
            ticksuffix="%",
            range=[0, 52],
            gridcolor="#F0F0F0"
        ),
        yaxis=dict(title=""),
        showlegend=False,
        hoverlabel=dict(bgcolor="white", font_size=13),
    )
    return fig


# ---------------------------------------------------------------------------
# Gráfico 3 — Mapa LM ≥ 24 meses
# ---------------------------------------------------------------------------

def _chart_mapa_lm24(df: pd.DataFrame, geojson: dict) -> go.Figure:
    """
    Mapa de España coloreado por % de LM ≥ 24 meses por CCAA.
    """
    sub = df[df["lm_24meses"].notna()]
    tasa = (
        sub.groupby("ccaa")["lm_24meses"]
        .agg(n="count", n_lm24=lambda x: x.sum())
        .reset_index()
    )
    tasa["pct"] = (tasa["n_lm24"] / tasa["n"] * 100).round(1)

    # Normalizar nombres para el GeoJSON
    tasa["ccaa_geo"] = tasa["ccaa"].map(CCAA_NORM).fillna(tasa["ccaa"])

    fig = px.choropleth(
        tasa,
        geojson=geojson,
        locations="ccaa_geo",
        featureidkey="properties.name",
        color="pct",
        color_continuous_scale=[
            [0.0, "#F6F0E6"],
            [0.5, "#E8B8B8"],
            [1.0, "#1A2E35"],
        ],
        range_color=(0, 20),
        labels={"pct": "% LM ≥ 24m", "ccaa_geo": "CCAA"},
        custom_data=["ccaa", "pct", "n"]
    )

    fig.update_traces(
        hovertemplate="<b>%{customdata[0]}</b><br>"
                      "LM ≥ 24 meses: %{customdata[1]:.1f}%<br>"
                      "n = %{customdata[2]}<extra></extra>"
    )

    fig.update_geos(fitbounds="locations", visible=False, bgcolor="white")
    fig.update_layout(
        height=360,
        margin=dict(t=0, b=0, l=0, r=0),
        paper_bgcolor="white",
        coloraxis_colorbar=dict(
            title="% LM<br>≥ 24 meses",
            ticksuffix="%",
            len=0.6,
            thickness=12,
        ),
        hoverlabel=dict(bgcolor="white", font_size=13),
    )
    return fig


# ---------------------------------------------------------------------------
# Tabla resumen por CCAA
# ---------------------------------------------------------------------------

def _tabla_ccaa(df: pd.DataFrame) -> pd.DataFrame:
    """
    Tabla resumen con los principales indicadores por CCAA.
    """
    sub_lme  = df[df["lme_6meses"].notna()]
    sub_lm24 = df[df["lm_24meses"].notna()]
    sub_lm   = df[df["lactancia_materna"].notna()]
    sub_dur  = df[df["meses_lactancia_total"].notna()]

    tasa_lme = (
        sub_lme.groupby("ccaa")["lme_6meses"]
        .agg(n="count", n_lme6=lambda x: x.sum())
        .reset_index()
    )
    tasa_lme["% LME ≥ 6m"] = (tasa_lme["n_lme6"] / tasa_lme["n"] * 100).round(1)

    tasa_lm24 = (
        sub_lm24.groupby("ccaa")["lm_24meses"]
        .agg(n24="count", n_lm24=lambda x: x.sum())
        .reset_index()
    )
    tasa_lm24["% LM ≥ 24m"] = (tasa_lm24["n_lm24"] / tasa_lm24["n24"] * 100).round(1)

    tasa_lm = (
        sub_lm.groupby("ccaa")["lactancia_materna"]
        .agg(nlm="count", n_lm=lambda x: x.sum())
        .reset_index()
    )
    tasa_lm["% inicio LM"] = (tasa_lm["n_lm"] / tasa_lm["nlm"] * 100).round(1)

    media_dur = (
        sub_dur.groupby("ccaa")["meses_lactancia_total"]
        .mean().round(1).reset_index()
        .rename(columns={"meses_lactancia_total": "Media meses LM"})
    )

    tabla = (
        tasa_lme[["ccaa", "n", "% LME ≥ 6m"]]
        .merge(tasa_lm24[["ccaa", "% LM ≥ 24m"]], on="ccaa", how="left")
        .merge(tasa_lm[["ccaa", "% inicio LM"]], on="ccaa", how="left")
        .merge(media_dur, on="ccaa", how="left")
        .rename(columns={"ccaa": "CCAA", "n": "n menores"})
        .sort_values("% LME ≥ 6m", ascending=False)
    )

    return tabla


# ---------------------------------------------------------------------------
# RENDER PRINCIPAL
# ---------------------------------------------------------------------------

def render(df: pd.DataFrame):

    # Cargar GeoJSON
    try:
        geojson = _cargar_geojson()
        geojson_ok = True
    except Exception:
        geojson_ok = False
        st.warning(
            "No se pudo cargar el mapa geográfico. "
            "Comprueba tu conexión a internet."
        )

    # Narrativa de apertura
    st.html("""
    <div style="background:linear-gradient(135deg,#F6F0E6,#E8D8C8);
                border-radius:14px;padding:1.2rem 1.8rem;margin-bottom:1.5rem;
                border-left:4px solid #1A2E35;">
        <div style="font-family:'DM Serif Display',serif;font-size:1.2rem;
                    color:#1A2E35;line-height:1.4;">
            La lactancia materna no es igual en toda España.
            Las diferencias entre CCAA superan los 20 puntos porcentuales.
        </div>
        <div style="font-size:0.8rem;color:#648A96;margin-top:0.4rem;">
            Castilla y León y Madrid lideran. Las causas son múltiples:
            políticas autonómicas, cultura local y acceso a asesoras IBCLC.
        </div>
    </div>
    """)

    # --- Fila 1: Mapa + Ranking ---
    col1, col2 = st.columns([4, 2])

    with col1:
        _titulo_seccion(
            "Lactancia exclusiva ≥ 6 meses por CCAA",
            "% de menores que alcanzaron el objetivo OMS · ENSE 2017"
        )
        if geojson_ok:
            st.plotly_chart(
                _chart_mapa_lme(df, geojson),
                use_container_width=True
            )
        else:
            st.info("Mapa no disponible sin conexión.")

    with col2:
        _titulo_seccion(
            "Ranking autonómico",
            "Azul = por encima de la media · Rosa = por debajo"
        )
        st.plotly_chart(_chart_ranking(df), use_container_width=True)

    st.markdown("---")

    # --- Fila 2: Mapa LM 24m + tabla ---
    col3, col4 = st.columns([2, 3])

    with col3:
        _titulo_seccion(
            "Lactancia materna ≥ 24 meses",
            "% por CCAA · objetivo OMS lactancia complementaria"
        )
        if geojson_ok:
            st.plotly_chart(
                _chart_mapa_lm24(df, geojson),
                use_container_width=True
            )

    with col4:
        _titulo_seccion(
            "Tabla resumen por CCAA",
            "Principales indicadores · ordenado por % LME ≥ 6 meses"
        )
        tabla = _tabla_ccaa(df)
        st.dataframe(
            tabla,
            use_container_width=True,
            hide_index=True,
            column_config={
                "% LME ≥ 6m": st.column_config.ProgressColumn(
                    "% LME ≥ 6m",
                    format="%.1f%%",
                    min_value=0,
                    max_value=50,
                ),
                "% LM ≥ 24m": st.column_config.ProgressColumn(
                    "% LM ≥ 24m",
                    format="%.1f%%",
                    min_value=0,
                    max_value=20,
                ),
                "% inicio LM": st.column_config.ProgressColumn(
                    "% inicio LM",
                    format="%.1f%%",
                    min_value=0,
                    max_value=100,
                ),
            }
        )

    # Nota interpretativa
    st.html("""
    <div style="background:#F0F4F8;border-radius:8px;
                padding:0.8rem 1.2rem;margin-top:1rem;">
        <div style="font-size:0.72rem;color:#648A96;line-height:1.6;">
            <strong>Nota:</strong>
            Las diferencias entre CCAA deben interpretarse con cautela.
            El tamaño muestral por comunidad es pequeño en algunas regiones
            (Ceuta, Melilla, La Rioja con n &lt; 30), lo que genera
            intervalos de confianza amplios. Ver sección
            <em>Sesgos y gobernanza</em> para más detalle.
        </div>
    </div>
    """)