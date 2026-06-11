"""
app.py
======
Punto de entrada del dashboard LactAnalytics.
Configura la página, aplica estilos globales y orquesta
el sidebar de filtros, el header, los KPIs y las secciones.
"""

import streamlit as st
import pandas as pd
import base64
from pathlib import Path
from src.data_loader import load_data
from src.stats import kpis_nacionales
from src.config import COLORES

# ---------------------------------------------------------------------------
# CONFIGURACIÓN DE PÁGINA
# Debe ser la primera llamada a Streamlit en el script.
# layout="wide" aprovecha todo el ancho de la pantalla.
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="LactAnalytics · Lactancia en España",
    page_icon="🤱",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# LOGO EN BASE64
# ---------------------------------------------------------------------------
def get_logo_b64() -> str:
    logo_path = Path(__file__).parent / "logo.jpg"
    if logo_path.exists():
        with open(logo_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

LOGO_B64 = get_logo_b64()

# ---------------------------------------------------------------------------
# CSS GLOBAL
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=Inter:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background-color: #F6F0E6;
}

section[data-testid="stSidebar"] {
    background-color: #1A2E35 !important;
}
section[data-testid="stSidebar"] * {
    color: #F6F0E6 !important;
}
section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stMultiSelect label {
    color: #E8B8B8 !important;
    font-size: 0.78rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
section[data-testid="stSidebar"] hr {
    border-color: #648A96 !important;
    opacity: 0.4;
}
section[data-testid="stSidebar"] span[data-baseweb="tag"] {
    background-color: #648A96 !important;
    border-color: #648A96 !important;
}
section[data-testid="stSidebar"] span[data-baseweb="tag"] span {
    color: #F6F0E6 !important;
}

.main .block-container {
    padding-top: 0rem;
    padding-left: 2rem;
    padding-right: 2rem;
    max-width: 1400px;
}

#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }
header    { visibility: hidden; }

::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #F6F0E6; }
::-webkit-scrollbar-thumb { background: #648A96; border-radius: 3px; }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# HEADER
# ---------------------------------------------------------------------------
def render_header(kpis: dict):
    logo_path = Path(__file__).parent / "logo.jpg"

    st.html("""
    <div style="
        background: linear-gradient(135deg, #1A2E35 0%, #648A96 100%);
        border-radius: 0 0 24px 24px;
        height: 100px;
        margin: -1rem -2rem 0 -2rem;
        position: relative;
        overflow: hidden;
    ">
        <svg style="position:absolute;bottom:0;right:0;opacity:0.07"
             width="340" height="80" viewBox="0 0 340 80" fill="none">
            <path d="M0 40 C40 10,80 70,120 40 S200 10,240 40 S300 70,340 40 L340 80 L0 80 Z"
                  fill="#E8B8B8"/>
        </svg>
    </div>
    """)

    col_logo, col_titulo, col_kpi = st.columns([1, 7, 2])

    with col_logo:
        if logo_path.exists():
            st.image(str(logo_path), width=80)

    with col_titulo:
        st.html("""
        <div style="padding-top:0.2rem;">
            <div style="font-family:'DM Serif Display',serif;font-size:1.85rem;
                        color:#1A2E35;line-height:1.1;">LactAnalytics</div>
            <div style="font-size:0.75rem;color:#648A96;font-weight:500;
                        letter-spacing:0.09em;text-transform:uppercase;margin-top:0.25rem;">
                Lactancia materna en España · ENSE 2017 · Ministerio de Sanidad
            </div>
        </div>
        """)

    with col_kpi:
        st.html(f"""
        <div style="text-align:right;padding-top:0.2rem;">
            <div style="font-family:'DM Serif Display',serif;font-size:2.1rem;
                        color:#E8B8B8;line-height:1;">{kpis['pct_lme_6meses']}%</div>
            <div style="font-size:0.68rem;color:#648A96;
                        text-transform:uppercase;letter-spacing:0.06em;line-height:1.4;">
                alcanzan LME ≥ 6 meses<br>
                <span style="color:#C0392B;font-weight:600;">OMS recomienda: 100%</span>
            </div>
        </div>
        """)

    st.html("""
    <div style="height:3px;
                background:linear-gradient(90deg,#1A2E35,#648A96,#E8B8B8);
                border-radius:2px;margin-bottom:1.5rem;margin-top:0.3rem;">
    </div>
    """)


# ---------------------------------------------------------------------------
# FOOTER
# ---------------------------------------------------------------------------
def render_footer():
    st.html("""
    <div style="
        margin-top: 3rem;
        padding: 1.2rem 2rem;
        background: #1A2E35;
        border-radius: 14px 14px 0 0;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 0.6rem;
    ">
        <div style="font-size:0.72rem;color:#648A96;line-height:1.6;">
            <strong style="color:#E8B8B8;">Fuente de datos:</strong>
            Encuesta Nacional de Salud de España 2017 (ENSE) ·
            Ministerio de Sanidad / INE<br>
            <strong style="color:#E8B8B8;">Licencia:</strong>
            Reutilización con atribución · CC BY 4.0
        </div>
        <div style="font-size:0.72rem;color:#648A96;text-align:right;line-height:1.6;">
            <strong style="color:#E8B8B8;">LactAnalytics</strong> ·
            Módulo II · Análisis y Visualización de Datos<br>
            Bootcamp IA &amp; Big Data · F5 · 2025
        </div>
    </div>
    """)


# ---------------------------------------------------------------------------
# CARGA DE DATOS
# ---------------------------------------------------------------------------
@st.cache_data
def cargar_datos():
    return load_data()


# ---------------------------------------------------------------------------
# SIDEBAR — FILTROS GLOBALES
# ---------------------------------------------------------------------------
def render_sidebar(df: pd.DataFrame) -> pd.DataFrame:
    with st.sidebar:

        st.html("""
        <div style="padding: 1rem 0 0.5rem 0;">
            <div style="font-family:'DM Serif Display',serif;font-size:1.2rem;
                        color:#F6F0E6;">Filtros</div>
            <div style="font-size:0.7rem;color:#648A96;margin-top:0.1rem;">
                Todos los gráficos se actualizan en tiempo real
            </div>
        </div>
        """)

        st.markdown("---")

        ccaas = sorted(df["ccaa"].dropna().unique().tolist())
        sel_ccaa = st.multiselect(
            "Comunidad Autónoma",
            options=ccaas,
            default=ccaas,
            key="filtro_ccaa"
        )

        st.markdown("---")

        niveles = ["Básico o menos", "Secundaria", "FP", "Universidad"]
        niveles_disp = [n for n in niveles if n in df["nivel_educativo_grupo"].values]
        sel_educ = st.multiselect(
            "Nivel educativo",
            options=niveles_disp,
            default=niveles_disp,
            key="filtro_educ"
        )

        st.markdown("---")

        edad_min, edad_max = int(df["edad_menor"].min()), int(df["edad_menor"].max())
        sel_edad = st.slider(
            "Edad del menor (años)",
            min_value=edad_min,
            max_value=edad_max,
            value=(edad_min, edad_max),
            key="filtro_edad"
        )

        st.markdown("---")

        sel_sexo = st.multiselect(
            "Sexo del menor",
            options=["Niño", "Niña"],
            default=["Niño", "Niña"],
            key="filtro_sexo"
        )

        st.markdown("---")

        df_f = df[
            df["ccaa"].isin(sel_ccaa) &
            df["nivel_educativo_grupo"].isin(sel_educ) &
            df["edad_menor"].between(*sel_edad) &
            df["sexo_menor"].isin(sel_sexo)
        ]

        st.html(f"""
        <div style="background:#0D1F25;border-radius:8px;
                    padding:0.8rem 1rem;margin-top:0.5rem;">
            <div style="font-size:1.3rem;font-family:'DM Serif Display',serif;
                        color:#E8B8B8;">{len(df_f):,}</div>
            <div style="font-size:0.68rem;color:#648A96;text-transform:uppercase;
                        letter-spacing:0.06em;">menores en la selección</div>
        </div>
        """)

    return df_f


# ---------------------------------------------------------------------------
# TARJETAS KPI
# ---------------------------------------------------------------------------
def render_kpis(kpis: dict):
    st.markdown("### Indicadores nacionales")

    c1, c2, c3, c4, c5 = st.columns(5)

    colores_borde = {
        "normal":  "#648A96",
        "alerta":  "#E8B8B8",
        "critico": "#C0392B"
    }

    tarjetas = [
        (c1, kpis["pct_lactancia_materna"], "%",
         "Recibieron lactancia materna",
         f"Media: {kpis['media_meses_lm']} meses",
         "OMS: promover inicio universal", "normal"),
        (c2, kpis["pct_lme_6meses"], "%",
         "LME ≥ 6 meses",
         f"Media LME: {kpis['media_meses_lme']} meses",
         f"OMS: 100% · Brecha: -{kpis['brecha_lme_meses']} m", "alerta"),
        (c3, kpis["pct_lm_24meses"], "%",
         "LM ≥ 24 meses",
         f"Mediana LM: {kpis['mediana_meses_lm']} meses",
         f"OMS: 100% · Brecha: -{kpis['brecha_lm_meses']} m", "critico"),
        (c4, kpis["media_meses_lm"], " m",
         "Duración media LM",
         f"Mediana: {kpis['mediana_meses_lm']} meses",
         "OMS mínimo: 6 meses", "alerta"),
        (c5, kpis["total_menores"], "",
         "Menores en la muestra",
         "ENSE 2017 · menores 0-4 años",
         "Representativa a nivel nacional", "normal"),
    ]

    for col, valor, sufijo, label, sub, oms, tipo in tarjetas:
        borde = colores_borde.get(tipo, "#648A96")
        with col:
            st.html(f"""
            <div style="background:#FFFFFF;border-radius:14px;padding:1.4rem 1.6rem;
                        border-left:4px solid {borde};
                        box-shadow:0 2px 12px rgba(100,138,150,0.10);
                        margin-bottom:0.5rem;">
                <div style="font-family:'DM Serif Display',serif;font-size:2.4rem;
                            color:#1A2E35;line-height:1;margin:0;">
                    {valor}{sufijo}
                </div>
                <div style="font-size:0.78rem;color:#648A96;font-weight:600;
                            text-transform:uppercase;letter-spacing:0.07em;
                            margin-top:0.3rem;">
                    {label}
                </div>
                <div style="font-size:0.72rem;color:#999;margin-top:0.2rem;">
                    {sub}
                </div>
                <div style="font-size:0.72rem;color:#E8B8B8;font-weight:600;
                            margin-top:0.4rem;">
                    {oms}
                </div>
            </div>
            """)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    df_total = cargar_datos()
    df = render_sidebar(df_total)
    kpis = kpis_nacionales(df)

    render_header(kpis)
    render_kpis(kpis)

    st.markdown("<br>", unsafe_allow_html=True)

    # Navegación por secciones mediante tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Resumen ejecutivo",
        "🎓 Factores condicionantes",
        "👶 Salud infantil",
        "🗺️ Mapa por CCAA",
        "⚠️ Sesgos y gobernanza",
        "🏥 Recursos sanitarios",
    ])

    with tab1:
        from secciones import resumen_ejecutivo
        resumen_ejecutivo.render(df, kpis)

    with tab2:
        from secciones import factores_condicionantes
        factores_condicionantes.render(df)

    with tab3:
        from secciones import salud_infantil
        salud_infantil.render(df)

    with tab4:
        from secciones import mapa_ccaa
        mapa_ccaa.render(df)

    with tab5:
        from secciones import sesgos_gobernanza
        sesgos_gobernanza.render(df)

    with tab6:
        from secciones import recursos_sanitarios
        recursos_sanitarios.render()

    render_footer()


if __name__ == "__main__":
    main()