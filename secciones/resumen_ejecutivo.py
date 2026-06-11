"""
resumen_ejecutivo.py
====================
Primera sección del dashboard LactAnalytics.
Muestra la narrativa principal: curva de abandono, distribución KDE
y comparativa por nivel educativo.
Orientada a audiencia no técnica — lenguaje de negocio, sin tecnicismos.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from scipy import stats as scipy_stats
from src.config import COLORES


# ---------------------------------------------------------------------------
# Helpers de estilo
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


def _tarjeta_insight(icono: str, texto: str, tipo: str = "normal"):
    colores = {
        "normal": ("#F0F7F9", "#648A96"),
        "alerta": ("#FFF8F0", "#E8B8B8"),
        "critico": ("#FFF0F0", "#C0392B"),
    }
    fondo, borde = colores.get(tipo, colores["normal"])
    st.html(f"""
    <div style="background:{fondo};border-left:3px solid {borde};
                border-radius:8px;padding:0.8rem 1rem;margin-bottom:0.6rem;">
        <span style="font-size:1.1rem;">{icono}</span>
        <span style="font-size:0.82rem;color:#1A2E35;margin-left:0.5rem;">
            {texto}
        </span>
    </div>
    """)


# ---------------------------------------------------------------------------
# Gráfico 1 — Curva de abandono
# ---------------------------------------------------------------------------

def _chart_curva_abandono(df: pd.DataFrame) -> go.Figure:
    """
    Muestra qué porcentaje de bebés sigue con lactancia materna
    a cada mes de vida. Líneas verticales marcan los hitos OMS.
    """
    sub = df[
        df["meses_lactancia_total"].notna() &
        (df["lactancia_materna"] == True)
    ].copy()
    total = len(sub)

    if total == 0:
        return go.Figure()

    meses = list(range(0, 25))
    pct = [round((sub["meses_lactancia_total"] >= m).sum() / total * 100, 1)
           for m in meses]

    fig = go.Figure()

    # Zona de relleno bajo la curva
    fig.add_trace(go.Scatter(
        x=meses, y=pct,
        fill="tozeroy",
        fillcolor="rgba(100,138,150,0.12)",
        line=dict(color="#648A96", width=2.5),
        mode="lines",
        name="% con LM activa",
        hovertemplate="Mes %{x}: <b>%{y:.1f}%</b> siguen con lactancia<extra></extra>",
    ))

    # Hito OMS: 6 meses LME
    fig.add_vline(
        x=6, line_dash="dash", line_color="#E8B8B8", line_width=1.5,
        annotation_text=f"6m · {pct[6]}% aún con LM",
        annotation_position="top right",
        annotation_font=dict(size=11, color="#E8B8B8")
    )

    # Hito OMS: 24 meses
    fig.add_vline(
        x=24, line_dash="dash", line_color="#C0392B", line_width=1.5,
        annotation_text=f"24m · {pct[24]}% aún con LM",
        annotation_position="top left",
        annotation_font=dict(size=11, color="#C0392B")
    )

    fig.update_layout(
        height=340,
        plot_bgcolor="white",
        paper_bgcolor="white",
        font_family="Inter, sans-serif",
        margin=dict(t=20, b=40, l=40, r=40),
        xaxis=dict(
            title="Mes de vida del bebé",
            tickmode="linear", dtick=2,
            gridcolor="#F0F0F0"
        ),
        yaxis=dict(
            title="% con lactancia activa",
            ticksuffix="%",
            range=[0, 105],
            gridcolor="#F0F0F0"
        ),
        showlegend=False,
        hoverlabel=dict(bgcolor="white", font_size=13),
    )
    return fig


# ---------------------------------------------------------------------------
# Gráfico 2 — KDE duración lactancia
# ---------------------------------------------------------------------------

def _chart_kde(df: pd.DataFrame) -> go.Figure:
    """
    Curva de densidad de la duración total de lactancia materna.
    Muestra dónde se concentra la mayoría de los casos.
    """
    datos = df["meses_lactancia_total"].dropna()

    if len(datos) < 10:
        return go.Figure()

    kde = scipy_stats.gaussian_kde(datos)
    x = np.linspace(datos.min(), datos.max(), 300)
    y = kde(x)

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=x, y=y,
        fill="tozeroy",
        fillcolor="rgba(232,184,184,0.2)",
        line=dict(color="#E8B8B8", width=2.5),
        mode="lines",
        hovertemplate="%{x:.1f} meses<extra></extra>",
    ))

    # Mediana
    mediana = datos.median()
    fig.add_vline(
        x=mediana, line_dash="dot", line_color="#648A96",
        annotation_text=f"Mediana: {mediana:.0f}m",
        annotation_position="top right",
        annotation_font=dict(size=11, color="#648A96")
    )

    # Objetivo OMS
    fig.add_vline(
        x=6, line_dash="dash", line_color="#C0392B",
        annotation_text="OMS: 6m mínimo",
        annotation_position="top left",
        annotation_font=dict(size=11, color="#C0392B")
    )

    fig.update_layout(
        height=300,
        plot_bgcolor="white",
        paper_bgcolor="white",
        font_family="Inter, sans-serif",
        margin=dict(t=20, b=40, l=20, r=20),
        xaxis=dict(title="Meses de lactancia", gridcolor="#F0F0F0"),
        yaxis=dict(title="Densidad", showticklabels=False, gridcolor="#F0F0F0"),
        showlegend=False,
        hoverlabel=dict(bgcolor="white", font_size=13),
    )
    return fig


# ---------------------------------------------------------------------------
# Gráfico 3 — Barras por nivel educativo
# ---------------------------------------------------------------------------

def _chart_educacion(df: pd.DataFrame) -> go.Figure:
    """
    % de LME ≥ 6 meses por nivel educativo agrupado.
    """
    orden = ["Básico o menos", "Secundaria", "FP", "Universidad"]
    sub = df[df["lme_6meses"].notna() & df["nivel_educativo_grupo"].notna()]

    tasa = (
        sub.groupby("nivel_educativo_grupo")["lme_6meses"]
        .agg(n="count", n_lme6=lambda x: x.sum())
        .reset_index()
    )
    tasa["pct"] = (tasa["n_lme6"] / tasa["n"] * 100).round(1)
    tasa = tasa[tasa["nivel_educativo_grupo"].isin(orden)].copy()
    tasa["nivel_educativo_grupo"] = pd.Categorical(
        tasa["nivel_educativo_grupo"], categories=orden, ordered=True
    )
    tasa = tasa.sort_values("nivel_educativo_grupo")

    media = tasa["pct"].mean()
    colores_barras = ["#C0392B", "#E8B8B8", "#648A96", "#1A2E35"]

    fig = go.Figure(go.Bar(
        x=tasa["pct"],
        y=tasa["nivel_educativo_grupo"],
        orientation="h",
        marker_color=colores_barras,
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
        height=280,
        plot_bgcolor="white",
        paper_bgcolor="white",
        font_family="Inter, sans-serif",
        margin=dict(t=20, b=40, l=10, r=60),
        xaxis=dict(
            title="% con LME ≥ 6 meses",
            ticksuffix="%",
            range=[0, 42],
            gridcolor="#F0F0F0"
        ),
        yaxis=dict(title=""),
        showlegend=False,
        hoverlabel=dict(bgcolor="white", font_size=13),
    )
    return fig


# ---------------------------------------------------------------------------
# Gráfico 4 — Comparativa LM vs LME
# ---------------------------------------------------------------------------

def _chart_comparativa_lm_lme(df: pd.DataFrame) -> go.Figure:
    """
    Barras apiladas comparando % que recibió LM, LME y ninguna.
    """
    total = len(df)
    pct_lm = round(df["lactancia_materna"].sum() / total * 100, 1)
    sub_lme = df[df["lme_6meses"].notna()]
    pct_lme = round(sub_lme["lme_6meses"].sum() / len(sub_lme) * 100, 1)
    pct_lm_24 = round(df["lm_24meses"].sum() / df["lm_24meses"].notna().sum() * 100, 1)

    categorias = ["Inició LM", "LME ≥ 6 meses", "LM ≥ 24 meses"]
    valores = [pct_lm, pct_lme, pct_lm_24]
    colores = ["#648A96", "#E8B8B8", "#1A2E35"]
    oms = [100, 100, 100]

    fig = go.Figure()

    # Barras reales
    fig.add_trace(go.Bar(
        name="España 2017",
        x=categorias,
        y=valores,
        marker_color=colores,
        text=[f"{v}%" for v in valores],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>España: %{y:.1f}%<extra></extra>",
    ))

    # Línea OMS
    fig.add_trace(go.Scatter(
        name="Objetivo OMS (100%)",
        x=categorias,
        y=oms,
        mode="lines+markers",
        line=dict(color="#C0392B", dash="dash", width=1.5),
        marker=dict(size=6),
        hovertemplate="OMS: %{y}%<extra></extra>",
    ))

    fig.update_layout(
        height=320,
        plot_bgcolor="white",
        paper_bgcolor="white",
        font_family="Inter, sans-serif",
        margin=dict(t=20, b=40, l=40, r=40),
        yaxis=dict(
            title="% de menores",
            ticksuffix="%",
            range=[0, 115],
            gridcolor="#F0F0F0"
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom", y=1.02,
            xanchor="right", x=1
        ),
        hoverlabel=dict(bgcolor="white", font_size=13),
        barmode="group",
    )
    return fig


# ---------------------------------------------------------------------------
# RENDER PRINCIPAL
# ---------------------------------------------------------------------------

def render(df: pd.DataFrame, kpis: dict):

    # --- Narrativa de apertura ---
    st.html("""
    <div style="background:linear-gradient(135deg,#1A2E35,#648A96);
                border-radius:14px;padding:1.4rem 1.8rem;margin-bottom:1.5rem;">
        <div style="font-family:'DM Serif Display',serif;font-size:1.3rem;
                    color:#F6F0E6;line-height:1.4;">
            Solo 1 de cada 4 bebés en España recibe lactancia materna exclusiva
            los primeros 6 meses de vida.
        </div>
        <div style="font-size:0.8rem;color:#E8B8B8;margin-top:0.5rem;">
            La OMS recomienda lactancia exclusiva hasta los 6 meses y complementaria
            hasta los 2 años. España está muy por debajo de ambos objetivos.
        </div>
    </div>
    """)

    # --- Insights clave ---
    col_ins, col_grafico = st.columns([1, 2])

    with col_ins:
        _titulo_seccion(
            "Lo que dicen los datos",
            "Principales hallazgos · ENSE 2017"
        )
        _tarjeta_insight(
            "🤱", f"El <b>{kpis['pct_lactancia_materna']}%</b> de los bebés "
            f"recibió lactancia materna.", "normal"
        )
        _tarjeta_insight(
            "⚠️", f"Solo el <b>{kpis['pct_lme_6meses']}%</b> alcanzó los "
            f"6 meses de lactancia exclusiva recomendados por la OMS.", "alerta"
        )
        _tarjeta_insight(
            "🚨", f"Apenas el <b>{kpis['pct_lm_24meses']}%</b> llegó a los "
            f"2 años. La brecha con el objetivo OMS es de "
            f"<b>{kpis['brecha_lm_meses']} meses</b>.", "critico"
        )
        _tarjeta_insight(
            "📚", "Las madres universitarias tienen un <b>71% más</b> de "
            "probabilidad de alcanzar LME 6 meses que las de estudios básicos.",
            "normal"
        )
        _tarjeta_insight(
            "📍", "Castilla y León y Madrid lideran el ranking autonómico "
            "con tasas superiores al 36%.", "normal"
        )

    with col_grafico:
        _titulo_seccion(
            "¿Cuánto dura la lactancia?",
            "Curva de abandono mes a mes · menores 0-2 años"
        )
        st.plotly_chart(
            _chart_curva_abandono(df),
            use_container_width=True
        )

    st.markdown("---")

    # --- Fila 2: KDE + Educación ---
    col_kde, col_educ = st.columns(2)

    with col_kde:
        _titulo_seccion(
            "Distribución de la duración",
            "Curva de densidad · análisis estadístico avanzado"
        )
        st.plotly_chart(_chart_kde(df), use_container_width=True)
        st.caption(
            "La curva muestra dónde se concentran los casos. "
            "El pico a la izquierda indica que la mayoría abandona antes del mes 3."
        )

    with col_educ:
        _titulo_seccion(
            "El nivel educativo importa",
            "% LME ≥ 6 meses según estudios de la madre"
        )
        st.plotly_chart(_chart_educacion(df), use_container_width=True)
        st.caption(
            "A mayor nivel educativo, mayor tasa de lactancia exclusiva. "
            "La brecha entre estudios básicos y universitarios es de casi 13 puntos."
        )

    st.markdown("---")

    # --- Fila 3: Comparativa España vs OMS ---
    _titulo_seccion(
        "España vs. objetivos OMS",
        "Comparativa de los tres indicadores clave de lactancia"
    )
    st.plotly_chart(_chart_comparativa_lm_lme(df), use_container_width=True)

    # --- Nota metodológica ---
    st.html("""
    <div style="background:#F0F4F8;border-radius:8px;padding:0.8rem 1.2rem;
                margin-top:1rem;">
        <div style="font-size:0.72rem;color:#648A96;line-height:1.6;">
            <strong>Nota metodológica:</strong>
            Los datos corresponden a menores de 0-4 años de la ENSE 2017
            (n=1.764). Los porcentajes de LME se calculan sobre los registros
            con respuesta válida. Los valores perdidos en ingresos (55,3%) y
            talla (92,9%) limitan algunos análisis — ver sección
            <em>Sesgos y gobernanza</em>.
        </div>
    </div>
    """)