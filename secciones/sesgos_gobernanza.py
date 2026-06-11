"""
sesgos_gobernanza.py
====================
Quinta sección del dashboard LactAnalytics.
Documenta explícitamente los sesgos detectados en el dataset,
su impacto potencial y las limitaciones metodológicas.

Esta sección es obligatoria según el checklist del proyecto:
cumple los criterios C10 (ética y gobernanza) e integridad del análisis.
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
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


def _tarjeta_sesgo(nivel: str, titulo: str, descripcion: str, impacto: str):
    """
    Tarjeta de sesgo con código de color por nivel de riesgo.
    nivel: 'alto' | 'medio' | 'bajo'
    """
    config = {
        "alto":  ("#FFF0F0", "#C0392B", "🔴"),
        "medio": ("#FFF8F0", "#E8A020", "🟡"),
        "bajo":  ("#F0F7F9", "#648A96", "🔵"),
    }
    fondo, borde, icono = config.get(nivel, config["medio"])

    st.html(f"""
    <div style="background:{fondo};border-left:4px solid {borde};
                border-radius:10px;padding:1rem 1.2rem;margin-bottom:0.8rem;">
        <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.4rem;">
            <span style="font-size:1rem;">{icono}</span>
            <span style="font-family:'DM Serif Display',serif;font-size:1rem;
                         color:#1A2E35;">{titulo}</span>
        </div>
        <div style="font-size:0.78rem;color:#444;line-height:1.5;
                    margin-bottom:0.5rem;">{descripcion}</div>
        <div style="font-size:0.72rem;color:{borde};font-weight:600;">
            Impacto si se ignora: {impacto}
        </div>
    </div>
    """)


# ---------------------------------------------------------------------------
# Gráfico 1 — Mapa de nulos
# ---------------------------------------------------------------------------

def _chart_nulos(df: pd.DataFrame) -> go.Figure:
    """
    Gráfico de barras horizontales con el % de valores perdidos
    por variable clave. Visualiza la calidad del dato.
    """
    cols_etiquetas = {
        "talla_cm":              "Talla del menor",
        "imc":                   "IMC del menor",
        "ingresos_hogar":        "Ingresos del hogar",
        "meses_lactancia_excl":  "Meses LME",
        "meses_inicio_artificial": "Inicio lactancia artificial",
        "meses_lactancia_total": "Meses LM total",
        "lactancia_exclusiva":   "¿LME? (sí/no)",
        "clase_social":          "Clase social",
        "nivel_educativo_grupo": "Nivel educativo",
        "lactancia_artificial":  "¿Lactancia artificial?",
    }

    nulos = []
    for col, etiqueta in cols_etiquetas.items():
        if col in df.columns:
            pct = df[col].isna().sum() / len(df) * 100
            nulos.append({"variable": etiqueta, "pct_nulos": round(pct, 1)})

    if not nulos:
        return go.Figure()

    df_nulos = pd.DataFrame(nulos).sort_values("pct_nulos", ascending=True)

    colores = [
        "#C0392B" if v > 40 else "#E8B8B8" if v > 15 else "#648A96"
        for v in df_nulos["pct_nulos"]
    ]

    fig = go.Figure(go.Bar(
        x=df_nulos["pct_nulos"],
        y=df_nulos["variable"],
        orientation="h",
        marker_color=colores,
        text=df_nulos["pct_nulos"].apply(lambda x: f"{x:.1f}%"),
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Valores perdidos: %{x:.1f}%<extra></extra>",
    ))

    # Línea de referencia umbral crítico
    fig.add_vline(
        x=30, line_dash="dash", line_color="#C0392B", line_width=1.5,
        annotation_text="Umbral crítico (30%)",
        annotation_position="top right",
        annotation_font=dict(size=10, color="#C0392B")
    )

    fig.update_layout(
        height=380,
        plot_bgcolor="white",
        paper_bgcolor="white",
        font_family="Inter, sans-serif",
        margin=dict(t=20, b=40, l=10, r=70),
        xaxis=dict(
            title="% de valores perdidos",
            ticksuffix="%",
            range=[0, 105],
            gridcolor="#F0F0F0"
        ),
        yaxis=dict(title=""),
        showlegend=False,
        hoverlabel=dict(bgcolor="white", font_size=13),
    )
    return fig


# ---------------------------------------------------------------------------
# Gráfico 2 — Distribución muestral por CCAA
# ---------------------------------------------------------------------------

def _chart_muestra_ccaa(df: pd.DataFrame) -> go.Figure:
    """
    Tamaño muestral por CCAA. Evidencia la subrepresentación
    de algunas comunidades con n < 30.
    """
    conteo = df.groupby("ccaa").size().reset_index(name="n")
    conteo = conteo.sort_values("n", ascending=True)

    colores = [
        "#C0392B" if v < 30 else "#E8B8B8" if v < 60 else "#648A96"
        for v in conteo["n"]
    ]

    fig = go.Figure(go.Bar(
        x=conteo["n"],
        y=conteo["ccaa"],
        orientation="h",
        marker_color=colores,
        text=conteo["n"],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>n = %{x}<extra></extra>",
    ))

    fig.add_vline(
        x=30, line_dash="dash", line_color="#C0392B", line_width=1.5,
        annotation_text="Mínimo recomendado (n=30)",
        annotation_position="top right",
        annotation_font=dict(size=10, color="#C0392B")
    )

    fig.update_layout(
        height=500,
        plot_bgcolor="white",
        paper_bgcolor="white",
        font_family="Inter, sans-serif",
        margin=dict(t=20, b=40, l=10, r=60),
        xaxis=dict(
            title="Número de menores en la muestra",
            gridcolor="#F0F0F0",
            range=[0, 280]
        ),
        yaxis=dict(title=""),
        showlegend=False,
        hoverlabel=dict(bgcolor="white", font_size=13),
    )
    return fig


# ---------------------------------------------------------------------------
# Gráfico 3 — Distribución por clase social
# ---------------------------------------------------------------------------

def _chart_distribucion_clase(df: pd.DataFrame) -> go.Figure:
    """
    Distribución de la muestra por clase social.
    Detecta si hay subrepresentación de alguna clase.
    """
    etiquetas = {
        1.0: "I · Alta",
        2.0: "II · Media-alta",
        3.0: "III · Media",
        4.0: "IV · Media-baja",
        5.0: "V · Baja",
        6.0: "VI · Agraria",
    }

    sub = df[df["clase_social"].notna() & df["clase_social"].isin(etiquetas.keys())].copy()
    sub["clase_label"] = sub["clase_social"].map(etiquetas)

    conteo = sub.groupby("clase_label").size().reset_index(name="n")
    conteo["pct"] = (conteo["n"] / len(sub) * 100).round(1)

    orden = list(etiquetas.values())
    conteo["clase_label"] = pd.Categorical(
        conteo["clase_label"], categories=orden, ordered=True
    )
    conteo = conteo.sort_values("clase_label")

    fig = go.Figure(go.Bar(
        x=conteo["clase_label"],
        y=conteo["pct"],
        marker_color="#648A96",
        text=conteo["pct"].apply(lambda x: f"{x:.1f}%"),
        textposition="outside",
        customdata=conteo["n"],
        hovertemplate="<b>%{x}</b><br>%{y:.1f}% · n = %{customdata}<extra></extra>",
    ))

    fig.update_layout(
        height=300,
        plot_bgcolor="white",
        paper_bgcolor="white",
        font_family="Inter, sans-serif",
        margin=dict(t=20, b=60, l=40, r=20),
        xaxis=dict(title="Clase social", tickangle=-20),
        yaxis=dict(
            title="% de la muestra",
            ticksuffix="%",
            range=[0, 35],
            gridcolor="#F0F0F0"
        ),
        showlegend=False,
        hoverlabel=dict(bgcolor="white", font_size=13),
    )
    return fig


# ---------------------------------------------------------------------------
# RENDER PRINCIPAL
# ---------------------------------------------------------------------------

def render(df: pd.DataFrame):

    # Narrativa de apertura
    st.html("""
    <div style="background:linear-gradient(135deg,#C0392B,#E8B8B8);
                border-radius:14px;padding:1.4rem 1.8rem;margin-bottom:1.5rem;">
        <div style="font-family:'DM Serif Display',serif;font-size:1.3rem;
                    color:#FFFFFF;line-height:1.4;">
            Los datos nunca son neutrales.
            Todo dataset tiene sesgos — lo importante es identificarlos
            y no ignorarlos en la toma de decisiones.
        </div>
        <div style="font-size:0.8rem;color:#FFF0F0;margin-top:0.5rem;">
            Esta sección documenta los sesgos detectados en la ENSE 2017
            y su impacto potencial si se usaran estos datos para
            automatizar decisiones de política sanitaria.
        </div>
    </div>
    """)

    # --- Sesgos identificados ---
    _titulo_seccion(
        "Sesgos detectados",
        "Clasificados por nivel de riesgo · rojo = alto · amarillo = medio · azul = bajo"
    )

    col_s1, col_s2 = st.columns(2)

    with col_s1:
        _tarjeta_sesgo(
            "alto",
            "Sesgo de memoria (autodeclaración)",
            "Las respuestas sobre lactancia son autodeclaradas por la madre "
            "o el tutor. La duración exacta de LME puede estar sobreestimada "
            "por deseabilidad social — las madres tienden a declarar más meses "
            "de LME de los reales para ajustarse a la recomendación OMS.",
            "Sobreestimación de tasas de LME. Las cifras reales podrían ser "
            "aún más bajas que las del 27.5% registrado."
        )
        _tarjeta_sesgo(
            "alto",
            "Subrepresentación de población migrante",
            "La ENSE se realiza en castellano y otras lenguas cooficiales, "
            "pero excluye a familias sin domicilio fijo o con barrera idiomática. "
            "Las madres migrantes tienen patrones de lactancia distintos "
            "y están sistemáticamente infrarrepresentadas.",
            "Los resultados no son extrapolables a toda la población española. "
            "Las políticas basadas en estos datos pueden ignorar colectivos vulnerables."
        )
        _tarjeta_sesgo(
            "alto",
            "Sesgo de no respuesta en ingresos",
            "El 55.3% de los hogares no declaró sus ingresos mensuales. "
            "La no respuesta en variables económicas no es aleatoria — "
            "los hogares con ingresos muy bajos o muy altos tienden "
            "a no responder más frecuentemente.",
            "El análisis socioeconómico de la lactancia está gravemente "
            "limitado. Las conclusiones sobre desigualdad económica "
            "deben tomarse con extrema cautela."
        )

    with col_s2:
        _tarjeta_sesgo(
            "medio",
            "Brecha urbano-rural no controlada",
            "El dataset no incluye variable de ruralidad de forma explícita. "
            "El acceso a grupos de apoyo a la lactancia, asesoras IBCLC "
            "y unidades de lactancia hospitalaria varía enormemente "
            "entre entornos urbanos y rurales.",
            "Las diferencias entre CCAA pueden estar parcialmente explicadas "
            "por el grado de urbanización, no solo por políticas autonómicas."
        )
        _tarjeta_sesgo(
            "medio",
            "Datos transversales, no longitudinales",
            "La ENSE es una encuesta de corte transversal — recoge el estado "
            "en un momento puntual. Los datos de lactancia son retrospectivos "
            "para menores de hasta 4 años, con el consiguiente error de memoria.",
            "No es posible establecer relaciones causales. Las asociaciones "
            "encontradas entre lactancia y salud pueden estar confundidas "
            "por variables no medidas."
        )
        _tarjeta_sesgo(
            "bajo",
            "Muestra pequeña en algunas CCAA",
            "Ceuta, Melilla y La Rioja tienen menos de 30 menores en la muestra. "
            "Los intervalos de confianza para estas comunidades son muy amplios "
            "y los resultados no son estadísticamente robustos.",
            "Las comparaciones entre CCAA pequeñas y grandes pueden "
            "llevar a conclusiones erróneas sobre diferencias territoriales."
        )

    st.markdown("---")

    # --- Mapa de nulos ---
    col_n1, col_n2 = st.columns(2)

    with col_n1:
        _titulo_seccion(
            "Calidad del dato por variable",
            "% de valores perdidos · rojo = crítico (>40%) · rosa = relevante (>15%)"
        )
        st.plotly_chart(_chart_nulos(df), use_container_width=True)

    with col_n2:
        _titulo_seccion(
            "Tamaño muestral por CCAA",
            "Menores con módulo de lactancia respondido · rojo = n < 30"
        )
        st.plotly_chart(_chart_muestra_ccaa(df), use_container_width=True)

    st.markdown("---")

    # --- Distribución clase social ---
    _titulo_seccion(
        "Distribución de la muestra por clase social",
        "Verificación de representatividad · ¿está bien distribuida la muestra?"
    )
    st.plotly_chart(_chart_distribucion_clase(df), use_container_width=True)
    st.caption(
        "La muestra está concentrada en clases III y IV. "
        "Las clases extremas (I y VI) están subrepresentadas, "
        "lo que limita el análisis de desigualdad en los extremos."
    )

    st.markdown("---")

    # --- Impacto en decisiones automatizadas ---
    _titulo_seccion(
        "¿Qué pasaría si ignorásemos estos sesgos?",
        "Impacto en decisiones de política sanitaria basadas en estos datos"
    )

    col_i1, col_i2, col_i3 = st.columns(3)

    with col_i1:
        st.html("""
        <div style="background:#FFF0F0;border-radius:10px;padding:1rem;
                    border-top:3px solid #C0392B;">
            <div style="font-size:0.9rem;font-weight:600;color:#C0392B;
                        margin-bottom:0.5rem;">📊 Decisión: asignación de recursos</div>
            <div style="font-size:0.78rem;color:#1A2E35;line-height:1.6;">
                Si una Consejería de Sanidad asignara recursos de apoyo
                a la lactancia basándose en las tasas de LME de este dataset,
                podría <strong>infrafinanciar zonas rurales</strong> y comunidades
                con alta población migrante, precisamente las que más apoyo necesitan.
            </div>
        </div>
        """)

    with col_i2:
        st.html("""
        <div style="background:#FFF8F0;border-radius:10px;padding:1rem;
                    border-top:3px solid #E8A020;">
            <div style="font-size:0.9rem;font-weight:600;color:#E8A020;
                        margin-bottom:0.5rem;">🤖 Decisión: modelo predictivo</div>
            <div style="font-size:0.78rem;color:#1A2E35;line-height:1.6;">
                Un modelo de ML entrenado con estos datos para predecir
                riesgo de abandono prematuro heredaría el sesgo de memoria
                y la subrepresentación migrante, generando un sistema
                <strong>injusto para las poblaciones más vulnerables</strong>.
            </div>
        </div>
        """)

    with col_i3:
        st.html("""
        <div style="background:#F0F7F9;border-radius:10px;padding:1rem;
                    border-top:3px solid #648A96;">
            <div style="font-size:0.9rem;font-weight:600;color:#648A96;
                        margin-bottom:0.5rem;">📋 Decisión: evaluación de programas</div>
            <div style="font-size:0.78rem;color:#1A2E35;line-height:1.6;">
                Evaluar el éxito de programas de promoción de la lactancia
                usando solo estas métricas podría dar una
                <strong>imagen falsamente positiva</strong> si los grupos
                más vulnerables no están representados en la muestra.
            </div>
        </div>
        """)

    st.markdown("---")

    # --- Recomendaciones ---
    _titulo_seccion(
        "Recomendaciones para mejorar la gobernanza",
        "Propuestas concretas para el Ministerio de Sanidad y la ONG"
    )

    st.html("""
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.8rem;">
        <div style="background:#FFFFFF;border-radius:10px;padding:1rem;
                    box-shadow:0 2px 8px rgba(100,138,150,0.10);">
            <div style="font-size:0.85rem;font-weight:600;color:#648A96;
                        margin-bottom:0.4rem;">1. Encuesta complementaria a población migrante</div>
            <div style="font-size:0.75rem;color:#444;line-height:1.5;">
                Diseñar un módulo específico multilingüe para capturar
                patrones de lactancia en familias no hispanohablantes.
            </div>
        </div>
        <div style="background:#FFFFFF;border-radius:10px;padding:1rem;
                    box-shadow:0 2px 8px rgba(100,138,150,0.10);">
            <div style="font-size:0.85rem;font-weight:600;color:#648A96;
                        margin-bottom:0.4rem;">2. Registro longitudinal de lactancia</div>
            <div style="font-size:0.75rem;color:#444;line-height:1.5;">
                Incorporar seguimiento prospectivo en el programa de
                salud infantil para eliminar el sesgo de memoria retrospectiva.
            </div>
        </div>
        <div style="background:#FFFFFF;border-radius:10px;padding:1rem;
                    box-shadow:0 2px 8px rgba(100,138,150,0.10);">
            <div style="font-size:0.85rem;font-weight:600;color:#648A96;
                        margin-bottom:0.4rem;">3. Variable de ruralidad explícita</div>
            <div style="font-size:0.75rem;color:#444;line-height:1.5;">
                Añadir indicador urbano/rural/semiurbano para controlar
                el efecto del acceso a servicios de apoyo a la lactancia.
            </div>
        </div>
        <div style="background:#FFFFFF;border-radius:10px;padding:1rem;
                    box-shadow:0 2px 8px rgba(100,138,150,0.10);">
            <div style="font-size:0.85rem;font-weight:600;color:#648A96;
                        margin-bottom:0.4rem;">4. Ampliar muestra en CCAA pequeñas</div>
            <div style="font-size:0.75rem;color:#444;line-height:1.5;">
                Garantizar n ≥ 100 en todas las CCAA para permitir
                comparaciones territoriales estadísticamente robustas.
            </div>
        </div>
    </div>
    """)

    # Declaración final de integridad
    st.html("""
    <div style="background:#1A2E35;border-radius:10px;padding:1.2rem 1.6rem;
                margin-top:1.5rem;">
        <div style="font-family:'DM Serif Display',serif;font-size:1rem;
                    color:#F6F0E6;margin-bottom:0.5rem;">
            Declaración de integridad del análisis
        </div>
        <div style="font-size:0.75rem;color:#648A96;line-height:1.7;">
            Este dashboard ha sido desarrollado con criterios de transparencia metodológica.
            Todos los sesgos conocidos han sido documentados antes de presentar conclusiones.
            Los resultados deben interpretarse como <strong style="color:#E8B8B8;">
            indicadores descriptivos orientativos</strong>, no como evidencia causal
            para la toma de decisiones clínicas o de política sanitaria sin
            análisis complementarios.
            <br><br>
            Fuente primaria: ENSE 2017 · Ministerio de Sanidad / INE ·
            Licencia CC BY 4.0 · Análisis realizado con Python, Pandas y Plotly.
        </div>
    </div>
    """)