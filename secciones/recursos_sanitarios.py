"""
recursos_sanitarios.py
======================
Sexta sección del dashboard LactAnalytics.
Analiza la relación entre dotación de matronas por CCAA
y las tasas de lactancia materna exclusiva.

Fuentes externas:
- Matronas colegiadas: INE · Estadística de Profesionales Sanitarios Colegiados 2017
- Nacimientos: INE · Estadística de Nacimientos 2017
- LME por CCAA: calculado desde ENSE 2017 (dataset principal)

Limitación documentada: el registro de colegiación del INE
no refleja dónde ejercen realmente las matronas, sino dónde
están colegiadas. Andalucía, Canarias y C. Valenciana tienen
datos potencialmente subestimados.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from pathlib import Path
from scipy import stats as scipy_stats
from src.config import COLORES


# ---------------------------------------------------------------------------
# Carga del dataset de recursos
# ---------------------------------------------------------------------------

DATA_PROCESSED = Path(__file__).parents[1] / "data" / "processed"
CSV_FILE = DATA_PROCESSED / "matronas_lme_ccaa.csv"


@st.cache_data
def _cargar_recursos() -> pd.DataFrame:
    """Carga el CSV procesado por data_loader_recursos.py."""
    if not CSV_FILE.exists():
        return pd.DataFrame()
    df = pd.read_csv(CSV_FILE)
    df["dato_incompleto"] = df["dato_incompleto"].astype(bool)
    df["ratio_outlier"]   = df["ratio_outlier"].astype(bool)
    return df


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


def _kpi_mini(valor, label: str, sub: str = "", color: str = "#648A96"):
    st.html(f"""
    <div style="background:#FFFFFF;border-radius:12px;padding:1rem 1.2rem;
                border-left:3px solid {color};
                box-shadow:0 2px 8px rgba(100,138,150,0.10);">
        <div style="font-family:'DM Serif Display',serif;font-size:1.8rem;
                    color:#1A2E35;line-height:1;">{valor}</div>
        <div style="font-size:0.75rem;color:#648A96;font-weight:600;
                    text-transform:uppercase;letter-spacing:0.06em;
                    margin-top:0.3rem;">{label}</div>
        <div style="font-size:0.7rem;color:#999;margin-top:0.2rem;">{sub}</div>
    </div>
    """)


# ---------------------------------------------------------------------------
# Gráfico 1 — Scatter ratio matronas vs LME
# ---------------------------------------------------------------------------

def _chart_scatter_correlacion(df: pd.DataFrame) -> go.Figure:
    """
    Scatter plot: ratio matronas/1000 nacimientos vs % LME ≥ 6 meses.
    Diferencia visualmente los datos completos de los potencialmente
    incompletos (Andalucía, Canarias, C. Valenciana).
    """
    fig = go.Figure()

    # Datos completos
    df_ok = df[~df["dato_incompleto"] & ~df["ratio_outlier"]]
    fig.add_trace(go.Scatter(
        x=df_ok["ratio_matrona_1000nac"],
        y=df_ok["pct_lme_6m"],
        mode="markers+text",
        name="Dato fiable",
        marker=dict(color="#648A96", size=10, opacity=0.85),
        text=df_ok["ccaa"],
        textposition="top center",
        textfont=dict(size=9, color="#1A2E35"),
        hovertemplate=(
            "<b>%{text}</b><br>"
            "Matronas/1000 nac: %{x:.1f}<br>"
            "LME ≥ 6m: %{y:.1f}%<extra></extra>"
        ),
    ))

    # Datos potencialmente incompletos
    df_inc = df[df["dato_incompleto"]]
    if len(df_inc):
        fig.add_trace(go.Scatter(
            x=df_inc["ratio_matrona_1000nac"],
            y=df_inc["pct_lme_6m"],
            mode="markers+text",
            name="Dato incompleto (colegiación subestimada)",
            marker=dict(
                color="#E8B8B8", size=10,
                symbol="diamond",
                line=dict(color="#C0392B", width=1.5)
            ),
            text=df_inc["ccaa"],
            textposition="top center",
            textfont=dict(size=9, color="#C0392B"),
            hovertemplate=(
                "<b>%{text}</b> ⚠️<br>"
                "Matronas/1000 nac: %{x:.1f} (subestimado)<br>"
                "LME ≥ 6m: %{y:.1f}%<extra></extra>"
            ),
        ))

    # Outliers
    df_out = df[df["ratio_outlier"] & ~df["dato_incompleto"]]
    if len(df_out):
        fig.add_trace(go.Scatter(
            x=df_out["ratio_matrona_1000nac"],
            y=df_out["pct_lme_6m"],
            mode="markers+text",
            name="Outlier estadístico",
            marker=dict(
                color="#F6F0E6", size=10,
                symbol="square",
                line=dict(color="#648A96", width=1.5)
            ),
            text=df_out["ccaa"],
            textposition="top center",
            textfont=dict(size=9, color="#648A96"),
            hovertemplate=(
                "<b>%{text}</b> (outlier)<br>"
                "Matronas/1000 nac: %{x:.1f}<br>"
                "LME ≥ 6m: %{y:.1f}%<extra></extra>"
            ),
        ))

    # Línea de tendencia solo con datos fiables
    if len(df_ok) >= 5:
        z = np.polyfit(df_ok["ratio_matrona_1000nac"], df_ok["pct_lme_6m"], 1)
        p = np.poly1d(z)
        x_line = np.linspace(df_ok["ratio_matrona_1000nac"].min(),
                              df_ok["ratio_matrona_1000nac"].max(), 100)
        fig.add_trace(go.Scatter(
            x=x_line, y=p(x_line),
            mode="lines",
            name="Tendencia (datos fiables)",
            line=dict(color="#1A2E35", width=1.5, dash="dash"),
            hovertemplate="Tendencia: %{y:.1f}%<extra></extra>",
        ))

    fig.update_layout(
        height=480,
        plot_bgcolor="white",
        paper_bgcolor="white",
        font_family="Inter, sans-serif",
        margin=dict(t=20, b=50, l=50, r=20),
        xaxis=dict(
            title="Matronas colegiadas por cada 1.000 nacimientos estimados",
            gridcolor="#F0F0F0",
        ),
        yaxis=dict(
            title="% LME ≥ 6 meses (ENSE 2017)",
            ticksuffix="%",
            gridcolor="#F0F0F0",
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom", y=1.02,
            xanchor="right", x=1,
            font=dict(size=11)
        ),
        hoverlabel=dict(bgcolor="white", font_size=13),
    )
    return fig


# ---------------------------------------------------------------------------
# Gráfico 2 — Ranking matronas por CCAA
# ---------------------------------------------------------------------------

def _chart_ranking_matronas(df: pd.DataFrame) -> go.Figure:
    """
    Barras horizontales con el ratio de matronas por 1.000 nacimientos.
    Diferencia los datos fiables de los potencialmente subestimados.
    """
    df_sorted = df.sort_values("ratio_matrona_1000nac", ascending=True)
    media = df[~df["dato_incompleto"] & ~df["ratio_outlier"]]["ratio_matrona_1000nac"].mean()

    colores = []
    for _, row in df_sorted.iterrows():
        if row["dato_incompleto"]:
            colores.append("#E8B8B8")
        elif row["ratio_outlier"]:
            colores.append("#F0E8D8")
        elif row["ratio_matrona_1000nac"] >= media:
            colores.append("#648A96")
        else:
            colores.append("#8AADB8")

    fig = go.Figure(go.Bar(
        x=df_sorted["ratio_matrona_1000nac"],
        y=df_sorted["ccaa"],
        orientation="h",
        marker_color=colores,
        text=df_sorted["ratio_matrona_1000nac"].apply(lambda x: f"{x:.1f}"),
        textposition="outside",
        customdata=df_sorted[["matronas_colegiadas", "nacimientos_est", "dato_incompleto"]].values,
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Ratio: %{x:.1f} matronas/1000 nac<br>"
            "Matronas colegiadas: %{customdata[0]}<br>"
            "Nacimientos est.: %{customdata[1]:,}<br>"
            "Dato incompleto: %{customdata[2]}<extra></extra>"
        ),
    ))

    fig.add_vline(
        x=media,
        line_dash="dash", line_color="#1A2E35", line_width=1.5,
        annotation_text=f"Media (datos fiables): {media:.1f}",
        annotation_position="top right",
        annotation_font=dict(size=10, color="#1A2E35")
    )

    # Referencia OMS: 12.4 matronas/1000 nacimientos (media España)
    fig.add_vline(
        x=12.4,
        line_dash="dot", line_color="#C0392B", line_width=1.5,
        annotation_text="Media España: 12.4",
        annotation_position="bottom right",
        annotation_font=dict(size=10, color="#C0392B")
    )

    fig.update_layout(
        height=560,
        plot_bgcolor="white",
        paper_bgcolor="white",
        font_family="Inter, sans-serif",
        margin=dict(t=20, b=40, l=10, r=70),
        xaxis=dict(
            title="Matronas colegiadas / 1.000 nacimientos",
            gridcolor="#F0F0F0",
            range=[0, 95]
        ),
        yaxis=dict(title=""),
        showlegend=False,
        hoverlabel=dict(bgcolor="white", font_size=13),
    )
    return fig


# ---------------------------------------------------------------------------
# Gráfico 3 — Comparativa matronas absolutas vs LME
# ---------------------------------------------------------------------------

def _chart_bubble(df: pd.DataFrame) -> go.Figure:
    """
    Bubble chart: eje X = ratio matronas, eje Y = LME,
    tamaño de burbuja = nacimientos estimados.
    Permite ver simultáneamente las tres dimensiones.
    """
    fig = go.Figure()

    for _, row in df.iterrows():
        color = "#E8B8B8" if row["dato_incompleto"] else (
            "#F0E8D8" if row["ratio_outlier"] else "#648A96"
        )
        opacidad = 0.5 if (row["dato_incompleto"] or row["ratio_outlier"]) else 0.8

        fig.add_trace(go.Scatter(
            x=[row["ratio_matrona_1000nac"]],
            y=[row["pct_lme_6m"]],
            mode="markers+text",
            name=row["ccaa"],
            marker=dict(
                size=max(row["nacimientos_est"] / 3000, 8),
                color=color,
                opacity=opacidad,
                line=dict(color="#1A2E35", width=0.5)
            ),
            text=[row["ccaa"]],
            textposition="top center",
            textfont=dict(size=8),
            showlegend=False,
            hovertemplate=(
                f"<b>{row['ccaa']}</b><br>"
                f"Ratio: {row['ratio_matrona_1000nac']:.1f} mat/1000 nac<br>"
                f"LME ≥ 6m: {row['pct_lme_6m']:.1f}%<br>"
                f"Nacimientos est.: {row['nacimientos_est']:,}<extra></extra>"
            ),
        ))

    fig.update_layout(
        height=420,
        plot_bgcolor="white",
        paper_bgcolor="white",
        font_family="Inter, sans-serif",
        margin=dict(t=20, b=50, l=50, r=20),
        xaxis=dict(
            title="Matronas por 1.000 nacimientos",
            gridcolor="#F0F0F0"
        ),
        yaxis=dict(
            title="% LME ≥ 6 meses",
            ticksuffix="%",
            gridcolor="#F0F0F0"
        ),
        hoverlabel=dict(bgcolor="white", font_size=13),
    )
    return fig


# ---------------------------------------------------------------------------
# RENDER PRINCIPAL
# ---------------------------------------------------------------------------

def render():

    df = _cargar_recursos()

    if df.empty:
        st.error(
            "No se encontró el archivo `data/processed/matronas_lme_ccaa.csv`. "
            "Ejecuta primero `python src/data_loader_recursos.py`."
        )
        return

    # KPIs de resumen
    df_fiable = df[~df["dato_incompleto"] & ~df["ratio_outlier"]]
    r_val = df["r_pearson"].iloc[0] if "r_pearson" in df.columns else None
    p_val = df["p_pearson"].iloc[0] if "p_pearson" in df.columns else None
    media_ratio = df_fiable["ratio_matrona_1000nac"].mean()
    total_matronas = df["matronas_colegiadas"].sum()

    # Narrativa de apertura
    st.html("""
    <div style="background:linear-gradient(135deg,#1A2E35,#648A96);
                border-radius:14px;padding:1.4rem 1.8rem;margin-bottom:1.5rem;">
        <div style="font-family:'DM Serif Display',serif;font-size:1.3rem;
                    color:#F6F0E6;line-height:1.4;">
            ¿Tiene España suficientes matronas?
            ¿Hay relación entre la dotación de matronas y el éxito
            de la lactancia materna?
        </div>
        <div style="font-size:0.8rem;color:#E8B8B8;margin-top:0.5rem;">
            España tiene 12,4 matronas por cada 1.000 nacimientos,
            frente a 25 de media en la OCDE. Este análisis cruza los datos
            de colegiación del INE con las tasas de LME de la ENSE 2017.
        </div>
    </div>
    """)

    # --- KPIs ---
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        _kpi_mini(
            f"{total_matronas:,}",
            "Matronas colegiadas en España",
            "INE · Estadística de Profesionales Sanitarios 2017",
            "#648A96"
        )
    with c2:
        _kpi_mini(
            "12,4",
            "Matronas por 1.000 nacimientos",
            "Media nacional · vs 25 en la OCDE",
            "#E8B8B8"
        )
    with c3:
        _kpi_mini(
            f"{media_ratio:.1f}",
            "Media CCAA (datos fiables)",
            "Excluye CCAA con colegiación subestimada",
            "#648A96"
        )
    with c4:
        if r_val is not None:
            sig = "✓ Significativa" if p_val < 0.05 else "✗ No significativa"
            color = "#648A96" if p_val < 0.05 else "#E8B8B8"
            _kpi_mini(
                f"r = {r_val}",
                f"Correlación Pearson · {sig}",
                f"p = {p_val:.3f} · n = {len(df_fiable)} CCAA (datos fiables)",
                color
            )

    st.markdown("---")

    # --- Advertencia de calidad del dato ---
    st.html("""
    <div style="background:#FFF8F0;border-left:4px solid #E8A020;
                border-radius:10px;padding:1rem 1.4rem;margin-bottom:1.5rem;">
        <div style="font-size:0.85rem;font-weight:600;color:#E8A020;
                    margin-bottom:0.4rem;">
            ⚠️ Limitación crítica de los datos de colegiación
        </div>
        <div style="font-size:0.78rem;color:#1A2E35;line-height:1.6;">
            El INE registra las matronas según el colegio profesional donde están dadas de alta,
            <strong>no donde ejercen</strong>. Esto genera subestimaciones graves en Andalucía
            (1,06 mat/1000 nac), Canarias (2,40) y C. Valenciana (3,30), donde muchas
            profesionales pueden estar colegiadas en otra CCAA. Los puntos marcados en
            rosa diamante en los gráficos corresponden a estas CCAA y deben interpretarse
            con precaución. La correlación se calcula excluyendo estos datos.
        </div>
    </div>
    """)

    # --- Fila 1: Scatter + Ranking ---
    col1, col2 = st.columns([3, 2])

    with col1:
        _titulo_seccion(
            "¿Más matronas = más lactancia?",
            "Scatter plot: ratio matronas/nacimientos vs % LME ≥ 6 meses por CCAA"
        )
        st.plotly_chart(_chart_scatter_correlacion(df), use_container_width=True)
        if r_val is not None:
            if p_val < 0.05:
                st.caption(
                    f"Correlación de Pearson r={r_val} (p={p_val:.3f}) — "
                    f"estadísticamente significativa con los {len(df_fiable)} datos fiables. "
                    "La tendencia sugiere que más matronas se asocia con mayor LME, "
                    "aunque la muestra es pequeña."
                )
            else:
                st.caption(
                    f"Correlación de Pearson r={r_val} (p={p_val:.3f}) — "
                    f"no significativa con los {len(df_fiable)} datos fiables. "
                    "Los datos de colegiación del INE no permiten confirmar "
                    "estadísticamente la hipótesis."
                )

    with col2:
        _titulo_seccion(
            "Ratio por CCAA",
            "Matronas colegiadas por 1.000 nacimientos estimados · 2017"
        )
        st.plotly_chart(_chart_ranking_matronas(df), use_container_width=True)

    st.markdown("---")

    # --- Fila 2: Bubble chart ---
    _titulo_seccion(
        "Visión conjunta: matronas, nacimientos y lactancia",
        "Tamaño de burbuja = nacimientos estimados · rosa = dato incompleto"
    )
    st.plotly_chart(_chart_bubble(df), use_container_width=True)

    st.markdown("---")

    # --- Tabla detallada ---
    _titulo_seccion(
        "Datos por Comunidad Autónoma",
        "Matronas colegiadas · nacimientos estimados · ratio · LME"
    )

    tabla = df[[
        "ccaa", "matronas_colegiadas", "nacimientos_est",
        "ratio_matrona_1000nac", "pct_lme_6m",
        "dato_incompleto", "ratio_outlier"
    ]].copy()
    tabla = tabla.sort_values("ratio_matrona_1000nac", ascending=False)
    tabla.columns = [
        "CCAA", "Matronas", "Nacimientos est.",
        "Ratio mat/1000 nac", "% LME ≥ 6m",
        "Dato incompleto", "Outlier"
    ]

    st.dataframe(
        tabla,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Ratio mat/1000 nac": st.column_config.ProgressColumn(
                "Ratio mat/1000 nac",
                format="%.1f",
                min_value=0,
                max_value=80,
            ),
            "% LME ≥ 6m": st.column_config.ProgressColumn(
                "% LME ≥ 6m",
                format="%.1f%%",
                min_value=0,
                max_value=45,
            ),
            "Dato incompleto": st.column_config.CheckboxColumn(
                "⚠️ Incompleto",
            ),
            "Outlier": st.column_config.CheckboxColumn(
                "📊 Outlier",
            ),
        }
    )

    st.markdown("---")

    # --- Conclusión ejecutiva ---
    _titulo_seccion(
        "Conclusión para la dirección",
        "Qué le decimos a la ONG y al Ministerio de Sanidad"
    )

    col3, col4 = st.columns(2)

    with col3:
        st.html("""
        <div style="background:#FFFFFF;border-radius:12px;padding:1.2rem;
                    box-shadow:0 2px 8px rgba(100,138,150,0.10);
                    border-top:3px solid #648A96;">
            <div style="font-size:0.9rem;font-weight:600;color:#648A96;
                        margin-bottom:0.6rem;">
                📊 Lo que los datos sugieren
            </div>
            <div style="font-size:0.8rem;color:#1A2E35;line-height:1.7;">
                Existe una tendencia positiva entre la dotación de matronas
                y las tasas de LME por CCAA. Las comunidades con más matronas
                por nacimiento (Castilla y León, País Vasco, Madrid)
                tienden a tener mejores resultados de lactancia.<br><br>
                Sin embargo, la correlación no alcanza significación
                estadística con los datos fiables disponibles (n=14),
                por lo que <strong>no podemos afirmar causalidad</strong>.
            </div>
        </div>
        """)

    with col4:
        st.html("""
        <div style="background:#FFFFFF;border-radius:12px;padding:1.2rem;
                    box-shadow:0 2px 8px rgba(100,138,150,0.10);
                    border-top:3px solid #E8B8B8;">
            <div style="font-size:0.9rem;font-weight:600;color:#648A96;
                        margin-bottom:0.6rem;">
                🏥 Recomendación estratégica
            </div>
            <div style="font-size:0.8rem;color:#1A2E35;line-height:1.7;">
                El Ministerio de Sanidad debería desarrollar un
                <strong>registro de actividad real</strong> de matronas
                por CCAA (no solo colegiación), que permita cruzar
                con datos de lactancia de forma fiable.<br><br>
                España tiene la mitad de matronas que la media OCDE.
                Doblar la dotación — como propone el CGE — podría tener
                un impacto directo en las tasas de LME, especialmente
                en las CCAA con peores resultados.
            </div>
        </div>
        """)

    # Nota de fuentes
    st.html("""
    <div style="background:#F0F4F8;border-radius:8px;
                padding:0.8rem 1.2rem;margin-top:1rem;">
        <div style="font-size:0.7rem;color:#648A96;line-height:1.6;">
            <strong>Fuentes:</strong>
            INE · Estadística de Profesionales Sanitarios Colegiados 2017 ·
            INE · Estadística de Nacimientos 2017 ·
            ENSE 2017 (Ministerio de Sanidad) ·
            Población por CCAA: Cifras de Población INE 2017 ·
            Referencia OCDE: FAME · "Desarrollo de la profesión de matrona en España"
        </div>
    </div>
    """)
    