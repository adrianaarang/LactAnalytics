"""
charts.py
=========
Funciones de visualización Plotly para el dashboard LactAnalytics.
Cada función recibe un DataFrame (o dict de KPIs) y devuelve un go.Figure.
No contiene lógica de negocio — solo presentación visual.
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from src.stats import (
    kpis_nacionales, tasa_lme_por_grupo, tasa_lm_24m_por_grupo,
    stats_por_grupo, matriz_correlacion, kde_duracion_lactancia,
    kde_por_grupo, get_df
)
from src.config import COLORES, CCAA_GEOJSON_URL


# ---------------------------------------------------------------------------
# Paleta y estilos comunes
# ---------------------------------------------------------------------------

LAYOUT_BASE = dict(
    font_family="Arial, sans-serif",
    plot_bgcolor="white",
    paper_bgcolor="white",
    margin=dict(t=60, b=40, l=40, r=40),
    hoverlabel=dict(bgcolor="white", font_size=13),
)


def _aplicar_layout(fig, titulo: str, fuente: bool = True) -> go.Figure:
    """Aplica estilos comunes y título a cualquier figura."""
    anotaciones = []
    if fuente:
        anotaciones.append(dict(
            text="Fuente: ENSE 2017 · Ministerio de Sanidad / INE",
            xref="paper", yref="paper", x=0, y=-0.12,
            showarrow=False, font=dict(size=10, color="#888888")
        ))
    fig.update_layout(
        title=dict(text=titulo, font=dict(size=16, color="#1A1A2E"), x=0.02),
        annotations=anotaciones,
        **LAYOUT_BASE
    )
    return fig


# ---------------------------------------------------------------------------
# 1. KPIs — tarjetas tipo gauge
# ---------------------------------------------------------------------------

def chart_kpis_gauge(kpis: dict) -> go.Figure:
    """
    Tres indicadores circulares: % LM, % LME 6m, % LM 24m.
    Línea roja marca el objetivo OMS (100% para LM, metas propias para resto).
    """
    fig = make_subplots(
        rows=1, cols=3,
        specs=[[{"type": "indicator"}, {"type": "indicator"}, {"type": "indicator"}]],
        subplot_titles=[
            "Lactancia materna<br><sup>% menores que la recibieron</sup>",
            "LME ≥ 6 meses<br><sup>Objetivo OMS: 100%</sup>",
            "LM ≥ 24 meses<br><sup>Objetivo OMS: 100%</sup>",
        ]
    )

    datos = [
        (kpis["pct_lactancia_materna"], 100, COLORES["verde"]),
        (kpis["pct_lme_6meses"], 100, COLORES["naranja"]),
        (kpis["pct_lm_24meses"], 100, COLORES["rojo"]),
    ]

    for i, (valor, maximo, color) in enumerate(datos, start=1):
        fig.add_trace(go.Indicator(
            mode="gauge+number+delta",
            value=valor,
            number={"suffix": "%", "font": {"size": 28}},
            delta={"reference": maximo, "valueformat": ".1f",
                   "suffix": "% vs OMS", "font": {"size": 12}},
            gauge={
                "axis": {"range": [0, 100], "ticksuffix": "%"},
                "bar": {"color": color},
                "bgcolor": "#F0F4F8",
                "threshold": {
                    "line": {"color": "#E63946", "width": 3},
                    "thickness": 0.75,
                    "value": maximo
                },
                "steps": [
                    {"range": [0, 33], "color": "#FFE5E5"},
                    {"range": [33, 66], "color": "#FFF3CD"},
                    {"range": [66, 100], "color": "#E8F5E9"},
                ]
            }
        ), row=1, col=i)

    fig.update_layout(height=280, **LAYOUT_BASE,
                      title=dict(text="España vs. recomendaciones OMS",
                                 font=dict(size=16, color="#1A1A2E"), x=0.02))
    return fig


# ---------------------------------------------------------------------------
# 2. Mapa coroplético por CCAA
# ---------------------------------------------------------------------------

def chart_mapa_ccaa(df: pd.DataFrame) -> go.Figure:
    """
    Mapa de España coloreado por % de LME ≥ 6 meses por CCAA.
    """
    import urllib.request, json

    tasa = tasa_lme_por_grupo(df, "ccaa")

    # GeoJSON de CCAA (IGN simplificado)
    url = CCAA_GEOJSON_URL
    with urllib.request.urlopen(url) as r:
        geojson = json.load(r)

    # El GeoJSON usa el nombre de la CCAA como feature id
    fig = px.choropleth(
        tasa,
        geojson=geojson,
        locations="ccaa",
        featureidkey="properties.name",
        color="pct_lme_6meses",
        color_continuous_scale=[
            [0, "#FFE5E5"], [0.5, "#FFB347"], [1, "#1D9E75"]
        ],
        range_color=(0, 50),
        labels={"pct_lme_6meses": "% LME ≥ 6 meses", "ccaa": "Comunidad Autónoma"},
        hover_data={"n": True, "pct_lme_6meses": ":.1f"},
    )

    fig.update_geos(
        fitbounds="locations",
        visible=False,
        bgcolor="white"
    )
    fig.update_layout(
        height=480,
        coloraxis_colorbar=dict(
            title="% LME<br>≥ 6 meses",
            ticksuffix="%"
        ),
        **LAYOUT_BASE
    )
    return _aplicar_layout(fig, "Lactancia materna exclusiva ≥ 6 meses por Comunidad Autónoma")


# ---------------------------------------------------------------------------
# 3. Barras horizontales por nivel educativo
# ---------------------------------------------------------------------------

def chart_barras_educacion(df: pd.DataFrame) -> go.Figure:
    """
    % LME ≥ 6 meses por nivel educativo agrupado.
    Incluye línea de referencia con la media nacional.
    """
    orden = ["Básico o menos", "Secundaria", "FP", "Universidad"]
    tasa = tasa_lme_por_grupo(df, "nivel_educativo_grupo")
    tasa = tasa[tasa["nivel_educativo_grupo"].isin(orden)].copy()
    tasa["nivel_educativo_grupo"] = pd.Categorical(
        tasa["nivel_educativo_grupo"], categories=orden, ordered=True
    )
    tasa = tasa.sort_values("nivel_educativo_grupo")

    media_nacional = tasa["pct_lme_6meses"].mean()

    colores_barras = [COLORES["rojo"], COLORES["naranja"],
                      COLORES["azul"], COLORES["verde"]]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=tasa["pct_lme_6meses"],
        y=tasa["nivel_educativo_grupo"],
        orientation="h",
        marker_color=colores_barras,
        text=tasa["pct_lme_6meses"].apply(lambda x: f"{x:.1f}%"),
        textposition="outside",
        customdata=tasa["n"],
        hovertemplate="<b>%{y}</b><br>LME ≥ 6m: %{x:.1f}%<br>n = %{customdata}<extra></extra>",
    ))

    fig.add_vline(
        x=media_nacional, line_dash="dash",
        line_color="#888888", line_width=1.5,
        annotation_text=f"Media: {media_nacional:.1f}%",
        annotation_position="top right"
    )

    fig.update_layout(
        height=340,
        xaxis=dict(title="% con LME ≥ 6 meses", ticksuffix="%", range=[0, 45]),
        yaxis=dict(title=""),
        showlegend=False,
        **LAYOUT_BASE
    )
    return _aplicar_layout(fig, "Lactancia exclusiva ≥ 6 meses según nivel educativo")


# ---------------------------------------------------------------------------
# 4. Box plot por clase social
# ---------------------------------------------------------------------------

def chart_boxplot_clase_social(df: pd.DataFrame) -> go.Figure:
    """
    Distribución de meses de lactancia total por clase social.
    Muestra la desigualdad socioeconómica en la duración.
    """
    sub = df[df["clase_social"].notna() & df["meses_lactancia_total"].notna()].copy()
    sub["clase_social"] = sub["clase_social"].astype(int)

    etiquetas = {
        1: "I · Alta", 2: "II · Media-alta",
        3: "III · Media", 4: "IV · Media-baja",
        5: "V · Baja", 6: "VI · Agraria"
    }
    sub["clase_label"] = sub["clase_social"].map(etiquetas)

    orden = [etiquetas[i] for i in range(1, 7) if i in sub["clase_social"].unique()]

    fig = px.box(
        sub,
        x="clase_label",
        y="meses_lactancia_total",
        category_orders={"clase_label": orden},
        color="clase_label",
        color_discrete_sequence=px.colors.sequential.Teal,
        labels={
            "clase_label": "Clase social",
            "meses_lactancia_total": "Meses de lactancia materna"
        },
        points="outliers",
    )

    fig.add_hline(
        y=6, line_dash="dot", line_color="#E63946",
        annotation_text="Mínimo OMS: 6 meses",
        annotation_position="top left"
    )

    fig.update_layout(
        height=420,
        showlegend=False,
        xaxis_title="Clase social",
        yaxis_title="Meses de lactancia materna",
        **LAYOUT_BASE
    )
    return _aplicar_layout(fig, "Duración de la lactancia materna por clase social")


# ---------------------------------------------------------------------------
# 5. Curva de abandono mes a mes
# ---------------------------------------------------------------------------

def chart_curva_abandono(df: pd.DataFrame) -> go.Figure:
    """
    Curva de supervivencia simplificada: % de menores que siguen
    con lactancia materna a cada mes de vida.
    """
    sub = df[df["meses_lactancia_total"].notna() & df["lactancia_materna"] == True].copy()
    total = len(sub)

    meses = list(range(0, 25))
    pct_activos = []
    for m in meses:
        activos = (sub["meses_lactancia_total"] >= m).sum()
        pct_activos.append(round(activos / total * 100, 1))

    fig = go.Figure()

    # Zona de relleno bajo la curva
    fig.add_trace(go.Scatter(
        x=meses, y=pct_activos,
        fill="tozeroy",
        fillcolor="rgba(29, 158, 117, 0.15)",
        line=dict(color=COLORES["verde"], width=2.5),
        mode="lines",
        name="% con lactancia activa",
        hovertemplate="Mes %{x}: %{y:.1f}% siguen con LM<extra></extra>",
    ))

    # Línea vertical mes 6 (OMS LME)
    fig.add_vline(x=6, line_dash="dash", line_color=COLORES["naranja"],
                  annotation_text="6m · fin LME recomendada",
                  annotation_position="top right")

    # Línea vertical mes 24 (OMS LM)
    fig.add_vline(x=24, line_dash="dash", line_color=COLORES["rojo"],
                  annotation_text="24m · OMS",
                  annotation_position="top left")

    fig.update_layout(
        height=380,
        xaxis=dict(title="Mes de vida del bebé", tickmode="linear", dtick=2),
        yaxis=dict(title="% con lactancia activa", ticksuffix="%", range=[0, 105]),
        **LAYOUT_BASE
    )
    return _aplicar_layout(fig, "Curva de abandono de la lactancia materna (mes a mes)")


# ---------------------------------------------------------------------------
# 6. KDE — curva de densidad de duración
# ---------------------------------------------------------------------------

def chart_kde_duracion(df: pd.DataFrame,
                        grupo: str = None,
                        variable: str = "meses_lactancia_total") -> go.Figure:
    """
    Curva KDE de la distribución de duración de lactancia.
    Si se pasa `grupo`, dibuja una curva por cada categoría.
    """
    from src.stats import kde_duracion_lactancia, kde_por_grupo

    titulo_var = "Meses de lactancia materna total" if "total" in variable else "Meses de LME"

    fig = go.Figure()

    if grupo is None:
        kde = kde_duracion_lactancia(df, variable)
        fig.add_trace(go.Scatter(
            x=kde["x"], y=kde["y"],
            fill="tozeroy",
            fillcolor="rgba(29, 158, 117, 0.2)",
            line=dict(color=COLORES["verde"], width=2),
            name="Distribución",
            hovertemplate="%{x:.1f} meses<extra></extra>",
        ))
    else:
        kde_df = kde_por_grupo(df, grupo, variable)
        for nombre, sub in kde_df.groupby(grupo):
            fig.add_trace(go.Scatter(
                x=sub["x"], y=sub["y"],
                mode="lines", name=str(nombre),
                hovertemplate=f"{nombre}: %{{x:.1f}} meses<extra></extra>",
            ))

    fig.add_vline(x=6, line_dash="dot", line_color=COLORES["naranja"],
                  annotation_text="6m OMS", annotation_position="top right")

    fig.update_layout(
        height=360,
        xaxis=dict(title=titulo_var),
        yaxis=dict(title="Densidad", showticklabels=False),
        **LAYOUT_BASE
    )
    return _aplicar_layout(fig, f"Distribución de la duración · {titulo_var}")


# ---------------------------------------------------------------------------
# 7. Heatmap de correlación
# ---------------------------------------------------------------------------

def chart_heatmap_correlacion(df: pd.DataFrame) -> go.Figure:
    """
    Heatmap de la matriz de correlación de Spearman.
    """
    corr = matriz_correlacion(df)

    fig = go.Figure(go.Heatmap(
        z=corr.values,
        x=corr.columns.tolist(),
        y=corr.index.tolist(),
        colorscale=[
            [0, "#E63946"], [0.5, "#FFFFFF"], [1, "#1D9E75"]
        ],
        zmid=0,
        zmin=-1, zmax=1,
        text=corr.round(2).values,
        texttemplate="%{text}",
        textfont=dict(size=11),
        hovertemplate="<b>%{y}</b> × <b>%{x}</b><br>Correlación: %{z:.3f}<extra></extra>",
        colorbar=dict(title="Spearman", tickvals=[-1, -0.5, 0, 0.5, 1])
    ))

    fig.update_layout(
        height=420,
        xaxis=dict(tickangle=-30),
        **LAYOUT_BASE
    )
    return _aplicar_layout(fig, "Correlaciones entre variables (Spearman)")


# ---------------------------------------------------------------------------
# 8. Ranking CCAA — barras verticales
# ---------------------------------------------------------------------------

def chart_ranking_ccaa(df: pd.DataFrame) -> go.Figure:
    """
    Ranking de todas las CCAA por % LME ≥ 6 meses.
    """
    tasa = tasa_lme_por_grupo(df, "ccaa").sort_values("pct_lme_6meses", ascending=True)
    media = tasa["pct_lme_6meses"].mean()

    colores = [
        COLORES["verde"] if v >= media else COLORES["naranja"]
        for v in tasa["pct_lme_6meses"]
    ]

    fig = go.Figure(go.Bar(
        x=tasa["pct_lme_6meses"],
        y=tasa["ccaa"],
        orientation="h",
        marker_color=colores,
        text=tasa["pct_lme_6meses"].apply(lambda x: f"{x:.1f}%"),
        textposition="outside",
        customdata=tasa["n"],
        hovertemplate="<b>%{y}</b><br>LME ≥ 6m: %{x:.1f}%<br>n = %{customdata}<extra></extra>",
    ))

    fig.add_vline(
        x=media, line_dash="dash", line_color="#888888",
        annotation_text=f"Media nacional: {media:.1f}%",
        annotation_position="top right"
    )

    fig.update_layout(
        height=580,
        xaxis=dict(title="% con LME ≥ 6 meses", ticksuffix="%", range=[0, 55]),
        yaxis=dict(title=""),
        showlegend=False,
        **LAYOUT_BASE
    )
    return _aplicar_layout(fig, "Ranking de Comunidades Autónomas · LME ≥ 6 meses")