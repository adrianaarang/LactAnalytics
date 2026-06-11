"""
data_loader_recursos.py
=======================
Carga y limpieza de datos externos de recursos sanitarios:
  - matronas.xlsx  → matronas colegiadas por CCAA (INE, EPSC 2017)
  - nacimientos.xlsx → tasa de natalidad por CCAA (INE, 2017)

Produce: data/processed/matronas_lme_ccaa.csv
"""

import pandas as pd
import numpy as np
import re
from pathlib import Path
from scipy import stats

DATA_RAW       = Path(__file__).parents[1] / "data" / "raw"
DATA_PROCESSED = Path(__file__).parents[1] / "data" / "processed"

MATRONAS_FILE    = DATA_RAW / "matronas.xlsx"
NACIMIENTOS_FILE = DATA_RAW / "nacimientos.xlsx"
OUTPUT_FILE      = DATA_PROCESSED / "matronas_lme_ccaa.csv"

# ---------------------------------------------------------------------------
# Mapas de normalización
# ---------------------------------------------------------------------------

# Códigos INE de CCAA (2 dígitos) → nombre normalizado del proyecto
CCAA_CODIGOS = {
    '01': 'Andalucía',
    '02': 'Aragón',
    '03': 'Asturias',
    '04': 'Baleares',
    '05': 'Canarias',
    '06': 'Cantabria',
    '07': 'Castilla y León',
    '08': 'Castilla-La Mancha',
    '09': 'Cataluña',
    '10': 'C. Valenciana',
    '11': 'Extremadura',
    '12': 'Galicia',
    '13': 'Madrid',
    '14': 'Murcia',
    '15': 'Navarra',
    '16': 'País Vasco',
    '17': 'La Rioja',
    '18': 'Ceuta',
    '19': 'Melilla',
}

# Nombre en fichero de nacimientos → nombre normalizado
CCAA_NAC_MAP = {
    '01 Andalucía':                     'Andalucía',
    '02 Aragón':                        'Aragón',
    '03 Asturias, Principado de':       'Asturias',
    '04 Balears, Illes':                'Baleares',
    '05 Canarias':                      'Canarias',
    '06 Cantabria':                     'Cantabria',
    '07 Castilla y León':               'Castilla y León',
    '08 Castilla - La Mancha':          'Castilla-La Mancha',
    '09 Cataluña':                      'Cataluña',
    '10 Comunitat Valenciana':          'C. Valenciana',
    '11 Extremadura':                   'Extremadura',
    '12 Galicia':                       'Galicia',
    '13 Madrid, Comunidad de':          'Madrid',
    '14 Murcia, Región de':             'Murcia',
    '15 Navarra, Comunidad Foral de':   'Navarra',
    '16 País Vasco':                    'País Vasco',
    '17 Rioja, La':                     'La Rioja',
    '18 Ceuta':                         'Ceuta',
    '19 Melilla':                       'Melilla',
}

# Población por CCAA 2017 (INE, Cifras de Población)
# Necesaria para convertir tasa de natalidad en nacimientos absolutos
POBLACION_2017 = {
    'Andalucía':          8_379_248,
    'Aragón':             1_308_728,
    'Asturias':           1_022_800,
    'Baleares':           1_115_999,
    'Canarias':           2_127_685,
    'Cantabria':            582_206,
    'Castilla y León':    2_423_441,
    'Castilla-La Mancha': 2_041_631,
    'Cataluña':           7_555_830,
    'C. Valenciana':      4_941_509,
    'Extremadura':        1_087_778,
    'Galicia':            2_701_743,
    'Madrid':             6_466_996,
    'Murcia':             1_475_568,
    'Navarra':              647_554,
    'País Vasco':         2_175_034,
    'La Rioja':             314_487,
    'Ceuta':                 84_202,
    'Melilla':               86_026,
}

# CCAA con dato de colegiación potencialmente incompleto
# (matronas que ejercen en la comunidad pero están colegiadas en otra)
CCAA_DATO_SOSPECHOSO = ['Andalucía', 'Canarias', 'C. Valenciana']


# ---------------------------------------------------------------------------
# Carga y limpieza: matronas
# ---------------------------------------------------------------------------

def _load_matronas(path: Path) -> pd.DataFrame:
    """
    Lee el fichero del INE de profesionales sanitarios colegiados.
    Filtra solo las filas de CCAA (código 01-19), descartando provincias.

    Lógica de filtrado:
    - Las filas de CCAA tienen el patrón "NN NombreCCAA"
      donde NN es un código de 2 dígitos presente en CCAA_CODIGOS.
    - Las filas de provincia tienen códigos de provincia (01-52)
      que NO están en CCAA_CODIGOS.
    """
    df = pd.read_excel(path, header=None)

    matronas = {}
    for _, row in df.iterrows():
        nombre = str(row[0]).strip()
        match = re.match(r'^(\d{2})\s+', nombre)
        if match:
            codigo = match.group(1)
            if codigo in CCAA_CODIGOS:
                try:
                    # Columna 1 = Total (todas situaciones laborales, ambos sexos)
                    total = int(
                        str(row[1])
                        .replace('.', '')   # separador de miles
                        .replace(',', '')
                        .strip()
                    )
                    matronas[CCAA_CODIGOS[codigo]] = total
                except (ValueError, TypeError):
                    pass

    df_out = pd.DataFrame([
        {'ccaa': ccaa, 'matronas_colegiadas': n}
        for ccaa, n in matronas.items()
    ])

    # Marcar CCAA con dato potencialmente subestimado
    df_out['dato_incompleto'] = df_out['ccaa'].isin(CCAA_DATO_SOSPECHOSO)

    return df_out


# ---------------------------------------------------------------------------
# Carga y limpieza: nacimientos
# ---------------------------------------------------------------------------

def _load_nacimientos(path: Path, anio: int = 2017) -> pd.DataFrame:
    """
    Lee el fichero de indicadores de natalidad del INE.
    Extrae la tasa de natalidad para el año indicado y la convierte
    en nacimientos absolutos usando la población de CCAA.

    La tasa de natalidad del INE = nacidos por cada 1.000 habitantes.
    nacimientos_est = tasa × población / 1000
    """
    df = pd.read_excel(path, header=None)

    # Fila 7 contiene los años en las columnas
    anios_fila = df.iloc[7].tolist()

    # Encontrar columna correspondiente al año solicitado
    col_anio = None
    for i, val in enumerate(anios_fila):
        try:
            if int(float(str(val).strip())) == anio:
                col_anio = i
                break
        except (ValueError, TypeError):
            pass

    if col_anio is None:
        raise ValueError(f"Año {anio} no encontrado en el fichero de nacimientos")

    nacimientos = []
    for idx in range(8, len(df)):
        row = df.iloc[idx]
        nombre = str(row[0]).strip()
        if nombre not in CCAA_NAC_MAP:
            continue
        try:
            tasa = float(str(row[col_anio]).replace(',', '.').strip())
            ccaa = CCAA_NAC_MAP[nombre]
            pob  = POBLACION_2017.get(ccaa, np.nan)
            nac  = round(tasa * pob / 1000) if not np.isnan(pob) else np.nan
            nacimientos.append({
                'ccaa':                ccaa,
                'tasa_natalidad':      tasa,
                'poblacion_2017':      pob,
                'nacimientos_est':     int(nac) if not np.isnan(nac) else np.nan,
            })
        except (ValueError, TypeError):
            pass

    return pd.DataFrame(nacimientos)


# ---------------------------------------------------------------------------
# Función principal
# ---------------------------------------------------------------------------

def load_recursos(force_reload: bool = False) -> pd.DataFrame:
    """
    Carga, limpia y fusiona los datos de matronas y nacimientos por CCAA.
    Calcula el ratio de matronas por cada 1.000 nacimientos.

    Si ya existe el CSV procesado lo devuelve directamente (cache).
    """
    if OUTPUT_FILE.exists() and not force_reload:
        return pd.read_csv(OUTPUT_FILE)

    print("Cargando matronas...")
    df_mat = _load_matronas(MATRONAS_FILE)
    print(f"  → {len(df_mat)} CCAA con dato de matronas")

    print("Cargando nacimientos 2017...")
    df_nac = _load_nacimientos(NACIMIENTOS_FILE, anio=2017)
    print(f"  → {len(df_nac)} CCAA con dato de nacimientos")

    # Fusión por CCAA
    df = df_mat.merge(df_nac, on='ccaa', how='inner')
    print(f"  → {len(df)} CCAA tras la fusión")

    # Calcular ratio principal
    df['ratio_matrona_1000nac'] = (
        df['matronas_colegiadas'] / df['nacimientos_est'] * 1000
    ).round(2)

    # Estadísticos de calidad del dato
    df['ratio_zscore'] = (
        (df['ratio_matrona_1000nac'] - df['ratio_matrona_1000nac'].mean())
        / df['ratio_matrona_1000nac'].std()
    ).round(2)

    # Marcar outliers (z > 2): ratios estadísticamente anómalos
    df['ratio_outlier'] = df['ratio_zscore'].abs() > 2

    # Informe de calidad
    print("\nRatio matronas/1000 nacimientos:")
    print(df[['ccaa', 'matronas_colegiadas', 'nacimientos_est',
              'ratio_matrona_1000nac', 'dato_incompleto', 'ratio_outlier']]
          .sort_values('ratio_matrona_1000nac', ascending=False)
          .to_string(index=False))

    # Correlación con LME si hay datos disponibles
    lme_file = DATA_PROCESSED / "lactancia_clean.csv"
    if lme_file.exists():
        df_lme = pd.read_csv(lme_file)
        df_lme['lme_6meses'] = df_lme['lme_6meses'].map(
            {'True': True, 'False': False, True: True, False: False}
        )
        tasa_lme = (
            df_lme[df_lme['lme_6meses'].notna()]
            .groupby('ccaa')['lme_6meses']
            .agg(n='count', n_lme6=lambda x: x.sum())
            .reset_index()
        )
        tasa_lme['pct_lme_6m'] = (tasa_lme['n_lme6'] / tasa_lme['n'] * 100).round(1)
        df = df.merge(tasa_lme[['ccaa', 'pct_lme_6m', 'n']], on='ccaa', how='left')
        df = df.rename(columns={'n': 'n_ense'})

        # Calcular correlación excluyendo outliers y datos incompletos
        df_corr = df[~df['dato_incompleto'] & ~df['ratio_outlier'] & df['pct_lme_6m'].notna()]
        if len(df_corr) >= 5:
            r, p = stats.pearsonr(df_corr['ratio_matrona_1000nac'], df_corr['pct_lme_6m'])
            rs, ps = stats.spearmanr(df_corr['ratio_matrona_1000nac'], df_corr['pct_lme_6m'])
            df['r_pearson']  = round(r, 3)
            df['p_pearson']  = round(p, 3)
            df['r_spearman'] = round(rs, 3)
            df['p_spearman'] = round(ps, 3)
            print(f"\nCorrelación (sin outliers ni datos incompletos, n={len(df_corr)}):")
            print(f"  Pearson:  r={r:.3f}, p={p:.3f}")
            print(f"  Spearman: r={rs:.3f}, p={ps:.3f}")

    # Guardar
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"\nDataset guardado en: {OUTPUT_FILE}")

    return df


# ---------------------------------------------------------------------------
# Ejecución directa para prueba
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    df = load_recursos(force_reload=True)
    print(f"\nShape final: {df.shape}")
    print(df.dtypes)