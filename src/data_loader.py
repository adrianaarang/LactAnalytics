"""
data_loader.py
==============
Carga, limpieza y fusión de los ficheros de la ENSE 2017:
  - ense2017_menor_xlsx.xlsx  → variables de lactancia y salud infantil
  - ense2017_hogar_xlsx.xlsx  → variables socioeconómicas del hogar

Fuente: Encuesta Nacional de Salud de España 2017 (INE / Ministerio de Sanidad)
"""

import pandas as pd
import numpy as np
from pathlib import Path

# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------
DATA_RAW = Path(__file__).parents[1] / "data" / "raw"
DATA_PROCESSED = Path(__file__).parents[1] / "data" / "processed"

MENOR_FILE = DATA_RAW / "ense2017_menor_xlsx.xlsx"
HOGAR_FILE = DATA_RAW / "ense2017_hogar_xlsx.xlsx"
OUTPUT_FILE = DATA_PROCESSED / "lactancia_clean.csv"

# ---------------------------------------------------------------------------
# Mapas de recodificación
# ---------------------------------------------------------------------------

CCAA_MAP = {
    1: "Andalucía", 2: "Aragón", 3: "Asturias", 4: "Baleares",
    5: "Canarias", 6: "Cantabria", 7: "Castilla-La Mancha",
    8: "Castilla y León", 9: "Cataluña", 10: "C. Valenciana",
    11: "Extremadura", 12: "Galicia", 13: "Madrid", 14: "Murcia",
    15: "Navarra", 16: "País Vasco", 17: "La Rioja",
    18: "Ceuta", 19: "Melilla"
}

CLASE_MAP = {
    1: "Clase I (directivos/profesionales)",
    2: "Clase II (mandos intermedios)",
    3: "Clase III (trabajadores no manuales)",
    4: "Clase IV (trabajadores manuales cualificados)",
    5: "Clase V (trabajadores manuales no cualificados)",
    6: "Clase VI (trabajadores no cualificados agrarios)",
    9: "No clasificable"
}

EDUC_MAP = {
    1: "Sin estudios",
    2: "Primaria incompleta",
    3: "Primaria",
    4: "Secundaria 1ª etapa",
    5: "Secundaria 2ª etapa",
    6: "FP grado medio",
    7: "FP grado superior",
    8: "Universitaria",
    9: "Posgrado",
    98: "No sabe / No contesta"
}

INGRESOS_MAP = {
    "01": "Menos de 500€",
    "02": "500 – 999€",
    "03": "1.000 – 1.499€",
    "04": "1.500 – 1.999€",
    "05": "2.000 – 2.499€",
    "06": "2.500 – 2.999€",
    "07": "3.000 – 3.999€",
    "08": "4.000 – 4.999€",
    "09": "5.000€ o más"
}


# ---------------------------------------------------------------------------
# Funciones auxiliares
# ---------------------------------------------------------------------------

def _to_numeric_clean(series, invalid=(8, 9, 98, 99)):
    """Convierte a numérico y reemplaza códigos de no respuesta por NaN."""
    s = pd.to_numeric(series, errors="coerce")
    s = s.replace(list(invalid), np.nan)
    return s


def _load_menor(path: Path) -> pd.DataFrame:
    """
    Carga el fichero de menores y selecciona las columnas relevantes.
    Solo conserva menores con el módulo de lactancia respondido (L64 válido).
    """
    df = pd.read_excel(path)

    cols = {
        "IDENTHOGAR": "id_hogar",
        "CCAA": "ccaa_cod",
        "SEXOm": "sexo_menor",
        "EDADm": "edad_menor",
        "L64": "lactancia_materna",
        "L65_1": "meses_lactancia_total",
        "L66": "lactancia_exclusiva",
        "L67_1": "meses_lactancia_excl",
        "L68": "lactancia_artificial",
        "L69_1": "meses_inicio_artificial",
        "B4": "valoracion_salud",
        "B5_1a": "enfermedad_cronica",
        "H33": "peso_kg",
        "H34": "talla_cm",
        "IMCm": "imc",
        "CLASE_PR": "clase_social",
        "FACTORMENOR": "factor_peso"
    }

    cols_existentes = {k: v for k, v in cols.items() if k in df.columns}
    df = df[list(cols_existentes.keys())].rename(columns=cols_existentes)

    numericas = [
        "meses_lactancia_total", "meses_lactancia_excl",
        "meses_inicio_artificial", "peso_kg", "talla_cm", "imc"
    ]
    for col in numericas:
        if col in df.columns:
            df[col] = _to_numeric_clean(df[col])

    for col in ["lactancia_materna", "lactancia_exclusiva", "lactancia_artificial"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").replace({8: np.nan, 9: np.nan})
            df[col] = df[col].map({1: True, 2: False})

    df["sexo_menor"] = df["sexo_menor"].map({1: "Niño", 2: "Niña"})
    df["clase_social"] = _to_numeric_clean(df["clase_social"], invalid=(9,))
    df["clase_social_label"] = df["clase_social"].map(CLASE_MAP)
    df["ccaa_cod"] = pd.to_numeric(df["ccaa_cod"], errors="coerce")
    df["ccaa"] = df["ccaa_cod"].map(CCAA_MAP)

    df = df[df["lactancia_materna"].notna()].copy()

    if "meses_lactancia_excl" in df.columns:
        df["lme_6meses"] = df["meses_lactancia_excl"] >= 6
        df["lm_24meses"] = df["meses_lactancia_total"] >= 24

    return df


def _load_hogar(path: Path) -> pd.DataFrame:
    """
    Carga el fichero de hogar y extrae variables socioeconómicas.
    """
    df = pd.read_excel(path)

    cols = {
        "IDENTHOGAR": "id_hogar",
        "A10": "nivel_educativo_cod",
        "D29": "ingresos_hogar_cod",
        "D27": "fuente_ingresos",
    }

    cols_existentes = {k: v for k, v in cols.items() if k in df.columns}
    df = df[list(cols_existentes.keys())].rename(columns=cols_existentes)

    if "nivel_educativo_cod" in df.columns:
        df["nivel_educativo_cod"] = pd.to_numeric(df["nivel_educativo_cod"], errors="coerce")
        df["nivel_educativo"] = df["nivel_educativo_cod"].map(EDUC_MAP)

        educ_grupo = {
            1: "Básico o menos", 2: "Básico o menos", 3: "Básico o menos",
            4: "Secundaria", 5: "Secundaria",
            6: "FP", 7: "FP",
            8: "Universidad", 9: "Universidad"
        }
        df["nivel_educativo_grupo"] = df["nivel_educativo_cod"].map(educ_grupo)

    if "ingresos_hogar_cod" in df.columns:
        df["ingresos_hogar_cod"] = df["ingresos_hogar_cod"].astype(str).str.zfill(2)
        df["ingresos_hogar"] = df["ingresos_hogar_cod"].map(INGRESOS_MAP)

    df = df.drop_duplicates(subset="id_hogar")

    return df


# ---------------------------------------------------------------------------
# Función principal
# ---------------------------------------------------------------------------

def load_data(force_reload: bool = False) -> pd.DataFrame:
    """
    Carga y devuelve el dataset limpio de lactancia.
    Si ya existe el CSV procesado lo devuelve directamente (cache).
    Usa force_reload=True para regenerar desde los ficheros originales.
    """
    if OUTPUT_FILE.exists() and not force_reload:
        return pd.read_csv(OUTPUT_FILE)

    print("Cargando fichero de menores...")
    df_menor = _load_menor(MENOR_FILE)
    print(f"  → {len(df_menor)} menores con módulo lactancia respondido")

    print("Cargando fichero de hogar...")
    df_hogar = _load_hogar(HOGAR_FILE)
    print(f"  → {len(df_hogar)} hogares")

    print("Fusionando datasets...")
    df = df_menor.merge(df_hogar, on="id_hogar", how="left")
    print(f"  → {len(df)} registros tras la fusión")

    print("\nValores nulos por variable clave:")
    key_cols = [
        "lactancia_materna", "meses_lactancia_total",
        "lactancia_exclusiva", "meses_lactancia_excl",
        "ccaa", "clase_social", "nivel_educativo_grupo", "ingresos_hogar"
    ]
    for col in key_cols:
        if col in df.columns:
            n = df[col].isna().sum()
            pct = n / len(df) * 100
            print(f"  {col}: {n} nulos ({pct:.1f}%)")

    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"\nDataset limpio guardado en: {OUTPUT_FILE}")

    return df


# ---------------------------------------------------------------------------
# Ejec'ución directa para prueba
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    df = load_data(force_reload=True)
    print(f"\nDataset final: {df.shape[0]} filas × {df.shape[1]} columnas")
    print(df.head())