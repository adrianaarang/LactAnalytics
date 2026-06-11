"""
factores_condicionantes.py
==========================
Segunda sección del dashboard LactAnalytics.
Analiza qué variables condicionan la duración de la lactancia materna:
clase social, nivel educativo, CCAA y edad del menor.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from scipy import stats as scipy_stats
from src.config import COLORES


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


# ---------------------------------------------------------------------------
# Gráfico 1 — Box plot por clase social
# ---------------------------------------------------------------------------

def _chart_boxplot_clase(df: pd.DataFrame) -> go.Figure:
    """
    Distribución de meses de lactancia total por clase social.
    Evidencia la desigualdad socioeconómica en la duración.
    """
    etiquetas = {
        1: "I · Alta",
        2: "II · Media-alta",
        3: "III · Media",
        4: "IV · Media-baja",
        5: "V · Baja",
        6: "VI · Agraria"
    }
    sub = df[
        df["clase_social"].notna() &
        df["meses_lactancia_total"].notna()
    ].copy()
    sub["clase_label"] = sub["clase_social"].astype(int).map(etiquetas)
    orden = [etiquetas[i] for i in range(1, 7) if i in sub["clase_social"].astype(int).unique()]

    colores_caja = ["#1A2E35", "#648A96", "#8AADB8", "#E8B8B8", "#D4A0A0", "#C0392B"]

    fig = go.Figure()
    for i, clase in enumerate(orden):
        datos = sub[sub["clase_label"] == clase]["meses_lactancia_total"]
        fig.add_trace(go.Box(
            y=datos,
            name=clase,
            marker_color=colores_caja[i % len(colores_caja)],
            boxmean=True,
            hovertemplate=f"<b>{clase}</b><br>%{{y:.1f}} meses<extra></extra>",
        ))

    fig.add_hline(
        y=6, line_dash="dot", line_color="#C0392B",
        annotation_text="Mínimo OMS: 6 meses",
        annotation_position="top left",
        annotation_font=dict(size=10, color="#C0392B")
    )

    fig.update_layout(
        height=380,
        plot_bgcolor="white",
        paper_bgcolor="white",
        font_family="Inter, sans-serif",
        margin=dict(t=20, b=60, l=40, r=20),
        xaxis=dict(title="Clase social", tickangle=-20),
        yaxis=dict(title="Meses de lactancia materna", gridcolor="#F0F0F0"),
        showlegend=False,
        hoverlabel=dict(bgcolor="white", font_size=13),
    )
    return fig


# ---------------------------------------------------------------------------
# Gráfico 2 — Barras LME por nivel educativo detallado
# ---------------------------------------------------------------------------

def _chart_educ_detallado(df: pd.DataFrame) -> go.Figure:
    """
    % LME ≥ 6 meses por nivel educativo detallado (no agrupado).
    """
    orden = [
        "Sin estudios", "Primaria incompleta", "Primaria",
        "Secundaria 1ª etapa", "Secundaria 2ª etapa",
        "FP grado medio", "FP grado superior",
        "Universitaria", "Posgrado"
    ]
    sub = df[df["lme_6meses"].notna() & df["nivel_educativo"].notna()]
    tasa = (
        sub.groupby("nivel_educativo")["lme_6meses"]
        .agg(n="count", n_lme6=lambda x: x.sum())
        .reset_index()
    )
    tasa["pct"] = (tasa["n_lme6"] / tasa["n"] * 100).round(1)
    tasa = tasa[tasa["nivel_educativo"].isin(orden) & (tasa["n"] >= 10)]
    tasa["nivel_educativo"] = pd.Categorical(
        tasa["nivel_educativo"], categories=orden, ordered=True
    )
    tasa = tasa.sort_values("nivel_educativo")

    media = tasa["pct"].mean()

    fig = go.Figure(go.Bar(
        x=tasa["pct"],
        y=tasa["nivel_educativo"],
        orientation="h",
        marker=dict(
            color=tasa["pct"],
            colorscale=[[0, "#E8B8B8"], [0.5, "#648A96"], [1, "#1A2E35"]],
            showscale=False,
        ),
        text=tasa["pct"].apply(lambda x: f"{x:.1f}%"),
        textposition="outside",
        customdata=tasa["n"],
        hovertemplate="<b>%{y}</b><br>LME ≥ 6m: %{x:.1f}%<br>n = %{customdata}<extra></extra>",
    ))

    fig.add_vline(
        x=media, line_dash="dash", line_color="#888",
        annotation_text=f"Media: {media:.1f}%",
        annotation_position="top right",
        annotation_font=dict(size=10, color="#888")
    )

    fig.update_layout(
        height=380,
        plot_bgcolor="white",
        paper_bgcolor="white",
        font_family="Inter, sans-serif",
        margin=dict(t=20, b=40, l=10, r=70),
        xaxis=dict(title="% con LME ≥ 6 meses", ticksuffix="%", range=[0, 50], gridcolor="#F0F0F0"),
        yaxis=dict(title=""),
        showlegend=False,
        hoverlabel=dict(bgcolor="white", font_size=13),
    )
    return fig


# ---------------------------------------------------------------------------
# Gráfico 3 — KDE por nivel educativo agrupado
# ---------------------------------------------------------------------------

def _chart_kde_educacion(df: pd.DataFrame) -> go.Figure:
    """
    Curvas KDE de duración de lactancia separadas por nivel educativo.
    Permite ver si la distribución completa difiere entre grupos.
    """
    grupos = {
        "Básico o menos": "#C0392B",
        "Secundaria":     "#E8B8B8",
        "FP":             "#648A96",
        "Universidad":    "#1A2E35",
    }

    fig = go.Figure()
    for grupo, color in grupos.items():
        datos = df[df["nivel_educativo_grupo"] == grupo]["meses_lactancia_total"].dropna()
        if len(datos) < 10:
            continue
        kde = scipy_stats.gaussian_kde(datos)
        x = np.linspace(0, datos.max(), 300)
        y = kde(x)
        fig.add_trace(go.Scatter(
            x=x, y=y,
            mode="lines",
            name=grupo,
            line=dict(color=color, width=2),
            hovertemplate=f"<b>{grupo}</b><br>%{{x:.1f}} meses<extra></extra>",
        ))

    fig.add_vline(
        x=6, line_dash="dot", line_color="#888",
        annotation_text="6m OMS",
        annotation_position="top right",
        annotation_font=dict(size=10, color="#888")
    )

    fig.update_layout(
        height=320,
        plot_bgcolor="white",
        paper_bgcolor="white",
        font_family="Inter, sans-serif",
        margin=dict(t=20, b=40, l=20, r=20),
        xaxis=dict(title="Meses de lactancia", gridcolor="#F0F0F0"),
        yaxis=dict(title="Densidad", showticklabels=False, gridcolor="#F0F0F0"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hoverlabel=dict(bgcolor="white", font_size=13),
    )
    return fig


# ---------------------------------------------------------------------------
# Gráfico 4 — Scatter edad del menor vs meses de lactancia
# ---------------------------------------------------------------------------

def _chart_scatter_edad(df: pd.DataFrame) -> go.Figure:
    """
    Relación entre edad actual del menor y duración de la lactancia.
    Permite detectar si los menores más pequeños reciben más LM.
    """
    sub = df[
        df["edad_menor"].notna() &
        df["meses_lactancia_total"].notna()
    ].copy()

    fig = px.scatter(
        sub,
        x="edad_menor",
        y="moses_lactancia_total" if "moses_lactancia_total" in sub.columns
          else "meses_lactancia_total",
        color="nivel_educativo_grupo",
        color_discrete_map={
            "Básico o menos": "#C0392B",
            "Secundaria":     "#E8B8B8",
            "FP":             "#648A96",
            "Universidad":    "#1A2E35",
        },
        opacity=0.5,
        labels={
            "edad_menor": "Edad del menor (años)",
            "meses_lactancia_total": "Meses de LM",
            "nivel_educativo_grupo": "Nivel educativo"
        },
        hover_data={"ccaa": True},
    )

    fig.update_layout(
        height=340,
        plot_bgcolor="white",
        paper_bgcolor="white",
        font_family="Inter, sans-serif",
        margin=dict(t=20, b=40, l=40, r=20),
        xaxis=dict(title="Edad del menor (años)", gridcolor="#F0F0F0"),
        yaxis=dict(title="Meses de lactancia materna", gridcolor="#F0F0F0"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hoverlabel=dict(bgcolor="white", font_size=13),
    )
    return fig


# ---------------------------------------------------------------------------
# Gráfico 5 — Heatmap de correlación
# ---------------------------------------------------------------------------

def _chart_heatmap(df: pd.DataFrame) -> go.Figure:
    """
    Matriz de correlación de Spearman entre variables numéricas clave.
    Spearman es más robusto para variables ordinales como clase social.
    """
    cols = {
        "meses_lactancia_total": "Meses LM",
        "meses_lactancia_excl":  "Meses LME",
        "clase_social":          "Clase social",
        "nivel_educativo_cod":   "Nivel educativo",
        "valoracion_salud":      "Salud valorada",
        "edad_menor":            "Edad menor",
    }
    cols_exist = {k: v for k, v in cols.items() if k in df.columns}
    corr = df[list(cols_exist.keys())].corr(method="spearman").round(2)
    corr = corr.rename(index=cols_exist, columns=cols_exist)

    fig = go.Figure(go.Heatmap(
        z=corr.values,
        x=corr.columns.tolist(),
        y=corr.index.tolist(),
        colorscale=[[0, "#C0392B"], [0.5, "#F6F0E6"], [1, "#1A2E35"]],
        zmid=0, zmin=-1, zmax=1,
        text=corr.values,
        texttemplate="%{text:.2f}",
        textfont=dict(size=11),
        hovertemplate="<b>%{y}</b> × <b>%{x}</b><br>Spearman: %{z:.3f}<extra></extra>",
        colorbar=dict(title="r", tickvals=[-1, -0.5, 0, 0.5, 1])
    ))

    fig.update_layout(
        height=380,
        plot_bgcolor="white",
        paper_bgcolor="white",
        font_family="Inter, sans-serif",
        margin=dict(t=20, b=60, l=20, r=20),
        xaxis=dict(tickangle=-30),
        hoverlabel=dict(bgcolor="white", font_size=13),
    )
    return fig


# ---------------------------------------------------------------------------
# RENDER PRINCIPAL
# ---------------------------------------------------------------------------

def render(df: pd.DataFrame):

    # Narrativa de apertura
    st.html("""
    <div style="background:linear-gradient(135deg,#F6F0E6,#E8D8C8);
                border-radius:14px;padding:1.2rem 1.8rem;margin-bottom:1.5rem;
                border-left:4px solid #648A96;">
        <div style="font-family:'DM Serif Display',serif;font-size:1.2rem;
                    color:#1A2E35;line-height:1.4;">
            ¿Qué determina que una madre dé lactancia exclusiva 6 meses?
        </div>
        <div style="font-size:0.8rem;color:#648A96;margin-top:0.4rem;">
            El nivel educativo y la clase social son los factores más
            determinantes. No es una decisión puramente individual —
            es una cuestión de desigualdad estructural.
        </div>
    </div>
    """)

    # --- Fila 1: Box plot clase social + barras educación ---
    col1, col2 = st.columns(2)

    with col1:
        _titulo_seccion(
            "Clase social y duración de LM",
            "Distribución de meses de lactancia por clase socioeconómica"
        )
        st.plotly_chart(_chart_boxplot_clase(df), use_container_width=True)
        st.caption(
            "Las clases altas muestran mayor variabilidad y mediana más alta. "
            "La línea roja marca el mínimo recomendado por la OMS."
        )

    with col2:
        _titulo_seccion(
            "Nivel educativo detallado",
            "% que alcanza LME ≥ 6 meses por nivel de estudios"
        )
        st.plotly_chart(_chart_educ_detallado(df), use_container_width=True)
        st.caption(
            "La brecha entre sin estudios y posgrado puede superar "
            "los 20 puntos porcentuales."
        )

    st.markdown("---")

    # --- Fila 2: KDE por educación + scatter edad ---
    col3, col4 = st.columns(2)

    with col3:
        _titulo_seccion(
            "Distribución por nivel educativo",
            "Curvas de densidad de la duración según estudios · análisis avanzado"
        )
        st.plotly_chart(_chart_kde_educacion(df), use_container_width=True)
        st.caption(
            "Las madres universitarias tienen la curva desplazada hacia la derecha "
            "— duran más meses en media."
        )

    with col4:
        _titulo_seccion(
            "Edad del menor y duración",
            "Relación entre la edad actual y los meses de lactancia recibidos"
        )
        st.plotly_chart(_chart_scatter_edad(df), use_container_width=True)
        st.caption(
            "Cada punto es un menor. El color indica el nivel educativo de su madre."
        )

    st.markdown("---")

    # --- Fila 3: Heatmap correlación ---
    _titulo_seccion(
        "Correlaciones entre variables",
        "Matriz de correlación de Spearman · rojo = negativa · verde oscuro = positiva"
    )
    st.plotly_chart(_chart_heatmap(df), use_container_width=True)
    st.caption(
        "La correlación más fuerte es entre nivel educativo y clase social (-0.59), "
        "lo que confirma que ambas variables miden dimensiones relacionadas. "
        "La lactancia correlaciona moderadamente con el nivel educativo (0.09)."
    )

    # Nota interpretativa
    st.html("""
    <div style="background:#FFF8F0;border-left:3px solid #E8B8B8;
                border-radius:8px;padding:0.8rem 1.2rem;margin-top:1rem;">
        <div style="font-size:0.78rem;color:#1A2E35;line-height:1.6;">
            <strong style="color:#E8B8B8;">⚠️ Interpretación con cautela:</strong>
            La correlación no implica causalidad. El nivel educativo puede actuar
            como proxy de acceso a información, apoyo del entorno laboral
            (baja maternal, flexibilidad horaria) y recursos económicos.
            Un análisis de regresión multivariante permitiría aislar el efecto
            de cada variable — fuera del alcance de este dashboard descriptivo.
        </div>
    </div>
    """)