"""
stats.py
========
Cálculos estadísticos descriptivos y KPIs para el dashboard LactAnalytics.
Fuente de datos: lactancia_clean.csv (generado por data_loader.py)

No contiene lógica de visualización — solo devuelve DataFrames y dicts.
"""

import pandas as pd
import numpy as np
from scipy import stats as scipy_stats
from pathlib import Path

DATA_PROCESSED = Path(__file__).parents[1] / "data" / "processed"
CSV_FILE = DATA_PROCESSED / "lactancia_clean.csv"


# ---------------------------------------------------------------------------
# Carga
# ---------------------------------------------------------------------------

def get_df() -> pd.DataFrame:
    """Carga el dataset limpio."""
    df = pd.read_csv(CSV_FILE)
    # Restaurar booleanos
    for col in ["lactancia_materna", "lactancia_exclusiva", "lactancia_artificial",
                "lme_6meses", "lm_24meses"]:
        if col in df.columns:
            df[col] = df[col].map({"True": True, "False": False, True: True, False: False})
    return df


# ---------------------------------------------------------------------------
# KPIs ejecutivos
# ---------------------------------------------------------------------------

def kpis_nacionales(df: pd.DataFrame) -> dict:
    """
    Devuelve los KPIs principales para las tarjetas del dashboard.
    Todos los porcentajes sobre el total con dato válido.
    """
    total = len(df)

    pct_lm = df["lactancia_materna"].sum() / total * 100
    pct_lme_6m = df["lme_6meses"].sum() / df["lme_6meses"].notna().sum() * 100
    pct_lm_24m = df["lm_24meses"].sum() / df["lm_24meses"].notna().sum() * 100

    media_meses_lm = df["meses_lactancia_total"].mean()
    mediana_meses_lm = df["meses_lactancia_total"].median()
    media_meses_lme = df["meses_lactancia_excl"].mean()

    return {
        "total_menores": total,
        "pct_lactancia_materna": round(pct_lm, 1),
        "pct_lme_6meses": round(pct_lme_6m, 1),
        "pct_lm_24meses": round(pct_lm_24m, 1),
        "media_meses_lm": round(media_meses_lm, 1),
        "mediana_meses_lm": round(mediana_meses_lm, 1),
        "media_meses_lme": round(media_meses_lme, 1),
        # Referencia OMS
        "oms_lme_objetivo": 6,
        "oms_lm_objetivo": 24,
        "brecha_lme_meses": round(6 - media_meses_lme, 1),
        "brecha_lm_meses": round(24 - media_meses_lm, 1),
    }


# ---------------------------------------------------------------------------
# Tendencia central y dispersión por subgrupos
# ---------------------------------------------------------------------------

def stats_por_grupo(df: pd.DataFrame, grupo: str, variable: str) -> pd.DataFrame:
    """
    Calcula media, mediana, desviación típica e IQR de `variable`
    agrupado por `grupo`.

    Ejemplo: stats_por_grupo(df, 'ccaa', 'meses_lactancia_total')
    """
    resultado = (
        df.groupby(grupo)[variable]
        .agg(
            n="count",
            media="mean",
            mediana="median",
            std="std",
            q25=lambda x: x.quantile(0.25),
            q75=lambda x: x.quantile(0.75),
        )
        .reset_index()
    )
    resultado["iqr"] = resultado["q75"] - resultado["q25"]
    resultado["media"] = resultado["media"].round(2)
    resultado["mediana"] = resultado["mediana"].round(2)
    resultado["std"] = resultado["std"].round(2)
    return resultado.sort_values("media", ascending=False)


def tasa_lme_por_grupo(df: pd.DataFrame, grupo: str) -> pd.DataFrame:
    """
    Calcula el % de menores con LME ≥ 6 meses agrupado por `grupo`.
    Solo sobre registros con dato válido en lme_6meses.
    """
    sub = df[df["lme_6meses"].notna()].copy()
    resultado = (
        sub.groupby(grupo)["lme_6meses"]
        .agg(
            n="count",
            n_lme6=lambda x: x.sum(),
        )
        .reset_index()
    )
    resultado["pct_lme_6meses"] = (resultado["n_lme6"] / resultado["n"] * 100).round(1)
    return resultado.sort_values("pct_lme_6meses", ascending=False)


def tasa_lm_24m_por_grupo(df: pd.DataFrame, grupo: str) -> pd.DataFrame:
    """
    Calcula el % de menores con LM ≥ 24 meses agrupado por `grupo`.
    """
    sub = df[df["lm_24meses"].notna()].copy()
    resultado = (
        sub.groupby(grupo)["lm_24meses"]
        .agg(
            n="count",
            n_lm24=lambda x: x.sum(),
        )
        .reset_index()
    )
    resultado["pct_lm_24meses"] = (resultado["n_lm24"] / resultado["n"] * 100).round(1)
    return resultado.sort_values("pct_lm_24meses", ascending=False)


# ---------------------------------------------------------------------------
# Matriz de correlación
# ---------------------------------------------------------------------------

def matriz_correlacion(df: pd.DataFrame) -> pd.DataFrame:
    """
    Correlación de Spearman entre variables numéricas clave.
    Spearman es más robusto que Pearson para variables ordinales como clase_social.
    """
    cols = [
        "meses_lactancia_total",
        "meses_lactancia_excl",
        "clase_social",
        "nivel_educativo_cod",
        "valoracion_salud",
        "imc",
        "edad_menor",
    ]
    cols_existentes = [c for c in cols if c in df.columns]
    corr = df[cols_existentes].corr(method="spearman").round(3)

    # Etiquetas legibles para el heatmap
    etiquetas = {
        "meses_lactancia_total": "Meses LM total",
        "meses_lactancia_excl": "Meses LME",
        "clase_social": "Clase social",
        "nivel_educativo_cod": "Nivel educativo",
        "valoracion_salud": "Valoración salud",
        "imc": "IMC",
        "edad_menor": "Edad menor",
    }
    corr = corr.rename(index=etiquetas, columns=etiquetas)
    return corr


# ---------------------------------------------------------------------------
# Distribución KDE (curvas de densidad)
# ---------------------------------------------------------------------------

def kde_duracion_lactancia(df: pd.DataFrame, variable: str = "meses_lactancia_total",
                            n_points: int = 200) -> pd.DataFrame:
    """
    Calcula la curva KDE de la duración de lactancia.
    Devuelve un DataFrame con columnas x e y para Plotly.
    """
    datos = df[variable].dropna()
    if len(datos) < 10:
        return pd.DataFrame({"x": [], "y": []})

    kde = scipy_stats.gaussian_kde(datos)
    x = np.linspace(datos.min(), datos.max(), n_points)
    y = kde(x)
    return pd.DataFrame({"x": x, "y": y})


def kde_por_grupo(df: pd.DataFrame, grupo: str,
                   variable: str = "meses_lactancia_total",
                   n_points: int = 200) -> pd.DataFrame:
    """
    Calcula curvas KDE separadas por cada categoría de `grupo`.
    Devuelve un DataFrame con columnas x, y y grupo para Plotly.
    """
    resultados = []
    for nombre, subdf in df.groupby(grupo):
        datos = subdf[variable].dropna()
        if len(datos) < 10:
            continue
        kde = scipy_stats.gaussian_kde(datos)
        x = np.linspace(datos.min(), datos.max(), n_points)
        y = kde(x)
        chunk = pd.DataFrame({"x": x, "y": y, grupo: nombre})
        resultados.append(chunk)

    return pd.concat(resultados, ignore_index=True) if resultados else pd.DataFrame()


# ---------------------------------------------------------------------------
# Resumen de nulos (para sección de gobernanza)
# ---------------------------------------------------------------------------

def resumen_nulos(df: pd.DataFrame) -> pd.DataFrame:
    """
    Devuelve un DataFrame con el recuento y porcentaje de nulos
    por variable. Útil para la sección de sesgos del dashboard.
    """
    nulos = df.isnull().sum()
    pct = (nulos / len(df) * 100).round(1)
    resultado = pd.DataFrame({
        "variable": nulos.index,
        "n_nulos": nulos.values,
        "pct_nulos": pct.values
    })
    return resultado[resultado["n_nulos"] > 0].sort_values("pct_nulos", ascending=False)


# ---------------------------------------------------------------------------
# Ejecución directa para prueba
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    df = get_df()
    print(f"Dataset cargado: {df.shape}\n")

    print("=== KPIs nacionales ===")
    kpis = kpis_nacionales(df)
    for k, v in kpis.items():
        print(f"  {k}: {v}")

    print("\n=== LME ≥6m por nivel educativo ===")
    print(tasa_lme_por_grupo(df, "nivel_educativo_grupo").to_string(index=False))

    print("\n=== LME ≥6m por CCAA (top 5) ===")
    print(tasa_lme_por_grupo(df, "ccaa").head(5).to_string(index=False))

    print("\n=== Matriz de correlación ===")
    print(matriz_correlacion(df).to_string())

    print("\n=== Resumen de nulos ===")
    print(resumen_nulos(df).to_string(index=False))