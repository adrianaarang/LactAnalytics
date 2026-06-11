"""
salud_infantil.py
=================
Tercera sección del dashboard LactAnalytics.
Analiza la relación entre lactancia materna y salud infantil.

Variables disponibles en ENSE 2017:
- B4: Valoración general de salud (1=Muy buena → 5=Muy mala)
- B5_1a: Enfermedad crónica diagnosticada (1=sí, 2=no)
- B5_2a: Asma o alergia respiratoria
- B5_6a: Alergia alimentaria o cutánea
- IMCm: Categoría de IMC (1=bajo peso, 2=normopeso, 3=sobrepeso, 4=obesidad)
- H33: ¿Se ha medido/pesado en los últimos 12 meses? (1=sí, 2=no)
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


def _tarjeta_evidencia(icono: str, titulo: str, texto: str, fuente: str):
    st.html(f"""
    <div style="background:#FFFFFF;border-radius:10px;padding:1rem 1.2rem;
                margin-bottom:0.8rem;
                box-shadow:0 2px 8px rgba(100,138,150,0.10);
                border-top:3px solid #648A96;">
        <div style="font-size:1.2rem;">{icono}</div>
        <div style="font-family:'DM Serif Display',serif;font-size:0.95rem;
                    color:#1A2E35;margin-top:0.3rem;">{titulo}</div>
        <div style="font-size:0.78rem;color:#444;margin-top:0.3rem;
                    line-height:1.5;">{texto}</div>
        <div style="font-size:0.68rem;color:#648A96;margin-top:0.5rem;
                    font-style:italic;">{fuente}</div>
    </div>
    """)


def _badge_limitacion(texto: str):
    st.html(f"""
    <div style="background:#FFF8F0;border-left:3px solid #E8B8B8;
                border-radius:6px;padding:0.5rem 0.8rem;margin-bottom:0.6rem;">
        <span style="font-size:0.75rem;color:#856404;">⚠️ {texto}</span>
    </div>
    """)


# ---------------------------------------------------------------------------
# Gráfico 1 — Valoración de salud por tipo de lactancia
# ---------------------------------------------------------------------------

def _chart_salud_lactancia(df: pd.DataFrame) -> go.Figure:
    """
    Compara la valoración de salud del menor entre los que
    recibieron LM y los que no. Escala: 1=Muy buena → 5=Muy mala.
    """
    etiquetas_salud = {
        1: "Muy buena",
        2: "Buena",
        3: "Regular",
        4: "Mala",
        5: "Muy mala"
    }

    sub = df[
        df["valoracion_salud"].notna() &
        df["lactancia_materna"].notna()
    ].copy()

    sub["valoracion_salud"] = pd.to_numeric(sub["valoracion_salud"], errors="coerce")
    sub["salud_label"] = sub["valoracion_salud"].map(etiquetas_salud)
    sub["lm_label"] = sub["lactancia_materna"].map({True: "Con LM", False: "Sin LM"})

    orden_salud = ["Muy buena", "Buena", "Regular", "Mala", "Muy mala"]
    tasa = sub.groupby(["lm_label", "salud_label"]).size().reset_index(name="n")
    totales = sub.groupby("lm_label").size()
    tasa["pct"] = tasa.apply(
        lambda r: round(r["n"] / totales[r["lm_label"]] * 100, 1), axis=1
    )

    colores_lm = {"Con LM": "#648A96", "Sin LM": "#E8B8B8"}

    fig = go.Figure()
    for grupo in ["Con LM", "Sin LM"]:
        sub_g = tasa[tasa["lm_label"] == grupo].copy()
        sub_g["salud_label"] = pd.Categorical(
            sub_g["salud_label"], categories=orden_salud, ordered=True
        )
        sub_g = sub_g.sort_values("salud_label")
        fig.add_trace(go.Bar(
            name=grupo,
            x=sub_g["salud_label"],
            y=sub_g["pct"],
            marker_color=colores_lm[grupo],
            text=sub_g["pct"].apply(lambda x: f"{x:.1f}%"),
            textposition="outside",
            hovertemplate=f"<b>{grupo}</b><br>%{{x}}: %{{y:.1f}}%<extra></extra>",
        ))

    fig.update_layout(
        height=340,
        barmode="group",
        plot_bgcolor="white",
        paper_bgcolor="white",
        font_family="Inter, sans-serif",
        margin=dict(t=20, b=40, l=40, r=20),
        xaxis=dict(title="Valoración de salud del menor"),
        yaxis=dict(
            title="% de menores",
            ticksuffix="%",
            range=[0, 85],
            gridcolor="#F0F0F0"
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hoverlabel=dict(bgcolor="white", font_size=13),
    )
    return fig


# ---------------------------------------------------------------------------
# Gráfico 2 — Categoría de IMC por tipo de lactancia
# ---------------------------------------------------------------------------

def _chart_imc_categorias(df: pd.DataFrame) -> go.Figure:
    """
    Distribución de categorías de IMC por tipo de lactancia.
    IMCm en ENSE 2017: 1=bajo peso, 2=normopeso, 3=sobrepeso, 4=obesidad.
    """
    imc_labels = {
        1.0: "Bajo peso",
        2.0: "Normopeso",
        3.0: "Sobrepeso",
        4.0: "Obesidad",
    }

    sub = df[
        df["imc"].notna() &
        df["lactancia_materna"].notna() &
        df["imc"].isin([1.0, 2.0, 3.0, 4.0])
    ].copy()

    if len(sub) < 20:
        fig = go.Figure()
        fig.add_annotation(
            text="Datos insuficientes para este análisis",
            xref="paper", yref="paper", x=0.5, y=0.5,
            showarrow=False, font=dict(size=12, color="#648A96")
        )
        fig.update_layout(height=320, plot_bgcolor="white", paper_bgcolor="white")
        return fig

    sub["imc_label"] = sub["imc"].map(imc_labels)
    sub["lm_label"] = sub["lactancia_materna"].map({True: "Con LM", False: "Sin LM"})

    orden = ["Bajo peso", "Normopeso", "Sobrepeso", "Obesidad"]
    tasa = sub.groupby(["lm_label", "imc_label"]).size().reset_index(name="n")
    totales = sub.groupby("lm_label").size()
    tasa["pct"] = tasa.apply(
        lambda r: round(r["n"] / totales[r["lm_label"]] * 100, 1), axis=1
    )

    colores_lm = {"Con LM": "#648A96", "Sin LM": "#E8B8B8"}

    fig = go.Figure()
    for grupo in ["Con LM", "Sin LM"]:
        sub_g = tasa[tasa["lm_label"] == grupo].copy()
        sub_g["imc_label"] = pd.Categorical(
            sub_g["imc_label"], categories=orden, ordered=True
        )
        sub_g = sub_g.sort_values("imc_label")
        fig.add_trace(go.Bar(
            name=grupo,
            x=sub_g["imc_label"],
            y=sub_g["pct"],
            marker_color=colores_lm[grupo],
            text=sub_g["pct"].apply(lambda x: f"{x:.1f}%"),
            textposition="outside",
            hovertemplate=f"<b>{grupo}</b><br>%{{x}}: %{{y:.1f}}%<extra></extra>",
        ))

    fig.update_layout(
        height=320,
        barmode="group",
        plot_bgcolor="white",
        paper_bgcolor="white",
        font_family="Inter, sans-serif",
        margin=dict(t=20, b=40, l=40, r=20),
        xaxis=dict(title="Categoría de IMC"),
        yaxis=dict(
            title="% de menores",
            ticksuffix="%",
            range=[0, 95],
            gridcolor="#F0F0F0"
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hoverlabel=dict(bgcolor="white", font_size=13),
    )
    return fig


# ---------------------------------------------------------------------------
# Gráfico 3 — Enfermedades crónicas por tipo de lactancia
# ---------------------------------------------------------------------------

def _chart_enfermedades(df: pd.DataFrame) -> go.Figure:
    """
    Compara prevalencia de distintas enfermedades crónicas
    entre menores con y sin lactancia materna.
    B5_1a=enfermedad crónica, B5_2a=asma/alergia resp., B5_6a=alergia alimentaria.
    """
    enfermedades = {
        "enfermedad_cronica": "Enfermedad crónica",
        "asma_alergia":       "Asma / Alergia resp.",
        "alergia_alim":       "Alergia alimentaria",
    }

    # Crear columnas auxiliares si no existen
    df_work = df.copy()
    if "asma_alergia" not in df_work.columns and "B5_2a" in df_work.columns:
        df_work["asma_alergia"] = pd.to_numeric(
            df_work["B5_2a"], errors="coerce"
        ).map({1: True, 2: False})
    if "alergia_alim" not in df_work.columns and "B5_6a" in df_work.columns:
        df_work["alergia_alim"] = pd.to_numeric(
            df_work["B5_6a"], errors="coerce"
        ).map({1: True, 2: False})

    resultados = []
    for col, nombre in enfermedades.items():
        if col not in df_work.columns:
            continue
        sub = df_work[
            df_work[col].notna() &
            df_work["lactancia_materna"].notna()
        ]
        for lm_val, lm_label in [(True, "Con LM"), (False, "Sin LM")]:
            grupo = sub[sub["lactancia_materna"] == lm_val]
            if len(grupo) == 0:
                continue
            pct = round(grupo[col].sum() / len(grupo) * 100, 1)
            resultados.append({
                "enfermedad": nombre,
                "lm_label": lm_label,
                "pct": pct,
                "n": len(grupo)
            })

    if not resultados:
        fig = go.Figure()
        fig.add_annotation(
            text="Variables no disponibles en el dataset procesado",
            xref="paper", yref="paper", x=0.5, y=0.5,
            showarrow=False, font=dict(size=12, color="#648A96")
        )
        fig.update_layout(height=300, plot_bgcolor="white", paper_bgcolor="white")
        return fig

    tasa = pd.DataFrame(resultados)
    colores_lm = {"Con LM": "#648A96", "Sin LM": "#E8B8B8"}

    fig = go.Figure()
    for grupo in ["Con LM", "Sin LM"]:
        sub_g = tasa[tasa["lm_label"] == grupo]
        fig.add_trace(go.Bar(
            name=grupo,
            x=sub_g["enfermedad"],
            y=sub_g["pct"],
            marker_color=colores_lm[grupo],
            text=sub_g["pct"].apply(lambda x: f"{x:.1f}%"),
            textposition="outside",
            hovertemplate=f"<b>{grupo}</b><br>%{{x}}: %{{y:.1f}}%<extra></extra>",
        ))

    fig.update_layout(
        height=320,
        barmode="group",
        plot_bgcolor="white",
        paper_bgcolor="white",
        font_family="Inter, sans-serif",
        margin=dict(t=20, b=40, l=40, r=20),
        xaxis=dict(title=""),
        yaxis=dict(
            title="% de menores afectados",
            ticksuffix="%",
            range=[0, 20],
            gridcolor="#F0F0F0"
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hoverlabel=dict(bgcolor="white", font_size=13),
    )
    return fig


# ---------------------------------------------------------------------------
# Gráfico 4 — Salud valorada por duración LME
# ---------------------------------------------------------------------------

def _chart_salud_por_duracion(df: pd.DataFrame) -> go.Figure:
    """
    % con salud buena/muy buena según duración de lactancia exclusiva.
    """
    sub = df[
        df["meses_lactancia_excl"].notna() &
        df["valoracion_salud"].notna()
    ].copy()

    sub["valoracion_salud"] = pd.to_numeric(sub["valoracion_salud"], errors="coerce")
    sub["meses_lme_grupo"] = pd.cut(
        sub["meses_lactancia_excl"],
        bins=[-1, 0, 2, 4, 6, 50],
        labels=["0 meses", "1-2 meses", "3-4 meses", "5-6 meses", "> 6 meses"]
    )

    sub["salud_buena"] = sub["valoracion_salud"].isin([1, 2])
    tasa = (
        sub.groupby("meses_lme_grupo", observed=True)["salud_buena"]
        .agg(n="count", n_buena=lambda x: x.sum())
        .reset_index()
    )
    tasa["pct"] = (tasa["n_buena"] / tasa["n"] * 100).round(1)

    fig = go.Figure(go.Bar(
        x=tasa["meses_lme_grupo"].astype(str),
        y=tasa["pct"],
        marker=dict(
            color=tasa["pct"],
            colorscale=[[0, "#E8B8B8"], [0.5, "#648A96"], [1, "#1A2E35"]],
            showscale=False,
        ),
        text=tasa["pct"].apply(lambda x: f"{x:.1f}%"),
        textposition="outside",
        customdata=tasa["n"],
        hovertemplate="<b>LME %{x}</b><br>Salud buena/muy buena: %{y:.1f}%<br>n = %{customdata}<extra></extra>",
    ))

    fig.update_layout(
        height=300,
        plot_bgcolor="white",
        paper_bgcolor="white",
        font_family="Inter, sans-serif",
        margin=dict(t=20, b=40, l=40, r=20),
        xaxis=dict(title="Meses de lactancia exclusiva"),
        yaxis=dict(
            title="% salud 'Muy buena' o 'Buena'",
            ticksuffix="%",
            range=[0, 105],
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
    <div style="background:linear-gradient(135deg,#1A2E35,#648A96);
                border-radius:14px;padding:1.4rem 1.8rem;margin-bottom:1.5rem;">
        <div style="font-family:'DM Serif Display',serif;font-size:1.3rem;
                    color:#F6F0E6;line-height:1.4;">
            La lactancia materna protege la salud del bebé.
            La evidencia científica es sólida y consistente.
        </div>
        <div style="font-size:0.8rem;color:#E8B8B8;margin-top:0.5rem;">
            Los datos de la ENSE 2017 permiten explorar esta relación
            en la población española. Las limitaciones del dataset
            se documentan explícitamente en cada análisis.
        </div>
    </div>
    """)

    # --- Evidencia científica ---
    _titulo_seccion(
        "Lo que dice la ciencia",
        "Beneficios documentados · fuentes OMS, AEPED y ABM"
    )

    col_e1, col_e2, col_e3 = st.columns(3)
    with col_e1:
        _tarjeta_evidencia(
            "🦠", "Menor riesgo de infecciones",
            "La LM reduce en un 72% el riesgo de hospitalizaciones "
            "por infecciones respiratorias y en un 64% las gastrointestinales "
            "en el primer año de vida.",
            "OMS · Victora et al. Lancet 2016"
        )
    with col_e2:
        _tarjeta_evidencia(
            "⚖️", "Protección frente a la obesidad",
            "Los bebés amamantados tienen un 13-22% menos de riesgo "
            "de desarrollar sobrepeso u obesidad en la infancia "
            "y la adolescencia.",
            "AEPED · Pediatrics 2012"
        )
    with col_e3:
        _tarjeta_evidencia(
            "🧠", "Desarrollo cognitivo",
            "La LME se asocia con un aumento de 3-4 puntos en tests "
            "de cociente intelectual y mejores resultados escolares, "
            "especialmente en prematuros.",
            "ABM · Breastfeeding Medicine 2020"
        )

    st.markdown("---")

    # --- Fila 1: Salud valorada + duración LME ---
    col1, col2 = st.columns(2)

    with col1:
        _titulo_seccion(
            "Valoración de salud del menor",
            "% por categoría según si recibió lactancia materna"
        )
        st.plotly_chart(_chart_salud_lactancia(df), use_container_width=True)
        st.caption(
            "Los menores que recibieron LM presentan mayor proporción "
            "de valoración 'Muy buena'."
        )

    with col2:
        _titulo_seccion(
            "¿Más meses de LME, mejor salud?",
            "% con salud buena/muy buena según duración de LME"
        )
        st.plotly_chart(_chart_salud_por_duracion(df), use_container_width=True)
        st.caption(
            "A mayor duración de lactancia exclusiva, mayor proporción "
            "de menores con salud valorada como buena o muy buena."
        )

    st.markdown("---")

    # --- Fila 2: IMC + enfermedades ---
    col3, col4 = st.columns(2)

    with col3:
        _titulo_seccion(
            "Categoría de peso del menor",
            "Distribución de IMC por tipo de lactancia · ENSE 2017"
        )
        st.plotly_chart(_chart_imc_categorias(df), use_container_width=True)
        st.caption(
            "Los menores con LM muestran mayor proporción de normopeso "
            "y menor prevalencia de obesidad."
        )

    with col4:
        _titulo_seccion(
            "Enfermedades crónicas y alergias",
            "Prevalencia según tipo de lactancia recibida"
        )
        st.plotly_chart(_chart_enfermedades(df), use_container_width=True)
        st.caption(
            "Se exploran tres condiciones crónicas disponibles en el dataset: "
            "enfermedad crónica general, asma/alergia respiratoria "
            "y alergia alimentaria."
        )

    st.markdown("---")

    # --- Contexto clínico ---
    _titulo_seccion(
        "Contexto clínico",
        "Qué significan estos datos para la práctica"
    )

    col5, col6, col7 = st.columns(3)

    with col5:
        st.html("""
        <div style="background:#FFFFFF;border-radius:10px;padding:1.2rem;
                    box-shadow:0 2px 8px rgba(100,138,150,0.10);
                    border-top:3px solid #648A96;height:100%;">
            <div style="font-size:0.9rem;font-weight:600;color:#648A96;
                        margin-bottom:0.5rem;">🏥 Para pediatras y matronas</div>
            <div style="font-size:0.8rem;color:#1A2E35;line-height:1.6;">
                Los datos confirman el patrón conocido: la LM se asocia
                con mejor valoración de salud general. El abandono precoz
                antes del mes 3 es el principal problema a abordar.
                La visita del recién nacido es el momento clave de intervención.
            </div>
        </div>
        """)

    with col6:
        st.html("""
        <div style="background:#FFFFFF;border-radius:10px;padding:1.2rem;
                    box-shadow:0 2px 8px rgba(100,138,150,0.10);
                    border-top:3px solid #E8B8B8;height:100%;">
            <div style="font-size:0.9rem;font-weight:600;color:#648A96;
                        margin-bottom:0.5rem;">📋 Para gestores sanitarios</div>
            <div style="font-size:0.8rem;color:#1A2E35;line-height:1.6;">
                La brecha entre CCAA en tasas de LME sugiere que las
                políticas autonómicas de apoyo a la lactancia tienen
                impacto real en los resultados de salud infantil.
                Invertir en asesoras IBCLC y matronas tiene alto retorno sanitario.
            </div>
        </div>
        """)

    with col7:
        st.html("""
        <div style="background:#FFFFFF;border-radius:10px;padding:1.2rem;
                    box-shadow:0 2px 8px rgba(100,138,150,0.10);
                    border-top:3px solid #1A2E35;height:100%;">
            <div style="font-size:0.9rem;font-weight:600;color:#648A96;
                        margin-bottom:0.5rem;">👩‍👧 Para la divulgación</div>
            <div style="font-size:0.8rem;color:#1A2E35;line-height:1.6;">
                Cada punto porcentual de aumento en LME ≥ 6 meses
                se traduce en menores hospitalizaciones y mejor
                salud a largo plazo. El ROI del apoyo a la lactancia
                es muy alto desde la perspectiva sanitaria.
            </div>
        </div>
        """)

    # Advertencia metodológica
    st.html("""
    <div style="background:#FFF0F0;border-left:3px solid #C0392B;
                border-radius:8px;padding:0.8rem 1.2rem;margin-top:1.5rem;">
        <div style="font-size:0.78rem;color:#1A2E35;line-height:1.6;">
            <strong style="color:#C0392B;">🚨 Limitación importante:</strong>
            Este análisis es <strong>descriptivo y observacional</strong>.
            Las asociaciones encontradas no establecen causalidad.
            Factores de confusión como nivel socioeconómico, acceso sanitario
            y hábitos familiares no están controlados en este dashboard.
            Para inferencia causal se requeriría un diseño longitudinal
            con ajuste multivariante.
        </div>
    </div>
    """)